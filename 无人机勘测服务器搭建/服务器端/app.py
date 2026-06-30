"""
位置勘测数据管理系统
====================
定位器读取经纬度+高度，获取 H/V/D 位置差分精度，A/B/C 三组不重复数据。
三组为一轮勘测，自动编号（如 HW-1），精度比较 -> 去重 -> 存入分部 -> 上传总部。
分部服务器：Home-HW（杭州）、Home-SX（绍兴）
总部服务器：Home-ALL
数据库引擎：DuckDB（应用层分片）
"""

import json
import re
import time
import random
import sys
import argparse
import logging
from logging_config import setup as setup_logging
setup_logging()
from typing import Dict, Tuple

from db_config import REGION_CONFIG, PRECISION_THRESHOLD
from shard_db import ShardDatabase
from main_db import MainDatabase
from position_compare import compare_position


# ============================================================
# 定位器模拟：读取位置值（经纬度 + 高度），H/V/D 精度
# ============================================================
def simulate_positioner() -> Dict:
    """模拟定位器在 1s 内读取位置数据。
    返回 {"lat": 纬度, "lng": 经度, "alt": 高度(m), "h": 水平精度(cm), "v": 垂直精度(cm), "d": 三维精度(cm)}
    """
    time.sleep(0.1)  # 模拟读数延迟
    return {
        "lat": round(random.uniform(29.0, 31.5), 6),   # 纬度
        "lng": round(random.uniform(118.0, 122.0), 6),  # 经度
        "alt": round(random.uniform(0, 500), 2),         # 高度(m)
        "h":   round(random.uniform(1.0, 8.0), 2),       # 水平精度(cm)
        "v":   round(random.uniform(1.0, 8.0), 2),       # 垂直精度(cm)
        "d":   round(random.uniform(1.0, 8.0), 2),       # 三维精度(cm)
    }


def input_group(label: str) -> Dict:
    """手动输入一组位置数据"""
    print(f"\n--- {label}组数据 ---")
    print("输入格式：纬度 经度 高度(m) H水平精度(cm) V垂直精度(cm) D三维精度(cm)")
    print("示例：30.25 120.16 50.0 3.2 2.8 4.1")
    while True:
        try:
            parts = input(f"{label}组> ").strip().split()
            if len(parts) != 6:
                print("错误：必须输入 6 个值（lat lng alt H V D）")
                continue
            vals = [float(x) for x in parts]
            return {
                "lat": vals[0], "lng": vals[1], "alt": vals[2],
                "h": vals[3], "v": vals[4], "d": vals[5],
            }
        except ValueError:
            print("错误：请输入有效数字")


# ============================================================
# 数据显示
# ============================================================
def print_group(label: str, g: Dict):
    e = float(g.get('e', g.get('h', 0)))
    n = float(g.get('n', g.get('v', 0)))
    u = float(g.get('u', g.get('d', 0)))
    print(f"  {label}: lat={g.get('lat',0):.6f}, lng={g.get('lng',0):.6f}, alt={g.get('alt',0):.2f}m")
    print(f"         北向={n*100:.2f}cm  东向={e*100:.2f}cm  高度={u*100:.2f}cm")


def print_record(record: Dict):
    """打印一条勘测记录"""
    print(f"  批次ID: {record['batch_id']}")
    print(f"  地区: {record['region_code']}  第{record['round_number']}轮 类型: {record['survey_type']}")
    print_group("A", {"lat": record["a_lat"], "lng": record["a_lng"], "alt": record["a_alt"],
                       "e": record.get("a_e",0), "n": record.get("a_n",0), "u": record.get("a_u",0)})
    print_group("B", {"lat": record["b_lat"], "lng": record["b_lng"], "alt": record["b_alt"],
                       "e": record.get("b_e",0), "n": record.get("b_n",0), "u": record.get("b_u",0)})
    print_group("C", {"lat": record["c_lat"], "lng": record["c_lng"], "alt": record["c_alt"],
                       "e": record.get("c_e",0), "n": record.get("c_n",0), "u": record.get("c_u",0)})
    print(f"  AB: E差{record.get('ab_e',0):.4f}m N差{record.get('ab_n',0):.4f}m U差{record.get('ab_u',0):.4f}m")
    print(f"  AC: E差{record.get('ac_e',0):.4f}m N差{record.get('ac_n',0):.4f}m U差{record.get('ac_u',0):.4f}m")
    print(f"  BC: E差{record.get('bc_e',0):.4f}m N差{record.get('bc_n',0):.4f}m U差{record.get('bc_u',0):.4f}m")
    print(f"  位置正确: {'是' if record['is_correct'] else '否'}  时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(record['survey_time']))) if record.get('survey_time') else 'N/A'}")


# ============================================================
# 主菜单
# ============================================================
def main():
    print("=" * 55)
    print("  勘测系统服务器 v0.1.1 — V4-Local 工业级测试引擎 (5.docx)")
    print("=" * 55)

    while True:
        print("\n请选择操作：")
        print("  1. 手动录入勘测数据（A/B/C 三组）")
        print("  2. 模拟定位器自动录入")
        print("  3. 查看分部服务器数据")
        print("  4. 查看总部服务器数据")
        print("  5. 查看总部汇总统计")
        print("  6. 图表/Excel 数据导入（JSON/Excel 接口）")
        print("  7. 网络健康检查区 (Check Zone)")
        print("  8. 数据管理 (删除/清除缓存)")
        print("  9. 系统升级功能 (重复检测/熔断/统计API)")
        print("  A. V4-Local EventBus 状态与回放")
        print("  B. V4-Local CLI 测试引擎")
        print("  C. V4-Local GPS 回放系统")
        print("  D. V4-Local 插件管理")
        print("  0. 退出")

        choice = input("\n请输入选择: ").strip()

        if choice == "0":
            print("退出系统")
            break

        elif choice == "1":
            _manual_input()

        elif choice == "2":
            _auto_simulate()

        elif choice == "3":
            _view_shard()

        elif choice == "4":
            _view_main()

        elif choice == "5":
            _view_summary()

        elif choice == "6":
            _chart_import()
        elif choice == "7":
            _show_check_zone()
        elif choice == "8":
            _data_management()

        elif choice == "8":
            _data_management()
        elif choice == "9":
            _upgrade_menu()
        elif choice == "A" or choice == "a":
            _eventbus_menu()
        elif choice == "B" or choice == "b":
            _cli_test_menu()
        elif choice == "C" or choice == "c":
            _gps_replay_menu()
        elif choice == "D" or choice == "d":
            _plugin_menu()
        elif choice == "E" or choice == "e":
            _result_service_menu()
        else:
            print("无效选择，请重新输入")


