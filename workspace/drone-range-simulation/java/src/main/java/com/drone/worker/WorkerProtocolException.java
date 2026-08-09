package com.drone.worker;

/**
 * 协议流失效（非 JSON、信封错误、id 不匹配等）；发生后必须销毁进程。
 */
public class WorkerProtocolException extends RuntimeException {

    public WorkerProtocolException(String message) {
        super(message);
    }

    public WorkerProtocolException(String message, Throwable cause) {
        super(message, cause);
    }
}
