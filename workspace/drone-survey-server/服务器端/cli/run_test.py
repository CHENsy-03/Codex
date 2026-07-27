"""V4-Local CLI 测试启动器

用法：
python -m cli.run_test --device cm510
python -m cli.run_test --device k803 --count 10
"""
import argparse, logging, time, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from upgrade.eventbus import Event, Topics, bus

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

def main():
    parser = argparse.ArgumentParser(description="勘测系统测试引擎")
    parser.add_argument("--device", choices=["cm510", "k803", "gps", "all"], default="gps",
                        help="模拟设备类型")
    parser.add_argument("--count", type=int, default=5, help="发送报文数")
    parser.add_argument("--delay", type=float, default=1.0, help="发送间隔(秒)")
    parser.add_argument("--topic", default="", help="指定发布主题")
    parser.add_argument("--file", default="", help="从文件读取报文")
    args = parser.parse_args()

    print(f"🔧 测试引擎启动: device={args.device} count={args.count}")
    print(f"   间隔={args.delay}s 主题={args.topic or 'auto'} 文件={args.file or '无'}")
    print()

    # 注册结果订阅
    results = []
    def on_result(event: Event):
        results.append(event.payload)
        print(f"  📥 收到: topic={event.topic} source={event.source} payload_keys={list(event.payload.keys())}")

    bus.subscribe(Topics.ANALYSIS_RESULT, on_result)
    bus.subscribe(Topics.SURVEY_RESULT, on_result)
    bus.subscribe(Topics.DEVICE_PARSED, on_result)

    # 发送测试事件
    sent = 0
    for i in range(args.count):
        payload = _gen_payload(args.device, i)
        topic = args.topic or Topics.GPS_DATA
        bus.publish(topic, payload, source=f"test:{args.device}")
        sent += 1
        print(f"  📤 发送 #{i+1}: topic={topic}")
        time.sleep(args.delay)

    time.sleep(0.5)
    print(f"\n✅ 测试完成: 发送 {sent} 条, 收到 {len(results)} 条")
    print(f"   EventBus 统计: {bus.stats()}")

def _gen_payload(device: str, idx: int) -> dict:
    """生成模拟数据"""
    import random
    base_lat, base_lng = 30.0, 120.5
    if device == "gps":
        return {
            "lat": round(base_lat + random.uniform(-0.01, 0.01), 6),
            "lng": round(base_lng + random.uniform(-0.01, 0.01), 6),
            "alt": round(50 + random.uniform(-5, 5), 2),
            "e": round(random.uniform(0.01, 0.05), 3),
            "n": round(random.uniform(0.01, 0.05), 3),
            "u": round(random.uniform(0.02, 0.06), 3),
            "quality": "good",
        }
    elif device == "cm510":
        return {
            "device_id": f"CM510-{idx:03d}",
            "signal_strength": random.randint(60, 95),
            "data": f"mock_cm510_data_{idx}",
            "lat": round(base_lat + random.uniform(-0.005, 0.005), 6),
            "lng": round(base_lng + random.uniform(-0.005, 0.005), 6),
        }
    elif device == "k803":
        return {
            "device_id": f"K803-{idx:03d}",
            "gps_status": "FIX" if random.random() > 0.1 else "NO_FIX",
            "lat": round(base_lat + random.uniform(-0.01, 0.01), 6),
            "lng": round(base_lng + random.uniform(-0.01, 0.01), 6),
            "alt": round(50 + random.uniform(-5, 5), 2),
        }
    return {"device": device, "index": idx, "timestamp": time.time()}

if __name__ == "__main__":
    main()