# ============================================================
# 操作实现
# ============================================================
def _select_region() -> str:
    """选择地区"""
    print("\n可用地区：")
    keys = list(REGION_CONFIG.keys())
    for i, k in enumerate(keys, 1):
        cfg = REGION_CONFIG[k]
        print(f"  {i}. {cfg['name']} ({cfg['code']}) - 农村高度范围: "
              f"{cfg['rural_alt_min']}~{cfg['rural_alt_max']}m")
    while True:
        try:
            idx = int(input("请选择地区: ").strip()) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except ValueError:
            pass
        print("无效选择")


def _do_survey(region_code: str, A: Dict, B: Dict, C: Dict) -> Tuple[bool, str]:
    """执行一次完整勘测流程"""
    cfg = REGION_CONFIG[region_code]
    print(f"\n地区: {cfg['name']} ({cfg['code']})")
    print_group("A", A)
    print_group("B", B)
    print_group("C", C)

    # E/N/U 精度比较
    passed, details = compare_position(A, B, C, threshold=PRECISION_THRESHOLD)
    ab = details["ab"]; ac = details["ac"]; bc = details["bc"]
    th_cm = int(PRECISION_THRESHOLD * 100)

    print(f"\n精度比较（阈值< {th_cm}cm）：")
    print(f"  AB: 北向差{ab['n']*100:.2f}cm  东向差{ab['e']*100:.2f}cm  高度差{ab['u']*100:.2f}cm")
    print(f"  AC: 北向差{ac['n']*100:.2f}cm  东向差{ac['e']*100:.2f}cm  高度差{ac['u']*100:.2f}cm")
    print(f"  BC: 北向差{bc['n']*100:.2f}cm  东向差{bc['e']*100:.2f}cm  高度差{bc['u']*100:.2f}cm")
    print(f"  最大差值: {details['max_diff']*100:.2f}cm")

    if not passed:
        print("\n[结果] 勘测失败：数据未保存")
        return False, "勘测失败"

    # 生成批次ID并存入数据库
    with ShardDatabase(region_code) as db:
        import time as _t
        st = int(_t.time())
        n = 1
        while True:
            batch_id = f"{region_code[:2].upper()}-{n}"
            existing = db.get_gps_by_batch(batch_id)
            if not existing: break
            n += 1
        ab_t = (ab['e'], ab['n'], ab['u'])
        ac_t = (ac['e'], ac['n'], ac['u'])
        bc_t = (bc['e'], bc['n'], bc['u'])
        db.save_survey(batch_id, A, B, C, region_code, n, True, ab_t, ac_t, bc_t, "", st)

    print(f"\n[结果] 勘测成功！批次ID: {batch_id}")
    return True, f"勘测成功 {batch_id}"


def _manual_input():
    """手动录入三组数据"""
    region_code = _select_region()
    print("\n输入三组不重复的勘测数据：")
    A = input_group("A")
    B = input_group("B")
    C = input_group("C")
    _do_survey(region_code, A, B, C)


def _auto_simulate():
    """模拟定位器自动录入"""
    region_code = _select_region()
    print("\n模拟定位器读取（1s 内读取位置值）...")

    A = simulate_positioner()
    time.sleep(0.3)
    B = simulate_positioner()
    time.sleep(0.3)
    C = simulate_positioner()

    # 让三组数据在同一位置附近（模拟同一轮勘测），但精度值不同
    base_lat, base_lng, base_alt = A["lat"], A["lng"], A["alt"]
    B["lat"], B["lng"], B["alt"] = base_lat, base_lng, base_alt
    C["lat"], C["lng"], C["alt"] = base_lat, base_lng, base_alt

    _do_survey(region_code, A, B, C)


def _view_shard():
    """查看分部数据"""
    region_code = _select_region()
    cfg = REGION_CONFIG[region_code]

    with ShardDatabase(region_code) as db:
        c = db.count_all()
        print(f"\n{cfg['name']}分部 ({cfg['code']}) 汇总：")
        print(f"  设备: {c['devices']}  GPS记录: {c['gps_records']}  结果: {c['results']}  日志: {c['logs']}")

        if c['gps_records'] > 0:
            show = input("\n是否查看详细数据（y/n）: ").strip().lower()
            if show == "y":
                from collections import defaultdict
                gps_list = db.get_all_gps(200)
                batches = defaultdict(dict)
                for r in gps_list:
                    batches[r.get('batch_id','?')][r.get('group_label','?')] = r
                for bid in sorted(batches, key=lambda x: str(x)):
                    grp = batches[bid]
                    a = grp.get('A', {}); b = grp.get('B', {}); c = grp.get('C', {})
                    print(f"  batch={bid}")
                    print(f"    A: 纬度={a.get('lat',0):.4f} 经度={a.get('lng',0):.4f}  东向={a.get('e',0):.3f}  北向={a.get('n',0):.3f}  高度={a.get('u',0):.3f}")
                    print(f"    B: 纬度={b.get('lat',0):.4f} 经度={b.get('lng',0):.4f}  东向={b.get('e',0):.3f}  北向={b.get('n',0):.3f}  高度={b.get('u',0):.3f}")
                    print(f"    C: 纬度={c.get('lat',0):.4f} 经度={c.get('lng',0):.4f}  东向={c.get('e',0):.3f}  北向={c.get('n',0):.3f}  高度={c.get('u',0):.3f}")


