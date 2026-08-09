package com.drone.worker;

import com.drone.worker.NdjsonCodec.WorkerResponse;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.function.Consumer;

/**
 * 常驻 Worker 进程句柄：独立消费 stdout/stderr，串行读写，受控销毁。
 *
 * stdout 采用有界队列（默认 8192）；业务行入队使用非阻塞 offer，队列第一次溢出时
 * 原子记录终止性错误（WorkerTransportException，含 "stdout queue overflow"），
 * 随后继续排空并丢弃后续 stdout；EOF/读取异常通过独立状态传达，不依赖队列剩余容量。
 */
public final class WorkerProcessHandle implements AutoCloseable {

    static final int DEFAULT_STDOUT_QUEUE_CAPACITY = 8192;
    private static final long MAX_WAIT_NANOS = 50_000_000L; // 50ms

    private final Process process;
    private final Consumer<String> stderrConsumer;
    private final BufferedWriter stdin;
    private final ArrayBlockingQueue<String> stdoutLines;
    private final AtomicBoolean stdoutEof = new AtomicBoolean(false);
    private final AtomicReference<WorkerTransportException> terminalError = new AtomicReference<>();
    private final CountDownLatch terminalLatch = new CountDownLatch(1);
    private final CountDownLatch stdoutReaderDone = new CountDownLatch(1);
    private final Object writeLock = new Object();
    private final AtomicBoolean closed = new AtomicBoolean(false);
    private final NdjsonCodec codec = new NdjsonCodec();
    private final Thread stdoutThread;
    private final Thread stderrThread;

    public WorkerProcessHandle(WorkerCommandLine commandLine, Consumer<String> stderrConsumer) {
        this(commandLine, stderrConsumer, DEFAULT_STDOUT_QUEUE_CAPACITY);
    }

    WorkerProcessHandle(WorkerCommandLine commandLine, Consumer<String> stderrConsumer,
                        int stdoutQueueCapacity) {
        Objects.requireNonNull(commandLine, "commandLine");
        Objects.requireNonNull(stderrConsumer, "stderrConsumer");
        if (stdoutQueueCapacity <= 0) {
            throw new IllegalArgumentException("stdout 队列容量必须大于 0");
        }
        this.stderrConsumer = stderrConsumer;
        this.stdoutLines = new ArrayBlockingQueue<>(stdoutQueueCapacity);
        ProcessBuilder pb = new ProcessBuilder(commandLine.command());
        pb.directory(commandLine.workingDirectory().toFile());
        pb.redirectErrorStream(false);
        pb.environment().putAll(commandLine.environment());
        try {
            this.process = pb.start();
        } catch (IOException e) {
            throw new WorkerTransportException("启动 Worker 进程失败: " + e.getMessage(), e);
        }
        this.stdin = new BufferedWriter(
                new OutputStreamWriter(process.getOutputStream(), StandardCharsets.UTF_8));
        this.stdoutThread = new Thread(this::readStdout, "worker-stdout-" + process.pid());
        this.stdoutThread.setDaemon(true);
        this.stderrThread = new Thread(this::readStderr, "worker-stderr-" + process.pid());
        this.stderrThread.setDaemon(true);
        this.stdoutThread.start();
        this.stderrThread.start();
    }

