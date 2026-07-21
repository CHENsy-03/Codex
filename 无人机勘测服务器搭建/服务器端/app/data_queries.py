# -*- coding: utf-8 -*-
"""V2.1 数据查询 — 浏览/录入/导入/统计"""
import sys, os, json, csv, time as _time, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def _get_server_id():
    try:
        from config.config_loader import ConfigLoader
        return ConfigLoader.load("config/server.yaml").id
    except Exception: return "SURVEY-SRV-001"

def data_query_menu(db):
    while True:
        print(); print("="*55); print("  数据查询与浏览"); print("="*55)
        sizes = db.get_table_sizes()
        print(f"  GNSS记录: {sizes.get('gnss_position',0)} | 设备会话: {sizes.get('device_session',0)}")
        print(f"  离线消息: {sizes.get('offline_message',0)} | 注册服务器: {sizes.get('server_registry',0)}")
        print()
        print("  1. 浏览全部 GNSS 数据 (分页, 每页30条)")
        print("  2. 按设备 ID 查询"); print("  3. 最新 N 条记录")
        print("  4. 按时间段查询 (YYYY-MM-DD HH:MM)")
        print("  5. 手动录入勘测数据 (A/B/C 三组)")
        print("  6. 分部/总部区域数据浏览")
        print("  7. 文件导入 (JSON/CSV/TXT)")
        print("  8. 总部汇总统计"); print("  9. 事件总线状态")
        print("  0. 返回主菜单")
        choice = input("\n请选择: ").strip()
        if choice == "0": break
        elif choice == "1": _browse_paged(db, sizes)
        elif choice == "2": _query_device(db)
        elif choice == "3": _query_recent(db)
        elif choice == "4": _query_timerange(db)
        elif choice == "5": manual_survey_input(db)
        elif choice == "6": region_browse(db)
        elif choice == "7": file_import(db)
        elif choice == "8": summary_stats(db)
        elif choice == "9": eventbus_status()
        else: print("  无效选择")
        input("\n按 Enter 继续...")

def _browse_paged(db, sizes):
    page = 0; page_size = 30
    while True:
        rows = db.query_gnss(limit=page_size, offset=page * page_size)
        print(f"\n  --- 第 {page+1} 页 (共 {sizes.get('gnss_position',0)} 条) ---")
        if not rows: print("  (无数据)"); input("\n按 Enter 返回..."); break
        for r in rows:
            print(f"  #{r.get('id','?')} dev={r.get('device_id','?')} type={r.get('msg_type','?')} lat={r.get('latitude',0):.6f} lng={r.get('longitude',0):.6f} alt={r.get('height',0):.2f}m")
        nav_opts = "n=下一页"; nav_opts += "  p=上一页" if page > 0 else ""; nav_opts += "  q=退出"
        print(f"\n  {nav_opts}")
        nav = input("选择: ").strip().lower()
        if nav == "n": page += 1
        elif nav == "p" and page > 0: page -= 1
        elif nav == "q": break

def _query_device(db):
    did = input("\n设备 ID: ").strip()
    if did:
        rows = db.query_gnss(limit=100, device_id=did)
        print(f"\n  设备 {did} 共 {len(rows)} 条记录:")
        for r in rows[:20]: print(f"  #{r.get('id','?')} type={r.get('msg_type','?')} lat={r.get('latitude',0):.6f} lng={r.get('longitude',0):.6f}")

def _query_recent(db):
    try: n = int(input("\n显示最近多少条 (默认 20): ").strip() or "20")
    except ValueError: n = 20
    rows = db.query_gnss(limit=n)
    print(f"\n  最近 {len(rows)} 条:")
    for r in rows: print(f"  #{r.get('id','?')} {r.get('msg_type','?')} lat={r.get('latitude',0):.6f} lng={r.get('longitude',0):.6f}")

def _query_timerange(db):
    from datetime import datetime
    try:
        t1_str = input("\n起始时间 (如 2026-07-14 07:00): ").strip()
        t2_str = input("结束时间 (如 2026-07-14 09:00): ").strip()
        t1 = int(datetime.strptime(t1_str, "%Y-%m-%d %H:%M").timestamp())
        t2 = int(datetime.strptime(t2_str, "%Y-%m-%d %H:%M").timestamp())
    except ValueError: print("  无效时间格式"); return
    rows = db.conn.execute("SELECT * FROM gnss_position WHERE created_at BETWEEN ? AND ? ORDER BY created_at DESC LIMIT 100", (min(t1,t2), max(t1,t2))).fetchall()
    cols = [d[0] for d in db.conn.description]
    print(f"\n  共 {len(rows)} 条:")
    for r in rows[:30]:
        rec = dict(zip(cols, r))
        print(f"  #{rec.get('id','?')} {rec.get('msg_type','?')} lat={rec.get('latitude',0):.6f} lng={rec.get('longitude',0):.6f}")

