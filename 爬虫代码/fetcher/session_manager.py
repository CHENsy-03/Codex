from anti_crawler.ua_pool import UAPool

_ua_pool = UAPool()


def get_session_for_domain(domain):
    """每个域名绑定固定UA"""
    import requests
    ua = _ua_pool.get_for_domain(domain)
    s = requests.Session()
    s.headers.update({
        'User-Agent': ua,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    })
    return s


def get_random_session():
    import requests
    ua = _ua_pool.get_random()
    s = requests.Session()
    s.headers.update({'User-Agent': ua})
    return s