def _view_main_old():
    """查看总部数据（旧版兼容）"""
    _view_main()


def _view_summary():
    """查看总部汇总"""
    with MainDatabase() as db:
        s = db.get_summary()

        print("\n" + "=" * 40)
        print("  总部 (Home-ALL) 数据汇总")
        print("=" * 40)
        print(f"  GPS记录: {s.get('total_gps',0)}")
        print(f"  结果: {s.get('total_results',0)}")
        print(f"  正确: {s.get('correct',0)}  错误: {s.get('failed',0)}")
        if s.get("regions"):
            print("\n  按地区分布：")
            for r, cnt in s["regions"].items():
                print(f"    {r}: {cnt} 条")


def detect_file_format(path):
    """Detect file format by reading first line (not extension)"""
    ext = __import__("os").path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls"):
        return "excel"
    # Try UTF-8 first, fallback to GBK
    _enc = "utf-8-sig"
    _raw = None
    for _enc_try in ("utf-8-sig", "gbk"):
        try:
            _raw = open(path, "r", encoding=_enc_try).read(500)
            _enc = _enc_try
            break
        except UnicodeDecodeError:
            continue
    if _raw is None:
        return "csv"
    # Check for specific signatures anywhere in content
    if "#BESTPOSA" in _raw:
        return "bestposa"
    if "$GP" in _raw or "$GN" in _raw and 36 in [ord(c) for c in _raw[:5]]:
        return "nmea"
    # Check first non-comment line for JSON
    for _line in _raw.split(chr(10)):
        _s = _line.strip()
        if _s.startswith("[") or _s.startswith("{"):
            return "json"
        if _s:
            break
    if ext == ".json":
        return "json"
    return "csv"


def read_file_to_records(path):
    """Auto-detect file format, parse, return List[Dict] with A/B/C groups"""
    fmt = detect_file_format(path)
    if fmt == "excel":
        return _read_excel_survey_data(path)
    if fmt == "json":
        import json
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list) and all("A" in d for d in data):
            return data
        raise ValueError("JSON must be list of {{A:..., B:..., C:...}}")
    if fmt == "bestposa":
        return _read_bestpos_ascii(path)
    if fmt == "nmea":
        return _read_nmea_file(path)
    # CSV default
    return _read_csv_survey_data(path)


def _read_nmea_file(path):
    """Read NMEA 0183 file -> group GGA positions into A/B/C triples"""
    from plugins.nmea import NMEAParser
    fixes = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            r = NMEAParser.parse(line)
            if r and "lat" in r:
                r.setdefault("e", 0.5)
                r.setdefault("n", 0.6)
                r.setdefault("u", 1.5)
                fixes.append(r)
    if len(fixes) < 3:
        raise ValueError(f"Need at least 3 GGA fixes, found {len(fixes)}")
    records = []
    for i in range(0, len(fixes) - 2, 3):
        A_best, B_best, C_best = fixes[i], fixes[i+1], fixes[i+2]
        records.append({"batch_id": "BEST-" + str(i//3 + 1),
            "a_lat": A_best.get("lat",0), "a_lng": A_best.get("lng",0), "a_alt": A_best.get("alt",0),
            "a_e": A_best.get("e",0), "a_n": A_best.get("n",0), "a_u": A_best.get("u",0),
            "b_lat": B_best.get("lat",0), "b_lng": B_best.get("lng",0), "b_alt": B_best.get("alt",0),
            "b_e": B_best.get("e",0), "b_n": B_best.get("n",0), "b_u": B_best.get("u",0),
            "c_lat": C_best.get("lat",0), "c_lng": C_best.get("lng",0), "c_alt": C_best.get("alt",0),
            "c_e": C_best.get("e",0), "c_n": C_best.get("n",0), "c_u": C_best.get("u",0)})
    return records


def _read_excel_survey_data(path: str) -> list:
    """从 Excel 文件读取勘测数据，返回 List[Dict] 供 import_from_chart 使用。

    Excel 列名（第一行表头，顺序不敏感）：
      A_lat, A_lng, A_alt, A_h, A_v, A_d
      B_lat, B_lng, B_alt, B_h, B_v, B_d
      C_lat, C_lng, C_alt, C_h, C_v, C_d
      可选: survey_type (rural/urban)
    """
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)

    # 第一行：表头 -> 列名到索引的映射
    try:
        headers = [str(c).strip().lower() if c is not None else "" for c in next(rows_iter)]
    except StopIteration:
        wb.close()
        raise ValueError("Excel 文件为空")

    col_map = {}
    for i, h in enumerate(headers):
        h_clean = h.strip().lower()
        if h_clean:
            col_map[h_clean] = i

    # 验证必需的 18 个字段
    required = ["a_lat", "a_lng", "a_alt", "a_e", "a_n", "a_u",
                 "b_lat", "b_lng", "b_alt", "b_e", "b_n", "b_u",
                 "c_lat", "c_lng", "c_alt", "c_e", "c_n", "c_u"]
    missing = [c for c in required if c not in col_map]
    if missing:
        wb.close()
        raise ValueError(f"Excel 缺少必要列: {', '.join(missing)}")

    records = []
    row_num = 1  # 已跳过表头
    for row in rows_iter:
        row_num += 1
        # 跳过全空行
        if all(cell is None or (isinstance(cell, str) and cell.strip() == "") for cell in row):
            continue

        try:
            def val(name):
                v = row[col_map[name]]
                if v is None:
                    raise ValueError(f"第{row_num}行 {name} 为空")
                return float(v)
            record = {
                "A": {"lat": val("a_lat"), "lng": val("a_lng"), "alt": val("a_alt"),
                      "e": val("a_e"), "n": val("a_n"), "u": val("a_u")},
                "B": {"lat": val("b_lat"), "lng": val("b_lng"), "alt": val("b_alt"),
                      "e": val("b_e"), "n": val("b_n"), "u": val("b_u")},
                "C": {"lat": val("c_lat"), "lng": val("c_lng"), "alt": val("c_alt"),
                      "e": val("c_e"), "n": val("c_n"), "u": val("c_u")},
            }
            if "survey_type" in col_map:
                st_raw = row[col_map["survey_type"]]
                if st_raw is not None:
                    st = str(st_raw).strip().lower()
                    if st in ("rural", "urban"):
                        record["survey_type"] = st
            records.append(record)
        except (TypeError, IndexError, ValueError) as e:
            wb.close()
            raise ValueError(f"第{row_num}行数据格式错误: {e}")
    wb.close()

    if not records:
        raise ValueError("Excel 文件中没有有效数据行")

    return records



