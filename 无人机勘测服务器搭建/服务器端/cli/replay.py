"""CLI GPS回放工具

用法：
python -m cli.replay --file data.txt
python -m cli.replay --lat 30.0 --lng 120.5 --count 5
"""
import argparse, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from upgrade.eventbus import Topics, bus
from replay.gps_replay import GPSReplayEngine

def main():
    parser = argparse.ArgumentParser(description="GPS回放CLI工具")
    parser.add_argument("--file", default="", help="回放文件路径")
    parser.add_argument("--lat", type=float, default=30.0, help="模拟纬度")
    parser.add_argument("--lng", type=float, default=120.5, help="模拟经度")
    parser.add_argument("--alt", type=float, default=50.0, help="模拟高度")
    parser.add_argument("--count", type=int, default=3, help="回放条数")
    parser.add_argument("--speed", type=float, default=1.0, help="回放速度倍数")
    parser.add_argument("--topic", default=Topics.GPS_DATA, help="发布主题")
    args = parser.parse_args()
    engine = GPSReplayEngine(speed=args.speed)
    if args.file:
        loaded = engine.load_file(args.file)
        cnt = engine.run(source="cli:replay")
        print(f"文件回放: 加载{loaded}条, 回放{cnt}条")
    else:
        cnt = engine.run_geo(args.lat, args.lng, args.alt, count=args.count, source="cli:replay")
        print(f"坐标回放: {cnt}条 (lat={args.lat}, lng={args.lng})")

if __name__ == "__main__":
    main()
