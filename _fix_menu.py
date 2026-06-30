import sys, os, re, py_compile
BASE = os.path.dirname(os.path.abspath(__file__))
APP_PATH = os.path.join(BASE, "app.py")

with open(APP_PATH, "r", encoding="utf-8") as f:
    data = f.read()

# ===== 1. Replace _view_shard() =====
old_shard = """def _view_shard():
    """ + "\u67e5\u770b\u5206\u90e8\u6570\u636e" + """
    region_code = _select_region()
    cfg = REGION_CONFIG[region_code]

    with ShardDatabase(region_code) as db:
        c = db.count_all()
        print(f"\\n{cfg['name']}\u5206\u90e8 ({cfg['code']}) \u6c47\u603b\uff1a")
        print(f"  \u8bbe\u5907: {c['devices']}  GPS\u8bb0\u5f55: {c['gps_records']}  \u7ed3\u679c: {c['results']}  \u65e5\u5fd7: {c['logs']}")

        if c['gps_records'] > 0:
            show = input("\\n\u662f\u5426\u67e5\u770b\u8be6\u7ec6\u6570\u636e\uff08y/n\uff09: ").strip().lower()
            if show == "y":
                from collections import defaultdict
                gps_list = db.get_all_gps(200)
                batches = defaultdict(dict)
                for r in gps_list:
                    batches[r.get('batch_id','?')][r.get('group_label','?')] = r
                for bid in sorted(batches, key=lambda x: str(x)):
                    grp = batches[bid]
                    a = grp.get('A', {}); b = grp.get('B', {}); c = grp.get('C', {})
                    print(f"  batch={bid}")
                    print(f"    A: \u7eac\u5ea6={a.get('lat',0):.4f} \u7ecf\u5ea6={a.get('lng',0):.4f}  \u4e1c\u5411={a.get('e',0):.3f}  \u5317\u5411={a.get('n',0):.3f}  \u9ad8\u5ea6={a.get('u',0):.3f}")
                    print(f"    B: \u7eac\u5ea6={b.get('lat',0):.4f} \u7ecf\u5ea6={b.get('lng',0):.4f}  \u4e1c\u5411={b.get('e',0):.3f}  \u5317\u5411={b.get('n',0):.3f}  \u9ad8\u5ea6={b.get('u',0):.3f}")
                    print(f"    C: \u7eac\u5ea6={c.get('lat',0):.4f} \u7ecf\u5ea6={c.get('lng',0):.4f}  \u4e1c\u5411={c.get('e',0):.3f}  \u5317\u5411={c.get('n',0):.3f}  \u9ad8\u5ea6={c.get('u',0):.3f}")"""

print("old_shard in data:", old_shard in data)
if old_shard not in data:
    with open(APP_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()
    for i, line in enumerate(lines[255:282], start=256):
        print(f"{i}: {line.rstrip()}")