def manual_survey_input(db):
    """手动录入勘测数据 — A/B/C 三组 + 精度比较"""
    from config.regions import list_provinces, list_cities, list_districts
    def _dist(lat1, lng1, lat2, lng2):
        dlat = (lat2 - lat1) * 111320; dlng = (lng2 - lng1) * 111320 * math.cos(math.radians((lat1+lat2)/2))
        return math.sqrt(dlat**2 + dlng**2)
    def _input_group(label):
        print(f"\n--- {label}组 ---")
        raw = input("纬度 经度 高度(m) H精度(cm) V精度(cm) D精度(cm): ").strip()
        parts = raw.split()
        if len(parts) != 6: print("错误: 需要 6 个值"); return None
        try: return [float(p) for p in parts]
        except ValueError: print("错误: 数值格式不正确"); return None
    print("\n" + "="*55); print("  手动录入勘测数据 (A/B/C 三组)"); print("="*55)
    provinces = list_provinces()
    for i, (code, name) in enumerate(provinces, 1): print(f"  {i}. {name} ({code})")
    try: prov_code = provinces[int(input("\n选择省份: ").strip())-1][0]
    except (ValueError, IndexError): prov_code = None
    city_code = None; district = None
    if prov_code:
        cities = list_cities(prov_code)
        for i, (code, name) in enumerate(cities, 1): print(f"  {i}. {name} ({code})")
        try: city_code = cities[int(input("\n选择城市: ").strip())-1][0]
        except (ValueError, IndexError): city_code = None
        if city_code:
            districts = list_districts(prov_code, city_code)
            print(f"\n区县列表: {', '.join(districts[:8])}...")
            district = input("输入区县名 (或留空): ").strip()
            if district and district not in districts:
                print(f"  '{district}' 不在辖区列表中"); return
    A = _input_group("A")
    if A is None: return
    B = _input_group("B")
    if B is None: return
    C = _input_group("C")
    if C is None: return
    h_ab = _dist(A[0], A[1], B[0], B[1]); h_ac = _dist(A[0], A[1], C[0], C[1]); h_bc = _dist(B[0], B[1], C[0], C[1])
    v_ab = abs(A[2] - B[2]); v_ac = abs(A[2] - C[2]); v_bc = abs(B[2] - C[2])
    print(f"\n  [比较结果]"); print(f"  A-B: H差={h_ab*100:.1f}cm V差={v_ab*100:.1f}cm"); print(f"  A-C: H差={h_ac*100:.1f}cm V差={v_ac*100:.1f}cm"); print(f"  B-C: H差={h_bc*100:.1f}cm V差={v_bc*100:.1f}cm")
    consistent = max(h_ab, h_ac, h_bc) < 0.05 and max(v_ab, v_ac, v_bc) < 0.20
    print(f"  一致性: {'通过' if consistent else '超标'}")
    if not consistent: print("  精度超标, 数据不存储"); return
    if input("\n保存到数据库? (y/n): ").strip().lower() != "y": return
    batch_id = f"SURVEY-{int(_time.time())}"; region_tag = f"{prov_code}-{city_code or ''}-{district or ''}"
    for label, vals in [("A", A), ("B", B), ("C", C)]:
        db.insert_gnss({"device_id": "MANUAL", "msg_type": "MANUAL", "latitude": vals[0], "longitude": vals[1], "height": vals[2], "e_accuracy": vals[3], "n_accuracy": vals[4], "u_accuracy": vals[5], "solution_type": 1, "diff_age": 0, "station_id": label, "source_channel": f"{batch_id} {region_tag}", "server_id": _get_server_id(), "gnss_time": int(_time.time()), "created_at": int(_time.time()), "raw_data": f"BATCH={batch_id} GROUP={label}".encode()})
    print(f"  已保存 batch={batch_id} ({region_tag})")

def region_browse(db):
    """分部/总部数据查看 — 三级区域层级浏览"""
    from config.regions import list_provinces, list_cities, list_districts, REGIONS
    while True:
        print(); print("="*55); print("  分部/总部数据查看"); print("="*55)
        total = db.count_gnss(); print(f"  总GNSS记录: {total}")
        provinces = list_provinces()
        for i, (code, name) in enumerate(provinces, 1): print(f"  {i}. {name} ({code})")
        print("  0. 返回")
        choice = input("\n选择省份: ").strip()
        if choice == "0": break
        try: prov_code = provinces[int(choice)-1][0]
        except (ValueError, IndexError): continue
        while prov_code:
            cities = list_cities(prov_code); print(f"\n  {REGIONS[prov_code]['name']} — 市级分部")
            for i, (code, name) in enumerate(cities, 1): print(f"  {i}. {name} ({code})")
            print("  0. 返回上级")
            cc = input("\n选择城市: ").strip()
            if cc == "0": break
            try: city_code = cities[int(cc)-1][0]
            except (ValueError, IndexError): continue
            while city_code:
                districts = list_districts(prov_code, city_code)
                print(f"\n  {REGIONS[prov_code]['cities'][city_code]['name']} — 区县级分部")
                for i, d in enumerate(districts, 1): print(f"  {i}. {d}")
                print("  98. 查看全部  99. 最近批次  0. 返回上级")
                dc = input("\n选择: ").strip()
                if dc == "0": break
                tag = f"{prov_code}-{city_code}"
                if dc == "98":
                    rows = db.conn.execute("SELECT * FROM gnss_position WHERE source_channel LIKE ? ORDER BY created_at DESC LIMIT 30", (f"%{tag}%",)).fetchall()
                elif dc == "99":
                    rows = db.query_gnss(limit=30)
                    print("\n  最近30条:"); _show_rows(rows, db); input("\n按 Enter 继续..."); continue
                else:
                    try: idx = int(dc) - 1
                    except ValueError: continue
                    if 0 <= idx < len(districts):
                        tag = f"{prov_code}-{city_code}-{districts[idx]}"
                        rows = db.conn.execute("SELECT * FROM gnss_position WHERE source_channel LIKE ? ORDER BY created_at DESC LIMIT 30", (f"%{tag}%",)).fetchall()
                    else: continue
                _show_rows(rows, db)
                input("\n按 Enter 继续...")

