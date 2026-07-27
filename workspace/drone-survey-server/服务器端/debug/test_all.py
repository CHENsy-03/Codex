# -*- coding: utf-8 -*-
"""一键批量测试 — 自动运行所有测试并汇总"""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
results = []
def run(name, func):
    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"{'='*55}")
    try:
        ok = func()
        results.append((name, ok))
    except Exception as e:
        print(f"  [FAIL] 异常: {e}")
        results.append((name, False))
def test_config():
    from config.config_loader import ConfigLoader
    c = ConfigLoader.load("config/server.yaml")
    assert c.id == "SURVEY-SRV-001", f"ID mismatch: {c.id}"
    assert c.name is not None
    print(f"  [PASS] config: {c.id} / {c.name} / {c.level}")
    return True
def test_db_tables():
    from storage.duckdb_manager import DuckDBManager
    db = DuckDBManager(); db.connect()
    sizes = db.get_table_sizes()
    required = ["gnss_position","device_session","offline_message","server_registry","sync_log","ack_pending"]
    ok = all(t in sizes for t in required)
    for t in required:
        print(f"  [{'PASS' if t in sizes else 'FAIL'}] {t}: {sizes.get(t, 'MISSING')}")
    db.disconnect(); return ok
def test_protocol():
    from protocol.parser import GPGGAParser, BESTPOSParser
    ok = True
    r = GPGGAParser.parse(b"$GPGGA,092750.000,3025.880631,N,12016.157907,E,1,15,0.9,58.68,M,0.0,M,,*4A")
    if r and abs(r.latitude - 30.4313) < 0.001: print("  [PASS] GPGGA正常")
    else: print("  [FAIL] GPGGA正常"); ok = False
    r2 = GPGGAParser.parse(b"$GPGGA,,,,,,,,,,,,,")
    if r2 is None: print("  [PASS] GPGGA空字段容错")
    else: print("  [FAIL] GPGGA空字段容错"); ok = False
    r3 = BESTPOSParser.parse(b"#BESTPOSA,COM1,0,60.0,FINESTEERING,2222,1.000,0,32,SOL_COMPUTED,PSRDIFF,30.880631,120.157907,58.6800,-16.2700,WGS84,0.003,0.006,0.009,,,0.000,0.000,0,0,0,0,0,,*")
    if r3 and abs(r3.latitude - 30.8806) < 0.001: print("  [PASS] BESTPOS正常")
    else: print("  [FAIL] BESTPOS正常"); ok = False
    return ok
def test_frame():
    from communication.frame import FrameHeader, pack_frame, unpack_frame, HEADER_SIZE
    ok = True
    h = FrameHeader(); h.device_id = "TEST-DEV-1234567"; h.msg_type = 0x0002; h.sequence = 99
    f = pack_frame(h, b"hello"); r = unpack_frame(f)
    if r and r[0].device_id.startswith("TEST-DEV"): print(f"  [PASS] frame roundtrip, size={HEADER_SIZE}")
    else: print("  [FAIL] frame roundtrip"); ok = False
    if HEADER_SIZE == 52: print("  [PASS] HEADER_SIZE=52")
    else: print(f"  [FAIL] HEADER_SIZE={HEADER_SIZE}"); ok = False
    return ok
def test_websocket():
    from debug.ws_test import run_test
    return run_test()
def test_weak_network():
    from debug.weak_network_test import run_test
    return run_test()
def test_network_switch():
    from debug.network_switch_test import run_test
    return run_test()
def test_stress():
    from debug.stress_test import run_stress
    r = run_stress(20, 50)
    return r["ok"] > 0 and r["throughput"] > 10
def test_message_pool():
    from message.pool import get_msg_pool
    p = get_msg_pool(50)
    for _ in range(30): p.release(p.acquire())
    s = p.stats
    ok = s["hits"] >= 30
    print(f"  [{'PASS' if ok else 'FAIL'}] pool hits={s['hits']} rate={s['hit_rate']}")
    return ok
def test_sync_protobuf():
    from cluster.sync import SyncEngine
    se = SyncEngine(None, "s1", "s2")
    payload = se.prepare_sync_payload([{"device_id":"t","latitude":30.5,"longitude":120.2,"height":50.0,"solution_type":1,"diff_age":0,"station_id":"","source_channel":"","raw_data":b"","gnss_time":0,"e_accuracy":0,"n_accuracy":0,"u_accuracy":0,"server_id":"","created_at":0,"msg_type":"GPGGA"}])
    ok = len(payload) > 0 and len(payload) < 500
    print(f"  [{'PASS' if ok else 'FAIL'}] sync payload: {len(payload)} bytes")
    return ok

if __name__ == "__main__":
    print("="*55)
    print("  勘测系统服务器 — 批量测试")
    print("="*55)
    run("T1 配置解析", test_config)
    run("T2 数据库表结构", test_db_tables)
    run("T3 协议解析", test_protocol)
    run("T4 通信帧协议", test_frame)
    run("T10.2 消息池", test_message_pool)
    run("T10.3 protobuf sync", test_sync_protobuf)
    run("T10.1 压力测试", test_stress)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    print(f"\n{'='*55}")
    print(f"  批量测试: {passed}/{total} 通过")
    for name, ok in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"{'='*55}")
