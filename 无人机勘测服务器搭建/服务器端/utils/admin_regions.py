# -*- coding: utf-8 -*-
CITIES = {'330100': '杭州', '330600': '绍兴'}
DISTRICTS = [
('330102','上城区',120.16922,30.24255),
('330105','拱墅区',120.13,30.32),
('330106','西湖区',120.13,30.27),
('330108','滨江区',120.2,30.2),
('330109','萧山区',120.27,30.17),
('330110','余杭区',120.3,30.42),
('330111','富阳区',119.95,30.05),
('330112','临安区',119.72,30.23),
('330113','临平区',120.29922,30.41915),
('330114','钱塘区',120.49394,30.32304),
('330122','桐庐县',119.67,29.8),
('330127','淳安县',119.03,29.6),
('330182','建德市',119.28,29.48),
('330602','越城区',120.5819,29.98895),
('330603','柯桥区',120.49274,30.08763),
('330604','上虞区',120.47608,30.07804),
('330624','新昌县',120.90435,29.49991),
('330681','诸暨市',120.23629,29.71358),
('330683','嵊州市',120.82174,29.58854),
]
def find_admin(lat,lng):
    best_d = 0.35; best = None
    for c,n,clng,clat in DISTRICTS:
        d = (lat-clat)**2+(lng-clng)**2
        if d < best_d: best_d = d; best = (c,n)
    if best:
            l1_n = '未知'
            for cc,nn in CITIES.items():
                if cc[:4] == best[0][:4]: l1_n = nn; break
            return {'code': best[0], 'name': best[1], 'l1': l1_n, 'l2': best[1]}
    return {'code': '', 'name': '未知', 'l1': '未知', 'l2': '未知'}

def register_city(code, name):
    CITIES[code] = name

def register_district(code, name, lng, lat):
    for i, (c, n, _, _) in enumerate(DISTRICTS):
        if c == code:
            DISTRICTS[i] = (code, name, lng, lat)
            return
    DISTRICTS.append((code, name, lng, lat))

def load_config(filepath):
    if not __import__('os').path.exists(filepath):
        return False
    with open(filepath, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) == 2:
                register_city(parts[0], parts[1])
            elif len(parts) == 4:
                register_district(parts[0], parts[1], float(parts[2]), float(parts[3]))
    return True
