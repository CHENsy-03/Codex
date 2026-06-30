import sys, py_compile

with open("app.py", "r", encoding="utf-8") as f:
    data = f.read()

# Normalize line endings FIRST
data = data.replace("\r\n", "\n")

# ===== 1. Replace _view_shard() =====
# Find exact position by def marker
start = data.find("def _view_shard():")
end = data.find("def _view_main_old():")
old_shard = data[start:end]
if not old_shard.startswith("def _view_shard"):
    print("ERROR: _view_shard not found!")
    sys.exit(1)

new_shard = '''def _view_shard():
    """\u67e5\u770b\u5206\u90e8\u670d\u52a1\u5668\u6570\u636e - \u4e09\u7ea7\u5206\u5c42\uff1a\u7701\u2192\u5e02\u2192\u6570\u636e"""
    from utils.admin_regions import PROVINCES, CITIES as _CITIES
    _CRM = {'\u676d\u5dde': 'hangzhou', '\u7ecd\u5174': 'shaoxing', '\u662d\u901a\u5e02': 'zhaotong'}
    _prov = sorted(PROVINCES.items())
    while True:
        print("\\n\u4e00\u7ea7 - \u7701\u7ea7\u5206\u90e8\uff1a")
        for i, (_,pn) in enumerate(_prov, 1):
            print(f"  {i}. {pn}")
        print(f"  {len(_prov)+1}. \u8fd4\u56de")
        c = input("\\n\u8bf7\u9009\u62e9\u7701\u4efd: ").strip()
        if not c.isdigit(): continue
        ic = int(c)
        if ic == len(_prov)+1: return
        if not(1<=ic<=len(_prov)): continue
        pc,pn = _prov[ic-1]
        _city = [(cc,cn) for cc,cn in _CITIES.items() if cc[:2]==pc]
        while True:
            print(f"\\n\u4e8c\u7ea7 - {pn} \u5e02\u7ea7\u5206\u90e8\uff1a")
            for i,(_,cn) in enumerate(_city,1):
                print(f"  {i}. {cn}")
            print(f"  {len(_city)+1}. \u8fd4\u56de")
            c2 = input("\\n\u8bf7\u9009\u62e9\u57ce\u5e02: ").strip()
            if not c2.isdigit(): continue
            i2 = int(c2)
            if i2 == len(_city)+1: break
            if not(1<=i2<=len(_city)): continue
            _,cn = _city[i2-1]
            rc = _CRM.get(cn,"")
            if not rc: print(f"  \u672a\u627e\u5230 {cn} \u6570\u636e\u5e93"); continue
            cfg = __import__("db_config",fromlist=[""]).REGION_CONFIG.get(rc,{})
            with __import__("shard_db",fromlist=[""]).ShardDatabase(rc) as db:
                _c = db.count_all()
                print(f"\\n{cn} ({cfg.get('code','?')}) - GPS: {_c['gps_records']}  \u7ed3\u679c: {_c['results']}")
                if _c['gps_records']>0 and input("\\n\u67e5\u770b\u8be6\u7ec6? (y/n): ").strip().lower()=='y':
                    from collections import defaultdict
                    _gl = db.get_all_gps(200); _bt = defaultdict(dict)
                    for r in _gl: _bt[r.get('batch_id','?')][r.get('group_label','?')]=r
                    for bd in sorted(_bt, key=lambda x: str(x)):
                        gp = _bt[bd]; a,b,c3 = gp.get('A',{}),gp.get('B',{}),gp.get('C',{})
                        print(f"  batch={bd}")
                        for lb,d in [('A',a),('B',b),('C',c3)]:
                            print(f"    {lb}: \u7eac\u5ea6={d.get('lat',0):.4f} \u7ecf\u5ea6={d.get('lng',0):.4f}  \u4e1c\u5411={d.get('e',0):.3f}  \u5317\u5411={d.get('n',0):.3f}  \u9ad8\u5ea6={d.get('u',0):.3f}")
            input("\\n\\u6309 Enter \u7ee7\u7eed...")

'''

data = data.replace(old_shard, new_shard, 1)
print("_view_shard() replaced")

# ===== 2. Remove _view_main_old() =====
start = data.find("def _view_main_old():")
end = data.find("def _view_summary():")
old = data[start:end]
if old.startswith("def _view_main_old"):
    data = data.replace(old, "\n", 1)
    print("_view_main_old() removed")

# ===== 3. Remove _view_summary() =====
start = data.find("def _view_summary():")
end = data.find("def detect_file_format():")
old = data[start:end]
if old.startswith("def _view_summary"):
    data = data.replace(old, "\n", 1)
    print("_view_summary() removed")
