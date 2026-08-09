package com.drone.worker;

/**
 * 三类坐标输入；JSON 字段与 type 必须精确符合 Python 协议。
 */
public sealed interface WorkerPoint permits WorkerPoint.Wgs84, WorkerPoint.MapCrs, WorkerPoint.Pixel {

    record Wgs84(double longitude, double latitude) implements WorkerPoint {}

    record MapCrs(double x, double y) implements WorkerPoint {}

    record Pixel(double column, double row) implements WorkerPoint {}
}
