import sys
fp = r"E:\AI_Projects\Codex\无人机勘测服务器搭建\服务器端\app.py"
with open(fp, "r", encoding="utf-8") as f:
    c = f.read()
old = """        region_groups = {}
        from utils.geo import which_polygon
        for rec in data:
            avg_lat = (float(rec.get('a_lat',0))+float(rec.get('b_lat',0))+float(rec.get('c_lat',0)))/3
            avg_lng = (float(rec.get('a_lng',0))+float(rec.get('b_lng',0))+float(rec.get('c_lng',0)))/3
            rc = which_polygon(avg_lat, avg_lng, REGION_CONFIG) or 'hangzhou'
            region_groups.setdefault(rc, []).append(rec)"""
new = """        region_groups = {}
        from utils.admin_regions import find_admin
        _city_map = {chr(39)+chr(26477)+chr(24030)+chr(39): chr(39)+chr(104)+chr(97)+chr(110)+chr(103)+chr(122)+chr(104)+chr(111)+chr(117)+chr(39), chr(39)+chr(32461)+chr(20852)+chr(39): chr(39)+chr(115)+chr(104)+chr(97)+chr(111)+chr(120)+chr(105)+chr(110)+chr(103)+chr(39)}
        for rec in data:
            avg_lat = (float(rec.get('a_lat',0))+float(rec.get('b_lat',0))+float(rec.get('c_lat',0)))/3
            avg_lng = (float(rec.get('a_lng',0))+float(rec.get('b_lng',0))+float(rec.get('c_lng',0)))/3
            _a = find_admin(avg_lat, avg_lng)
            rc = _city_map.get(_a.get('l1', ''), None)
            if not rc:
                rc = which_polygon(avg_lat, avg_lng, REGION_CONFIG) or chr(39)+chr(104)+chr(97)+chr(110)+chr(103)+chr(122)+chr(104)+chr(111)+chr(117)+chr(39)
            region_groups.setdefault(rc, []).append(rec)"""
c = c.replace(old, new)
with open(fp, "w", encoding="utf-8") as f:
    f.write(c)
compile(open(fp, "r", encoding="utf-8").read(), "app.py", "exec")
print("Syntax OK")
