# -*- coding: utf-8 -*-
"""V2.1 网络切换实测 - SignalMonitor + Modem 模拟切换"""
import time, random, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_test():
    from network_manager.signal_monitor import SignalMonitor, LinkType
    results = []
    def check(name, cond, detail=""):
        ok = bool(cond)
        results.append((name, ok, detail))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}{' — '+detail if detail else ''}")
        return ok

    print("=" * 55)
    print("  网络切换实测 — 信号评分 + 自动切换")
    print("=" * 55)

    sm = SignalMonitor()
    check("SignalMonitor初始化", sm.active == "4g")

    # Test 1: 正常评分
    print("\n--- Test 1: 正常信号评分 ---")
    sm.update(LinkType.N4G, signal=85, latency_ms=30, packet_loss=0.01)
    sm.update(LinkType.WIFI, signal=50, latency_ms=15, packet_loss=0.05)
    scores = sm.get_all_scores()
    for s in scores:
        print(f"  {s['type']}: score={s['score']} signal={s['signal']} latency={s['latency_ms']}ms{' *' if s['active'] else ''}")
    best = sm.best_link()
    check("4G 是最佳链路", best == LinkType.N4G, f"best={best.value}")

    # Test 2: 4G 信号下降 → 切换到 WiFi
    print("\n--- Test 2: 4G 弱信号 → WiFi 切换 ---")
    sm.update(LinkType.N4G, signal=15, latency_ms=500, packet_loss=0.3)
    sm.update(LinkType.WIFI, signal=80, latency_ms=20, packet_loss=0.02)
    best2 = sm.best_link()
    switched = sm.switch_to(best2)
    check("自动选WiFi", best2 == LinkType.WIFI, f"best={best2.value}")
    check("切换成功", switched, f"active={sm.active}")

    # Test 3: 4G 恢复 → 切回 4G
    print("\n--- Test 3: 4G 信号恢复 → 切回 ---")
    sm.update(LinkType.N4G, signal=90, latency_ms=25, packet_loss=0.01)
    best3 = sm.best_link()
    sm.switch_to(best3)
    check("切回4G", sm.active == "4g", f"active={sm.active}")

    # Test 4: 全部链路弱 → 保持当前
    print("\n--- Test 4: 全弱 → 保持当前 ---")
    sm.update(LinkType.N4G, signal=5, latency_ms=999, packet_loss=0.5)
    sm.update(LinkType.WIFI, signal=3, latency_ms=800, packet_loss=0.6)
    best4 = sm.best_link()
    sm.switch_to(best4)
    check("全弱仍保持连接", sm.active in ("4g", "wifi"), f"active={sm.active}")

    # Test 5: 评分公式验证 (signal*0.4 + latency*0.3 + loss*0.3)
    print("\n--- Test 5: 评分公式验证 ---")
    sm2 = SignalMonitor()
    sm2.update(LinkType.N4G, signal=100, latency_ms=0, packet_loss=0.0)
    perfect_score = sm2._links[LinkType.N4G]["score"]
    check("满分≈1.0", abs(perfect_score - 1.0) < 0.01, f"score={perfect_score:.3f}")
    sm2.update(LinkType.N4G, signal=0, latency_ms=1000, packet_loss=1.0)
    zero_score = sm2._links[LinkType.N4G]["score"]
    check("零分≈0.0", zero_score < 0.1, f"score={zero_score:.3f}")

    # Test 6: 模拟真实场景 — 4G→WiFi→4G 波动
    print("\n--- Test 6: 真实波动模拟 ---")
    sm3 = SignalMonitor()
    for t in range(5):
        sig_4g = max(0, min(100, 80 + random.randint(-30, 30)))
        lat_4g = max(1, 30 + random.randint(-15, 40))
        sig_wifi = max(0, min(100, 60 + random.randint(-40, 20)))
        sm3.update(LinkType.N4G, signal=sig_4g, latency_ms=lat_4g, packet_loss=random.uniform(0, 0.1))
        sm3.update(LinkType.WIFI, signal=sig_wifi, latency_ms=15, packet_loss=random.uniform(0, 0.05))
        best = sm3.best_link()
        sm3.switch_to(best)
        print(f"  t={t}: 4G(sig={sig_4g} lat={lat_4g}ms) WiFi(sig={sig_wifi}) → best={best.value}")
    check("波动中不崩溃", True, "5轮切换完成")

    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    print(f"\n{'='*55}")
    print(f"  网络切换测试: {passed}/{total} 通过")
    print(f"{'='*55}")
    return passed == total

if __name__ == "__main__":
    run_test()
