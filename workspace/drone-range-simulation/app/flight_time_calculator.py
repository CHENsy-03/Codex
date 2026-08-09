"""整数飞行速度解析与飞行时间计算。

TASK-006：
- 速度单位 m/s，仅接受 1–99 的整数；
- exact_seconds = distance_m / speed_m_s（完整精度）；
- rounded_seconds = math.ceil(exact_seconds)；
- HH:MM:SS 由同一个 rounded_seconds 生成，上限 99:59:59（359999 秒）。

不实现动画、三维距离、DEM、航线规划等。不依赖 Qt 控件或界面标签。
"""

from __future__ import annotations

import dataclasses
import math
import re
from dataclasses import dataclass

MAX_DISPLAY_SECONDS = 99 * 3600 + 59 * 60 + 59  # 359999

_SPEED_PATTERN = re.compile(r"^[0-9]+$")


class SpeedValidationError(Exception):
    """速度输入无效（非 1–99 整数）。"""


class FlightTimeCalculationError(Exception):
    """飞行时间计算参数无效。"""


class FlightTimeLimitError(Exception):
    """飞行时间超过 99 小时上限。"""


@dataclasses.dataclass(frozen=True)
class FlightTimeResult:
    """一次成功的飞行时间计算结果。"""

    distance_m: float  # 参与计算的完整精度距离
    speed_m_s: int  # 整数速度
    exact_seconds: float  # 未取整的完整精度秒数
    rounded_seconds: int  # 向上取整后的整数秒
    hhmmss: str  # 格式化时间字符串


def parse_speed_m_s(text: str) -> int:
    """严格解析 1–99 的整数速度（m/s）。

    拒绝：0、负数、100+、小数、科学计数法、NaN/inf、正负号、
    前后空格/纯空格以及其他非数字字符。
    """
    if not isinstance(text, str) or not _SPEED_PATTERN.fullmatch(text):
        raise SpeedValidationError("速度必须为 1–99 的整数（m/s）。")
    value = int(text)
    if not (1 <= value <= 99):
        raise SpeedValidationError("速度必须为 1–99 的整数（m/s）。")
    return value


def calculate_flight_time(distance_m: float, speed_m_s: int) -> FlightTimeResult:
    """按完整精度距离与整数速度计算飞行时间。"""
    if isinstance(speed_m_s, bool) or not isinstance(speed_m_s, int):
        raise FlightTimeCalculationError("速度必须是 1–99 的整数。")
    if not (1 <= speed_m_s <= 99):
        raise FlightTimeCalculationError("速度必须在 1–99 m/s 之间。")
    if isinstance(distance_m, bool) or not isinstance(distance_m, (int, float)):
        raise FlightTimeCalculationError("距离参数无效。")
    if not math.isfinite(distance_m) or distance_m < 0:
        raise FlightTimeCalculationError("距离必须为有限非负数值。")

    exact_seconds = distance_m / speed_m_s
    if not math.isfinite(exact_seconds):
        raise FlightTimeCalculationError("飞行时间计算结果无效。")
    rounded_seconds = math.ceil(exact_seconds)
    if rounded_seconds >= MAX_DISPLAY_SECONDS + 1:
        raise FlightTimeLimitError("飞行时间超过99小时")

    return FlightTimeResult(
        distance_m=float(distance_m),
        speed_m_s=speed_m_s,
        exact_seconds=float(exact_seconds),
        rounded_seconds=rounded_seconds,
        hhmmss=format_hhmmss(rounded_seconds),
    )


def format_hhmmss(total_seconds: int) -> str:
    """将整数秒格式化为 HH:MM:SS；上限 359999 秒（99:59:59）。"""
    if isinstance(total_seconds, bool) or not isinstance(total_seconds, int):
        raise FlightTimeCalculationError("秒数必须是整数。")
    if total_seconds < 0 or total_seconds > MAX_DISPLAY_SECONDS:
        raise FlightTimeLimitError("飞行时间超过99小时")
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"