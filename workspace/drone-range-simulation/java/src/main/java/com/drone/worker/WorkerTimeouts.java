package com.drone.worker;

import java.time.Duration;
import java.util.Objects;

/**
 * 不可变的超时配置；所有值非 null 且严格大于 0。
 * 正式默认值：hello/startup 15s、load_map 60s、calculate 10s、
 * shutdown 响应 5s、destroy 等待 2s、destroyForcibly 等待 2s。
 */
public final class WorkerTimeouts {

    private final Duration helloStartup;
    private final Duration loadMap;
    private final Duration calculate;
    private final Duration shutdownResponse;
    private final Duration destroyWait;
    private final Duration destroyForciblyWait;

    public WorkerTimeouts(Duration helloStartup, Duration loadMap, Duration calculate,
                          Duration shutdownResponse, Duration destroyWait,
                          Duration destroyForciblyWait) {
        this.helloStartup = requirePositive(helloStartup, "helloStartup");
        this.loadMap = requirePositive(loadMap, "loadMap");
        this.calculate = requirePositive(calculate, "calculate");
        this.shutdownResponse = requirePositive(shutdownResponse, "shutdownResponse");
        this.destroyWait = requirePositive(destroyWait, "destroyWait");
        this.destroyForciblyWait = requirePositive(destroyForciblyWait, "destroyForciblyWait");
    }

    private static Duration requirePositive(Duration duration, String name) {
        Objects.requireNonNull(duration, name);
        if (duration.isZero() || duration.isNegative()) {
            throw new IllegalArgumentException(name + " 必须严格大于 0");
        }
        return duration;
    }

    public static WorkerTimeouts defaults() {
        return new WorkerTimeouts(
                Duration.ofSeconds(15),
                Duration.ofSeconds(60),
                Duration.ofSeconds(10),
                Duration.ofSeconds(5),
                Duration.ofSeconds(2),
                Duration.ofSeconds(2));
    }

    public Duration helloStartup() { return helloStartup; }
    public Duration loadMap() { return loadMap; }
    public Duration calculate() { return calculate; }
    public Duration shutdownResponse() { return shutdownResponse; }
    public Duration destroyWait() { return destroyWait; }
    public Duration destroyForciblyWait() { return destroyForciblyWait; }
}