def _show_rows(rows, db):
    cols = [d[0] for d in db.conn.description]
    result = [dict(zip(cols, r)) for r in rows]
    print(f"\n  共 {len(result)} 条匹配记录:")
    for r in result: print(f"  #{r.get('id','?')} grp={r.get('station_id','?')} lat={r.get('latitude',0):.6f} lng={r.get('longitude',0):.6f} alt={r.get('height',0):.2f}m")

def file_import(db):
    """文件导入 — JSON/CSV/TXT → 自动识别地区 → 入库"""
    from config.regions import find_region
    print("\n"+"="*55); print("  数据文件导入"); print("="*55)
    print("  支持: JSON (.json) | CSV (.csv) | TXT (.txt)")
    path = input("\n文件路径: ").strip().strip('"').strip("'")
    if not os.path.exists(path): print(f"  文件不存在: {path}"); return
    ext = os.path.splitext(path)[1].lower(); records = []
    if ext == ".json":
        with open(path,"r",encoding="utf-8") as f: data = json.load(f)
        records = data if isinstance(data, list) else [data]
    elif ext in (".csv",".txt"):
        with open(path,"r",encoding="utf-8") as f:
            for row in csv.reader(f):
                if len(row) >= 4:
                    try: records.append({"device_id":row[0],"latitude":float(row[1]),"longitude":float(row[2]),"height":float(row[3])})
                    except ValueError: pass
    else: print(f"  不支持的格式: {ext}"); return
    if not records: print("  无有效数据"); return
    region_counts = {}; inserted = 0
    for r in records:
        lat = r.get("latitude",0); lng = r.get("longitude",0)
        prov, city = find_region(lat, lng)
        tag = f"{prov or '?'}-{city or '?'}"; region_counts[tag] = region_counts.get(tag,0)+1
        db.insert_gnss({"device_id":r.get("device_id","import"),"msg_type":"GPGGA","latitude":lat,"longitude":lng,"height":r.get("height",0),"solution_type":1,"diff_age":0,"station_id":"","source_channel":f"import {tag}","server_id":_get_server_id(),"gnss_time":int(_time.time()),"created_at":int(_time.time()),"e_accuracy":0,"n_accuracy":0,"u_accuracy":0,"raw_data":b""}); inserted += 1
    print(f"\n  导入结果: {inserted}/{len(records)} 条")
    for tag, cnt in sorted(region_counts.items()): print(f"    {tag}: {cnt} 条")

def summary_stats(db):
    """总部汇总统计 — 聚合数据概览"""
    print("\n"+"="*55); print("  总部汇总统计"); print("="*55)
    print(f"  总 GNSS 记录: {db.count_gnss()}")
    try:
        cnt = db.conn.execute("SELECT count(DISTINCT substr(source_channel,1,20)) FROM gnss_position WHERE source_channel LIKE 'SURVEY-%'").fetchone()[0]
        print(f"  总勘测批次: {cnt}")
    except Exception: pass
    try:
        by_type = db.conn.execute("SELECT msg_type, count(*) as cnt FROM gnss_position GROUP BY msg_type ORDER BY cnt DESC").fetchall()
        print(f"\n  按类型:"); [print(f"    {t}: {c} 条") for t,c in by_type]
    except Exception: pass
    try:
        recent = db.conn.execute("SELECT source_channel, station_id, latitude, longitude, height FROM gnss_position ORDER BY created_at DESC LIMIT 5").fetchall()
        if recent:
            print(f"\n  最近 5 条:"); [print(f"    grp={r[1] or '?'} lat={r[2]:.6f} lng={r[3]:.6f} alt={r[4]:.2f}m") for r in recent]
    except Exception: pass

def eventbus_status():
    """事件总线状态"""
    print("\n"+"="*55); print("  事件总线 EventBus"); print("="*55)
    try:
        from eventbus.core import EventBus
        bus = EventBus(); stats = bus.get_statistics() if hasattr(bus,'get_statistics') else {}
        print(f"  事件总数: {stats.get('total_events','?')}"); print(f"  主题: {stats.get('topics',{})}")
    except Exception as e: print(f"  EventBus 不可用: {e}")
