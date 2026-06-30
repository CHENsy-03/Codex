#!/usr/bin/env python3
"""
模拟GPS定位脚本 - GPS报文生成器 (GPS Message Simulator)
基于真实GPGGA(NMEA 0183)和BESTPOS(NovAtel OEM7)报文格式生成模拟定位数据

参考报文来源:
  - （公司版）GPGGA报文.txt  (坐标: 29.593N, 120.467E)
  - （宿舍版）GPGGA报文.txt  (坐标: 29.6002N, 120.5056E)
  - （宿舍版）BESTPOS报文.txt  (坐标: 29.6002N, 120.5056E, NovAtel格式)
"""

import datetime

import argparse
import asyncio
import logging
import os
import math
import random
import time
import zlib

log = logging.getLogger('GPS.Simulator')


# ──────────────── NMEA 0183 Checksum ────────────────
def nmea_checksum(sentence: str) -> int:
    """计算NMEA校验和：对 $ 和 * 之间的所有字节做异或(XOR)."""
    cksum = 0
    for ch in sentence:
        cksum ^= ord(ch)
    return cksum


# ──────────────── Coordinate Conversion ──────────────
def dd_to_dmm(dec_deg: float, is_longitude: bool = False) -> str:
    """将十进制度数转换为 NMEA DDDMM.MMMMMMM 格式.
    纬度: DDMM.MMMMMMM (2位度)
    经度: DDDMM.MMMMMMM (3位度)
    """
    abs_deg = abs(dec_deg)
    deg = int(abs_deg)
    minutes = (abs_deg - deg) * 60.0
    if is_longitude:
        return f"{deg:03d}{minutes:010.7f}"
    else:
        return f"{deg:02d}{minutes:010.7f}"


