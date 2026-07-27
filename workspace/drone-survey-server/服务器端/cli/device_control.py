"""V4-Local 设备控制终端

用于启动/停止/监控模拟设备。
用法：
python -m cli.device_control list
python -m cli.device_control start cm510
"""
import argparse, sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from upgrade.eventbus import Topics, bus

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# 模拟设备注册表
DEVICES = {
    "cm510": {"desc": "CM510-71X 无线数传设备", "topics": [Topics.CM510_SIGNAL]},
    "k803": {"desc": "K803 GNSS 模块", "topics": [Topics.K803_SIGNAL, Topics.GPS_DATA]},
    "gps_sim": {"desc": "GPS 模拟器", "topics": [Topics.GPS_DATA]},
}

def cmd_list():
    print("📋 可用设备列表")
    print("   " + "-" * 40)
    for name, info in DEVICES.items():
        print(f"   {name:<12} {info['desc']}")
        print(f"              topics: {', '.join(info['topics'])}")
    print()

def cmd_start(device: str, count: int = 3):
    if device not in DEVICES:
        print(f"❌ 未知设备: {device}")
        return
    print(f"▶️ 启动设备: {device} ({DEVICES[device]['desc']})")
    print(f"   将发送 {count} 条模拟数据...")
    for i in range(count):
        time.sleep(1)
        bus.publish(Topics.GPS_DATA, {"device": device, "index": i,
                     "lat": 30.0, "lng": 120.5, "alt": 50.0,
                     "timestamp": time.time()}, source=f"device:{device}")
        print(f"   📤 发送 #{i+1} -> {Topics.GPS_DATA}")
    print("✅ 发送完成")

def main():
    parser = argparse.ArgumentParser(description="设备控制终端")
    parser.add_argument("command", choices=["list", "start"], help="命令")
    parser.add_argument("device", nargs="?", default="", help="设备名")
    parser.add_argument("--count", type=int, default=3, help="发送次数")
    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "start":
        cmd_start(args.device, args.count)

if __name__ == "__main__":
    main()