else:
    print("WARNING: _view_summary not found")

# ===== 4. Replace _view_main() =====
start = data.find("def _view_main():")
# Find end: either next "def " or __name__ guard
rest = data[start:]
import re
m = re.search(r"\n(?:def |if __name__)", rest)
if m:
    end = start + m.start()
else:
    end = len(data)
old = data[start:end]

new_main = '''def _view_main():
    """\u67e5\u770b\u603b\u90e8\u670d\u52a1\u5668\u6570\u636e (\u5408\u5e76\u6c47\u603b)"""
    from main_db import MainDatabase
    from utils.admin_regions import PROVINCES
    _CRM = {'\u676d\u5dde': 'hangzhou', '\u7ecd\u5174': 'shaoxing', '\u662d\u901a\u5e02': 'zhaotong'}
    with MainDatabase() as db:
        s = db.get_summary()
        tot_gps = s.get('total_gps',0); tot_res = s.get('total_results',0)
        print("\\n" + "="*50)
        print("  \u603b\u90e8\u670d\u52a1\u5668\u6570\u636e\u7edf\u8ba1")
        print("="*50)
        print(f"  \u603bGPS\u8bb0\u5f55: {tot_gps}")
        print(f"  \u603b\u7ed3\u679c\u6570: {tot_res}")
        print(f"  \u603b\u52d8\u6d4b\u70b9: {tot_gps//3 if tot_gps else 0} \u4e2a\uff08\u6bcf\u70b93\u6b21\u6d4b\u91cf\uff09")
        print()
        _pv = sorted(PROVINCES.items())
        _pdata = {}
        for pc,pn in _pv:
            total=0
            for cc,cn in [(k,v) for k,v in [('330100','\\u676d\\u5dde'),('330600','\\u7ecd\\u5174'),('530600','\\u662d\\u901a\\u5e02')]]:
                if cc.startswith(pc):
                    rc=_CRM.get(cn,"")
                    if rc:
                        try:
                            from shard_db import ShardDatabase
                            with ShardDatabase(rc) as sd:
                                sc=sd.count_all(); total+=sc['gps_records']
                        except: pass
            _pdata[pn]=total
            print(f"  {pn} - {total} \\u6761GPS\\u8bb0\\u5f55")
        print()
        for i,(_,pn) in enumerate(_pv,1):
            print(f"  {i}. {pn} ({_pdata.get(pn,0)}\\u6761)")
        print(f"  {len(_pv)+1}. \\u8fd4\\u56de")
        c=input("\\n\\u8bf7\\u9009\\u62e9\\u7701\\u4efd\\u67e5\\u770b\\u8be6\\u60c5: ").strip()
        if c.isdigit() and 1<=int(c)<=len(_pv):
            pc,pn=_pv[int(c)-1]
            _show_province_detail(pn,pc,_CRM)
'''

# Fix the escaped unicode in new_main - they should NOT be double-escaped
# Actually, this is inside a Python string literal, so \uXXXX works correctly
# Let me handle the printing differently

new_main_fixed = '''def _view_main():
    """\u67e5\u770b\u603b\u90e8\u670d\u52a1\u5668\u6570\u636e (\u5408\u5e76\u6c47\u603b)"""
    from main_db import MainDatabase
    from utils.admin_regions import PROVINCES
    _CRM = {'\u676d\u5dde': 'hangzhou', '\u7ecd\u5174': 'shaoxing', '\u662d\u901a\u5e02': 'zhaotong'}
    with MainDatabase() as db:
        s = db.get_summary()
        tot_gps = s.get('total_gps',0); tot_res = s.get('total_results',0)
        print("\\n" + "="*50)
        print("  \u603b\u90e8\u670d\u52a1\u5668\u6570\u636e\u7edf\u8ba1")
        print("="*50)
        print(f"  \u603bGPS\u8bb0\u5f55: {tot_gps}")
        print(f"  \u603b\u7ed3\u679c\u6570: {tot_res}")
        print(f"  \u603b\u52d8\u6d4b\u70b9: {tot_gps//3 if tot_gps else 0} \u4e2a\uff08\u6bcf\u70b93\u6b21\u6d4b\u91cf\uff09")
        print()
        from shard_db import ShardDatabase
        _pv = sorted(PROVINCES.items())
        for pc,pn in _pv:
            total=0
            for cc,cn in [('330100','\u676d\u5dde'),('330600','\u7ecd\u5174'),('530600','\u662d\u901a\u5e02')]:
                if cc.startswith(pc):
                    rc=_CRM.get(cn,"")
                    if rc:
                        try:
                            with ShardDatabase(rc) as sd:
                                sc=sd.count_all(); total+=sc['gps_records']
                        except: pass
            print(f"  {pn} - {total} \u6761GPS\u8bb0\u5f55")
        print()
        for i,(_,pn) in enumerate(_pv,1):
            print(f"  {i}. {pn}")
        print(f"  {len(_pv)+1}. \u8fd4\u56de")
        c=input("\\n\\u8bf7\\u9009\\u62e9\u7701\u4efd\u67e5\u770b\u8be6\u60c5: ").strip()
        if c.isdigit() and 1<=int(c)<=len(_pv):
            pc,pn=_pv[int(c)-1]
            _show_province_detail(pn,pc,_CRM)
'''

