import sys
fp=r"E:\AI_Projects\Codex\无人机勘测服务器搭建\服务器端\app.py"
with open(fp,"r",encoding="utf-8") as f:
    lines=f.readlines()
old=''.join(lines[679:692])
new='''        from utils.geo import which_polygon
        region_groups = {}
        for rec in data:
            avg_lat = (float(rec.get("a_lat",0))+float(rec.get("b_lat",0))+float(rec.get("c_lat",0)))/3
            avg_lng = (float(rec.get("a_lng",0))+float(rec.get("b_lng",0))+float(rec.get("c_lng",0)))/3
            rc = which_polygon(avg_lat, avg_lng, REGION_CONFIG) or "hangzhou"
            region_groups.setdefault(rc, []).append(rec)
        total_ok = 0
        for rc, recs in region_groups.items():
            cfg = REGION_CONFIG.get(rc, {})
            print("  "+cfg.get("name",rc)+" ("+cfg.get("code",rc)+") - "+str(len(recs))+" 条")
            with ShardDatabase(rc) as db:
                ok, msgs = db.import_from_chart(recs, "rural")
                total_ok += ok
        ok = total_ok
'''
c=''.join(lines)
c=c.replace(old,new)
with open(fp,"w",encoding="utf-8") as f:
    f.write(c)
compile(open(fp,"r",encoding="utf-8").read(),"app.py","exec")
print("Syntax OK")
