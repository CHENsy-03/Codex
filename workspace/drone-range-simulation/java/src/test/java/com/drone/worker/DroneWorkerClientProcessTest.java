package com.drone.worker;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.fail;

/**
 * 使用 @TempDir 动态生成的受控 Python 脚本测试客户端进程行为；
 * 不提交任何 fixture 脚本。
 */
class DroneWorkerClientProcessTest {

    private static final String PYTHON = System.getProperty("drone.python.executable");

    private final List<Long> pids = new ArrayList<>();

    @TempDir
    Path tmp;

    @AfterEach
    void noResidualProcesses() {
        for (Long pid : pids) {
            assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false),
                    "残留进程 PID=" + pid);
        }
        pids.clear();
    }

    private Path writeScript(String name, String content) throws IOException {
        Path p = tmp.resolve(name);
        Files.writeString(p, content, StandardCharsets.UTF_8);
        return p;
    }

    private DroneWorkerClient clientFor(Path script, WorkerTimeouts timeouts,
                                        Consumer<String> stderr, Map<String, String> extraEnv) {
        java.util.Objects.requireNonNull(PYTHON, "缺少系统属性 drone.python.executable");
        Map<String, String> env = new LinkedHashMap<>();
        env.put("PYTHONUTF8", "1");
        env.put("PYTHONIOENCODING", "utf-8");
        if (extraEnv != null) {
            env.putAll(extraEnv);
        }
        WorkerCommandLine cl = new WorkerCommandLine(
                List.of(PYTHON, "-u", script.toString()), script.getParent(), env);
        return new DroneWorkerClient(cl, timeouts, stderr);
    }

    private DroneWorkerClient startClient(Path script, WorkerTimeouts timeouts,
                                          Consumer<String> stderr) throws Exception {
        return startClient(script, timeouts, stderr, null);
    }

    private DroneWorkerClient startClient(Path script, WorkerTimeouts timeouts,
                                          Consumer<String> stderr, Map<String, String> extraEnv)
            throws Exception {
        DroneWorkerClient client = clientFor(script, timeouts, stderr, extraEnv);
        client.start();
        pids.add(client.pid());
        return client;
    }

    private static WorkerTimeouts normal() {
        return new WorkerTimeouts(Duration.ofSeconds(3), Duration.ofSeconds(5),
                Duration.ofSeconds(5), Duration.ofSeconds(2), Duration.ofSeconds(1),
                Duration.ofSeconds(2));
    }

    private static WorkerTimeouts fastCalculate() {
        return new WorkerTimeouts(Duration.ofSeconds(3), Duration.ofSeconds(5),
                Duration.ofMillis(500), Duration.ofSeconds(2), Duration.ofSeconds(1),
                Duration.ofSeconds(2));
    }

    private static final String RESIDENT = """
            import sys, json, os

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            count_file = os.environ.get("COUNT_FILE")
            count = 0
            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    req = json.loads(raw)
                except Exception:
                    send({"id": None, "success": False, "error": {"code": "E_PROTOCOL_INVALID_JSON", "message": "bad"}})
                    continue
                rid = req.get("id")
                op = req.get("operation")
                count += 1
                if count_file:
                    with open(count_file, "a", encoding="utf-8") as f:
                        f.write(str(count) + "\\n")
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                elif op == "load_map":
                    send({"id": rid, "success": True, "data": {"state": "MAP_LOADED", "crs": "EPSG:3857", "width": 16, "height": 12, "bands": 3}})
                elif op == "calculate":
                    send({"id": rid, "success": True, "data": {"pointA": {"longitude": 1.0, "latitude": 2.0}, "pointB": {"longitude": 3.0, "latitude": 4.0}, "distanceMeters": 123.456, "exactSeconds": 12.3456, "roundedSeconds": 13, "duration": "00:00:13"}})
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
                else:
                    send({"id": rid, "success": False, "error": {"code": "E_OPERATION_UNKNOWN", "message": "unknown"}})
            """;

    private static final String BUSINESS_ERROR = """
            import sys, json

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                req = json.loads(raw)
                rid = req.get("id")
                op = req.get("operation")
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                elif op == "load_map":
                    send({"id": rid, "success": True, "data": {"state": "MAP_LOADED", "crs": "EPSG:3857", "width": 16, "height": 12, "bands": 3}})
                elif op == "calculate":
                    send({"id": rid, "success": False, "error": {"code": "E_SPEED_INVALID", "message": "bad speed"}})
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
            """;

    private static final String STDERR_SPAM = """
            import sys, json

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            def err(line):
                sys.stderr.write(line + "\\n")
                sys.stderr.flush()

            for i in range(3000):
                err("stderr line " + str(i))

            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                req = json.loads(raw)
                rid = req.get("id")
                op = req.get("operation")
                err('{"id":"fake","success":true,"data":{}}')
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                elif op == "load_map":
                    send({"id": rid, "success": True, "data": {"state": "MAP_LOADED", "crs": "EPSG:3857", "width": 16, "height": 12, "bands": 3}})
                elif op == "calculate":
                    send({"id": rid, "success": True, "data": {"pointA": {"longitude": 1.0, "latitude": 2.0}, "pointB": {"longitude": 3.0, "latitude": 4.0}, "distanceMeters": 123.456, "exactSeconds": 12.3456, "roundedSeconds": 13, "duration": "00:00:13"}})
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
            """;

    private static final String GARBAGE_STDOUT = """
            import sys, json

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                req = json.loads(raw)
                rid = req.get("id")
                op = req.get("operation")
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                elif op == "load_map":
                    send({"id": rid, "success": True, "data": {"state": "MAP_LOADED", "crs": "EPSG:3857", "width": 16, "height": 12, "bands": 3}})
                elif op == "calculate":
                    sys.stdout.write("not-json\\n")
                    sys.stdout.flush()
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
            """;

    private static final String WRONG_ID = """
            import sys, json

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                req = json.loads(raw)
                rid = req.get("id")
                op = req.get("operation")
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                elif op == "load_map":
                    send({"id": rid, "success": True, "data": {"state": "MAP_LOADED", "crs": "EPSG:3857", "width": 16, "height": 12, "bands": 3}})
                elif op == "calculate":
                    send({"id": "wrong", "success": True, "data": {}})
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
            """;

    private static final String SLOW_CALC = """
            import sys, json, time

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                req = json.loads(raw)
                rid = req.get("id")
                op = req.get("operation")
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                elif op == "load_map":
                    send({"id": rid, "success": True, "data": {"state": "MAP_LOADED", "crs": "EPSG:3857", "width": 16, "height": 12, "bands": 3}})
                elif op == "calculate":
                    time.sleep(30)
                    send({"id": rid, "success": True, "data": {"pointA": {"longitude": 1.0, "latitude": 2.0}, "pointB": {"longitude": 3.0, "latitude": 4.0}, "distanceMeters": 123.456, "exactSeconds": 12.3456, "roundedSeconds": 13, "duration": "00:00:13"}})
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
            """;

    private static final String EXIT_AFTER_HELLO = """
            import sys, json

            def send(obj):
                sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\\n")
                sys.stdout.flush()

            for raw in sys.stdin:
                raw = raw.strip()
                if not raw:
                    continue
                req = json.loads(raw)
                rid = req.get("id")
                op = req.get("operation")
                if op == "hello":
                    send({"id": rid, "success": True, "data": {"protocolVersion": 1, "engineVersion": "1.0.0", "state": "READY", "coordinateTypes": ["wgs84", "map_crs", "pixel"]}})
                    sys.exit(3)
                elif op == "shutdown":
                    send({"id": rid, "success": True, "data": {"state": "TERMINATING"}})
                    sys.exit(0)
            """;

    @Test
    void residentProcessMultipleRequestsNoCrossTalk() throws Exception {
        DroneWorkerClient client = startClient(writeScript("resident.py", RESIDENT), normal(), line -> {
        });
        for (int i = 0; i < 10; i++) {
            WorkerResults.HelloResult h = client.hello();
            assertEquals("READY", h.state());
        }
        WorkerResults.LoadMapResult loaded = client.loadMap(Path.of("D:/maps/a.tif"));
        assertEquals("MAP_LOADED", loaded.state());
        for (int i = 0; i < 10; i++) {
            WorkerResults.CalculationResult c = client.calculate(
                    new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0);
            assertEquals(123.456, c.distanceMeters(), 1e-9);
            assertEquals(13, c.roundedSeconds());
        }
        client.shutdown();
        assertEquals(0, client.lastExitCode().intValue());
    }

    @Test
    void concurrentThreadsAreSerializedAndCounted() throws Exception {
        Path countFile = tmp.resolve("count.txt");
        Map<String, String> extra = new LinkedHashMap<>();
        extra.put("COUNT_FILE", countFile.toString());
        DroneWorkerClient client = startClient(writeScript("resident.py", RESIDENT), normal(), line -> {
        }, extra);

        int threads = 8;
        int perThread = 10;
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        List<java.util.concurrent.Future<?>> futures = new ArrayList<>();
        for (int t = 0; t < threads; t++) {
            futures.add(pool.submit(() -> {
                for (int i = 0; i < perThread; i++) {
                    try {
                        assertEquals("READY", client.hello().state());
                    } catch (Exception e) {
                        throw new RuntimeException(e);
                    }
                }
                return null;
            }));
        }
        for (java.util.concurrent.Future<?> f : futures) {
            f.get(60, TimeUnit.SECONDS);
        }
        pool.shutdown();
        assertTrue(pool.awaitTermination(10, TimeUnit.SECONDS));

        long lines = Files.readAllLines(countFile, StandardCharsets.UTF_8).size();
        assertEquals(1 + threads * perThread, lines); // 1 次握手 hello + 80 次显式 hello
        client.shutdown();
        assertEquals(0, client.lastExitCode().intValue());
    }

    @Test
    void businessErrorKeepsSameProcessUsable() throws Exception {
        DroneWorkerClient client = startClient(writeScript("business.py", BUSINESS_ERROR), normal(), line -> {
        });
        long pid = client.pid();
        try {
            client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0);
            fail("应抛出 WorkerBusinessException");
        } catch (WorkerBusinessException e) {
            assertEquals("E_SPEED_INVALID", e.code());
        }
        assertEquals(pid, client.pid());
        assertEquals(DroneWorkerClient.State.READY, client.state());
        WorkerResults.HelloResult h = client.hello();
        assertEquals("READY", h.state());
        client.shutdown();
        assertEquals(0, client.lastExitCode().intValue());
    }

    @Test
    void stderrSpamAndJsonShapeDoesNotBecomeResponse() throws Exception {
        ConcurrentLinkedQueue<String> stderrLines = new ConcurrentLinkedQueue<>();
        DroneWorkerClient client = startClient(writeScript("stderr_spam.py", STDERR_SPAM), normal(),
                stderrLines::add);
        WorkerResults.HelloResult h = client.hello();
        assertEquals("READY", h.state());
        WorkerResults.LoadMapResult loaded = client.loadMap(Path.of("D:/maps/a.tif"));
        assertEquals("MAP_LOADED", loaded.state());
        WorkerResults.CalculationResult c = client.calculate(
                new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0);
        assertEquals(123.456, c.distanceMeters(), 1e-9);
        assertTrue(stderrLines.size() >= 3000);
        assertTrue(stderrLines.stream().anyMatch(l -> l.contains("\"success\"")));
        client.shutdown();
        assertEquals(0, client.lastExitCode().intValue());
    }

    @Test
    void stdoutNonJsonMarksBrokenAndDestroys() throws Exception {
        DroneWorkerClient client = startClient(writeScript("garbage.py", GARBAGE_STDOUT), normal(), line -> {
        });
        long pid = client.pid();
        client.loadMap(Path.of("D:/maps/a.tif"));
        assertThrows(WorkerProtocolException.class,
                () -> client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0));
        assertEquals(DroneWorkerClient.State.BROKEN, client.state());
        assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false));
    }

    @Test
    void idMismatchMarksBrokenAndDestroys() throws Exception {
        DroneWorkerClient client = startClient(writeScript("wrong_id.py", WRONG_ID), normal(), line -> {
        });
        long pid = client.pid();
        client.loadMap(Path.of("D:/maps/a.tif"));
        assertThrows(WorkerProtocolException.class,
                () -> client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0));
        assertEquals(DroneWorkerClient.State.BROKEN, client.state());
        assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false));
    }

    @Test
    void requestTimeoutDestroysWithoutAutoReplay() throws Exception {
        DroneWorkerClient client = startClient(writeScript("slow.py", SLOW_CALC), fastCalculate(), line -> {
        });
        long pid = client.pid();
        client.loadMap(Path.of("D:/maps/a.tif"));
        assertThrows(WorkerTransportException.class,
                () -> client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0));
        assertEquals(DroneWorkerClient.State.BROKEN, client.state());
        assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false));
        assertThrows(IllegalStateException.class,
                () -> client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0));
    }

    @Test
    void workerAbnormalExitYieldsTransportError() throws Exception {
        DroneWorkerClient client = startClient(writeScript("exit_after_hello.py", EXIT_AFTER_HELLO), normal(), line -> {
        });
        long pid = client.pid();
        assertThrows(WorkerTransportException.class, () -> client.loadMap(Path.of("D:/maps/a.tif")));
        assertEquals(DroneWorkerClient.State.BROKEN, client.state());
        assertFalse(ProcessHandle.of(pid).map(ProcessHandle::isAlive).orElse(false));
    }

    @Test
    void restartReEstablishesHello() throws Exception {
        // 未加载地图时破坏进程：restart 只重新握手，不重载地图
        DroneWorkerClient client = startClient(writeScript("garbage.py", GARBAGE_STDOUT), normal(), line -> {
        });
        long oldPid = client.pid();
        assertThrows(WorkerProtocolException.class,
                () -> client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0));
        assertFalse(ProcessHandle.of(oldPid).map(ProcessHandle::isAlive).orElse(false));

        WorkerResults.HelloResult h = client.restart();
        assertEquals("READY", h.state());
        assertEquals(DroneWorkerClient.State.READY, client.state());
        pids.add(client.pid());
        client.shutdown();
        assertEquals(0, client.lastExitCode().intValue());
    }

    @Test
    void restartReloadsLastSuccessfulMap() throws Exception {
        DroneWorkerClient client = startClient(writeScript("garbage.py", GARBAGE_STDOUT), normal(), line -> {
        });
        long oldPid = client.pid();
        client.loadMap(Path.of("D:/maps/area/main.tif"));
        assertThrows(WorkerProtocolException.class,
                () -> client.calculate(new WorkerPoint.Pixel(1.0, 1.0), new WorkerPoint.Pixel(2.0, 2.0), 10.0));
        assertFalse(ProcessHandle.of(oldPid).map(ProcessHandle::isAlive).orElse(false));

        WorkerResults.HelloResult h = client.restart();
        assertEquals("READY", h.state());
        assertEquals(DroneWorkerClient.State.MAP_LOADED, client.state());
        pids.add(client.pid());
        client.shutdown();
        assertEquals(0, client.lastExitCode().intValue());
    }


    private WorkerProcessHandle handleFor(Path script, WorkerTimeouts timeouts, int capacity,
                                          Consumer<String> stderr, Map<String, String> extraEnv)
            throws Exception {
        Map<String, String> env = new LinkedHashMap<>();
        env.put("PYTHONUTF8", "1");
        env.put("PYTHONIOENCODING", "utf-8");
        if (extraEnv != null) {
            env.putAll(extraEnv);
        }
        WorkerCommandLine cl = new WorkerCommandLine(
                List.of(PYTHON, "-u", script.toString()), script.getParent(), env);
        return new WorkerProcessHandle(cl, stderr, capacity);
    }

    private static final String OVERFLOW_SCRIPT = """
            import sys, json, os

            n = int(os.environ.get("CAP", "2"))
            for i in range(n + 1):
                sys.stdout.write(json.dumps({"id": "x", "success": True, "data": {}}) + "\\n")
                sys.stdout.flush()
            sys.exit(0)
            """;

    private static final String EXACTFULL_SCRIPT = """
            import sys, json, os

            n = int(os.environ.get("CAP", "3"))
            for i in range(n):
                sys.stdout.write(json.dumps({"id": "x", "success": True, "data": {}}) + "\\n")
                sys.stdout.flush()
            sys.exit(0)
            """;

    @Test
    void stdoutQueueOverflowIsTerminalWithoutReaderDeadlock() throws Exception {
        int capacity = 2;
        Map<String, String> extra = new LinkedHashMap<>();
        extra.put("CAP", String.valueOf(capacity));
        Path script = writeScript("overflow.py", OVERFLOW_SCRIPT);
        WorkerProcessHandle handle = handleFor(script, normal(), capacity, line -> {
        }, extra);
        pids.add(handle.pid());
        try {
            // 确定性同步：等待 stdout 读取线程完成（latch），不使用 Thread.sleep
            assertTrue(handle.awaitStdoutReaderTerminated(Duration.ofSeconds(10)),
                    "stdout 读取线程未在限定时间内结束");

            WorkerTransportException e = assertThrows(WorkerTransportException.class,
                    () -> handle.readResponse(Duration.ofSeconds(2), "x"));
            assertTrue(e.getMessage().contains("stdout queue overflow"),
                    "应为溢出终止错误而非普通超时: " + e.getMessage());
            assertFalse(e.getMessage().contains("超时"));

            // 终止性错误持久：再次读取仍为同一溢出错误；从未写入请求，不存在自动重放
            WorkerTransportException e2 = assertThrows(WorkerTransportException.class,
                    () -> handle.readResponse(Duration.ofSeconds(2), "x"));
            assertTrue(e2.getMessage().contains("stdout queue overflow"));
        } finally {
            handle.close();
        }
        assertTrue(handle.awaitStdoutReaderTerminated(Duration.ofSeconds(5)),
                "close 后 stdout 读取线程应结束");
    }

    @Test
    void stdoutEofRemainsObservableWhenQueueIsExactlyFull() throws Exception {
        int capacity = 3;
        Map<String, String> extra = new LinkedHashMap<>();
        extra.put("CAP", String.valueOf(capacity));
        Path script = writeScript("exactfull.py", EXACTFULL_SCRIPT);
        WorkerProcessHandle handle = handleFor(script, normal(), capacity, line -> {
        }, extra);
        pids.add(handle.pid());
        try {
            // 确定性同步：读取前等待 stdout 读取线程完成（latch）
            assertTrue(handle.awaitStdoutReaderTerminated(Duration.ofSeconds(10)),
                    "stdout 读取线程未在限定时间内结束");

            // N 条缓冲行按顺序全部读出
            for (int i = 0; i < capacity; i++) {
                NdjsonCodec.WorkerResponse r = handle.readResponse(Duration.ofSeconds(2), "x");
                assertTrue(r.success());
            }
            // 缓冲行读完后，下一次 readResponse 迅速报告 EOF（不是超时）
            WorkerTransportException e = assertThrows(WorkerTransportException.class,
                    () -> handle.readResponse(Duration.ofSeconds(2), "x"));
            assertTrue(e.getMessage().contains("EOF"), e.getMessage());
            assertFalse(e.getMessage().contains("超时"),
                    "EOF 不得伪装成操作超时: " + e.getMessage());
        } finally {
            handle.close();
        }
        assertTrue(handle.awaitStdoutReaderTerminated(Duration.ofSeconds(5)),
                "close 后 stdout 读取线程应结束");
    }
}
