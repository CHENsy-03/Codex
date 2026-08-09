package com.drone.worker;

/**
 * 对应合法 success=false 响应；不污染进程，抛出后进程仍可继续使用。
 * code 使用字符串原样保存，不建立白名单枚举。
 */
public class WorkerBusinessException extends Exception {

    private final String requestId;
    private final String code;
    private final String errorMessage;

    public WorkerBusinessException(String requestId, String code, String message) {
        super(code + ": " + message);
        this.requestId = requestId;
        this.code = code;
        this.errorMessage = message;
    }

    public String requestId() {
        return requestId;
    }

    public String code() {
        return code;
    }

    public String message() {
        return errorMessage;
    }
}