def _read_gga_survey_data(path: str) -> list:
    """Read $GPGGA file, group every 3 lines into A/B/C survey records"""
    from plugins.nmea import NMEAParser
    from position_compare import compare_position
    fixes = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            if line.startswith("$GPGGA") or line.startswith("$GNGGA"):
                r = NMEAParser.parse_gga(line)
                if r: fixes.append(r)
    surveys = []
    for i in range(0, len(fixes) - 2, 3):
        A, B, C = fixes[i], fixes[i+1], fixes[i+2]
        passed, details = compare_position(A, B, C, 0.05)
        ab = details["ab"]; ac = details["ac"]; bc = details["bc"]
        _hdop_a=round(A.get("hdop",5)*150,2)
        _hdop_b=round(B.get("hdop",5)*150,2)
        _hdop_c=round(C.get("hdop",5)*150,2)
        surveys.append({
            "batch_id": f"GGA-{i//3 + 1}",
            "a_lat": A["lat"], "a_lng": A["lng"], "a_alt": A.get("alt", 0),
            "a_e": _hdop_a, "a_n": _hdop_a, "a_u": round(_hdop_a*2,2),
            "b_lat": B["lat"], "b_lng": B["lng"], "b_alt": B.get("alt", 0),
            "b_e": _hdop_b, "b_n": _hdop_b, "b_u": round(_hdop_b*2,2),
            "c_lat": C["lat"], "c_lng": C["lng"], "c_alt": C.get("alt", 0),
            "c_e": _hdop_c, "c_n": _hdop_c, "c_u": round(_hdop_c*2,2),
        })
    return surveys

def _read_bestpos_ascii(path: str) -> list:
    """Read #BESTPOSA ASCII file -> list of A/B/C grouped records (optimized with regex)"""
    from plugins.bestpos import BESTPOSASCIIParser
    
    # Pre-compile regex patterns for faster parsing
    _BESTPOSA_LINE = re.compile(r"^#[A-Z]+,\S+,\d+,\S+,\S+,\S+,\S+,\S+,\S+,\S+,\S+,")
    _FLOAT_CHECK = re.compile(r"^-?\d+\.?\d*$")
    
    fixes = []
    _enc = "utf-8"
    try:
        open(path, "r", encoding=_enc).readline()
    except UnicodeDecodeError:
        _enc = "gbk"
    with open(path, "r", encoding=_enc) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if not _BESTPOSA_LINE.match(line):
                continue
            r = BESTPOSA_FAST_PARSE(line)
            if r:
                fixes.append(r)
    if not fixes:
        raise ValueError("No valid BESTPOS records found in file")
    # Group fixes by quality type
    # 按文件顺序分组（3条连续为1组），替代原按质量类型分组
    fixes.sort(key=lambda x: x.get("seq", 0))
    records = []
    for i in range(0, len(fixes) - 2, 3):
        A_best, B_best, C_best = fixes[i], fixes[i+1], fixes[i+2]
        records.append({"batch_id": "BEST-" + str(i//3 + 1),
            "a_lat": A_best.get("lat",0), "a_lng": A_best.get("lng",0), "a_alt": A_best.get("alt",0),
            "a_e": A_best.get("e",0), "a_n": A_best.get("n",0), "a_u": A_best.get("u",0),
            "b_lat": B_best.get("lat",0), "b_lng": B_best.get("lng",0), "b_alt": B_best.get("alt",0),
            "b_e": B_best.get("e",0), "b_n": B_best.get("n",0), "b_u": B_best.get("u",0),
            "c_lat": C_best.get("lat",0), "c_lng": C_best.get("lng",0), "c_alt": C_best.get("alt",0),
            "c_e": C_best.get("e",0), "c_n": C_best.get("n",0), "c_u": C_best.get("u",0)})
    return records


def BESTPOSA_FAST_PARSE(raw: str) -> dict or None:
    """Fast BESTPOSA line parser using pre-validated check"""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    raw = raw.strip()
    if not raw:
        return None
    
    # Quick validation: count commas
    _COMMA_COUNT = re.compile(r",")
    if len(_COMMA_COUNT.findall(raw)) < 23:
        return None
    
    parts = raw.split(",")
    if len(parts) < 24:
        return None
    
    # Fast numeric parsing with try/except
    try:
        lat = float(parts[11])
        lng = float(parts[12])
        alt = float(parts[13])
        std_lat = float(parts[16]) if parts[16] else 0.005
        std_lng = float(parts[17]) if parts[17] else 0.006
        std_hgt = float(parts[18]) if parts[18] else 0.015
        seq = float(parts[6]) if parts[6] else 0
    except (ValueError, IndexError):
        return None
    
    e_cm = round(std_lat * 100, 2)
    n_cm = round(std_lng * 100, 2)
    u_cm = round(std_hgt * 100, 2)
    
    pos_type = parts[10] if len(parts) > 10 else "UNKNOWN"
    quality = 4 if "INT" in pos_type else 2 if "FLOAT" in pos_type else 0
    
    return {
        "lat": round(lat, 6), "lng": round(lng, 6), "alt": round(alt, 2),
        "e": e_cm, "n": n_cm, "u": u_cm,
        "pos_type": pos_type, "quality": quality,
        "source": "BESTPOSA", "seq": seq
    }

def _read_csv_survey_data(path: str) -> list:
    """Read survey data from CSV/TXT file, return List[Dict] for import_from_chart.

    Headers (1st row, comma or tab separated):
      A_lat, A_lng, A_alt, A_h, A_v, A_d  (same for B/C groups)
      Optional: survey_type (rural/urban)
    """
    import csv

    required = ["a_lat", "a_lng", "a_alt", "a_e", "a_n", "a_u",
                 "b_lat", "b_lng", "b_alt", "b_e", "b_n", "b_u",
                 "c_lat", "c_lng", "c_alt", "c_e", "c_n", "c_u"]

    # Auto-detect delimiter
    with open(path, "r", encoding=_enc) as f:
        first_line = f.readline().strip()
    delimiter = "	" if "	" in first_line else ","

    records = []
    row_num = 0
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=delimiter)
        reader.fieldnames = [h.strip().lower() if h else "" for h in reader.fieldnames]

        missing = [c for c in required if c not in reader.fieldnames]
        if missing:
            raise ValueError("CSV missing columns: " + ", ".join(missing) +
                             ". Found: " + str([c for c in reader.fieldnames if c]))

        for row in reader:
            row_num += 1
            if not any(row.get(c, "").strip() for c in required):
                continue

            try:
                def get_val(name):
                    v = row.get(name, "").strip()
                    if v == "":
                        raise ValueError("Row " + str(row_num + 1) + " " + name + " is empty")
                    return float(v)

                record = {
                    "A": {"lat": get_val("a_lat"), "lng": get_val("a_lng"), "alt": get_val("a_alt"),
                          "e": get_val("a_e"), "n": get_val("a_n"), "u": get_val("a_u")},
                    "B": {"lat": get_val("b_lat"), "lng": get_val("b_lng"), "alt": get_val("b_alt"),
                          "e": get_val("b_e"), "n": get_val("b_n"), "u": get_val("b_u")},
                    "C": {"lat": get_val("c_lat"), "lng": get_val("c_lng"), "alt": get_val("c_alt"),
                          "e": get_val("c_e"), "n": get_val("c_n"), "u": get_val("c_u")},
                }

                st = row.get("survey_type", "").strip().lower()
                if st in ("rural", "urban"):
                    record["survey_type"] = st

                records.append(record)
            except (ValueError, TypeError) as e:
                raise ValueError("Row " + str(row_num + 1) + " data error: " + str(e))

    if not records:
        raise ValueError("No valid data rows in CSV file")

    return records

