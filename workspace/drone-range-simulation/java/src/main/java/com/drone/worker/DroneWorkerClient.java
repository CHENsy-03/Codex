package com.drone.worker;

import com.drone.worker.NdjsonCodec.WorkerResponse;
import com.fasterxml.jackson.databind.JsonNode;

import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.locks.ReentrantLock;
import java.util.function.Consumer;

/**
 * Java 21 ProcessBuilder 常驻 Worker 客户端。
 * 公平锁保证单在途；业务错误不销毁进程；协议/传输/超时错误立即 BROKEN 并销毁，绝不自动重放。
 */
public final class DroneWorkerClient implements AutoCloseable {

    public enum State {
        NEW, READY, MAP_LOADED, BROKEN, CLOSED
    }

    private final WorkerCommandLine commandLine;
    private final WorkerTimeouts timeouts;
    private final Consumer<String> stderrConsumer;
    private final ReentrantLock lock = new ReentrantLock(true);
    private final AtomicLong requestSeq = new AtomicLong();
    private final NdjsonCodec codec = new NdjsonCodec();

    private WorkerProcessHandle handle;
    private State state = State.NEW;
    private String lastSuccessfulMapPath;
    private Integer lastExitCode;

    public DroneWorkerClient(WorkerCommandLine commandLine, WorkerTimeouts timeouts,
                             Consumer<String> stderrConsumer) {
        this.commandLine = Objects.requireNonNull(commandLine, "commandLine");
        this.timeouts = Objects.requireNonNull(timeouts, "timeouts");
        this.stderrConsumer = Objects.requireNonNull(stderrConsumer, "stderrConsumer");
    }

    public DroneWorkerClient(WorkerCommandLine commandLine, WorkerTimeouts timeouts) {
        this(commandLine, timeouts, line -> {
        });
    }

    // ------------------------------------------------------------------ //
    // 公共 API
    // ------------------------------------------------------------------ //
    public WorkerResults.HelloResult start() throws WorkerBusinessException {
        lock.lock();
        try {
            if (state == State.CLOSED) {
                throw new IllegalStateException("客户端已关闭");
            }
            if (handle != null && handle.isAlive()) {
                throw new IllegalStateException("Worker 已启动");
            }
            return startInternal();
        } finally {
            lock.unlock();
        }
    }

    public WorkerResults.HelloResult hello() throws WorkerBusinessException {
        lock.lock();
        try {
            ensureStarted();
            return doHelloHandshake();
        } finally {
            lock.unlock();
        }
    }

    public WorkerResults.LoadMapResult loadMap(Path path) throws WorkerBusinessException {
        lock.lock();
        try {
            return loadMapInternal(path);
        } catch (WorkerProtocolException | WorkerTransportException e) {
            breakAndDestroy(e);
            throw e;
        } finally {
            lock.unlock();
        }
    }

    public WorkerResults.CalculationResult calculate(WorkerPoint pointA, WorkerPoint pointB,
                                                     double speedMps) throws WorkerBusinessException {
        lock.lock();
        try {
            ensureStarted();
            String id = nextId("c");
            handle.writeRequest(codec.encodeCalculate(id, pointA, pointB, speedMps));
            WorkerResponse resp = handle.readResponse(timeouts.calculate(), id);
            if (!resp.success()) {
                throw new WorkerBusinessException(id, resp.errorCode(), resp.errorMessage());
            }
            return parseCalculation(resp.data());
        } catch (WorkerProtocolException | WorkerTransportException e) {
            breakAndDestroy(e);
            throw e;
        } finally {
            lock.unlock();
        }
    }

    public WorkerResults.HelloResult restart() throws WorkerBusinessException {
        lock.lock();
        try {
            if (state == State.CLOSED) {
                throw new IllegalStateException("客户端已关闭");
            }
            destroyCurrent();
            state = State.NEW;
            WorkerResults.HelloResult hello = startInternal();
            if (lastSuccessfulMapPath != null) {
                loadMapInternal(Path.of(lastSuccessfulMapPath));
            }
            return hello;
        } finally {
            lock.unlock();
        }
    }

    public void shutdown() {
        lock.lock();
        try {
            if (state == State.CLOSED) {
                return;
            }
            if (handle != null && handle.isAlive()) {
                String id = nextId("s");
                try {
                    handle.writeRequest(codec.encodeShutdown(id));
                    WorkerResponse resp = handle.readResponse(timeouts.shutdownResponse(), id);
                    if (!resp.success()) {
                        throw new WorkerBusinessException(id, resp.errorCode(), resp.errorMessage());
                    }
                } catch (WorkerProtocolException | WorkerTransportException | WorkerBusinessException ignored) {
                    // shutdown 失败也进入受控销毁
                }
                handle.destroy(timeouts);
                if (!handle.isAlive()) {
                    try {
                        lastExitCode = handle.exitCode();
                    } catch (IllegalThreadStateException ignored) {
                        lastExitCode = null;
                    }
                }
            }
            state = State.CLOSED;
            handle = null;
        } finally {
            lock.unlock();
        }
    }

