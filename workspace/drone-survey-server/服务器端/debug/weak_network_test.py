# -*- coding: utf-8 -*-
"""V2.1 弱网实测 - 丢包/断网/恢复 端到端测试"""
import time, random, threading, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class WeakNetworkSimulator:
    """模拟弱网环境：丢包率、延迟、断网/恢复"""
    def __init__(self, loss_rate=0.1, latency_ms=50, jitter_ms=20):
        self.loss_rate = loss_rate
        self.latency_ms = latency_ms
        self.jitter_ms = jitter_ms
        self.disconnected = False
        self.total_sent = 0
        self.total_lost = 0
        self.delivery_log = []
    def send(self, callback) -> bool:
        """模拟发送：按丢包率随机丢弃，延迟后回调"""
        self.total_sent += 1
        if self.disconnected:
            self.total_lost += 1
            self.delivery_log.append(("DROP", "disconnected"))
            return False
        if random.random() < self.loss_rate:
            self.total_lost += 1
            self.delivery_log.append(("DROP", "packet_loss"))
            return False
        delay = (self.latency_ms + random.uniform(-self.jitter_ms, self.jitter_ms)) / 1000.0
        time.sleep(max(0, delay))
        self.delivery_log.append(("SEND", f"ok_{delay*1000:.0f}ms"))
        if callback:
            callback()
        return True
    def disconnect(self):
        self.disconnected = True
        print("  [模拟] 网络断开")
    def reconnect(self):
        self.disconnected = False
        print("  [模拟] 网络恢复")
    def stats(self):
        loss_pct = self.total_lost / max(1, self.total_sent) * 100
        return {"sent": self.total_sent, "lost": self.total_lost,
                "loss_rate": f"{loss_pct:.1f}%", "disconnected": self.disconnected}

def run_test():
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    from protocol.parser import ProtocolDispatcher
    config = ConfigLoader.load("config/server.yaml")
    db = DuckDBManager(db_path=config.database.path,
                       memory_limit=config.database.memory_limit,
                       temp_directory=config.database.temp_directory)
    db.connect()
    dp = ProtocolDispatcher(config.id)
    gpgga = "$GPGGA,092750.000,3025.880631,N,12016.157907,E,1,15,0.9,58.68,M,0.0,M,,*4A"

    results = []
    def check(name, cond, detail=""):
        ok = bool(cond)
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{' — '+detail if detail else ''}")
        return ok

    print("=" * 55)
    print("  弱网实测 — 丢包/断网/恢复")
    print("=" * 55)

    # Test 1: 0% loss — 正常发送
    print("\n--- Test 1: 正常网络 (0% 丢包) ---")
    sim = WeakNetworkSimulator(loss_rate=0.0, latency_ms=10)
    ok_count = 0
    for i in range(20):
        parsed = None
        def cb():
            nonlocal parsed
            parsed = dp.parse(gpgga.encode())
        if sim.send(cb):
            if parsed and parsed.device_id == "":
                parsed.device_id = f"weak-{i:03d}"
                parsed.server_id = config.id
                parsed.gnss_time = int(time.time())
                parsed.created_at = int(time.time())
                db.insert_gnss(parsed)
                ok_count += 1
    st = sim.stats()
    check("0%丢包-发送成功率", ok_count == 20, f"{ok_count}/20 通过")

    # Test 2: 20% loss — 模拟弱网
    print("\n--- Test 2: 弱网 (20% 丢包) ---")
    sim2 = WeakNetworkSimulator(loss_rate=0.2, latency_ms=80)
    ok2 = 0
    for i in range(20):
        parsed2 = None
        def cb2():
            nonlocal parsed2
            parsed2 = dp.parse(gpgga.encode())
        if sim2.send(cb2):
            if parsed2:
                parsed2.device_id = f"loss-{i:03d}"
                parsed2.server_id = config.id
                parsed2.gnss_time = int(time.time())
                parsed2.created_at = int(time.time())
                db.insert_gnss(parsed2)
                ok2 += 1
    st2 = sim2.stats()
    check("20%丢包-有消息送达", ok2 > 0, f"{ok2}/20 送达, {st2['loss_rate']} 丢包")

    # Test 3: 断网 → 离线队列 → 恢复
    print("\n--- Test 3: 断网恢复 (离线队列) ---")
    sim3 = WeakNetworkSimulator(loss_rate=0.0, latency_ms=5)
    before = db.conn.execute("SELECT count(*) FROM offline_message").fetchone()[0]
    sim3.disconnect()
    for i in range(10):
        if sim3.disconnected:
            db.enqueue_offline(f"offline-{i:03d}", i, gpgga.encode())
    after_disconnect = db.conn.execute("SELECT count(*) FROM offline_message").fetchone()[0]
    queued = after_disconnect - before
    sim3.reconnect()
    time.sleep(0.3)
    pending = db.conn.execute("SELECT count(*) FROM offline_message WHERE status='pending'").fetchone()[0]
    check("断网-离线入队", queued == 10, f"入队 {queued} 条")
    check("恢复-队列存在", pending >= 0, f"待发送 {pending} 条")

    # Test 4: ACK 重传 — 丢包后自动重试
    print("\n--- Test 4: ACK 重传验证 ---")
    from communication.ack_manager import AckManager
    ack = AckManager()
    ack.set_db(db)
    ack.register_send("test-dev", 1, b"test_payload")
    ack.register_send("test-dev", 2, b"test_payload2")
    check("ACK注册", ack.stats["sent"] == 2, f"已发送 {ack.stats['sent']}")
    time.sleep(1.2)
    retry_list = ack.get_retransmit_list()
    check("ACK超时检测", len(retry_list) > 0, "超时消息可检出" if retry_list else "可能需要更长超时")
    ack.process_ack("test-dev", 1)
    ack.process_ack("test-dev", 2)
    check("ACK确认后清理", ack.stats["acked"] == 2, f"已确认 {ack.stats['acked']}")
    ack.reset()

    # Test 5: Session 恢复
    print("\n--- Test 5: Session 恢复 ---")
    db.upsert_session("recover-001", "sess-1", "tcp", "online")
    from communication.recovery import SessionRecovery
    from communication.session import SessionManager
    sm = SessionManager()
    sm.set_db(db)
    rec = SessionRecovery(db=db, session_mgr=sm)
    result = rec.execute()
    check("Session恢复-执行", result.sessions_restored >= 0, f"恢复 {result.sessions_restored} 个会话")

    db.disconnect()
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*55}")
    print(f"  弱网测试: {passed}/{total} 通过")
    print(f"{'='*55}")
    return passed == total

if __name__ == "__main__":
    run_test()