    /**
     * stdout 读取线程：非阻塞入队；溢出后原子记录终止错误并继续排空丢弃；
     * EOF/读取异常独立记录，不依赖队列剩余容量。
     */
    private void readStdout() {
        boolean overflow = false;
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getInputStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                if (overflow) {
                    continue;
                }
                if (!stdoutLines.offer(line)) {
                    overflow = true;
                    recordTerminal(new WorkerTransportException(
                            "stdout queue overflow: 响应流终止"));
                }
            }
        } catch (IOException e) {
            recordTerminal(new WorkerTransportException("stdout 读取失败", e));
        } finally {
            stdoutEof.set(true);
            terminalLatch.countDown();
            stdoutReaderDone.countDown();
        }
    }

    private void recordTerminal(WorkerTransportException error) {
        if (terminalError.compareAndSet(null, error)) {
            terminalLatch.countDown();
        }
    }

    private void readStderr() {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(process.getErrorStream(), StandardCharsets.UTF_8))) {
            String line;
            while ((line = reader.readLine()) != null) {
                try {
                    stderrConsumer.accept(line);
                } catch (RuntimeException ignored) {
                    // 消费者异常不影响协议通道
                }
            }
        } catch (IOException ignored) {
            // stderr 通道结束即忽略
        }
    }

    public void writeRequest(String line) {
        synchronized (writeLock) {
            try {
                stdin.write(line);
                stdin.write('\n');
                stdin.flush();
            } catch (IOException e) {
                throw new WorkerTransportException("写入 stdin 失败（管道可能已关闭）", e);
            }
        }
    }

    /**
     * 处理优先级：已记录的溢出/读取异常 → 已缓冲响应行 → 队列空且正常 EOF → 操作超时。
     * 等待使用单调时钟与原始截止时间，单次等待不超过 50ms，可由终止事件立即唤醒。
     */
    public WorkerResponse readResponse(Duration timeout, String expectedId) {
        long deadline = System.nanoTime() + timeout.toNanos();
        while (true) {
            long remaining = deadline - System.nanoTime();
            if (remaining <= 0) {
                throw new WorkerTransportException(
                        "等待 Worker 响应超时（" + timeout.toMillis() + " ms）");
            }
            WorkerTransportException terminal = terminalError.get();
            if (terminal != null) {
                throw terminal;
            }
            String line = stdoutLines.poll();
            if (line != null) {
                return codec.decode(line, expectedId);
            }
            if (stdoutEof.get()) {
                throw new WorkerTransportException("Worker stdout 已关闭（EOF）");
            }
            long waitNanos = Math.min(MAX_WAIT_NANOS, remaining);
            try {
                terminalLatch.await(waitNanos, TimeUnit.NANOSECONDS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new WorkerTransportException("等待响应被中断", e);
            }
        }
    }

    public boolean isAlive() {
        return process.isAlive();
    }

    public long pid() {
        return process.pid();
    }

    public int exitCode() {
        return process.exitValue();
    }

    public void closeStdin() {
        synchronized (writeLock) {
            try {
                stdin.close();
            } catch (IOException ignored) {
                // 已关闭则忽略
            }
        }
    }

    public void awaitExit(Duration timeout) {
        long deadline = System.nanoTime() + timeout.toNanos();
        while (process.isAlive()) {
            long remaining = deadline - System.nanoTime();
            if (remaining <= 0) {
                return;
            }
            try {
                Thread.sleep(Math.min(50L, Math.max(1L, remaining / 1_000_000L)));
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    /**
     * 包级私有：仅供确定性测试使用，等待 stdout 读取线程在限定时间内完成。
     */
    boolean awaitStdoutReaderTerminated(Duration timeout) {
        try {
            return stdoutReaderDone.await(timeout.toNanos(), TimeUnit.NANOSECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    /**
     * 销毁顺序：等待正常退出 → destroy() → destroyForcibly()；随后有界等待读取线程结束。
     */
    public void destroy(WorkerTimeouts timeouts) {
        if (closed.getAndSet(true)) {
            return;
        }
        closeStdin();
        awaitExit(timeouts.shutdownResponse());
        if (process.isAlive()) {
            process.destroy();
            awaitExit(timeouts.destroyWait());
        }
        if (process.isAlive()) {
            process.destroyForcibly();
            awaitExit(timeouts.destroyForciblyWait());
        }
        closeStreamsAndAwaitReader();
    }

    @Override
    public void close() {
        if (closed.getAndSet(true)) {
            return;
        }
        closeStdin();
        if (process.isAlive()) {
            process.destroyForcibly();
            awaitExit(Duration.ofSeconds(2));
        }
        closeStreamsAndAwaitReader();
    }

    private void closeStreamsAndAwaitReader() {
        try {
            process.getInputStream().close();
        } catch (IOException ignored) {
        }
        try {
            process.getErrorStream().close();
        } catch (IOException ignored) {
        }
        awaitStdoutReaderTerminated(Duration.ofSeconds(2));
    }
}