    @Override
    public void close() {
        lock.lock();
        try {
            if (handle != null) {
                handle.close();
                handle = null;
            }
            state = State.CLOSED;
        } finally {
            lock.unlock();
        }
    }

    public State state() {
        lock.lock();
        try {
            return state;
        } finally {
            lock.unlock();
        }
    }

    public long pid() {
        lock.lock();
        try {
            if (handle == null) {
                throw new IllegalStateException("Worker 未启动");
            }
            return handle.pid();
        } finally {
            lock.unlock();
        }
    }

    public Integer lastExitCode() {
        lock.lock();
        try {
            return lastExitCode;
        } finally {
            lock.unlock();
        }
    }

    // ------------------------------------------------------------------ //
    // 内部实现（调用方必须已持有锁）
    // ------------------------------------------------------------------ //
    private WorkerResults.HelloResult startInternal() throws WorkerBusinessException {
        WorkerProcessHandle newHandle = new WorkerProcessHandle(commandLine, stderrConsumer);
        this.handle = newHandle;
        this.state = State.BROKEN;
        try {
            WorkerResults.HelloResult hello = doHelloHandshake();
            this.state = State.READY;
            return hello;
        } catch (WorkerProtocolException | WorkerTransportException | WorkerBusinessException e) {
            destroyCurrent();
            this.state = State.BROKEN;
            throw e;
        }
    }

    private WorkerResults.LoadMapResult loadMapInternal(Path path) throws WorkerBusinessException {
        ensureStarted();
        String pathText = Objects.requireNonNull(path, "path").toAbsolutePath().normalize().toString();
        String id = nextId("m");
        handle.writeRequest(codec.encodeLoadMap(id, pathText));
        WorkerResponse resp = handle.readResponse(timeouts.loadMap(), id);
        if (!resp.success()) {
            throw new WorkerBusinessException(id, resp.errorCode(), resp.errorMessage());
        }
        JsonNode data = resp.data();
        WorkerResults.LoadMapResult result = new WorkerResults.LoadMapResult(
                data.path("state").asText(),
                data.path("crs").asText(),
                data.path("width").asInt(),
                data.path("height").asInt(),
                data.path("bands").asInt());
        this.lastSuccessfulMapPath = pathText;
        this.state = State.MAP_LOADED;
        return result;
    }

    private WorkerResults.HelloResult doHelloHandshake() throws WorkerBusinessException {
        String id = nextId("h");
        handle.writeRequest(codec.encodeHello(id));
        WorkerResponse resp = handle.readResponse(timeouts.helloStartup(), id);
        if (!resp.success()) {
            throw new WorkerBusinessException(id, resp.errorCode(), resp.errorMessage());
        }
        JsonNode data = resp.data();
        if (!data.path("protocolVersion").isInt() || data.path("protocolVersion").asInt() != 1) {
            throw new WorkerProtocolException("hello 响应 protocolVersion 必须为 1");
        }
        List<String> coordinateTypes = new ArrayList<>();
        JsonNode types = data.path("coordinateTypes");
        if (types.isArray()) {
            for (JsonNode n : types) {
                coordinateTypes.add(n.asText());
            }
        }
        return new WorkerResults.HelloResult(
                1,
                data.path("engineVersion").asText(""),
                data.path("state").asText(""),
                List.copyOf(coordinateTypes));
    }

    private WorkerResults.CalculationResult parseCalculation(JsonNode data) {
        JsonNode pointA = data.path("pointA");
        JsonNode pointB = data.path("pointB");
        return new WorkerResults.CalculationResult(
                new WorkerResults.GeographicPoint(
                        pointA.path("longitude").asDouble(), pointA.path("latitude").asDouble()),
                new WorkerResults.GeographicPoint(
                        pointB.path("longitude").asDouble(), pointB.path("latitude").asDouble()),
                data.path("distanceMeters").asDouble(),
                data.path("exactSeconds").asDouble(),
                data.path("roundedSeconds").asInt(),
                data.path("duration").asText());
    }

    private void ensureStarted() {
        if (state == State.CLOSED) {
            throw new IllegalStateException("客户端已关闭");
        }
        if (handle == null) {
            throw new IllegalStateException("Worker 未启动，请先调用 start()");
        }
        if (!handle.isAlive()) {
            WorkerTransportException e = new WorkerTransportException("Worker 进程已退出");
            breakAndDestroy(e);
            throw e;
        }
    }

    private void breakAndDestroy(Throwable cause) {
        state = State.BROKEN;
        destroyCurrent();
    }

    private void destroyCurrent() {
        if (handle != null) {
            try {
                handle.destroy(timeouts);
            } catch (RuntimeException ignored) {
            }
            try {
                handle.close();
            } catch (RuntimeException ignored) {
            }
            handle = null;
        }
    }

    private String nextId(String prefix) {
        return prefix + "-" + requestSeq.incrementAndGet();
    }
}
