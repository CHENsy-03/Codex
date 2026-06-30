"""V4-Local CLI 压力测试工具

用法：
python -m cli.stress_test --count 100 --device gps
python -m cli.stress_test --count 500 --device cm510 --api http://localhost:8080
"""
import argparse, sys, os, time, json, random
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from upgrade.eventbus import Event, Topics, bus

def main():
    parser = argparse.ArgumentParser(description="CLI 压力测试")
    parser.add_argument("--count", type=int, default=50, help="发送报文数")
    parser.add_argument("--device", choices=["gps", "cm510", "k803"], default="gps")
    parser.add_argument("--delay", type=float, default=0.01, help="发送间隔(秒)")
    parser.add_argument("--api", default="", help="HTTP API 地址（可选）")
    args = parser.parse_args()

    print(f"⚡ 压力测试: device={args.device} count={args.count} delay={args.delay}s")
    start = time.time()
    ok = 0; fail = 0

    for i in range(args.count):
        payload = _gen(args.device, i)
        try:
            bus.publish(Topics.DEVICE_RAW, payload, source=f"stress:{args.device}")
            ok += 1
        except:
            fail += 1
        time.sleep(args.delay)

    elapsed = time.time() - start
    rps = args.count / elapsed if elapsed > 0 else 0
    print(f"\n结果: 成功={ok} 失败={fail} 耗时={elapsed:.2f}s RPS={rps:.0f}")

def _gen(device, idx):
    random.seed(idx)
    if device == "gps":
        return {"lat": round(30 + random.random()/10, 6), "lng": round(120.5 + random.random()/10, 6),
                "alt": round(50 + random.random()*10, 2), "e": 0.01, "n": 0.01, "u": 0.02}
    return {"device": device, "index": idx, "data": f"mock_{idx}"}

if __name__ == "__main__":
    main()
