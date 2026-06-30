import requests
import random
import time
import logging

log = logging.getLogger('crawler.fetch')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/131.0.0.0 Edg/131.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.1 Safari/605.1.15',
]

def random_ua():
    return random.choice(USER_AGENTS)

def make_session(site_cfg=None):
    s = requests.Session()
    s.headers.update({'User-Agent': random_ua(), 'Accept': 'text/html,*/*'})
    if site_cfg and site_cfg.get('proxy_url'):
        p = site_cfg['proxy_url']
        s.proxies = {'http': p, 'https': p}
    return s

def polite_sleep(rate_cfg=None, factor=1.0):
    delay = rate_cfg.get('delay', 1.5) if rate_cfg else 1.5
    jitter = rate_cfg.get('jitter', 0.8) if rate_cfg else 0.8
    d = max(0.0, delay * factor)
    if jitter > 0:
        d += random.uniform(0, jitter)
    if d > 0:
        time.sleep(d)

def request_with_retries(session, method, url, max_retries=3, timeout=15, **kwargs):
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.request(method, url, timeout=timeout, **kwargs)
            resp.encoding = resp.apparent_encoding or resp.encoding or 'utf-8'
            if 200 <= resp.status_code < 300:
                return resp
            log.warning('HTTP %d (attempt %d/%d): %s', resp.status_code, attempt, max_retries, url[:80])
        except requests.RequestException as e:
            log.warning('Request failed (attempt %d/%d): %s', attempt, max_retries, str(e)[:60])
        if attempt < max_retries:
            polite_sleep(None, factor=attempt)
    return None

def safe_post_json(api_url, data, max_retries=3, timeout=15, site_cfg=None):
    ua = random_ua()
    headers = {'User-Agent': ua, 'Content-Type': 'application/json', 'Accept': 'application/json'}
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(api_url, json=data, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            log.warning('POST HTTP %d (attempt %d): %s', resp.status_code, attempt, api_url[:60])
        except requests.RequestException as e:
            log.warning('POST failed (attempt %d): %s', attempt, str(e)[:60])
        if attempt < max_retries:
            time.sleep(attempt * 0.5)
    return None


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

def fetch_url(url, timeout=15):
    s = make_session()
    return request_with_retries(s, 'GET', url, max_retries=3, timeout=timeout)
