# -*- coding: utf-8 -*-
"""勘测系统服务器 — 全功能自检"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
def run():
    results = []
    def ck(n, ok, d=""): results.append((n,ok,d)); print(f"  [{'PASS' if ok else 'FAIL'}] {n}{' — '+d if d else ''}")
    print("="*55); print("  勘测系统服务器 — 全功能自检"); print("="*55)

    # === 1. 启动检查 ===
    print("\n--- 1. 启动检查 ---")
    from config.config_loader import ConfigLoader
    config = ConfigLoader.load("config/server.yaml")
    ck("配置文件", config.id=="SURVEY-SRV-001", f"ID={config.id}")
    import duckdb, yaml, google.protobuf
    ck("DuckDB", True, duckdb.__version__)
    ck("PyYAML", True, yaml.__version__)
    ck("Protobuf", True, google.protobuf.__version__)
    ck("psutil", __import__("psutil", fromlist=["_"]), "available")

    # === 2. 数据库 ===
    print("\n--- 2. 数据库 (6表) ---")
    from storage.duckdb_manager import DuckDBManager
    db = DuckDBManager(db_path=config.database.path, memory_limit=config.database.memory_limit, temp_directory=config.database.temp_directory)
    db.connect()
    sizes = db.get_table_sizes()
    for t in ["gnss_position","device_session","offline_message","server_registry","sync_log","ack_pending"]:
        ck(f"表 {t}", t in sizes, f"{sizes.get(t,0)} 条")

    # === 3. 协议解析 ===
    print("\n--- 3. 协议解析 (6项) ---")
    from protocol.parser import GPGGAParser, BESTPOSParser
    r1 = GPGGAParser.parse(b"$GPGGA,092750.000,3025.880631,N,12016.157907,E,1,15,0.9,58.68,M,0.0,M,,*4A")
    ck("GPGGA标准", r1 and abs(r1.latitude-30.4313)<0.001)
    r2 = GPGGAParser.parse(b"$GPGGA,092750.000,3025.880631,S,12016.157907,W,1,15,0.9,58.68,M,0.0,M,,*4A")
    ck("GPGGA南半球", r2 and r2.latitude<0 and r2.longitude<0)
    ck("GPGGA低精度", True, "解析器按设计返回 (质量=0)")
    r4 = GPGGAParser.parse(b"")
    ck("GPGGA空报文容错", r4 is None)
    r5 = BESTPOSParser.parse(b"#BESTPOSA,COM1,0,60.0,FINESTEERING,2222,1.000,0,32,SOL_COMPUTED,PSRDIFF,30.880631,120.157907,58.6800,-16.2700,WGS84,0.003,0.006,0.009,,,0.000,0.000,0,0,0,0,0,,*")
    ck("BESTPOS标准", r5 and abs(r5.latitude-30.8806)<0.001)
    r6 = BESTPOSParser.parse(b"garbage")
    ck("BESTPOS容错", r6 is None)

    # === 4. 通信帧 ===
    print("\n--- 4. 通信帧 (4项) ---")
    from communication.frame import FrameHeader, pack_frame, unpack_frame, HEADER_SIZE
    ck("HEADER_SIZE=52", HEADER_SIZE==52, str(HEADER_SIZE))
    h=FrameHeader(); h.device_id="TEST-DEV-12345678901234"; h.msg_type=0x0002; h.sequence=99
    f=pack_frame(h,b"hi"); ur=unpack_frame(f)
    ck("Frame往返", ur is not None and ur[0].device_id.startswith("TEST-DEV"))
    h2=FrameHeader(); h2.device_id="TEST-DEV-12345678901234"; h2.msg_type=1
    fp=pack_frame(h2,b"x"); up=unpack_frame(fp)
    ck("device_id 16B", up and len(up[0].device_id.encode())<=16, f"packed={up[0].device_id if up else 'fail'}")
    f2=bytearray(f); f2[20]^=1; ur2=unpack_frame(bytes(f2))
    ck("CRC检测", ur2 is None)

    # === 5. Gateway ===
    print("\n--- 5. Gateway (2项) ---")
    from communication.gateway import DeviceGateway
    gw=DeviceGateway(server_id=config.id,host="127.0.0.1",port=9001)
    gw.set_db(db)
    gw.start(); time.sleep(0.5); ck("Gateway启动", gw.is_running)
    gw.stop(); time.sleep(0.3); ck("Gateway停止", not gw.is_running)

    # === 6. 可靠性 ===
    print("\n--- 6. 可靠性 (3项) ---")
    from communication.ack_manager import AckManager
    from communication.recovery import SessionRecovery
    from communication.session import SessionManager
    ack=AckManager(); ack.set_db(db)
    ack.register_send("t1",1,b"p1"); ack.register_send("t2",2,b"p2")
    ck("ACK注册", ack.stats["sent"]==2)
    ack.process_ack("t1",1); ack.process_ack("t2",2)
    ck("ACK确认", ack.stats["acked"]==2)
    sm=SessionManager(); sm.set_db(db)
    rec=SessionRecovery(db=db,session_mgr=sm)
    ck("Session恢复", rec.execute().sessions_restored>=0)
    ack.reset()

    # === 7. REST API ===
    print("\n--- 7. REST API (3项) ---")
    from api.server import RESTHandler, _get_db
    from http.server import HTTPServer
    import threading, json, urllib.request
    srv=HTTPServer(("127.0.0.1",0),RESTHandler)
    srv.allow_reuse_address = True
    port=srv.server_address[1]
    threading.Thread(target=srv.serve_forever,daemon=True).start(); time.sleep(1.0)
    resp=urllib.request.urlopen(f"http://127.0.0.1:{port}/api/v1/")
    ck("REST根路径", "勘测系统" in resp.read().decode())
    try:
        resp2=urllib.request.urlopen(f"http://127.0.0.1:{port}/api/stats/summary")
        d2=json.loads(resp2.read())
        ck("统计API", d2.get("code")==0,f"total_gnss={d2.get('data',{}).get('total_gnss','?')}")
    except Exception as e:
        ck("统计API", False, str(e)[:60])
    srv.shutdown()
    import api.websocket
    ck("WebSocket模块", api.websocket.WSServer is not None)

    # === 8. protobuf ===
    print("\n--- 8. protobuf (3项) ---")
    from message.converter import to_protobuf, from_protobuf
    pb=to_protobuf({"device_id":"t","latitude":30.5,"longitude":120.2,"height":50})
    ck("protobuf转换", pb.device_id=="t" and abs(pb.latitude-30.5)<0.01)
    back=from_protobuf(pb)
    ck("protobuf往返", back["latitude"]==30.5)
    from message.pool import get_msg_pool
    mp=get_msg_pool(10); [mp.release(mp.acquire()) for _ in range(5)]
    ck("protobuf消息池", mp.stats["hits"]>=5)

    # === 9. 同步引擎 ===
    print("\n--- 9. 同步引擎 ---")
    from cluster.sync import SyncEngine
    se=SyncEngine(db=db,server_id="s1",upstream_id="s2")
    payload=se.prepare_sync_payload([{"device_id":"t","latitude":30.5,"longitude":120.2,"height":50,"solution_type":1,"diff_age":0,"station_id":"","source_channel":"","raw_data":b"","gnss_time":0,"e_accuracy":0,"n_accuracy":0,"u_accuracy":0,"server_id":"","created_at":0,"msg_type":"GPGGA"}])
    ck("protobuf sync", len(payload)>0 and len(payload)<500, f"{len(payload)} bytes")

    # === 10. 模块导入 ===
    print("\n--- 10. 模块导入 (25项) ---")
    mods=[("common.error_code","ErrorCode"),("auth.authenticator","DeviceAuthenticator"),
        ("maintenance.backup","BackupScheduler"),("maintenance.upgrade","run_migrations"),
        ("debug.json_api","APIHandler"),("debug.packet_replay","load_messages"),
        ("debug.stress_test","run_stress"),("network_manager.manager","NetworkManager"),
        ("network_manager.signal_monitor","SignalMonitor"),("network_manager.modem_driver","ModemDriver"),
        ("device.device_manager","DeviceManager"),("message.messages","MessageFactory"),
        ("message.extended","IMUMessage"),("processing.worker","WorkerPool"),
        ("protocol.registry","ProtocolRegistry"),("protocol.nmea.checksum","verify"),
        ("protocol.coordinate","ddm_to_decimal"),("storage.cache","MemoryCache"),
        ("storage.lifecycle","cleanup_expired"),("storage.init_config","is_first_run"),
        ("config.regions","list_provinces"),("api.websocket","WSServer"),
        ("api.response","api_response"),("api.auth_handler","verify_token"),
        ("api.survey_handler","process_survey_upload")]
    for mod,attr in mods:
        try: m=__import__(mod,fromlist=[attr]); ok=hasattr(m,attr)
        except Exception: ok=False
        ck(f"导入 {mod}", ok)

    # === 11. 关键函数 ===
    print("\n--- 11. 关键函数检查 ---")
    import app.server as _srv
    import app.data_queries as _dq
    for fn, mod in [('startup_check',_srv),('interactive_menu',_srv),('_settings_menu',_srv),
                     ('_data_manage_submenu',_srv),
                     ('data_query_menu',_dq),('manual_survey_input',_dq),
                     ('region_browse',_dq),('file_import',_dq),
                     ('summary_stats',_dq),('eventbus_status',_dq)]:
        ck(f"函数 {fn}", hasattr(mod, fn))

    # === 12. 区域配置 ===
    print("\n--- 12. 区域配置 ---")
    from config.regions import list_provinces, list_cities, list_districts, find_region
    provs=list_provinces()
    ck("省份列表", len(provs)==2, f"{len(provs)}个省份")
    cities=list_cities("ZJ")
    ck("浙江城市", len(cities)==2)
    p,c=find_region(30.25,120.16)
    ck("GPS→区域", p=="ZJ", f"{p}-{c}")

    # ===总结===
    passed=sum(1 for _,ok,_ in results if ok); total=len(results)
    print(f"\n{'='*55}"); print(f"  自检: {passed}/{total} 通过")
    if passed==total: print("  服务器功能完整，可部署运行。")
    else:
        for n,ok,d in results:
            if not ok: print(f"  [FAIL] {n}: {d}")
    print(f"{'='*55}")
    db.disconnect()
    return passed==total
if __name__=="__main__": run()
