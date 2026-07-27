"""5.docx §8 CLI 设备模拟器"""
import argparse, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from eventbus import Event, Topic, bus

def main():
    parser = argparse.ArgumentParser(description="设备模拟器")
    parser.add_argument("--type", choices=["gps","cm510","k803"], default="gps")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    topic_map = {"gps": Topic.GPS_DATA, "cm510": Topic.SIGNAL_CM510, "k803": Topic.SIGNAL_K803}
    print(f"模拟设备: type={args.type} count={args.count}")
    for i in range(args.count):
        bus.publish(topic_map[args.type], Event(topic=topic_map[args.type],
            device_id=f"{args.type}_{i:03d}", data={"index": i, "sim": True}))
        print(f"  [{i+1}/{args.count}] {topic_map[args.type]}")
        time.sleep(args.delay)
    print("完成")

if __name__ == "__main__":
    main()
