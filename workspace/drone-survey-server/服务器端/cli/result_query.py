"""5.docx §8 CLI 结果查询"""
import argparse, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from result_service.store import store

def main():
    parser = argparse.ArgumentParser(description="查询设备结果")
    parser.add_argument("device_id", nargs="?", default="", help="设备ID")
    parser.add_argument("--all", action="store_true", help="显示全部")
    args = parser.parse_args()
    if args.all:
        all_r = store.get_all()
        for r in all_r:
            print(f"  {r.get('device_id'):<20} result={r.get('result')}  {r.get('reason','')}")
        print(f"\n总计: {len(all_r)} 条")
    elif args.device_id:
        r = store.get_or_default(args.device_id)
        emoji = {1:"OK",0:"FAIL",-1:"?"}
        print(f"  {emoji.get(r.get('result'),'?')} {args.device_id}: result={r.get('result')}  reason={r.get('reason')}")
    else:
        print("用法: python -m cli.result_query <device_id>")
        print("      python -m cli.result_query --all")

if __name__ == "__main__":
    main()
