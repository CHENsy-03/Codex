package com.drone.worker;

/**
 * 传输层错误（启动失败、写入失败、管道破裂、EOF、异常退出、超时等）；
 * 保存明确原因与可用退出码；发生后必须销毁进程。
 */
public class WorkerTransportException extends RuntimeException {

    private final Integer exitCode;

    public WorkerTransportException(String message) {
        this(message, null, null);
    }

    public WorkerTransportException(String message, Throwable cause) {
        this(message, cause, null);
    }

    public WorkerTransportException(String message, Integer exitCode) {
        this(message, null, exitCode);
    }

    public WorkerTransportException(String message, Throwable cause, Integer exitCode) {
        super(message, cause);
        this.exitCode = exitCode;
    }

    public Integer exitCode() {
        return exitCode;
    }
}
