# -*- coding: utf-8 -*-
"""V2.0 统一 CLI — python cli/main.py <command> [args]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMMANDS = {
    "test":     ("运行自检",        "debug.selftest"),
    "stress":   ("压力测试 [设备数] [消息数]", "debug.stress_test run_stress"),
    "replay":   ("GPS回放 [文件路径] [--speed 2]", "debug.packet_replay"),
    "ws-test":  ("WebSocket测试",   "debug.ws_test"),
    "weak-net": ("弱网测试",        "debug.weak_network_test"),
    "net-switch": ("网络切换测试",  "debug.network_switch_test"),
    "api":      ("启动REST API [--port 8080]", "api.server"),
    "stats":    ("查看统计",        "main"),
}
def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("勘测系统服务器 CLI")
        print("用法: python cli/main.py <命令> [参数]")
        print()
        for name, (desc, _) in COMMANDS.items():
            print(f"  {name:<12} {desc}")
        sys.exit(0)
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"未知命令: {cmd}")
        print(f"可用: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    _, mod_path = COMMANDS[cmd]
    if cmd == "stress":
        devices = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        msgs = int(sys.argv[3]) if len(sys.argv) > 3 else 200
        from debug.stress_test import run_stress
        run_stress(devices, msgs)
    elif cmd == "replay":
        if len(sys.argv) < 3:
            print("用法: python cli/main.py replay <文件路径> [--speed 2]"); return
        from debug.packet_replay import replay_to_db
        path = sys.argv[2]
        speed = 1.0
        if "--speed" in sys.argv:
            idx = sys.argv.index("--speed")
            if idx + 1 < len(sys.argv):
                speed = float(sys.argv[idx + 1])
        replay_to_db(path, interval=1.0/speed)
    elif cmd == "test":
        import selftest
        selftest.run()
    elif cmd == "ws-test":
        from debug.ws_test import run_test
        run_test()
    elif cmd == "weak-net":
        from debug.weak_network_test import run_test
        run_test()
    elif cmd == "net-switch":
        from debug.network_switch_test import run_test
        run_test()
    elif cmd == "api":
        import argparse
        from api.server import main as api_main
        api_main()
    elif cmd == "stats":
        from config.config_loader import ConfigLoader
        from storage.duckdb_manager import DuckDBManager
        c = ConfigLoader.load("config/server.yaml")
        db = DuckDBManager(db_path=c.database.path, memory_limit=c.database.memory_limit, temp_directory=c.database.temp_directory)
        db.connect()
        print(f"GNSS: {db.count_gnss()} | Sessions: {db.get_table_sizes().get('device_session',0)} | Offline: {db.get_table_sizes().get('offline_message',0)}")
        db.disconnect()
if __name__ == "__main__":
    main()
