"""5.docx §8 CLI 测试运行器"""
import argparse, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from eventbus import Event, Topic, bus

def main():
    parser = argparse.ArgumentParser(description="CLI测试运行器")
    parser.add_argument("--device", choices=["gps","cm510","k803"], default="gps")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()
    print(f"测试运行: device={args.device} count={args.count}")
    for i in range(args.count):
        data = {"lat": 30.0+i*0.001, "lng": 120.5+i*0.001, "alt": 50.0, "e": 0.01, "n": 0.01, "u": 0.02}
        bus.publish(Topic.GPS_DATA, Event(topic=Topic.GPS_DATA, device_id=args.device, data=data))
        print(f"  [{i+1}/{args.count}] -> {Topic.GPS_DATA}")
        time.sleep(args.delay)
    print("完成")

if __name__ == "__main__":
    main()
