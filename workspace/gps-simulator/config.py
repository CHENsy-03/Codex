"""
模拟GPS定位脚本 - 配置文件

坐标预设和默认运行参数。
参考报文来源:
  - （公司版）GPGGA报文.txt  (坐标: 29.593N, 120.467E)
  - （宿舍版）GPGGA报文.txt  (坐标: 29.6002N, 120.5056E)
  - （宿舍版）BESTPOS报文.txt (坐标: 29.6002N, 120.5056E)
"""

# 坐标预设
PRESETS = {
    "dormitory": {
        "lat": 29.6002,
        "lon": 120.5056,
        "alt": 40.0,
        "geoid_sep": 10.306,
        "undulation": 10.3055,
        "gps_week": 2425,
        "gps_start_seconds": 11716.0,
        "description": "宿舍区坐标 (参考 宿舍版GPGGA/BESTPOS 报文)"
    },
    "company": {
        "lat": 29.593,
        "lon": 120.467,
        "alt": 150.0,
        "geoid_sep": 10.109,
        "undulation": 10.3055,
        "gps_week": 2425,
        "gps_start_seconds": 14717.0,
        "description": "公司区坐标 (参考 公司版GPGGA 报文)"
    }
}

# 默认运行参数
DEFAULT = {
    "update_rate_hz": 1.0,          # 更新频率 (Hz)
    "msg_types": ["GPGGA"],         # 报文类型: GPGGA / BESTPOS / [GPGGA, BESTPOS]
    "noise_std": 0.000005,          # 位置噪声标准差 (度), ~0.5m
    "alt_noise_std": 0.5,           # 高度噪声标准差 (米)
    "drift_sigma": 0.000001,        # 随机漂移步长 (度), ~0.1m/步
    "sv_min": 8,                    # 最少卫星数
    "sv_max": 16,                   # 最多卫星数
    "hdop_min": 0.8,                # 最小HDOP
    "hdop_max": 9.9,                # 最大HDOP
    "quality": 1,                   # GPS质量 (1=单点定位, 2=差分定位)
    "sol_types": ["SINGLE", "NARROW_INT", "NARROW_FLOAT"],
}