def _chart_import():
    """数据导入接口

    Supported formats:
    - JSON (.json) - file or paste
    - Excel (.xlsx / .xls)
    - CSV / TXT (.csv / .txt) - comma or tab separated
    """
    print("\n数据导入")
    print("支持格式:")
    print("  1) JSON 文件 (.json)")
    print("  2) Excel 文件 (.xlsx / .xls)")
    print("  3) CSV / TXT 文件 (.csv / .txt)")
    print("  4) JSON 手动粘贴")

    path = input("\n输入文件路径: ").strip().strip('"').strip("'")

    try:
        if path.lower() == "json":
            raw = input("粘贴 JSON 数据: ").strip()
            data = json.loads(raw)
        elif path.lower().endswith((".xlsx", ".xls")):
            data = _read_excel_survey_data(path)
        elif path.lower().endswith((".csv", ".txt")):
            # First line detection: BESTPOSA or CSV
            with open(path, "r", encoding="utf-8") as _fh:
                _first = _fh.readline().strip()
            if _first.startswith("#BESTPOSA"):
                data = _read_bestpos_ascii(path)
            elif _first.startswith("$GPGGA") or _first.startswith("$GNGGA"):
                data = _read_gga_survey_data(path)
            else:
                data = _read_csv_survey_data(path)
        else:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            data = json.loads(raw)

        if not isinstance(data, list):
            print("错误: 数据必须是数组格式 [{...}, ...]")
            return

        from utils.admin_regions import find_admin
        from utils.geo import which_polygon
        CITY_REGION_MAP = {"杭州": "hangzhou", "绍兴": "shaoxing"}
        region_groups = {}
        for rec in data:
            avg_lat = (float(rec.get("a_lat",0))+float(rec.get("b_lat",0))+float(rec.get("c_lat",0)))/3
            avg_lng = (float(rec.get("a_lng",0))+float(rec.get("b_lng",0))+float(rec.get("c_lng",0)))/3
            _ad = find_admin(avg_lat, avg_lng)
            rc = CITY_REGION_MAP.get(_ad.get("l1", "")) or which_polygon(avg_lat, avg_lng, REGION_CONFIG) or "hangzhou"
            region_groups.setdefault(rc, []).append(rec)
        total_ok = 0
        all_msgs = []
        for rc, recs in region_groups.items():
            cfg = REGION_CONFIG.get(rc, {})
            from collections import Counter
            _dc = Counter()
            for _rec in recs:
                _al = (_rec.get("a_lat",0)+_rec.get("b_lat",0)+_rec.get("c_lat",0))/3
                _ag = (_rec.get("a_lng",0)+_rec.get("b_lng",0)+_rec.get("c_lng",0))/3
                _adm = find_admin(_al, _ag)
                _dc[_adm.get("l2", "?")] += 1
            _ds = ", ".join(f"{d}:{c}" for d,c in _dc.most_common())
            print(f"  {cfg.get('name',rc)} ({cfg.get('code',rc)}) - {len(recs)}条 [{_ds}]")
            with ShardDatabase(rc) as db:
                ok, batch_msgs = db.import_from_chart(recs, "rural")
                total_ok += ok
                all_msgs.extend(batch_msgs)

        print("\n导入结果: " + str(total_ok) + "/" + str(len(data)) + " 条")
        for msg in all_msgs:
            print("  " + msg)

    except FileNotFoundError:
        print("文件不存在: " + path)
    except json.JSONDecodeError as e:
        print("JSON 解析错误: " + str(e))
    except ValueError as e:
        print("数据错误: " + str(e))
    except Exception as e:
        print("导入失败: " + type(e).__name__ + ": " + str(e))
