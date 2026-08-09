package com.drone.worker;

import java.nio.file.Path;

/**
 * 演示 Java 21 ProcessBuilder 集成最低流程：
 * 启动常驻 Worker → hello → load_map → calculate → shutdown（try-with-resources 清理）。
 */
public final class ProcessBuilderDemo {

    public static void main(String[] args) {
        if (args.length < 3) {
            System.err.println("用法: ProcessBuilderDemo <python绝对路径> <项目绝对路径> <GeoTIFF绝对路径>");
            System.exit(2);
        }
        Path python = Path.of(args[0]);
        Path project = Path.of(args[1]);
        Path geotiff = Path.of(args[2]);

        WorkerCommandLine commandLine = WorkerCommandLine.forPythonWorker(python, project);
        try (DroneWorkerClient client = new DroneWorkerClient(commandLine, WorkerTimeouts.defaults())) {
            WorkerResults.HelloResult hello = client.start();
            System.out.println("hello: protocolVersion=" + hello.protocolVersion()
                    + " engineVersion=" + hello.engineVersion()
                    + " state=" + hello.state());

            WorkerResults.LoadMapResult loaded = client.loadMap(geotiff);
            System.out.println("load_map: crs=" + loaded.crs()
                    + " " + loaded.width() + "x" + loaded.height()
                    + " bands=" + loaded.bands());

            WorkerResults.CalculationResult calc = client.calculate(
                    new WorkerPoint.Pixel(1.0, 1.0),
                    new WorkerPoint.Pixel(2.0, 2.0),
                    10.0);
            System.out.println("calculate: distance=" + calc.distanceMeters()
                    + " exact=" + calc.exactSeconds()
                    + " rounded=" + calc.roundedSeconds()
                    + " duration=" + calc.duration());

            client.shutdown();
        } catch (WorkerBusinessException e) {
            System.err.println("业务错误: " + e.code() + " " + e.message());
            System.exit(1);
        } catch (Exception e) {
            System.err.println("失败: " + e.getMessage());
            System.exit(1);
        }
    }
}
