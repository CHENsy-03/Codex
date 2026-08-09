package com.drone.worker;

import java.util.List;

/**
 * 与现有 Python 成功响应一致的嵌套结果类型；不增加协议字段。
 */
public final class WorkerResults {

    private WorkerResults() {
    }

    public record GeographicPoint(double longitude, double latitude) {
    }

    public record HelloResult(int protocolVersion, String engineVersion, String state,
                              List<String> coordinateTypes) {
    }

    public record LoadMapResult(String state, String crs, int width, int height, int bands) {
    }

    public record CalculationResult(GeographicPoint pointA, GeographicPoint pointB,
                                    double distanceMeters, double exactSeconds,
                                    int roundedSeconds, String duration) {
    }
}