# ──────────────── GPGGA Message ─────────────────────
def format_gpgga(utc_time_sec: float, lat_dd: float, lon_dd: float,
                 quality: int = 1, num_sv: int = 10, hdop: float = 2.5,
                 altitude: float = 50.0, geoid_sep: float = 10.306) -> str:
    """生成符合NMEA 0183标准的 $GPGGA 报文（含正确校验和）.

    格式: $GPGGA,<UTC时间>,<纬度>,<N/S>,<经度>,<E/W>,<质量>,<卫星数>,<HDOP>,<海拔>,M,<大地水准面>,M,,*<校验和>
    """
    # 格式化UTC时间 HHMMSS.SS
    hours = int(utc_time_sec // 3600) % 24
    minutes = int((utc_time_sec % 3600) // 60)
    seconds = utc_time_sec % 60
    time_str = f"{hours:02d}{minutes:02d}{seconds:05.2f}"

    # 纬度转换
    lat_str = dd_to_dmm(lat_dd)
    ns = 'N' if lat_dd >= 0 else 'S'

    # 经度转换
    lon_str = dd_to_dmm(lon_dd, is_longitude=True)
    ew = 'E' if lon_dd >= 0 else 'W'

    # 构建报文主体（不含 $ 和 *校验和）
    body = (f"GPGGA,{time_str},{lat_str},{ns},{lon_str},{ew},"
            f"{quality},{num_sv},{hdop:.1f},{altitude:.4f},M,{geoid_sep:.3f},M,,")

    cksum = nmea_checksum(body)
    return f"${body}*{cksum:02X}"


# ──────────────── BESTPOS Message (NovAtel OEM7) ─────
def bestpos_crc(data: str) -> str:
    """计算NovAtel BESTPOS 32位CRC (标准CRC-32).
    CRC计算范围: # 和 * 之间的所有ASCII字符（不含#和*本身）
    """
    crc = zlib.crc32(data.encode('ascii')) & 0xFFFFFFFF
    return f"{crc:08x}"


def format_bestpos(gps_week: int, gps_seconds: float, lat_dd: float, lon_dd: float,
                   altitude: float, sol_type: str = "SINGLE", undulation: float = 10.3055,
                   num_obs: int = 34, num_sv: int = 18) -> str:
    """生成符合NovAtel OEM7标准的 #BESTPOSA 报文（含正确CRC32）.

    格式: #BESTPOSA,<COM口>,0,60.0,FINESTEERING,<GPS周>,<GPS秒>,00000000,0000,1114;
          SOL_COMPUTED,<解类型>,<纬度>,<经度>,<高程>,<高程异常>,WGS84,
          <纬度标准差>,<经度标准差>,<高程标准差>,"",<差分龄期>,<解龄期>,
          <观测数>,<GPS L1>,<GPS L2>,<GPS L5>,143,0,0,25*<CRC32>
    """
    # 标准差（模拟真实噪声）
    sdev_lat = round(0.3 + random.uniform(0, 0.15), 4)
    sdev_lon = round(0.8 + random.uniform(0, 0.4), 4)
    sdev_alt = round(1.5 + random.uniform(0, 0.8), 4)

    diff_age = round(random.uniform(0, 0.5), 3)
    sol_age = round(100 + random.uniform(0, 20), 3)

    # GPS时间字符串: SSSSS.TTT
    gps_time_str = f"{gps_seconds:06.3f}"

    # 构建CRC数据区（#和*之间的所有内容）
    body = (f"BESTPOSA,COM3,0,60.0,FINESTEERING,{gps_week},{gps_time_str},00000000,0000,1114;"
            f"SOL_COMPUTED,{sol_type},{lat_dd:.11f},{lon_dd:.11f},{altitude:.4f},{undulation:.4f},WGS84,"
            f"{sdev_lat},{sdev_lon},{sdev_alt},\"\",{diff_age},{sol_age},"
            f"{num_obs},{num_sv},{num_sv},{num_sv},143,0,0,25")

    crc = bestpos_crc(body)
    return f"#{body}*{crc}"


# ──────────────── GPS Simulator ─────────────────────
class GpsSimulator:
    """GPS接收机模拟器 - 生成符合真实格式的GPGGA和BESTPOS定位报文."""

    def __init__(self, config: dict):
        self.lat = config.get('lat', 29.6002)       # 基准纬度
        self.lon = config.get('lon', 120.5056)      # 基准经度
        self.alt = config.get('alt', 40.0)           # 基准海拔 (米)
        self.geoid_sep = config.get('geoid_sep', 10.306)
        self.undulation = config.get('undulation', 10.3055)
        self.msg_types = config.get('msg_types', ['GPGGA'])
        self.update_rate_hz = config.get('update_rate_hz', 1.0)
        self.noise_std = config.get('noise_std', 0.000005)    # ~0.5m 位置噪声
        self.alt_noise_std = config.get('alt_noise_std', 0.5) # 高度噪声
        self.sv_range = config.get('sv_range', (8, 16))
        self.hdop_range = config.get('hdop_range', (0.8, 9.9))
        self.quality = config.get('quality', 1)
        self.sol_types = config.get('sol_types', ['SINGLE', 'NARROW_INT', 'NARROW_FLOAT'])

        # GPS时间追踪
        self._gps_week = config.get('gps_week', 2425)
        self._gps_seconds = config.get('gps_start_seconds', 11716.0)

        # 随机游走状态（模拟真实接收机的微小漂移）
        self._lat_drift = 0.0
        self._lon_drift = 0.0
        self._alt_drift = 0.0
        self._walk_sigma = config.get('drift_sigma', 0.000001)

        # 统计
        self.msg_count = 0
        self.start_time = time.time()

    def _step(self) -> tuple:
        """推进一步仿真状态，返回 (lat, lon, alt) 含噪声."""
        interval = 1.0 / self.update_rate_hz

        # GPS时间推进
        self._gps_seconds += interval
        if self._gps_seconds >= 604800:  # GPS周翻转
            self._gps_seconds -= 604800
            self._gps_week += 1

        # 随机游走（模拟接收机位置微小漂移）
        self._lat_drift += random.gauss(0, self._walk_sigma)
        self._lon_drift += random.gauss(0, self._walk_sigma)
        self._alt_drift += random.gauss(0, self.alt_noise_std * 0.1)

        # 含噪声的当前位置
        lat = self.lat + self._lat_drift + random.gauss(0, self.noise_std)
        lon = self.lon + self._lon_drift + random.gauss(0, self.noise_std)
        alt = self.alt + self._alt_drift + random.gauss(0, self.alt_noise_std)

        return lat, lon, alt

    def _utc_time(self) -> float:
        """从GPS时间推导当前UTC时刻（秒，从午夜开始）."""
        tod_seconds = self._gps_seconds % 86400  # GPS日内秒
        utc_tod = (tod_seconds - 18) % 86400     # GPS-UTC跳秒修正
        return utc_tod

    def generate_gpgga(self) -> str:
        """生成一条 $GPGGA 报文."""
        lat, lon, alt = self._step()
        utc = self._utc_time()
        num_sv = random.randint(*self.sv_range)
        hdop = round(random.uniform(*self.hdop_range), 1)

        return format_gpgga(
            utc_time_sec=utc, lat_dd=lat, lon_dd=lon,
            quality=self.quality, num_sv=num_sv, hdop=hdop,
            altitude=alt, geoid_sep=self.geoid_sep
        )

    def generate_bestpos(self) -> str:
        """生成一条 #BESTPOSA 报文."""
        lat, lon, alt = self._step()
        sol_type = random.choice(self.sol_types)
        num_obs = random.randint(30, 40)
        num_sv = random.randint(*self.sv_range)

        return format_bestpos(
            gps_week=self._gps_week, gps_seconds=self._gps_seconds,
            lat_dd=lat, lon_dd=lon, altitude=alt,
            sol_type=sol_type, undulation=self.undulation,
            num_obs=num_obs, num_sv=num_sv
        )

    def generate_message(self) -> str:
        """按配置的报文类型生成一条报文."""
        self.msg_count += 1

        if len(self.msg_types) == 1:
            msg_type = self.msg_types[0]
        else:
            msg_type = random.choice(self.msg_types)

        if msg_type == 'GPGGA':
            return self.generate_gpgga()
        else:
            return self.generate_bestpos()


# ──────────────── Main Runner ────────────────────────

# ──────────────── 城市坐标数据 ────────────────
CITY_DATA = {
    "绍兴": {
        "lat_min": 29.90, "lat_max": 30.12,
        "lon_min": 120.40, "lon_max": 120.85,
        "alt_min": 5.0,
        "alt_max": 15.0,
        "geoid_sep": 10.306,
    },
    "昭通_永善县": {
        "lat_min": 28.21, "lat_max": 28.25,
        "lon_min": 103.62, "lon_max": 103.66,
        "alt_min": 500.0,
        "alt_max": 2500.0,
        "geoid_sep": 10.306,
    },
    "昭通_威信县": {
        "lat_min": 27.83, "lat_max": 27.87,
        "lon_min": 105.03, "lon_max": 105.07,
        "alt_min": 500.0,
        "alt_max": 2500.0,
        "geoid_sep": 10.306,
    },
    "昭通_昭阳区": {
        "lat_min": 27.30, "lat_max": 27.34,
        "lon_min": 103.69, "lon_max": 103.73,
        "alt_min": 500.0,
        "alt_max": 2500.0,
        "geoid_sep": 10.306,
    },
    "昭通": {
        "lat_min": 26.90, "lat_max": 28.60,
        "lon_min": 102.93, "lon_max": 105.05,
        "alt_min": 500.0,
        "alt_max": 2000.0,
        "geoid_sep": 10.306,
    },
    "杭州": {
        "lat_min": 30.18, "lat_max": 30.45,
        "lon_min": 119.90, "lon_max": 120.35,
        "alt_min": 5.0,
        "alt_max": 20.0,
        "geoid_sep": 10.306,
    }
}



# 行政区域码数据 (来源: 行政区划（杭州，绍兴）.txt)
DISTRICT_DATA = {
    "杭州": [
        ("330102", "上城区", 120.16922, 30.24255),
        ("330105", "拱墅区", 120.13000, 30.32000),
        ("330106", "西湖区", 120.13000, 30.27000),
        ("330108", "滨江区", 120.20000, 30.20000),
        ("330109", "萧山区", 120.27000, 30.17000),
        ("330110", "余杭区", 120.30000, 30.42000),
        ("330111", "富阳区", 119.95000, 30.05000),
        ("330112", "临安区", 119.72000, 30.23000),
        ("330113", "临平区", 120.29922, 30.41915),
        ("330114", "钱塘区", 120.49394, 30.32304),
        ("330122", "桐庐县", 119.67000, 29.80000),
        ("330127", "淳安县", 119.03000, 29.60000),
        ("330182", "建德市", 119.28000, 29.48000),
    ],
    "昭通": [
        ("530602", "昭阳区", 103.706539, 27.320088),
        ("530621", "鲁甸县", 103.557870, 27.186694),
        ("530622", "巧家县", 102.930158, 26.908458),
        ("530623", "盐津县", 104.235061, 28.108800),
        ("530624", "大关县", 103.891459, 27.747993),
        ("530625", "永善县", 103.638047, 28.229089),
        ("530626", "绥江县", 103.961013, 28.599261),
        ("530627", "镇雄县", 104.873224, 27.441580),
        ("530628", "彝良县", 104.048398, 27.625418),
        ("530629", "威信县", 105.047039, 27.846554),
        ("530681", "水富市", 104.400000, 28.600000),
    ],
    "昭通_永善县": [
        ("530625", "永善县", 103.638047, 28.229089),
    ],
    "昭通_威信县": [
        ("530629", "威信县", 105.047039, 27.846554),
    ],
    "昭通_昭阳区": [
        ("530602", "昭阳区", 103.706539, 27.320088),
    ],
    "绍兴": [
        ("330602", "越城区", 120.58190, 29.98895),
        ("330603", "柯桥区", 120.49274, 30.08763),
        ("330604", "上虞区", 120.47608, 30.07804),
        ("330624", "新昌县", 120.90435, 29.49991),
        ("330681", "诸暨市", 120.23629, 29.71358),
        ("330683", "嵊州市", 120.82174, 29.58854),
    ]
}

def find_district(lat, lon, city):
    """根据坐标查找最近的行政区，返回 (名称, 代码)"""
    import math
    best_dist = float('inf')
    best_name, best_code = "", ""
    for code, name, dlon, dlat in DISTRICT_DATA.get(city, []):
        d = (lat - dlat) ** 2 + (lon - dlon) ** 2
        if d < best_dist:
            best_dist = d
            best_name, best_code = name, code
    return best_name, best_code


def generate_city_messages(mode, num_waypoints):
    if mode == 1:
        city_names = ["绍兴", "杭州"]
    elif mode == 2:
        city_names = ["绍兴"]
    else:
        city_names = ["杭州"]

    # 生成不重复的测量点位
    waypoints = []
    for _ in range(num_waypoints):
        city = random.choice(city_names)
        cd = CITY_DATA[city]
        lat = random.uniform(cd["lat_min"], cd["lat_max"])
        lon = random.uniform(cd["lon_min"], cd["lon_max"])
        alt = random.uniform(cd["alt_min"], cd["alt_max"])
        dist_name, dist_code = find_district(lat, lon, city)
        waypoints.append((lat, lon, alt, city, dist_name, dist_code))

    # 每个点位测量3次
    results = []
    base_time = 8 * 3600
    for wp_idx, (lat, lon, alt, city, dn, dc) in enumerate(waypoints):
        for meas_idx in range(3):
            utc_sec = base_time + (wp_idx * 3 + meas_idx)
            lat_m = lat + random.gauss(0, 0.000003)
            lon_m = lon + random.gauss(0, 0.000003)
            alt_m = alt + random.gauss(0, 0.3)
            sv = random.randint(8, 16)
            hdop = round(random.uniform(0.8, 9.9), 1)
            msg = format_gpgga(utc_sec, lat_m, lon_m, 1, sv, hdop, alt_m, 10.306)
            results.append((msg, city, wp_idx, dn, dc))
    return results
def _get_input(prompt):
    """安全获取用户输入，处理Ctrl+C返回None"""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None

def _get_number(prompt, default=10):
    """获取正整数输入，默认值10"""
    val = _get_input(prompt)
    if val is None:
        return None
    if val == "":
        return default
    if val.isdigit() and int(val) > 0:
        return int(val)
    return default

def _generate_save(cities, repeat, filename):
    """生成GPS报文并保存到文件"""
    num_points = _get_number("请输入测量点数（每个点测量3次，默认10个点）: ")
    if num_points is None:
        return
    meas_per = 6 if repeat else 3
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    random.seed()
    waypoints = []
    for _ in range(num_points):
        city = random.choice(cities)
        cd = CITY_DATA[city]
        lat = random.uniform(cd["lat_min"], cd["lat_max"])
        lon = random.uniform(cd["lon_min"], cd["lon_max"])
        alt = random.uniform(cd["alt_min"], cd["alt_max"])
        dist_name, dist_code = find_district(lat, lon, city)
        waypoints.append((lat, lon, alt, city, dist_name, dist_code))
    msgs = []
    base_time = 8 * 3600
    for wp_idx, (lat, lon, alt, city, _, _) in enumerate(waypoints):
        for meas_idx in range(meas_per):
            utc_sec = base_time + (wp_idx * meas_per + meas_idx)
            lat_m = lat + random.gauss(0, 0.000003)
            lon_m = lon + random.gauss(0, 0.000003)
            alt_m = alt + random.gauss(0, 0.3)
            sv = random.randint(8, 16)
            hdop = round(random.uniform(0.8, 9.9), 1)
            msg = format_gpgga(utc_sec, lat_m, lon_m, 1, sv, hdop, alt_m)
            msgs.append((msg, city, wp_idx))
    with open(out_path, "w", encoding="utf-8") as ff:
        for msg, _, _ in msgs:
            ff.write(msg + "\n")
            print(msg)
    with open(out_path, "a", encoding="utf-8") as ff:
        ff.write("\n-----\n")
        ff.write("测量位置明细:\n")
        prev_city, prev_idx, start_line = None, None, 1
        for i, (_, city, wp_idx) in enumerate(msgs):
            if city != prev_city or wp_idx != prev_idx:
                if prev_city is not None:
                    ff.write(f"第{start_line}-{i}行: {prev_city}(点{prev_idx+1})\n")
                prev_city, prev_idx, start_line = city, wp_idx, i + 1
        ff.write(f"第{start_line}-{len(msgs)}行: {prev_city}(点{prev_idx+1})\n")
        ff.write("\n行政区域码:\n")
        for wp_idx in range(num_points):
            _, _, _, _, dn, dc = waypoints[wp_idx]
            start = wp_idx * meas_per + 1
            end = min((wp_idx + 1) * meas_per, len(msgs))
            ff.write(f"第{start}-{end}行: {dc} {dn}\n")
        city_pts = {}
        city_cnt = {}
        city_rep = {}
        for _, city, wp_idx in msgs:
            if city not in city_pts:
                city_pts[city] = set()
                city_cnt[city] = 0
                city_rep[city] = {}
            city_pts[city].add(wp_idx)
            city_cnt[city] += 1
            if repeat:
                if wp_idx not in city_rep[city]:
                    city_rep[city][wp_idx] = 0
                city_rep[city][wp_idx] += 1
        ff.write(f"共{num_points}个测量点，{len(msgs)}条报文\n")
        parts = [f"{c}{len(city_pts[c])}个测量点" for c in sorted(city_pts.keys())]
        ff.write("，".join(parts) + "\n")
        if repeat:
            rep_parts = []
            for c in sorted(city_rep.keys()):
                reps = city_rep[c]
                details = [f"点{wp+1}的{cnt}次测量" for wp, cnt in sorted(reps.items())]
                rep_parts.append(f"{c}{len(reps)}个，{'，'.join(details)}")
            ff.write(f"重复测量点：{'；'.join(rep_parts)}\n")
        # 按行政区域统计
        dist_counts = {}
        for wp_idx in range(num_points):
            dn = waypoints[wp_idx][4]
            dist_counts[dn] = dist_counts.get(dn, 0) + 1
        dist_parts = [f"{dn}:{cnt}" for dn, cnt in sorted(dist_counts.items())]
        sep = "，"
        ff.write(f"[{sep.join(dist_parts)}]\n")
    print(f"\n完成！共生成 {len(msgs)} 条报文")
    print(f"已保存到: {out_path}")

def run_menu_mode():
    """菜单模式主入口 - 多级菜单"""
    while True:
        print("=" * 60)
        print("  模拟GPS定位脚本 - 菜单模式")
        print("=" * 60)
        print()
        print("一级菜单 - 请选择区域模式:")
        print("  1. 随机地区生成（绍兴/杭州混合）")
        print("  2. 精确地区生成（指定城市）")
        print("  q. 退出")
        print()
        choice = _get_input("请输入 1/2/q: ")
        if choice is None:
            return
        if choice == "1":
            _random_submenu()
        elif choice == "2":
            _specific_submenu()
        elif choice.lower() == "q":
            print("已退出")
            return
        else:
            print("无效选择，请重新输入")

def _random_submenu():
    """随机地区生成二级菜单"""
    print()
    print("二级菜单 - 选择生成方式:")
    print("  1. 随机不重复（每个点测量3次）")
    print("  2. 随机且有重复（每个点测量6次）")
    print("  b. 返回上一级")
    choice = _get_input("请输入 1/2/b: ")
    if choice is None:
        return
    if choice == "1":
        _generate_save(["绍兴", "杭州"], False, "随机生成（不重复）.txt")
    elif choice == "2":
        _generate_save(["绍兴", "杭州"], True, "随机生成（含重复）.txt")
    elif choice.lower() == "b":
        return
    else:
        print("无效选择")

def _specific_submenu():
    """精确地区生成二级菜单"""
    print()
    print("二级菜单 - 选择城市:")
    print("  1. 绍兴(SX)")
    print("  2. 杭州(HZ)")
    print("  3. 昭通(ZT)")
    print("  4. 自定义地区（预留）")
    print("  b. 返回上一级")
    city = _get_input("请输入 1/2/3/b: ")
    if city is None:
        return
    cities, prefix = None, None
    if city == "1":
        cities, prefix = ["绍兴"], "SX"
    elif city == "2":
        cities, prefix = ["杭州"], "HZ"
    elif city == "3":
        print()
        print("昭通区县选择:")
        print("  1. 永善县")
        print("  2. 威信县")
        print("  3. 昭阳区")
        print("  b. 返回上一级")
        sub = _get_input("请输入 1/2/3/b: ")
        if sub is None:
            return
        if sub == "1":
            cities, prefix = ["昭通_永善县"], "ZT_YS"
        elif sub == "2":
            cities, prefix = ["昭通_威信县"], "ZT_WX"
        elif sub == "3":
            cities, prefix = ["昭通_昭阳区"], "ZT_ZY"
        elif sub.lower() == "b":
            return
        else:
            print("无效选择")
            return
    elif city == "4":
        print("\n【自定义地区】功能预留，尚未实现。代码中已预留扩展位，后续可在CITY_DATA中添加新城市。")
        return
    elif city.lower() == "b":
        return
    else:
        print("无效选择")
        return
    print()
    print("三级菜单 - 选择生成方式:")
    print("  1. 不重复（每个点测量3次）")
    print("  2. 含重复（每个点测量6次）")
    print("  b. 返回上一级")
    rep = _get_input("请输入 1/2/b: ")
    if rep is None:
        return
    if rep == "1":
        _generate_save(cities, False, f"{prefix}随机生成（不重复）.txt")
    elif rep == "2":
        _generate_save(cities, True, f"{prefix}随机生成（含重复）.txt")
    elif rep.lower() == "b":
        return
    else:
        print("无效选择")


async def main():
    parser = argparse.ArgumentParser(
        description='模拟GPS定位脚本 - 生成符合真实格式的GPGGA/BESTPOS定位报文',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 每秒输出1条GPGGA报文（使用宿舍区坐标，默认）
  python gps_simulator.py

  # 每秒输出10条BESTPOS报文
  python gps_simulator.py --rate 10 --type BESTPOS

  # 使用公司坐标（参考（公司版）GPGGA报文.txt）
  python gps_simulator.py --preset company

  # 同时输出两种报文并通过TCP发送
  python gps_simulator.py --rate 5 --type BOTH --tcp-host localhost --tcp-port 9001

  # 生成1000条GPGGA报文并保存到文件
  python gps_simulator.py --rate 20 --type GPGGA --count 1000 --output gpgga_output.txt

报文格式参考:
  GPGGA:  $GPGGA,<UTC时间>,<纬度>,<N/S>,<经度>,<E/W>,<质量>,<卫星数>,<HDOP>,<海拔>,M,<大地水准面>,M,,*<NMEA校验和>
  BESTPOS: #BESTPOSA,COM3,0,60.0,FINESTEERING,<GPS周>,<GPS秒>,...;<解状态>,<解类型>,<纬度>,<经度>,<高程>,...*<CRC32>
        """
    )
    parser.add_argument('--rate', '-r', type=float, default=1.0,
                        help='报文更新频率 (Hz)，默认 1.0')
    parser.add_argument('--type', '-t', choices=['GPGGA', 'BESTPOS', 'BOTH'],
                        default='GPGGA', help='报文类型，默认 GPGGA')
    parser.add_argument('--preset', '-p', choices=['dormitory', 'company'],
                        default='dormitory', help='坐标预设 (dormitory=宿舍区, company=公司区)')
    parser.add_argument('--count', '-c', type=int, default=0,
                        help='发送报文数量 (0=持续发送)')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='输出到文件 (默认输出到控制台)')
    parser.add_argument('--tcp-host', type=str, default=None,
                        help='TCP发送目标主机 (可选)')
    parser.add_argument('--tcp-port', type=int, default=9001,
                        help='TCP发送目标端口 (默认 9001)')
    parser.add_argument('--lat', type=float, default=None,
                        help='自定义基准纬度 (十进制度)')
    parser.add_argument('--lon', type=float, default=None,
                        help='自定义基准经度 (十进制度)')
    parser.add_argument('--alt', type=float, default=None,
                        help='自定义基准海拔 (米)')
    parser.add_argument('--noise', type=float, default=0.000005,
                        help='位置噪声标准差 (度)，默认 0.000005 (~0.5m)')
    parser.add_argument('--sv-min', type=int, default=8,
                        help='最少卫星数 (默认 8)')
    parser.add_argument('--sv-max', type=int, default=16,
                        help='最多卫星数 (默认 16)')
    parser.add_argument('--menu', action='store_true',
                        help='交互式菜单模式')
    parser.add_argument('--mode', type=int, choices=[1, 2, 3],
                        help='直接运行模式: 1=随机不重复, 2=绍兴, 3=杭州')
    parser.add_argument('--debug', action='store_true',
                            help='开启调试日志')

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s'
    )

    # ── 菜单/模式分发 ──
    if args.menu or not args.mode:
        run_menu_mode()
        return
    if args.mode:
        fnames = {1: "随机生成（不重复）.txt", 2: "SX随机生成.txt", 3: "HZ随机生成.txt"}
        fname = fnames[args.mode]
        sdir = os.path.dirname(os.path.abspath(__file__))
        opath = os.path.join(sdir, fname)
        print(f"模式 {args.mode}: 正在生成...")
        msgs = generate_city_messages(args.mode, 10)
        # 统计每个城市出现的点位
        city_points = {}
        for _, city, wp_idx, *__ in msgs:
            if city not in city_points:
                city_points[city] = set()
            city_points[city].add(wp_idx)
        total_points = sum(len(v) for v in city_points.values())

        with open(opath, "w", encoding="utf-8") as f:
            for msg, *__ in msgs:
                f.write(msg + "\n")
        with open(opath, "a", encoding="utf-8") as f:
            f.write("\n-----\n")
            if args.mode == 1:
                f.write("测量位置明细:\n")
                prev_city, prev_idx, start_line = None, None, 1
                for i, (_, city, wp_idx, *__) in enumerate(msgs):
                    if city != prev_city or wp_idx != prev_idx:
                        if prev_city is not None:
                            f.write(f"“{start_line}-{i}”行: {prev_city}(点{prev_idx+1})\n")
                        prev_city, prev_idx, start_line = city, wp_idx, i + 1
                f.write(f"第{start_line}-{len(msgs)}行: {prev_city}(点{prev_idx+1})\n")
                f.write(f"共{total_points}个测量点，{len(msgs)}条报文\n")
                f.write("\n行政区域码:\n")
                for wp_idx in range(len(msgs) // 3):
                    dn = msgs[wp_idx * 3][3]
                    dc = msgs[wp_idx * 3][4]
                    s = wp_idx * 3 + 1
                    e = (wp_idx + 1) * 3
                    f.write(f"第{s}-{e}行: {dc} {dn}\n")

                city_lines = {}
                for _, city, *__ in msgs:
                    city_lines[city] = city_lines.get(city, 0) + 1
                city_line = ""
                for city, cnt in city_lines.items():
                    if city_line:
                        city_line += "，"
                    city_line += f"{city}{cnt}条"
                f.write(city_line + "\n")
                # 按行政区域统计
                dist_counts = {}
                seen = set()
                for _, _, wp_idx, dn, _ in msgs:
                    if (dn, wp_idx) not in seen:
                        seen.add((dn, wp_idx))
                        dist_counts[dn] = dist_counts.get(dn, 0) + 1
                dist_parts = [f"{dn}:{cnt}" for dn, cnt in sorted(dist_counts.items())]
                sep = "，"
                f.write(f"[{sep.join(dist_parts)}]\n")
            else:
                summary_parts = [f"{c}({len(pts)}个点)" for c, pts in city_points.items()]
                f.write(f"测量位置: {chr(44).join(summary_parts)}\n")
                f.write(f"共{total_points}个测量点，{len(msgs)}条报文\n")
                f.write("\n行政区域码:\n")
                for wp_idx in range(len(msgs) // 3):
                    dn = msgs[wp_idx * 3][3]
                    dc = msgs[wp_idx * 3][4]
                    s = wp_idx * 3 + 1
                    e = (wp_idx + 1) * 3
                    f.write(f"第{s}-{e}行: {dc} {dn}\n")
                # 按行政区域统计
                dist_counts = {}
                seen = set()
                for _, _, wp_idx, dn, _ in msgs:
                    if (dn, wp_idx) not in seen:
                        seen.add((dn, wp_idx))
                        dist_counts[dn] = dist_counts.get(dn, 0) + 1
                dist_parts = [f"{dn}:{cnt}" for dn, cnt in sorted(dist_counts.items())]
                sep = "，"
                f.write(f"[{sep.join(dist_parts)}]\n")

        print(f"完成！共 {len(msgs)} 条报文，已保存到: {opath}")
        return
    # ── 坐标预设 ──
    presets = {
        'dormitory': {
            'lat': 29.6002,
            'lon': 120.5056,
            'alt': 40.0,
            'geoid_sep': 10.306,
            'undulation': 10.3055,
            'gps_week': 2425,
            'gps_start_seconds': 11716.0,
            'description': '宿舍区坐标 (参考 宿舍版GPGGA/BESTPOS 报文)'
        },
        'company': {
            'lat': 29.593,
            'lon': 120.467,
            'alt': 150.0,
            'geoid_sep': 10.109,
            'undulation': 10.3055,
            'gps_week': 2425,
            'gps_start_seconds': 14717.0,
            'description': '公司区坐标 (参考 公司版GPGGA 报文)'
        }
    }

    preset = presets[args.preset]
    config = {
        'lat': args.lat if args.lat is not None else preset['lat'],
        'lon': args.lon if args.lon is not None else preset['lon'],
        'alt': args.alt if args.alt is not None else preset['alt'],
        'geoid_sep': preset['geoid_sep'],
        'undulation': preset['undulation'],
        'gps_week': preset['gps_week'],
        'gps_start_seconds': preset['gps_start_seconds'],
        'update_rate_hz': args.rate,
        'noise_std': args.noise,
        'alt_noise_std': 0.5,
        'sv_range': (args.sv_min, args.sv_max),
        'hdop_range': (0.8, 9.9),
        'quality': 1,
        'drift_sigma': 0.000001,
        'sol_types': ['SINGLE', 'NARROW_INT', 'NARROW_FLOAT'],
    }

    if args.type == 'BOTH':
        config['msg_types'] = ['GPGGA', 'BESTPOS']
    else:
        config['msg_types'] = [args.type]

    # ── 初始化TCP发送器 ──
    sender = None
    if args.tcp_host:
        try:
            from sender import TcpSender
            sender = TcpSender(args.tcp_host, args.tcp_port)
            await sender.start()
        except Exception as e:
            log.warning(f"TCP连接失败: {e} (继续使用控制台输出)")

    # ── 初始化模拟器 ──
    sim = GpsSimulator(config)

    # ── 输出文件 ──
    out_file = None
    if args.output:
        out_file = open(args.output, 'w', encoding='utf-8')

    # ── 打印头部信息 ──
    msg_type_label = '+'.join(config['msg_types'])
    print("=" * 70)
    print(f"  模拟GPS定位脚本 v1.0 - GPS Message Simulator")
    print(f"  坐标预设: {args.preset} - {preset['description']}")
    print(f"  基准坐标: ({config['lat']:.4f}, {config['lon']:.4f}), 海拔 {config['alt']:.1f}m")
    print(f"  报文类型: {msg_type_label}  @  {args.rate} Hz")
    if args.count > 0:
        print(f"  发送数量: {args.count} 条")
    else:
        print(f"  发送数量: 持续发送 (Ctrl+C 停止)")
    print("=" * 70)

    # ── 主循环 ──
    count = 0
    try:
        while True:
            if args.count > 0 and count >= args.count:
                break

            msg = sim.generate_message()
            count += 1

            # 输出
            if out_file:
                out_file.write(msg + '\n')
                out_file.flush()
            else:
                print(f"[{count:6d}] {msg}")

            # TCP发送
            if sender:
                try:
                    await sender.send(msg)
                except Exception as e:
                    log.warning(f"TCP发送错误: {e}")

            await asyncio.sleep(1.0 / args.rate)

    except (asyncio.CancelledError, KeyboardInterrupt):
        log.info("用户中断")
    finally:
        elapsed = time.time() - sim.start_time
        effective_rate = count / elapsed if elapsed > 0 else 0

        # 构建结果摘要
        result_lines = []
        result_lines.append("=" * 70)
        ts_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result_lines.append(f"  结束时间: {ts_str}")
        result_lines.append(f"  运行时间: {elapsed:.1f} 秒")
        result_lines.append(f"  发送报文: {count} 条")
        result_lines.append(f"  平均速率: {effective_rate:.1f} Hz")
        result_lines.append(f"  报文类型: {msg_type_label}")
        result_lines.append(f"  基准坐标: ({config["lat"]:.4f}, {config["lon"]:.4f})")
        result_lines.append("=" * 70)

        # 保存到运行结果.txt
        script_dir = os.path.dirname(os.path.abspath(__file__))
        result_path = os.path.join(script_dir, "运行结果.txt")
        try:
            with open(result_path, "a", encoding="utf-8") as rf:
                rf.write("\n".join(result_lines) + "\n\n")
        except Exception as e:
            log.warning(f"保存结果失败: {e}")
        print("\n".join(result_lines))

        if out_file:
            out_file.close()
        if sender:
            await sender.close()


if __name__ == "__main__":
    asyncio.run(main())