def _startup_check():
    """Startup check: verify DB, config, and dependencies"""
    import os
    print("\n" + "=" * 55)
    print("  System Startup Check")
    print("=" * 55)
    checks = []

    # DB directory
    from db_config import DB_DIR
    checks.append(("DB directory", os.path.exists(DB_DIR)))

    # Region config
    from db_config import REGION_CONFIG
    checks.append(("Region config", len(REGION_CONFIG) > 0))

    # Main DB path
    from db_config import MAIN_DB_PATH
    checks.append(("Main DB path", isinstance(MAIN_DB_PATH, str)))

    # Import check
    try:
        import duckdb
        checks.append(("DuckDB", True))
    except ImportError:
        checks.append(("DuckDB", False))

    try:
        import openpyxl
        checks.append(("openpyxl", True))
    except ImportError:
        checks.append(("openpyxl", False))

    for name, ok in checks:
        status = "OK" if ok else "FAIL"
        print(f"  [{status}] {name}")

    if all(ok for _, ok in checks):
        print("\n  All checks passed.")
    else:
        print("\n  Some checks failed. Check dependencies.")

    return all(ok for _, ok in checks)


def _show_check_zone():
    """网络健康检查区"""
    from monitor.reporter import print_check_zone, get_recommendations
    from monitor.metrics_collector import MetricsCollector
    print("\n" + "=" * 55)
    print("  网络健康检查区")
    print("=" * 55)
    did = input("\n设备 ID (留空=全部): ").strip()
    print_check_zone(did if did else None)
    if did:
        m = MetricsCollector.get_instance().get_device_metrics(did)
        if m:
            print("\n建议:")
            for r in get_recommendations(m):
                print("  " + r)
    input("\n按 Enter 继续...")



def _data_management():
    """数据管理: 删除/清除缓存"""
    print("\n" + "=" * 55)
    print("  数据管理")
    print("=" * 55)
    print("  1. 删除指定数据 (按 batch_id)")
    print("  2. 清空全部数据 (分库和总库)")
    print("  3. 清除上传缓冲区和锁文件")
    print("  0. 返回")
    choice = input("\n请选择: ").strip()
    if choice == "0":
        return
    region_code = _select_region()
    with ShardDatabase(region_code) as db:
        if choice == "1":
            bid = input("输入 batch_id (例如 HW-7): ").strip()
            if bid:
                db.delete_by_batch(bid); ok, msg = True, "已删除 "+bid
                print("\n  " + msg)
        elif choice == "2":
            print("\n  警告: 这将删除全部数据!")
            if input('输入 "yes" 确认: ').strip().lower() == "yes":
                db.clear_all(); ok, msg = True, "已清空"
                print("\n  " + msg)
            else:
                print("  已取消.")
        elif choice == "3":
            msg = "缓冲区已清除"
            try:
                from cache.idempotency import IdempotencyManager
                IdempotencyManager().reset()
                msg += ", idempotency cache reset"
            except Exception:
                pass
            print("\n  " + msg)
    input("\n按 Enter 继续...")



_API_SERVERS = {}

def _upgrade_menu():
    """系统升级功能菜单：重复检测 / 精度校验 / 熔断 / 统计API"""
    global _api_server_ref
    print("  系统升级功能")
    print("=" * 55)

    # 延迟导入避免启动时加载
    from upgrade.duplicate_detector import get_default as get_dd
    from upgrade.sequence_checker import get_default as get_sc
    from upgrade.circuit_breaker import get_default as get_cb

    dd = get_dd()
    sc = get_sc()
    cb = get_cb()
    _api_server = _API_SERVERS.get('stats')

    while True:
        print("\n请选择：")
        print("  1. 查看重复检测统计")
        print("  2. 查看序列完整性检测统计")
        print("  3. 查看熔断机制状态")
        print("  4. 手动恢复熔断设备")
        print("  5. 启动/重启 统计API (端口 8080)")
        print("  6. 停止统计API")
        print("  0. 返回主菜单")

        choice = input("\n请选择: ").strip()
        if choice == "0":
            return
        elif choice == "1":
            print("\n重复检测统计:")
            s = dd.stats()
            for k, v in s.items():
                print(f"  {k}: {v}")
        elif choice == "2":
            print("\n序列完整性检测统计:")
            s = sc.stats()
            for k, v in s.items():
                print(f"  {k}: {v}")
        elif choice == "3":
            print("\n熔断机制状态:")
            s = cb.stats()
            if not s:
                print("  无设备记录")
            for dev, info in s.items():
                status = "🔴 已隔离" if info.get("isolated") else "🟢 正常"
                print(f"  {dev}: {status}  样本={info['samples']}  错误率={info['error_rate']*100:.1f}%  "
                      f"剩余冷却={info.get('remaining_cooldown', 0)}s")
        elif choice == "4":
            did = input("\n输入设备ID (留空=全部恢复): ").strip()
            cb.reset(did or "")
            print(f"  已恢复: {did or '全部设备'}")
        elif choice == "5":
            try:
                from upgrade.stats_api import run_server
                if _api_server:
                    _api_server.shutdown()
                from upgrade import duplicate_detector, sequence_checker, circuit_breaker
                from upgrade.stats_api import register
                register("duplicate_detector", dd)
                register("sequence_checker", sc)
                register("circuit_breaker", cb)
                _api_server = run_server(port=8080, blocking=False); _API_SERVERS['stats'] = _api_server
                print("  统计API已启动: http://localhost:8080/api/survey/stats")
            except Exception as e:
                print(f"  启动失败: {e}")
        elif choice == "6":
            if _api_server:
                _api_server.shutdown()
                _api_server = _API_SERVERS.get('stats')
                print("  统计API已停止")
            else:
                print("  统计API未运行")
        else:
            print("无效选择")
        input("\n按 Enter 继续...")