if old.startswith("def _view_main"):
    data = data.replace(old, new_main_fixed, 1)
    print("_view_main() replaced")
else:
    print("ERROR: _view_main not found!")
    sys.exit(1)

# ===== 5. Add helper function before "if __name__" =====
helper = '''
def _show_province_detail(pname, pcode, _CRM):
    """\u663e\u793a\u7701\u7ea7\u8be6\u60c5\uff1a\u6700\u8fd130\u6761\u8bb0\u5f55"""
    _cities = [(cn, _CRM.get(cn,'')) for cc,cn in [('330100','\u676d\u5dde'),('330600','\u7ecd\u5174'),('530600','\u662d\u901a\u5e02')] if cc.startswith(pcode)]
    all_rec = []
    from shard_db import ShardDatabase
    for cn, rc in _cities:
        if not rc: continue
        try:
            with ShardDatabase(rc) as sd:
                for r in sd.get_all_gps(100):
                    r["_city"]=cn; all_rec.append(r)
        except: pass
    all_rec.sort(key=lambda x: str(x.get("batch_id","")), reverse=True)
    recent = all_rec[:30]
    total = len(set(r.get("batch_id","") for r in all_rec))
    print(f"\\n  {pname}\u603b\u7684\u65e0\u4eba\u673a\u52d8\u6d4b\u70b9: {total}")
    print(f"  \u6700\u8fd1\u5b58\u50a8\u7684{len(recent)}\u4e2a\u5b9a\u4f4d\u70b9\uff1a")
    for r in recent:
        bid = r.get("batch_id","?")
        rc_label = r.get("_city","?").replace('\u676d\u5dde','HW').replace('\u7ecd\u5174','SX').replace('\u662d\u901a\u5e02','ZT')
        print(f"    Home-{rc_label}-batch={bid:<12}  \u7eac\u5ea6={r.get('lat',0):.4f} \u7ecf\u5ea6={r.get('lng',0):.4f} \u4e1c\u5411={r.get('e',0):.3f} \u5317\u5411={r.get('n',0):.3f} \u9ad8\u5ea6={r.get('u',0):.3f}")
    input("\\n\\u6309 Enter \u7ee7\u7eed...")

'''

target = "if __name__ == \"__main__\":"
if target in data:
    idx = data.find(target)
    data = data[:idx] + helper + data[idx:]
    print("_show_province_detail helper added")
else:
    print("ERROR: __name__ guard not found!")
    sys.exit(1)

# ===== 6. Update menu =====
# Option 5 label
old_lbl = '        print("  5. \u67e5\u770b\u603b\u90e8\u6c47\u603b\u7edf\u8ba1")'
new_lbl = '        print("  5. (\u5408\u5e76\u81f34)\u67e5\u770b\u603b\u90e8\u670d\u52a1\u5668")'
if old_lbl in data:
    data = data.replace(old_lbl, new_lbl, 1)
    print("Menu option 5 label updated")

# Choice 5 redirect
old_ch = '        elif choice == "5":\n            _view_summary()'
new_ch = '        elif choice == "5":\n            print("  (\u5df2\u5408\u5e76\u81f3\u83dc\u53554)"); _view_main()'
if old_ch in data:
    data = data.replace(old_ch, new_ch, 1)
    print("Choice 5 redirected")

# ===== 7. Write back =====
with open("app.py", "w", encoding="utf-8") as f:
    f.write(data)

# ===== 8. Verify =====
try:
    py_compile.compile("app.py", doraise=True)
    print("\\nAll changes applied! Syntax OK.")
except py_compile.PyCompileError as e:
    print(f"\\nSyntax ERROR: {e}")
    import traceback
    traceback.print_exc()
