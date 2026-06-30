"""5.docx §8.1 CLI主入口"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def main():
    print("=" * 50)
    print("  V4-Local CLI 测试引擎 (5.docx §8)")
    print("=" * 50)
    print("\n  命令:")
    print("  python -m cli.run_test --device gps --count 5")
    print("  python -m cli.replay --lat 30.0 --lng 120.5")
    print("  python -m cli.stream_view --topic gps.data")
    print("  python -m cli.result_query CM510_001")
    print("  python -m cli.device_simulator --type cm510 --count 3")
    print("  python -m cli.stress_test --count 100")
    print()

if __name__ == "__main__":
    main()
