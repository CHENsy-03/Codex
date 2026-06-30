import sys
sys.stdout.reconfigure(encoding='utf-8')
from utils.admin_regions import find_admin
tests = [(27.32,103.70),(27.19,103.56),(30.29,120.24),(30.02,120.44)]
for lat,lng in tests:
    r = find_admin(lat,lng)
    c = '('+str(lat)+','+str(lng)+') -> p='+r['p']+' l1='+r['l1']+' l2='+r['l2']
    print('  OK: '+c)

from utils.geo import which_polygon
exec(open('db_config.py',encoding='utf-8').read())
CITY = {'杭州':'hangzhou','绍兴':'shaoxing','昭通市':'zhaotong'}
PROV = {'浙江':'zhejiang','云南':'yunnan'}
pts = [(27.32,103.70),(30.29,120.24),(30.02,120.44)]
for lat,lng in pts:
    ad = find_admin(lat,lng)
    rc = CITY.get(ad['l1'],'') or PROV.get(ad.get('p',''),'') or which_polygon(lat,lng,REGION_CONFIG) or 'hangzhou'
    print('  Route: '+ad['p']+'>'+ad['l1']+' -> '+rc)

import py_compile
for f in ['utils/admin_regions.py','db_config.py','app.py','gateway.py']:
    try:
        py_compile.compile(f,doraise=True)
        print('  [OK] '+f)
    except py_compile.PyCompileError as e:
        print('  [FAIL] '+f+': '+str(e))
print('Done')

