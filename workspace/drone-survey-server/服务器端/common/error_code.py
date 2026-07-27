# -*- coding: utf-8 -*-
"""V2.0 统一错误码枚举"""
from enum import IntEnum


class ErrorCode(IntEnum):
    """全局错误码"""
    SUCCESS = 0

    # 通用错误 (1xxx)
    UNKNOWN = 1000
    INVALID_PARAM = 1001
    NOT_IMPLEMENTED = 1002
    TIMEOUT = 1003
    RESOURCE_EXHAUSTED = 1004
    INTERNAL_ERROR = 1099

    # 网络错误 (2xxx)
    NETWORK_UNREACHABLE = 2000
    PORT_IN_USE = 2001
    CONNECTION_REFUSED = 2002
    CONNECTION_TIMEOUT = 2003
    CONNECTION_RESET = 2004
    DNS_RESOLVE_FAILED = 2005

    # 协议错误 (3xxx)
    PARSE_FAILED = 3000
    CRC_MISMATCH = 3001
    UNKNOWN_PROTOCOL = 3002
    INVALID_FRAME = 3003
    FIELD_MISSING = 3004
    VERSION_MISMATCH = 3005

    # 数据库错误 (4xxx)
    DB_CONNECTION_FAILED = 4000
    DB_WRITE_FAILED = 4001
    DB_READ_FAILED = 4002
    DB_INTEGRITY_ERROR = 4003
    DB_NOT_FOUND = 4004
    DB_DUPLICATE = 4005

    # 设备错误 (5xxx)
    DEVICE_OFFLINE = 5000
    DEVICE_TIMEOUT = 5001
    DEVICE_NOT_REGISTERED = 5002
    DEVICE_AUTH_FAILED = 5003
    DEVICE_FIRMWARE_MISMATCH = 5004

    # 同步错误 (6xxx)
    SYNC_UPSTREAM_UNREACHABLE = 6000
    SYNC_DATA_CONFLICT = 6001
    SYNC_PARTIAL_FAILURE = 6002

    # 安全错误 (7xxx)
    ENCRYPT_FAILED = 7000
    DECRYPT_FAILED = 7001
    AUTH_REQUIRED = 7002
    PERMISSION_DENIED = 7003

    @classmethod
    def category(cls, code: int) -> str:
        """返回错误分类名"""
        cat = code // 1000
        return {
            1: "通用", 2: "网络", 3: "协议",
            4: "数据库", 5: "设备", 6: "同步",
            7: "安全",
        }.get(cat, "未知")

    @classmethod
    def describe(cls, code: int) -> str:
        """返回错误码描述"""
        try:
            ec = cls(code)
            descriptions = {
                cls.SUCCESS: "操作成功",
                cls.UNKNOWN: "未知错误",
                cls.INVALID_PARAM: "参数无效",
                cls.NOT_IMPLEMENTED: "功能未实现",
                cls.TIMEOUT: "操作超时",
                cls.NETWORK_UNREACHABLE: "网络不可达",
                cls.PORT_IN_USE: "端口被占用",
                cls.CONNECTION_REFUSED: "连接被拒绝",
                cls.CONNECTION_TIMEOUT: "连接超时",
                cls.CONNECTION_RESET: "连接被重置",
                cls.PARSE_FAILED: "报文解析失败",
                cls.CRC_MISMATCH: "CRC校验失败",
                cls.UNKNOWN_PROTOCOL: "未知协议类型",
                cls.INVALID_FRAME: "无效通信帧",
                cls.DB_CONNECTION_FAILED: "数据库连接失败",
                cls.DB_WRITE_FAILED: "数据库写入失败",
                cls.DB_READ_FAILED: "数据库读取失败",
                cls.DEVICE_OFFLINE: "设备离线",
                cls.DEVICE_TIMEOUT: "设备超时",
                cls.DEVICE_NOT_REGISTERED: "设备未注册",
                cls.DEVICE_AUTH_FAILED: "设备认证失败",
                cls.SYNC_UPSTREAM_UNREACHABLE: "上级服务器不可达",
                cls.SYNC_DATA_CONFLICT: "同步数据冲突",
                cls.ENCRYPT_FAILED: "加密失败",
                cls.DECRYPT_FAILED: "解密失败",
                cls.AUTH_REQUIRED: "需要认证",
                cls.PERMISSION_DENIED: "权限不足",
            }
            return descriptions.get(ec, f"错误码{code}")
        except ValueError:
            return f"未知错误码{code}"


class ErrorResult:
    """统一的错误返回对象"""
    def __init__(self, code: ErrorCode, message: str = "", detail: str = ""):
        self.code = code
        self.message = message or ErrorCode.describe(int(code))
        self.detail = detail
        self.category = ErrorCode.category(int(code))

    def to_dict(self) -> dict:
        return {
            "code": int(self.code),
            "message": self.message,
            "category": self.category,
            "detail": self.detail,
        }

    def __bool__(self) -> bool:
        return self.code == ErrorCode.SUCCESS

    def __str__(self) -> str:
        return f"[{self.category}] {self.message}"


def ok() -> ErrorResult:
    return ErrorResult(ErrorCode.SUCCESS)


def err(code: ErrorCode, detail: str = "") -> ErrorResult:
    return ErrorResult(code, detail=detail)
