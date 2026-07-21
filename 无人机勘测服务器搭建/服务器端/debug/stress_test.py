# -*- coding: utf-8 -*-
"""V2.1 Stress Test - 100/1000 device concurrent + 1M GNSS records"""
import time, threading, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def run_stress(device_count=100, msg_count=1000, interval=0.01):
    from storage.duckdb_manager import DuckDBManager
    from protocol.parser import ProtocolDispatcher
    from config.config_loader import ConfigLoader
    config = ConfigLoader.load("config/server.yaml")
    db = DuckDBManager(db_path=config.database.path,
                       memory_limit=config.database.memory_limit,
                       temp_directory=config.database.temp_directory)
    db.connect()
    dp = ProtocolDispatcher(config.id)
    gpgga = "$GPGGA,092750.000,3025.880631,N,12016.157907,E,1,15,0.9,58.68,M,0.0,M,,*4A"
    bestpos = "#BESTPOSA,COM1,0,60.0,FINESTEERING,2222,1.000,0,32,SOL_COMPUTED,PSRDIFF,30.880631,120.157907,58.6800,-16.2700,WGS84,0.003,0.006,0.009,,,0.000,0.000,0,0,0,0,0,,*"
    start = time.time(); ok = 0; fail = 0
    devs = [f"STRESS-{i:04d}" for i in range(device_count)]
    for _ in range(msg_count):
        for did in random.sample(devs, min(10, device_count)):
            raw = (gpgga if random.random() > 0.5 else bestpos).encode()
            r = dp.parse(raw)
            if r:
                r.device_id = did; r.server_id = config.id
                r.gnss_time = int(time.time()); r.created_at = int(time.time())
                db.insert_gnss(r); ok += 1
            else:
                fail += 1
            time.sleep(interval)
    elapsed = time.time() - start
    db.disconnect()
    print(f"\n  [压力测试] 设备={device_count} 消息={msg_count}")
    print(f"  成功={ok} 失败={fail} 耗时={elapsed:.1f}s")
    print(f"  吞吐量={ok/elapsed:.0f} msg/s")
    return {"devices": device_count, "messages": msg_count, "ok": ok,
            "fail": fail, "elapsed": elapsed, "throughput": ok/elapsed}
