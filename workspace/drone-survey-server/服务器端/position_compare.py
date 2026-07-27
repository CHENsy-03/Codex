# -*- coding: utf-8 -*-
"""
位置比对模块 — 三组 A/B/C 定位数据精度校验 (E/N/U 格式 + 5cm 阈值)
"""
import math
from typing import Dict, Tuple


def _enu_distance(a: dict, b: dict) -> Tuple[float, float, float]:
    """计算两点间的三轴距离差 (E, N, U) 单位: m

    E = 东向距离 = 经度差 * cos(平均纬度) * 111320
    N = 北向距离 = 纬度差 * 111320
    U = 高度差
    """
    lat1, lng1 = float(a.get("lat", 0)), float(a.get("lng", 0))
    lat2, lng2 = float(b.get("lat", 0)), float(b.get("lng", 0))
    alt1, alt2 = float(a.get("alt", 0)), float(b.get("alt", 0))

    mean_lat = math.radians((lat1 + lat2) / 2)
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)

    n = d_lat * 111320          # 北向距离 (m)
    e = d_lng * 111320 * math.cos(mean_lat)  # 东向距离 (m)
    u = alt2 - alt1             # 高度差 (m)

    return e, n, u


def compare_position(A: dict, B: dict, C: dict,
                     threshold: float = 0.05) -> Tuple[bool, dict]:
    """比较三组定位数据 A/B/C 的精度差是否全部小于阈值

    Args:
        A/B/C: 每组包含 {"lat", "lng", "alt", "e", "n", "u"}
        threshold: 阈值，单位 m，默认 0.05 (5cm)

    Returns:
        (passed, details)
        passed: True 表示全部通过
        details: {
            "ab": {"e": ..., "n": ..., "u": ...},
            "ac": {"e": ..., "n": ..., "u": ...},
            "bc": {"e": ..., "n": ..., "u": ...},
            "max_diff": 最大差值,
        }
    """
    ab = _enu_distance(A, B)
    ac = _enu_distance(A, C)
    bc = _enu_distance(B, C)

    all_diffs = [abs(x) for d in [ab, ac, bc] for x in d]
    max_diff = max(all_diffs) if all_diffs else 0.0
    passed = max_diff < threshold

    details = {
        "ab": {"e": round(ab[0], 4), "n": round(ab[1], 4), "u": round(ab[2], 4)},
        "ac": {"e": round(ac[0], 4), "n": round(ac[1], 4), "u": round(ac[2], 4)},
        "bc": {"e": round(bc[0], 4), "n": round(bc[1], 4), "u": round(bc[2], 4)},
        "max_diff": round(max_diff, 4),
        "threshold": threshold,
    }
    return passed, details


if __name__ == "__main__":
    A = {"lat": 30.0, "lng": 120.5, "alt": 50.0}
    B = {"lat": 30.00001, "lng": 120.50001, "alt": 50.01}
    C = {"lat": 30.00002, "lng": 120.50002, "alt": 50.02}
    passed, details = compare_position(A, B, C)
    print(f"PASS: {passed}")
    print(f"Details: {details}")
    print(f"AB: E={details['ab']['e']:.4f}m N={details['ab']['n']:.4f}m U={details['ab']['u']:.4f}m")
    print(f"AC: E={details['ac']['e']:.4f}m N={details['ac']['n']:.4f}m U={details['ac']['u']:.4f}m")
    print(f"BC: E={details['bc']['e']:.4f}m N={details['bc']['n']:.4f}m U={details['bc']['u']:.4f}m")
