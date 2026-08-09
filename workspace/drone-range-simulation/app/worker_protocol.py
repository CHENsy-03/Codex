"""常驻 Worker 的严格 NDJSON 传输协议（TASK-008 / TASK-009）。

冻结基线：《无人机二维航程计算引擎_Java21常驻子进程集成技术设计 V1.0 冻结版》。

TASK-008 实现严格 UTF-8 NDJSON 读写循环（hello/shutdown）。
TASK-009 接入 WorkerEngine：通用请求信封校验后，将合法操作分发给
同一 WorkerEngine 实例（状态机、load_map、calculate）。

通道约定：
- stdin：请求通道（每行一个 UTF-8 JSON 对象）；
- stdout：协议响应通道（每行一个 UTF-8 JSON 对象，LF 结束，每次响应后立即 flush）；
- stderr：日志通道（不记录请求原文、路径、坐标、结果、源码路径或完整异常堆栈）。
"""

from __future__ import annotations

import json
import sys
from typing import Any, BinaryIO, Optional

PROTOCOL_VERSION = 1
ENGINE_VERSION = "1.0.0"
COORDINATE_TYPES = ("wgs84", "map_crs", "pixel")

# 传输层错误码（TASK-008）
E_PROTOCOL_INVALID_JSON = "E_PROTOCOL_INVALID_JSON"
E_PROTOCOL_VERSION = "E_PROTOCOL_VERSION"
E_OPERATION_UNKNOWN = "E_OPERATION_UNKNOWN"
E_REQUEST_INVALID = "E_REQUEST_INVALID"
E_INTERNAL = "E_INTERNAL"

# 地图/坐标/计算错误码（TASK-009 接入）
E_MAP_NOT_LOADED = "E_MAP_NOT_LOADED"
E_MAP_NOT_FOUND = "E_MAP_NOT_FOUND"
E_MAP_OPEN_FAILED = "E_MAP_OPEN_FAILED"
E_MAP_CRS_MISSING = "E_MAP_CRS_MISSING"
E_MAP_TRANSFORM_INVALID = "E_MAP_TRANSFORM_INVALID"
E_POINT_TYPE = "E_POINT_TYPE"
E_POINT_INVALID = "E_POINT_INVALID"
E_POINT_OUT_OF_BOUNDS = "E_POINT_OUT_OF_BOUNDS"
E_CRS_TRANSFORM = "E_CRS_TRANSFORM"
E_SPEED_INVALID = "E_SPEED_INVALID"
E_TIME_LIMIT = "E_TIME_LIMIT"
E_CALCULATION = "E_CALCULATION"

_MESSAGES = {
    E_PROTOCOL_INVALID_JSON: "请求不是有效的 JSON 对象。",
    E_PROTOCOL_VERSION: "protocolVersion 不兼容。",
    E_OPERATION_UNKNOWN: "未知操作。",
    E_REQUEST_INVALID: "请求结构无效。",
    E_INTERNAL: "内部错误。",
    E_MAP_NOT_LOADED: "尚未加载地图。",
    E_MAP_NOT_FOUND: "地图文件不存在或不可读。",
    E_MAP_OPEN_FAILED: "地图文件无法打开或不是有效 GeoTIFF。",
    E_MAP_CRS_MISSING: "地图缺少有效坐标参考系（CRS）。",
    E_MAP_TRANSFORM_INVALID: "地图仿射变换无效。",
    E_POINT_TYPE: "坐标点类型无效。",
    E_POINT_INVALID: "坐标点字段无效。",
    E_POINT_OUT_OF_BOUNDS: "坐标点超出影像范围。",
    E_CRS_TRANSFORM: "坐标参考系转换失败。",
    E_SPEED_INVALID: "速度必须为 1–99 的整数（m/s）。",
    E_TIME_LIMIT: "飞行时间超过99小时",
    E_CALCULATION: "距离或飞行时间计算失败。",
}

_HELLO = "hello"
_SHUTDOWN = "shutdown"
_LOAD_MAP = "load_map"
_CALCULATE = "calculate"


def _reject_json_constant(value: str) -> Any:
    """拒绝 NaN/Infinity 等非标准 JSON 常量。"""
    raise ValueError(f"非标准 JSON 常量：{value}")


def _success_response(request_id: str, data: dict[str, Any]) -> dict[str, Any]:
    return {"id": request_id, "success": True, "data": data}


def _error_response(request_id: Optional[str], code: str) -> dict[str, Any]:
    return {
        "id": request_id,
        "success": False,
        "error": {"code": code, "message": _MESSAGES[code]},
    }


