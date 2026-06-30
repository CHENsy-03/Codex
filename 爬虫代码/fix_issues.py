import os, py_compile
 
 base = 'E:/AI_Projects/Codex/爬虫代码'
 
 # Fix 1: Add polite_sleep to run.py imports
 fp = os.path.join(base, 'run.py')
 with open(fp, 'r', encoding='utf-8') as f:
     c = f.read()
 c = c.replace(
     'from modules.fetch import make_session, request_with_retries',
     'from modules.fetch import make_session, request_with_retries, polite_sleep'
 )
 with open(fp, 'w', encoding='utf-8') as f:
     f.write(c)
 print('Fix 1: added polite_sleep import')
 
 # Fix 2: Add safe_post_form to fetch.py
 fp = os.path.join(base, 'modules', 'fetch.py')
 with open(fp, 'r', encoding='utf-8') as f:
     c = f.read()
 new_func = '''
 def safe_post_form(url, data, max_retries=3, timeout=15):
     import urllib.parse
     ua = random_ua()
     headers = {'User-Agent': ua,
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json, text/plain, */*'}
     for attempt in range(1, max_retries + 1):
         try:
             resp = requests.post(url, data=urllib.parse.urlencode(data), headers=headers, timeout=timeout)
             if resp.status_code == 200:
                 return resp.json()
             log.warning('POST form HTTP %d (attempt %d)', resp.status_code, attempt)
         except requests.RequestException as e:
             log.warning('POST form failed (attempt %d): %s', attempt, str(e)[:60])
         if attempt < max_retries:
             time.sleep(attempt * 0.5)
     return None
 '''
 c = c.replace('def fetch_url(url, timeout=15):', new_func + 'def fetch_url(url, timeout=15):')
 with open(fp, 'w', encoding='utf-8') as f:
     f.write(c)
 print('Fix 2: added safe_post_form function')
 
 # Fix 3: Update search_trs to use safe_post_form
 fp = os.path.join(base, 'modules', 'crawler.py')
 with open(fp, 'r', encoding='utf-8') as f:
     c = f.read()
 c = c.replace(
     'from modules.fetch import make_session, request_with_retries, safe_post_json, polite_sleep',
     'from modules.fetch import make_session, request_with_retries, safe_post_json, safe_post_form, polite_sleep'
 )
 c = c.replace('result = safe_post_json(api_url, params)', 'result = safe_post_form(api_url, params)')
 with open(fp, 'w', encoding='utf-8') as f:
     f.write(c)
 print('Fix 3: updated search_trs to use safe_post_form')
 
 # Verify
 for f in ['run.py', 'modules/fetch.py', 'modules/crawler.py']:
     fp2 = os.path.join(base, f)
     try:
         py_compile.compile(fp2, doraise=True)
         print(f'  OK: {f}')
     except py_compile.PyCompileError as e:
         print(f'  ERR: {f}: {str(e)[:100]}')
