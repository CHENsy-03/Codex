import re
p=re.compile(r'(\d{4}\.\d+),N,(\d{5}\.\d+),E')
lats=[]; lngs=[]
for line in open(r'E:\AI_Projects\Codex\模拟GPS定位脚本\随机生成（不重复）.txt','r',encoding='utf-8'):
    m=p.search(line)
    if m:
        lat=int(m.group(1)[:2])+float(m.group(1)[2:])/60
        lng=int(m.group(2)[:3])+float(m.group(2)[3:])/60
        lats.append(lat); lngs.append(lng)
print('GPS points:', len(lats), 'Groups:', len(lats)//3)
