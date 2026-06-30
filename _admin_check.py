import re, sys
sys.path.insert(0,r"E:\AI_Projects\Codex\无人机勘测服务器搭建\服务器端")
from utils.admin_regions import find_admin
from utils.geo import which_polygon
from db_config import REGION_CONFIG

p=re.compile(r"(\d{4}\.\d+),N,(\d{5}\.\d+),E")
lats=[]; lngs=[]
with open(r"E:\AI_Projects\Codex\模拟GPS定位脚本\随机生成（不重复）.txt","rb") as f:
    for raw in f:
        try: line=raw.decode("utf-8",errors="replace")
        except: continue
        m=p.search(line)
        if m:
            lat=int(m.group(1)[:2])+float(m.group(1)[2:])/60
            lng=int(m.group(2)[:3])+float(m.group(2)[3:])/60
            lats.append(lat); lngs.append(lng)
print("Points:",len(lats),"Groups:",len(lats)//3)
hw=sx=unk=0
for i in range(0,len(lats)-2,3):
    al=(lats[i]+lats[i+1]+lats[i+2])/3
    ag=(lngs[i]+lngs[i+1]+lngs[i+2])/3
    a=find_admin(al,ag)
    c=which_polygon(al,ag,REGION_CONFIG)
    if c=="hangzhou": hw+=1
    elif c=="shaoxing": sx+=1
    else: unk+=1
    if i//3+1<=30:
        d=a.get("l1","?")+" "+a.get("l2","?")
        print(str(i//3+1)+": "+d+" (city="+str(c)+")")
print("Total: HW="+str(hw)+" SX="+str(sx)+" UNK="+str(unk))