def _validate_request(
    obj: Any,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """校验通用请求信封，返回 (request_id, operation, error_code)。"""
    if not isinstance(obj, dict):
        return None, None, E_PROTOCOL_INVALID_JSON

    request_id = obj.get("id")
    if not isinstance(request_id, str) or request_id == "":
        return None, None, E_REQUEST_INVALID

    if "protocolVersion" not in obj:
        return request_id, None, E_REQUEST_INVALID
    protocol_version = obj["protocolVersion"]
    if (
        isinstance(protocol_version, bool)
        or not isinstance(protocol_version, int)
        or protocol_version != PROTOCOL_VERSION
    ):
        return request_id, None, E_PROTOCOL_VERSION

    operation = obj.get("operation")
    if not isinstance(operation, str):
        return request_id, None, E_REQUEST_INVALID
    return request_id, operation, None


def handle_raw_line(
    raw: bytes,
    engine: Optional[Any] = None,
) -> tuple[dict[str, Any], bool]:
    """处理一行原始字节输入，返回 (响应 JSON 对象, 是否应退出循环)。

    engine 为空时创建一次性 WorkerEngine（用于纯函数测试）；
    run_worker 会传入同一个引擎实例供全部请求串行复用。
    """
    line = raw.rstrip(b"\r\n")
    try:
        text = line.decode("utf-8")
    except UnicodeDecodeError:
        return _error_response(None, E_PROTOCOL_INVALID_JSON), False

    try:
        obj = json.loads(text, parse_constant=_reject_json_constant)
    except ValueError:
        return _error_response(None, E_PROTOCOL_INVALID_JSON), False

    request_id, operation, error_code = _validate_request(obj)
    if error_code is not None:
        return _error_response(request_id, error_code), False

    if engine is None:
        from app.worker_engine import WorkerEngine

        engine = WorkerEngine()

    try:
        if operation == _HELLO:
            return _success_response(request_id, engine.hello()), False
        if operation == _SHUTDOWN:
            return _success_response(request_id, engine.shutdown()), True
        if operation == _LOAD_MAP:
            return _success_response(request_id, engine.load_map(obj)), False
        if operation == _CALCULATE:
            return _success_response(request_id, engine.calculate(obj)), False
        return _error_response(request_id, E_OPERATION_UNKNOWN), False
    except Exception as exc:
        from app.worker_engine import WorkerProtocolError

        if isinstance(exc, WorkerProtocolError):
            return _error_response(request_id, exc.code), False
        return _error_response(request_id, E_INTERNAL), False


def encode_response(response: dict[str, Any]) -> bytes:
    """将响应编码为单行 UTF-8 JSON + LF（紧凑、无 BOM）。"""
    text = json.dumps(
        response,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    )
    try:
        return text.encode("utf-8") + b"\n"
    except UnicodeEncodeError:
        # 极端输入（如孤立代理项）时回退 ASCII 转义，保证仍输出合法 JSON
        text = json.dumps(
            response,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        return text.encode("utf-8") + b"\n"


def write_response(stream: BinaryIO, response: dict[str, Any]) -> None:
    """写入一条响应并立即 flush。"""
    stream.write(encode_response(response))
    stream.flush()


def _log(error_stream: Optional[BinaryIO], message: str) -> None:
    if error_stream is None:
        return
    try:
        error_stream.write(f"[worker] {message}\n".encode("utf-8"))
        error_stream.flush()
    except Exception:
        pass


def run_worker(
    input_stream: BinaryIO,
    output_stream: BinaryIO,
    error_stream: Optional[BinaryIO] = None,
) -> int:
    """严格串行 NDJSON 循环；返回进程退出码。

    每次启动只创建一个 WorkerEngine，全部请求串行复用该实例；
    不使用模块级可变状态；finally 中释放当前地图或其他资源。
    """
    from app.worker_engine import WorkerEngine

    engine = WorkerEngine()
    _log(error_stream, "worker started")
    try:
        while True:
            raw = input_stream.readline()
            if raw == b"":
                break
            try:
                response, should_exit = handle_raw_line(raw, engine)
            except Exception:
                response, should_exit = _error_response(None, E_INTERNAL), False
            try:
                write_response(output_stream, response)
            except Exception:
                _log(error_stream, "output stream closed")
                return 0
            if should_exit:
                break
    except Exception:
        try:
            write_response(output_stream, _error_response(None, E_INTERNAL))
        except Exception:
            pass
    finally:
        engine.release()
        _log(error_stream, "worker exiting")
    return 0


def main() -> int:
    """进程入口：使用 sys.stdin.buffer / stdout.buffer / stderr.buffer。"""
    return run_worker(sys.stdin.buffer, sys.stdout.buffer, sys.stderr.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