def _eventbus_menu():
    """V4-Local EventBus 状态与回放"""
    from upgrade.eventbus import bus, Topics
    print("\n" + "=" * 55)
    print("  V4-Local EventBus 状态与回放")
    print("=" * 55)
    while True:
        s = bus.stats()
        print(f"\n  总事件数: {s['total_events']}")
        print(f"  历史队列: {s['history_size']}/{s['max_history']}")
        print(f"  Pipeline: {'启用' if s['pipeline_active'] else '未启用'}")
        print(f"  活跃主题:")
        for t, c in s.get('topics', {}).items():
            if c > 0:
                print(f"    - {t} ({c} 个订阅者)")
        print("\n  操作: 1.刷新  2.回放历史  3.清空历史  0.返回")
        ch = input("选择: ").strip()
        if ch == "0": return
        elif ch == "1": continue
        elif ch == "2":
            events = bus.replay_all()
            print(f"\n  历史事件 ({len(events)} 条):")
            for ev in events[-20:]:
                print(f"    [{ev.topic}] {ev.id} src={ev.source} t={ev.timestamp:.1f}")
        elif ch == "3":
            bus.clear_history()
            print("  历史已清空")
        else: print("  无效选择")

def _cli_test_menu():
    """V4-Local CLI 测试引擎"""
    print("\n" + "=" * 55)
    print("  V4-Local CLI 测试引擎")
    print("=" * 55)
    print("\n  CLI 命令 (在终端中使用):")
    print("  python -m cli.run_test --device gps --count 5")
    print("  python -m cli.run_test --device cm510 --count 10")
    print("  python -m cli.stream_view --topic gps.data")
    print("  python -m cli.stream_view --all")
    print("  python -m cli.device_control list")
    print("  python -m cli.device_control start gps_sim --count 5")
    print()
    import subprocess, sys
    print("  输入 CLI 命令直接运行 (留空返回):")
    while True:
        cmd = input("  $ ").strip()
        if not cmd: return
        try:
            if cmd.startswith("python "):
                subprocess.run(cmd, shell=True, cwd=__import__('os').path.dirname(__file__))
            else:
                subprocess.run(f"python -m {cmd}", shell=True, cwd=__import__('os').path.dirname(__file__))
        except Exception as e:
            print(f"  错误: {e}")

def _gps_replay_menu():
    """V4-Local GPS 回放系统"""
    print("\n" + "=" * 55)
    print("  V4-Local GPS 回放系统")
    print("=" * 55)
    print("\n  功能: 通过 EventBus 回放 GPS 数据")
    print("\n  命令 (在终端中使用):")
    print("  python -c 'from replay.gps_replay import GPSReplayEngine; e=GPSReplayEngine();")
    print("  e.load_file(\"文件路径\"); e.run()'")
    print()
    import os
    from upgrade.eventbus import bus
    base = os.path.dirname(__file__)
    while True:
        print("\n  1. 回放模拟坐标 (绍兴)")
        print("  2. 回放模拟坐标 (杭州)")
        print("  3. 从文件回放")
        print("  0. 返回")
        ch = input("选择: ").strip()
        if ch == "0": return
        elif ch == "1":
            from replay.gps_replay import GPSReplayEngine
            e = GPSReplayEngine(speed=5.0)
            cnt = e.run_geo(30.0, 120.5, 50.0, count=3)
            print(f"  回放完成: {cnt} 条坐标到绍兴")
        elif ch == "2":
            from replay.gps_replay import GPSReplayEngine
            e = GPSReplayEngine(speed=5.0)
            cnt = e.run_geo(30.27, 120.15, 50.0, count=3)
            print(f"  回放完成: {cnt} 条坐标到杭州")
        elif ch == "3":
            fp = input("文件路径: ").strip().strip('\"')
            if os.path.exists(fp):
                from replay.gps_replay import GPSReplayEngine
                e = GPSReplayEngine(speed=2.0)
                loaded = e.load_file(fp)
                cnt = e.run(source="replay:file")
                print(f"  加载 {loaded} 条, 回放 {cnt} 条")
            else:
                print(f"  文件不存在: {fp}")

def _plugin_menu():
    """V4-Local 插件管理"""
    from upgrade.plugin_sdk import manager
    print("\n" + "=" * 55)
    print("  V4-Local 插件管理")
    print("=" * 55)
    while True:
        plugins = manager.list()
        s = manager.stats()
        print(f"\n  已注册插件: {s['count']}")
        print(f"  沙箱模式: {'启用' if s['sandbox'] else '禁用'}")
        print(f"  超时: {s['timeout']}s")
        for p in plugins:
            print(f"    - {p['name']} v{p['version']}")
        print("\n  操作: 1.刷新  2.沙箱开/关  3.测试处理  0.返回")
        ch = input("选择: ").strip()
        if ch == "0": return
        elif ch == "1": continue
        elif ch == "2":
            manager.use_sandbox = not manager.use_sandbox
            print(f"  沙箱模式已切换: {'启用' if manager.use_sandbox else '禁用'}")
        elif ch == "3":
            result = manager.process({"topic": "test", "data": {"msg": "hello"}})
            for name, r in result.items():
                print(f"    {name}: {r.get('status','?')} {r.get('processing_ms','?')}ms")
        else: print("  无效选择")


