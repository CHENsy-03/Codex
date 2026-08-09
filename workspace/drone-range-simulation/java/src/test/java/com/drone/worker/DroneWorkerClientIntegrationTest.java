package com.drone.worker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

/**
 * 真实 Python Worker（worker_main.py / app.worker_protocol / app.worker_engine /
 * app.headless_core）集成测试。测试地图与生成脚本均由测试在临时目录动态生成。
 */
class DroneWorkerClientIntegrationTest {

    private static final String PYTHON = System.getProperty("drone.python.executable");
    private static final Path PROJECT_ROOT = Path.of("").toAbsolutePath().getParent();

    private static final String GENERATOR = """
            import json, os, sys
            import numpy as np
            import rasterio
            from pyproj import Transformer
            from rasterio.transform import Affine

            out_dir = sys.argv[1]
            os.makedirs(out_dir, exist_ok=True)
            transform = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)
            data = np.zeros((3, 12, 16), dtype=np.uint8)
            path = os.path.join(out_dir, "map.tif")
            with rasterio.open(path, "w", driver="GTiff", width=16, height=12, count=3, dtype="uint8", crs="EPSG:3857", transform=transform) as dst:
                dst.write(data)
            tr = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
            def wgs(col, row):
                x = transform.a * col + transform.b * row + transform.c
                y = transform.d * col + transform.e * row + transform.f
                return tr.transform(x, y, errcheck=True)
            a_lon, a_lat = wgs(2.0, 3.0)
            b_lon, b_lat = wgs(14.0, 11.0)
            with open(os.path.join(out_dir, "points.json"), "w", encoding="utf-8") as f:
                json.dump({"a": {"longitude": a_lon, "latitude": a_lat}, "b": {"longitude": b_lon, "latitude": b_lat}}, f)
            print(path)
            """;

    @TempDir
    Path tmp;

    private Path generateMap() throws Exception {
        java.util.Objects.requireNonNull(PYTHON, "缺少系统属性 drone.python.executable");
        Path dir = tmp.resolve("地图 数据 test");
        Files.createDirectories(dir);
        Path gen = tmp.resolve("gen_map.py");
        Files.writeString(gen, GENERATOR, StandardCharsets.UTF_8);
        Process p = new ProcessBuilder(PYTHON, "-u", gen.toString(), dir.toString())
                .redirectErrorStream(true).start();
        assertTrue(p.waitFor(120, TimeUnit.SECONDS), "生成脚本超时");
        assertEquals(0, p.exitValue(), "生成脚本失败");
        assertTrue(Files.exists(dir.resolve("map.tif")));
        assertTrue(Files.exists(dir.resolve("points.json")));
        return dir;
    }

    @Test
    void realWorkerEndToEnd() throws Exception {
        Path dir = generateMap();
        Path tif = dir.resolve("map.tif");
        JsonNode points = new ObjectMapper().readTree(dir.resolve("points.json").toFile());

        WorkerCommandLine cl = WorkerCommandLine.forPythonWorker(Path.of(PYTHON), PROJECT_ROOT);
        try (DroneWorkerClient client = new DroneWorkerClient(cl, WorkerTimeouts.defaults())) {
            WorkerResults.HelloResult hello = client.start();
            assertEquals(1, hello.protocolVersion());
            assertEquals("READY", hello.state());
            long pid = client.pid();

            WorkerResults.LoadMapResult loaded = client.loadMap(tif);
            assertEquals("MAP_LOADED", loaded.state());
            assertEquals("EPSG:3857", loaded.crs());
            assertEquals(16, loaded.width());
            assertEquals(12, loaded.height());
            assertEquals(3, loaded.bands());

            WorkerResults.CalculationResult c1 = client.calculate(
                    new WorkerPoint.Pixel(2.0, 3.0), new WorkerPoint.Pixel(14.0, 11.0), 10.0);
            assertTrue(c1.distanceMeters() > 0);
            assertEquals(c1.distanceMeters() / 10.0, c1.exactSeconds(), 1e-9);
            assertEquals((long) Math.ceil(c1.exactSeconds()), c1.roundedSeconds());
            assertTrue(c1.duration().matches("\\d{2}:\\d{2}:\\d{2}"));
            assertEquals(c1.roundedSeconds(), hmsToSeconds(c1.duration()));

            double aLon = points.path("a").path("longitude").asDouble();
            double aLat = points.path("a").path("latitude").asDouble();
            double bLon = points.path("b").path("longitude").asDouble();
            double bLat = points.path("b").path("latitude").asDouble();

            // WGS84 calculate 与 pixel 同物理点结果一致
            WorkerResults.CalculationResult c2 = client.calculate(
                    new WorkerPoint.Wgs84(aLon, aLat), new WorkerPoint.Wgs84(bLon, bLat), 10.0);
            assertEquals(c1.distanceMeters(), c2.distanceMeters(), 1e-6);

            // 混合坐标类型 calculate
            WorkerResults.CalculationResult c3 = client.calculate(
                    new WorkerPoint.Pixel(2.0, 3.0), new WorkerPoint.Wgs84(bLon, bLat), 10.0);
            assertEquals(c1.distanceMeters(), c3.distanceMeters(), 1e-6);

            // E_SPEED_INVALID -> WorkerBusinessException；同一进程继续可用
            try {
                client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 0.0);
                fail("应抛出 WorkerBusinessException");
            } catch (WorkerBusinessException e) {
                assertEquals("E_SPEED_INVALID", e.code());
            }
            assertEquals(pid, client.pid());
            WorkerResults.CalculationResult c4 = client.calculate(
                    new WorkerPoint.Pixel(2.0, 3.0), new WorkerPoint.Pixel(14.0, 11.0), 10.0);
            assertTrue(c4.distanceMeters() > 0);

            // 失败 load_map 不破坏已加载地图
            Path bad = dir.resolve("bad.tif");
            Files.write(bad, new byte[]{1, 2, 3});
            try {
                client.loadMap(bad);
                fail("应抛出 WorkerBusinessException");
            } catch (WorkerBusinessException e) {
                assertEquals("E_MAP_OPEN_FAILED", e.code());
            }
            WorkerResults.CalculationResult c5 = client.calculate(
                    new WorkerPoint.Pixel(2.0, 3.0), new WorkerPoint.Pixel(14.0, 11.0), 10.0);
            assertEquals(c1.distanceMeters(), c5.distanceMeters(), 1e-9);

            // 连续 20 次请求无串线
            for (int i = 0; i < 20; i++) {
                WorkerResults.CalculationResult r = client.calculate(
                        new WorkerPoint.Pixel(2.0, 3.0), new WorkerPoint.Pixel(14.0, 11.0), 10.0);
                assertEquals(c1.distanceMeters(), r.distanceMeters(), 1e-9);
            }

            client.shutdown();
            assertEquals(0, client.lastExitCode().intValue());
            assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false));
        }
        // try-with-resources 结束后不得残留 Worker
    }

    private static int hmsToSeconds(String hms) {
        String[] parts = hms.split(":");
        return Integer.parseInt(parts[0]) * 3600 + Integer.parseInt(parts[1]) * 60
                + Integer.parseInt(parts[2]);
    }
}
