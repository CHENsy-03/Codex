import logging
import time
from urllib.parse import urlparse, urlencode
import requests as req
from fetcher.session_manager import get_session_for_domain
from anti_crawler.jitter import jitter_sleep
from anti_crawler.rate_limiter import RateLimiter
from anti_crawler.circuit_breaker import CircuitBreaker

log = logging.getLogger('crawler.http_client')


def fetch(url, site_cfg=None, max_retries=3, timeout=15):
    """请求流程：Session -> RateLimiter -> Jitter -> CircuitBreaker -> HTTP"""
    domain = urlparse(url).netloc
    session = get_session_for_domain(domain)
    rate_cfg = site_cfg.get('rate_limit', {}) if site_cfg else {}
    delay = rate_cfg.get('delay', 1.5)
    jitter = rate_cfg.get('jitter', 0.8)
    max_r = rate_cfg.get('max_retry', max_retries)
    rl = RateLimiter(rate=rate_cfg.get('rate', max(0.5, 1.0 / (delay or 1.5))), per=1)
    cb = CircuitBreaker(name=domain)
    for attempt in range(1, max_r + 1):
        try:
            rl.acquire()
            def _do():
                jitter_sleep(delay, jitter)
                resp = session.get(url, timeout=timeout)
                resp.encoding = resp.apparent_encoding or resp.encoding or 'utf-8'
                if resp.status_code >= 300:
                    raise Exception('HTTP ' + str(resp.status_code))
                return resp
            return cb.call(_do)
        except RuntimeError as e:
            if 'OPEN' in str(e):
                log.warning('Breaker open for %s, skip %s', domain, url[:50])
                return None
            raise
        except Exception as e:
            if attempt < max_r:
                log.warning('Retry %d/%d for %s: %s', attempt, max_r, url[:50], str(e)[:60])
                time.sleep(attempt)
            else:
                log.warning('Failed after %d retries: %s', max_r, url[:50])
        if attempt < max_r:
            time.sleep(attempt)
    return None


def get_json(url, params=None, site_cfg=None, max_retries=3, timeout=15):
    # GET with custom headers for JPAAS API
    from urllib.parse import urlparse
    domain = urlparse(url).netloc
    session = get_session_for_domain(domain)
    rate_cfg = site_cfg.get('rate_limit', {}) if site_cfg else {}
    delay = rate_cfg.get('delay', 1.5)
    jitter = rate_cfg.get('jitter', 0.8)
    max_r = rate_cfg.get('max_retry', max_retries)
    rl = RateLimiter(rate=rate_cfg.get('rate', max(0.5, 1.0 / (delay or 1.5))), per=1)
    cb = CircuitBreaker(name=domain)
    for attempt in range(1, max_r + 1):
        try:
            rl.acquire()
            def _do():
                jitter_sleep(delay, jitter)
                headers = {'X-Requested-With': 'XMLHttpRequest','Accept': 'application/json','Referer': url}
                resp = session.get(url, params=params, headers=headers, timeout=timeout)
                if resp.status_code == 200:
                    return resp.json()
                raise Exception('HTTP ' + str(resp.status_code))
            return cb.call(_do)
        except RuntimeError as e:
            if 'OPEN' in str(e):
                log.warning('Breaker open for %s, skip', domain)
                return None
            raise
        except Exception as e:
            if attempt < max_r:
                log.warning('JPAAS retry %d/%d: %s', attempt, max_r, str(e)[:60])
                time.sleep(attempt)
            else:
                log.warning('JPAAS failed after %d retries: %s', max_r, url[:50])
    return None
def post_json(url, data, site_cfg=None, max_retries=3, timeout=15):
    """POST请求（form-encoded），专为TRS API设计"""
    domain = urlparse(url).netloc
    session = get_session_for_domain(domain)
    rate_cfg = site_cfg.get('rate_limit', {}) if site_cfg else {}
    delay = rate_cfg.get('delay', 1.5)
    jitter = rate_cfg.get('jitter', 0.8)
    max_r = rate_cfg.get('max_retry', max_retries)
    rl = RateLimiter(rate=rate_cfg.get('rate', max(0.5, 1.0 / (delay or 1.5))), per=1)
    cb = CircuitBreaker(name=domain)
    for attempt in range(1, max_r + 1):
        try:
            rl.acquire()
            def _do_post():
                jitter_sleep(delay, jitter)
                headers = {'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
                resp = session.post(url, data=urlencode(data), headers=headers, timeout=timeout)
                if resp.status_code == 200:
                    return resp.json()
                raise Exception('POST HTTP ' + str(resp.status_code))
            return cb.call(_do_post)
        except RuntimeError as e:
            if 'OPEN' in str(e):
                log.warning('Breaker open for %s, skip', domain)
                return None
            raise
        except Exception as e:
            if attempt < max_r:
                log.warning('POST retry %d/%d: %s', attempt, max_r, str(e)[:60])
                time.sleep(attempt)
            else:
                log.warning('POST failed after %d retries: %s', max_r, url[:50])
        if attempt < max_r:
            time.sleep(attempt)
    return None