def _result_service_menu():
    """V4-Local 结果服务 — 工业测试裁决"""
    print("\n" + "=" * 55)
    print("  V4-Local 结果服务 (Result Service)")
    print("=" * 55)
    print("\n  功能: 计算设备勘察结果 (1=正确 / 0=错误 / -1=未知)")
    print("  依据: 4.docx 结果输出接口增强版")
    print()
    from result_service import ResultRecord, ResultEngine, ResultStore, ResultAPI
    from result_service.result_store import store
    from result_service.result_api import api_server
    engine = ResultEngine(store)

    while True:
        total = store.count()
        print(f"\n  已记录设备: {total} 个")
        print("  1. 查询设备结果")
        print("  2. 测试计算设备结果")
        print("  3. 查看全部结果")
        print("  4. 启动 Result API (端口 8081)")
        print("  5. 停止 Result API")
        print("  6. 清空结果")
        print("  0. 返回")
        ch = input("\n选择: ").strip()
        if ch == "0":
            return
        elif ch == "1":
            did = input("设备ID: ").strip()
            r = store.get_or_default(did)
            emoji = {1: "\u2705", 0: "\u274c", -1: "\u2753"}
            print(f"  {emoji.get(r.get('result'),'?')} {did}: result={r.get('result')}  原因={r.get('reason')}")
        elif ch == "2":
            did = input("设备ID (留空=auto): ").strip() or "CM510_TEST"
            import time, random
            data = {"lat": 30.0 + random.random()/100, "lng": 120.5 + random.random()/100,
                    "alt": 50.0, "e": 0.01, "n": 0.01, "u": 0.02}
            rec = engine.compute(did, data)
            emoji = {1: "\u2705", 0: "\u274c", -1: "\u2753"}
            print(f"  {emoji.get(rec.result,'?')} {did}: result={rec.result}  reason={rec.reason}")
        elif ch == "3":
            all_r = store.get_all()
            emoji = {1: "\u2705", 0: "\u274c", -1: "\u2753"}
            for r in all_r[-20:]:
                print(f"  {emoji.get(r.get('result'),'?')} {r.get('device_id','?')}: {r.get('result')}  {r.get('reason','')}")
            if not all_r:
                print("  (无记录)")
        elif ch == "4":
            import threading
            t = threading.Thread(target=api_server.start, daemon=True)
            t.start()
            print("  Result API 已启动: http://localhost:8081/result/")
        elif ch == "5":
            api_server.stop()
            print("  Result API 已停止")
        elif ch == "6":
            store.clear()
            print("  结果已清空")


def cli_main():
    """Entry point with CLI argument support"""
    parser = argparse.ArgumentParser(description="Drone Survey Data Management")
    parser.add_argument("--import", dest="import_file", help="Import data file (JSON/XLSX/CSV/TXT)")
    parser.add_argument("--export", choices=["csv", "json"], help="Export data format")
    parser.add_argument("--db", default="hangzhou", choices=["hangzhou", "shaoxing"], help="Database region")
    parser.add_argument("--summary", action="store_true", help="Show main DB summary")
    parser.add_argument("--check", action="store_true", help="Run system startup check")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")

    # Parse known args first, ignore unknown (for interactive mode)
    args, _ = parser.parse_known_args()

    # Non-interactive mode
    if args.check:
        _startup_check()
        return
    if args.summary:
        from main_db import MainDatabase
        with MainDatabase() as m:
            s = m.get_summary()
            print(f"\nTotal: {s['total_records']} records")
            print(f"Rural: {s['rural_total']}, Urban: {s['urban_total']}")
            for name, info in s.get("by_region", {}).items():
                print(f"  {name}: {info['total']}")
        return
    if args.import_file:
        _run_cli_import(args.import_file, args.db)
        return
    if args.export:
        _run_cli_export(args.export, args.db)
        return

    # Interactive mode (default)
    _startup_check()
    main()


def _run_cli_import(filepath, region):
    """Non-interactive import"""
    from shard_db import ShardDatabase
    if filepath.lower().endswith((".xlsx", ".xls")):
        from app import _read_excel_survey_data as reader
    elif filepath.lower().endswith((".csv", ".txt")):
        from app import _read_csv_survey_data as reader
    else:
        print(f"Unknown format: {filepath}")
        return
    try:
        data = reader(filepath)
        with ShardDatabase(region) as db:
            ok, msgs = db.import_from_chart(data, "rural")
        print(f"Imported {ok}/{len(data)} records")
        for m in msgs:
            print(f"  {m}")
    except Exception as e:
        print(f"Import failed: {e}")


def _run_cli_export(fmt, region):
    """Non-interactive export"""
    from shard_db import ShardDatabase
    import json
    with ShardDatabase(region) as db:
        data = db.get_all_gps(9999)
    filename = f"export_{region}_{int(time.time())}.{fmt}"
    if fmt == "json":
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        import csv
        if not data:
            print("No data to export")
            return
        with open(filename, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=data[0].keys())
            w.writeheader()
            w.writerows(data)
    print(f"Exported {len(data)} records to {filename}")



def _view_main():
    """查看总部服务器数据 (新4表)"""
    from main_db import MainDatabase
    with MainDatabase() as db:
        summary = db.get_summary()
        print("\n  总部数据库统计:")
        lbl = {"total_gps":"GPS数","total_results":"结果数","correct":"正确","failed":"错误","regions":"地区"}
        for k, v in summary.items():
            print(f"    {k}: {v}")
        print("\n  最近GPS记录:")
        from collections import defaultdict
        gps = db.get_all_gps(200)
        batches = defaultdict(dict)
        for r in gps:
            batches[r.get('batch_id','?')][r.get('group_label','?')] = r
        for bid in sorted(batches, key=lambda x: str(x)):
            grp = batches[bid]
            a = grp.get('A', {}); b = grp.get('B', {}); c = grp.get('C', {})
            rc = a.get('region_code', '?')
            print(f"    batch={bid:<10} {rc:<4}")
            print(f"      A: 纬度={a.get('lat',0):.4f} 经度={a.get('lng',0):.4f}  东向={a.get('e',0):.3f}  北向={a.get('n',0):.3f}  高度={a.get('u',0):.3f}")
            print(f"      B: 纬度={b.get('lat',0):.4f} 经度={b.get('lng',0):.4f}  东向={b.get('e',0):.3f}  北向={b.get('n',0):.3f}  高度={b.get('u',0):.3f}")
            print(f"      C: 纬度={c.get('lat',0):.4f} 经度={c.get('lng',0):.4f}  东向={c.get('e',0):.3f}  北向={c.get('n',0):.3f}  高度={c.get('u',0):.3f}")
        results = db.get_all_results(10)
        if results:
            print("\n  最近结果:")
            for r in results:
                em = {1:"OK",0:"FAIL",-1:"?" }
                print(f"    {r.get('batch_id','?'):<20} 结果={em.get(r.get('result'),'?')} "
                      f"原因={r.get('reason','')}")

if __name__ == "__main__":
    cli_main()

