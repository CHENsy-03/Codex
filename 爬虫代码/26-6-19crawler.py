#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
融合版爬虫 — 整合两个版本的优势
=================================
核心特性:
  - 直接调用后端 JSON API（快速 + 隐蔽）
  - lxml + 正则双保险 HTML 解析（微信版）
  - 多站点配置驱动（SITE_CONFIGS）
  - 随机 UA 轮换 + 随机间隔 + 指数退避
  - 全量翻页（不限制 2 页）
  - 站点自动发现 --discover
  - Selenium 浏览器回退
  - 正文打分提取 + 文章跨关键词合并
  - --title-only / --with-detail / --self-test
  - JSON + CSV 双格式导出

目标关键词: 低空经济 / 低空政策 / 低空监管 / 低空
"""

from __future__ import annotations
import argparse, csv, html as html_lib, json, logging, os, random, re, sys, time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional, Tuple
from urllib.parse import quote, urlencode, urljoin, urlparse
import requests

try:
    from lxml import html as lxml_html
except ImportError:
    lxml_html = None

try:
    from selenium import webdriver
    from selenium.webdriver.edge.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

def configure_stdio() -> None:
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
configure_stdio()

@dataclass
class CrawlStats:
    start_time: datetime = field(default_factory=datetime.now)
    request_total: int = 0
    request_success: int = 0
    request_fail: int = 0
    article_total: int = 0
    article_matched: int = 0
    column_count: int = 0
    keywords: tuple = ()
    site_key: str = ''

    def summary(self) -> str:
        elapsed = datetime.now() - self.start_time
        e = str(elapsed).split('.')[0]
        return ('[Stats] site=' + self.site_key + ' | req=' + str(self.request_total)
                + ' (ok=' + str(self.request_success) + ', fail=' + str(self.request_fail)
                + ') | articles=' + str(self.article_total) + ' matched=' + str(self.article_matched)
                + ' | cols=' + str(self.column_count) + ' | time=' + e)

# ============================================================
#  配置
# ============================================================
SITE_CONFIGS: dict[str, dict] = {
    "czj_beijing": {
        "name": "北京市财政局", "domain": "czj.beijing.gov.cn",
        "base_url": "https://czj.beijing.gov.cn",
        "search_page_url": "https://czj.beijing.gov.cn/so/s",
        "search_api_url": "https://czj.beijing.gov.cn/so/ss/query/s",
        "site_code": "1100000092", "api_type": "trs_json",
    },
    "bj_gov": {
        "name": "北京市人民政府", "domain": "www.beijing.gov.cn",
        "base_url": "https://www.beijing.gov.cn",
        "search_page_url": "https://www.beijing.gov.cn/so/s",
        "search_api_url": "https://www.beijing.gov.cn/so/ss/query/s",
        "site_code": "1100000092", "api_type": "trs_json",
    },
    "czj_hangzhou": {
        "name": "杭州市财政局", "domain": "czj.hangzhou.gov.cn",
        "base_url": "https://czj.hangzhou.gov.cn",
        "search_page_url": "https://search.zj.gov.cn/api-gateway/jpaas-jsearch-web-server/search",
        "search_api_url": "https://search.zj.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info",
        "site_code": "330100000000",
        "api_type": "jpaas_jsearch",
        "jpaas_service_id": "YcTOd1ftgC5dxzJ8RhCBN",
       "jpaas_web_id": "3217",
    },
   "sxcs_shaoxing": {
       "name": "绍兴市财政局", "domain": "sxcs.sx.gov.cn",
       "base_url": "https://sxcs.sx.gov.cn",
       "search_page_url": "https://sxcs.sx.gov.cn",
        "search_api_url": "https://search.zj.gov.cn/api-gateway/jpaas-jsearch-web-server/interface/search/app/info",
        "site_code": "330600000000",
        "api_type": "jpaas_jsearch",
        "jpaas_service_id": "YcTOd1ftgC5dxzJ8RhCBN",
        "jpaas_web_id": "2959",
    },
}
DEFAULT_SITE = "czj_beijing"
DEFAULT_KEYWORDS = ("低空经济", "低空政策", "低空监管", "低空")
DEFAULT_OUTPUT_DIR = "output_czj"
PAGE_SIZE = 20
REQUEST_DELAY = 1.5
REQUEST_JITTER = 0.8
MAX_RETRIES = 3
TIMEOUT = 15
MAX_DETAIL_CHARS = 3000

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:133.0) Gecko/20100101 Firefox/133.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
]
ARTICLE_URL_HINTS = (".html", "/content/", "/article/", "/detail/", "/info/", "/zwgk/", "/zwxx/", "/gzdt/", "/tzgg/")
CONTENT_XPATHS = (
    "//article",
    "//*[contains(concat(' ', normalize-space(@class), ' '), ' TRS_Editor ')]",
    "//*[contains(@class, 'article')]",
    "//*[contains(@class, 'content')]",
    "//*[contains(@class, 'main')]",
    "//*[contains(@class, 'text')]",
    "//*[contains(@class, 'detail')]",
    "//*[contains(@id, 'article')]",
    "//*[contains(@id, 'content')]",
    "//*[contains(@id, 'main')]",
    "//*[contains(@id, 'detail')]",
)
DATE_PATTERNS = (
    re.compile(r"(?:发布日期|发布时间|日期)[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)"),
    re.compile(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?"),
    re.compile(r"(\d{4}年\d{1,2}月\d{1,2}日)"),
)
TAG_RE = re.compile(r"(?is)<(script|style|noscript).*?</\1>|<[^>]+>")
SPACE_RE = re.compile(r"\s+")

# ============================================================
#  日志
# ============================================================
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("crawler")
# ============================================================
#  运行时配置
# ============================================================
@dataclass
class CrawlConfig:
    site_key: str = DEFAULT_SITE
    name: str = ""; domain: str = ""; base_url: str = ""
    search_page_url: str = ""; search_api_url: Optional[str] = ""
    site_code: str = ""
    proxy_url: str = ""
    api_type: str = ""

    jpaas_service_id: str = ""

    jpaas_web_id: str = ""

    keywords: Tuple[str, ...] = DEFAULT_KEYWORDS
    output_dir: Path = Path(DEFAULT_OUTPUT_DIR)
    request_delay: float = REQUEST_DELAY
    request_jitter: float = REQUEST_JITTER
    max_retries: int = MAX_RETRIES
    timeout: int = TIMEOUT
    page_size: int = PAGE_SIZE
    max_pages: int = 0
    fetch_details: bool = False
    force_html: bool = False
    same_domain_only: bool = True
    max_detail_chars: int = MAX_DETAIL_CHARS
    title_only: bool = False
    use_selenium: bool = False

    @classmethod
    def from_site(cls, site_key: str, **overrides: Any) -> CrawlConfig:
        s = SITE_CONFIGS.get(site_key, {})
        return cls(site_key=site_key, name=s.get("name", ""), domain=s.get("domain", ""),

                  base_url=s.get("base_url", ""), search_page_url=s.get("search_page_url", ""),
                   search_api_url=s.get("search_api_url", ""), site_code=s.get("site_code", ""),
                   api_type=s.get("api_type", ""), jpaas_service_id=s.get("jpaas_service_id", ""),
                   jpaas_web_id=s.get("jpaas_web_id", ""), proxy_url=s.get("proxy_url", ""), **overrides)

def _random_ua() -> str:
    return random.choice(USER_AGENTS)

def _random_headers(extra: Optional[dict] = None) -> dict:
    h = {"User-Agent": _random_ua(), "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
         "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8", "Accept-Encoding": "gzip, deflate", "Connection": "keep-alive"}
    if extra: h.update(extra)
    return h

def clean_text(value: Any) -> str:
    if value is None: return ""
    text = TAG_RE.sub(" ", str(value))
    text = html_lib.unescape(text)
    text = text.replace("\xa0", " ").replace("\u3000", " ")
    return SPACE_RE.sub(" ", text).strip()

def normalize_date(value: Any) -> str:
    text = clean_text(value)
    if not text: return ""
    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if not m: continue
        parts = re.findall(r"\d+", m.group(1))
        if len(parts) >= 3: return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    return ""

def safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))

# ============================================================
#  请求工具
# ============================================================
def make_session(config: CrawlConfig) -> requests.Session:
    s = requests.Session()
    s.headers.update(_random_headers())
    if config.search_page_url:
        s.headers.update({"Referer": config.search_page_url})
    if config.proxy_url:
        s.proxies = {"http": config.proxy_url, "https": config.proxy_url}
    return s

def polite_sleep(config: CrawlConfig, factor: float = 1.0) -> None:
    d = max(0.0, config.request_delay * factor)
    if config.request_jitter > 0: d += random.uniform(0, config.request_jitter)
    if d > 0: time.sleep(d)

def request_with_retries(session: requests.Session, method: str, url: str, config: CrawlConfig, **kwargs: Any) -> Optional[requests.Response]:
    for attempt in range(1, config.max_retries + 1):
        try:
            resp = session.request(method, url, timeout=config.timeout, **kwargs)
            resp.encoding = resp.apparent_encoding or resp.encoding or "utf-8"
            if 200 <= resp.status_code < 300: return resp
            log.warning("HTTP %s (attempt %d/%d): %s", resp.status_code, attempt, config.max_retries, url[:80])
        except requests.RequestException as exc:
            log.warning("Request failed (attempt %d/%d): %s", attempt, config.max_retries, str(exc)[:80])
        if attempt < config.max_retries: polite_sleep(config, factor=attempt)
    return None

def safe_post_json(api_url: str, data: dict, session: requests.Session, config: CrawlConfig, origin: str = "") -> Optional[dict]:
    ua = _random_ua()
    headers = {"User-Agent": ua, "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Accept": "application/json, text/plain, */*"}
    if origin: headers["Origin"] = origin; headers["Referer"] = origin + "/"
    for attempt in range(1, config.max_retries + 1):
        try:
            resp = session.post(api_url, data=urlencode(data), headers=headers, timeout=config.timeout)
            if resp.status_code == 200:
                try: return resp.json()
                except json.JSONDecodeError: log.warning("Non-JSON: %s...", resp.text[:200])
            else: log.warning("HTTP %d (attempt %d): %s", resp.status_code, attempt, api_url[:80])
        except requests.RequestException as e:
            log.warning("POST failed (attempt %d/%d): %s", attempt, config.max_retries, str(e)[:80])
        if attempt < config.max_retries: polite_sleep(config, factor=attempt)
    return None
# ============================================================
#  HTML 解析工具
# ============================================================
def same_domain(base_url: str, target_url: str) -> bool:
    bh = urlparse(base_url).netloc.lower(); th = urlparse(target_url).netloc.lower()
    if not bh or not th: return True
    return th == bh or th.endswith("." + bh)

def should_keep_link(title: str, url: str, keywords: Iterable[str]) -> bool:
    kws = tuple(kw for kw in keywords if kw)
    haystack = f"{title} {url}"
    if kws and any(kw in haystack for kw in kws): return True
    return any(hint in url.lower() for hint in ARTICLE_URL_HINTS)

def extract_date_from_text(text: str) -> str:
    return normalize_date(text)

def _node_text(node: Any) -> str:
    try: return clean_text(node.text_content())
    except Exception: return ""

def _context_summary_for_link(link: Any, title: str, keyword: str) -> Tuple[str, str]:
    date = ""; summary = ""
    for depth, node in enumerate([link, *list(link.iterancestors())]):
        if depth > 4: break
        text = _node_text(node)
        if not text: continue
        if not date: date = extract_date_from_text(text)
        if not summary and keyword and keyword in text: summary = text.replace(title, " ").strip()
        if date and summary: break
    return clean_text(summary)[:300], date

def _regex_context_for_match(html: str, match: re.Match, title: str, keyword: str) -> Tuple[str, str]:
    sc = [html.rfind(t, 0, match.start()) for t in ("<li", "<div", "<tr", "<p", "<section", "<article")]
    cs = max([i for i in sc if i >= 0], default=max(0, match.start() - 600))
    ec = []
    for t in ("</li>", "</div>", "</tr>", "</p>", "</section>", "</article>"):
        i = html.find(t, match.end())
        if i >= 0: ec.append(i + len(t))
    ce = min(ec) if ec else min(len(html), match.end() + 800)
    ct = clean_text(html[cs:ce])
    pd = extract_date_from_text(ct)
    sm = ct.replace(title, " ").strip()
    if keyword and keyword not in sm: sm = ""
    return clean_text(sm)[:300], pd

def extract_links_from_html(html: str, base_url: str, keywords: Iterable[str] = (), same_domain_only: bool = True) -> list[dict]:
    keywords = tuple(keywords)
    articles: list[dict] = []
    if lxml_html is not None:
        try:
            doc = lxml_html.fromstring(html)
            doc.make_links_absolute(base_url)
            for link in doc.xpath("//a[@href]"):
                url = (link.get("href") or "").strip()
                if not url or url.startswith(("javascript:", "mailto:", "tel:", "#")): continue
                if same_domain_only and not same_domain(base_url, url): continue
                title = clean_text(link.get("title") or link.text_content())
                if not title or len(title) < 2: continue
                if not should_keep_link(title, url, keywords): continue
                kw = next((k for k in keywords if k and k in f"{title} {url}"), "")
                sm, pd = _context_summary_for_link(link, title, kw)
                articles.append({"title": title, "url": url, "publish_date": pd, "summary": sm, "content": "", "source": "", "source_keywords": [kw] if kw else []})
        except Exception as exc: log.warning("lxml failed: %s", str(exc)[:60])
    if not articles:
        lp = re.compile(r"<a\b(?P<attrs>(?:[^>\"]+|\"[^\"]*\"|'[^']*')*)>(?P<body>.*?)</a>", re.I | re.S)
        hp = re.compile(r"\bhref\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<bare>[^\s>]+))", re.I)
        tp = re.compile(r"\btitle\s*=\s*(?:\"(?P<dq>[^\"]*)\"|'(?P<sq>[^']*)'|(?P<bare>[^\s>]+))", re.I)
        for m in lp.finditer(html):
            attrs = m.group("attrs")
            hm = hp.search(attrs)
            if not hm: continue
            rh = next((hm.group(n) for n in ("dq", "sq", "bare") if hm.group(n)), "").strip()
            if not rh or rh.startswith(("javascript:", "mailto:", "tel:", "#")): continue
            url = urljoin(base_url, rh)
            if same_domain_only and not same_domain(base_url, url): continue
            tm = tp.search(attrs)
            rt = next((tm.group(n) for n in ("dq", "sq", "bare") if tm.group(n)), "") if tm else ""
            title = clean_text(rt or m.group("body"))
            if not title or len(title) < 2: continue
            if not should_keep_link(title, url, keywords): continue
            kw = next((k for k in keywords if k and k in f"{title} {url}"), "")
            sm, pd = _regex_context_for_match(html, m, title, kw)
            articles.append({"title": title, "url": url, "publish_date": pd, "summary": sm, "content": "", "source": "", "source_keywords": [kw] if kw else []})
    return dedupe_articles(articles)
# ============================================================
#  API 搜索
# ============================================================
def normalize_api_doc(result_doc: dict, keyword: str) -> Optional[dict]:
    data = result_doc.get("data") if isinstance(result_doc.get("data"), dict) else result_doc
    if not isinstance(data, dict): return None
    title = clean_text(data.get("titleO") or data.get("title") or data.get("TITLE"))
    url = clean_text(data.get("url") or data.get("URL") or data.get("parentUrl"))
    if not title or not url: return None
    ft = clean_text(data.get("fileType")).lower()
    pu = clean_text(data.get("parentUrl"))
    if pu and ft and ft not in {"html", "data"}: url = pu
    sl = data.get("siteLabel")
    source = clean_text(sl.get("value")) if isinstance(sl, dict) else clean_text(data.get("source") or "")
    return {"title": title, "url": url,
            "publish_date": normalize_date(data.get("docDate") or data.get("dreDate") or data.get("publishTime")),
            "summary": clean_text(data.get("summary") or data.get("content") or ""),
            "content": "", "source": source, "source_keywords": [keyword] if keyword else []}

def search_by_api(keyword: str, session: requests.Session, config: CrawlConfig) -> list[dict]:
    if not config.search_api_url: return []
    log.info("  [API] %s", keyword)
    articles: list[dict] = []; total_hits: Optional[int] = None; page = 1
    while True:
        data = {"siteCode": config.site_code, "tab": "", "qt": keyword, "page": page, "pageSize": config.page_size}
        result = safe_post_json(config.search_api_url, data, session, config, origin=config.base_url)
        if not result: break
        if result.get("ok") is False: log.warning("  API error: %s", str(result.get("msg", ""))[:60]); break
        total_hits = result.get("totalHits", total_hits)
        docs = result.get("resultDocs") or []
        pa = [a for a in (normalize_api_doc(d, keyword) for d in docs) if a]
        articles.extend(pa)
        log.info("  Page %d: %d hits", page, len(pa))
        if not docs or len(pa) < config.page_size: break
        if total_hits and len(articles) >= int(total_hits): break
        if config.max_pages > 0 and page >= config.max_pages: break
        page += 1; polite_sleep(config)
    return dedupe_articles(articles)

# ============================================================
#  HTML 搜索
# ============================================================
def search_by_html(keyword: str, session: requests.Session, config: CrawlConfig) -> list[dict]:
    if not config.search_page_url: return []
    log.info("  [HTML] %s", keyword)
    articles: list[dict] = []; page = 1
    while True:
        if "{" in config.search_page_url:
            url = config.search_page_url.format(keyword=quote(keyword), query=quote(keyword), raw_keyword=keyword, page=page, page_size=config.page_size, site_code=config.site_code)
        else:
            params = {"qt": keyword, "page": page, "pageSize": config.page_size}
            if config.site_code: params["siteCode"] = config.site_code
            sep = "&" if "?" in config.search_page_url else "?"
            url = config.search_page_url + sep + urlencode(params)
        resp = request_with_retries(session, "GET", url, config)
        if not resp: break
        pa = extract_links_from_html(resp.text, config.base_url, keywords=(keyword,), same_domain_only=config.same_domain_only)
        if not pa: break
        articles.extend(pa)
        log.info("  Page %d: %d candidates", page, len(pa))
        if config.max_pages > 0 and page >= config.max_pages: break
        page += 1; polite_sleep(config)
    return dedupe_articles(articles)
# ============================================================
#  Selenium 回退
# ============================================================
def search_via_selenium(config: CrawlConfig) -> list[dict]:
    if not HAS_SELENIUM: log.error("Selenium not installed"); return []
    if not config.search_page_url: return []
    all_r: list[dict] = []; seen: set = set()
    for kw in config.keywords:
        log.info("  [Selenium] %s", kw)
        driver = None
        try:
            opts = Options()
            opts.add_argument("--headless=new"); opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_experimental_option("excludeSwitches", ["enable-automation"])
            opts.add_experimental_option("useAutomationExtension", False)
            opts.add_argument("--disable-gpu"); opts.add_argument("--window-size=1920,1080")
            opts.add_argument("--no-sandbox"); opts.add_argument("--disable-dev-shm-usage")
            if config.proxy_url:
                opts.add_argument('--proxy-server=' + config.proxy_url)
            opts.add_argument(f"--user-agent={_random_ua()}")
            driver = webdriver.Edge(options=opts)
            sep = "&" if "?" in config.search_page_url else "?"
            url = config.search_page_url + sep + urlencode({"tab": "all", "siteCode": config.site_code, "q": kw})
            driver.get(url)
            try: WebDriverWait(driver, 20).until(lambda d: d.execute_script("return document.getElementById('left-box').children.length > 0"))
            except TimeoutException: time.sleep(5)
            page = 1
            while True:
                if config.max_pages > 0 and page > config.max_pages: break
                polite_sleep(config)
                try:
                    lb = driver.find_element(By.ID, "left-box")
                    links = lb.find_elements(By.TAG_NAME, "a")
                except NoSuchElementException: break
                for lk in links:
                    try:
                        href = lk.get_attribute("href"); title = lk.get_attribute("title") or lk.text.strip()
                        if not title or not href: continue
                        item = {"title": clean_text(title), "url": href if href.startswith("http") else urljoin(config.base_url, href), "summary": "", "content": "", "publish_date": "", "source": config.name, "source_keywords": [kw]}
                        if item["url"] not in seen: seen.add(item["url"]); all_r.append(item)
                    except Exception: continue
                try:
                    n = driver.find_element(By.CSS_SELECTOR, "a[class*='next'], .M-box a.next, .pagination a.next")
                    n.click(); page += 1
                except NoSuchElementException: break
        except Exception as e: log.error("  Selenium error: %s", str(e)[:100])
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
    log.info("  Selenium total: %d", len(all_r))
    return all_r

# ============================================================
#  详情页抓取
# ============================================================
def extract_title_from_detail(html: str) -> str:
    if lxml_html is not None:
        try:
            doc = lxml_html.fromstring(html)
            for node in doc.xpath("//h1/text() | //title/text()"):
                t = clean_text(node)
                if t: return t
        except Exception: pass
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return clean_text(m.group(1)) if m else ""

def regex_content_candidates(html: str) -> list[str]:
    cds: list[str] = []
    for pat in (re.compile(r"<!--\s*正文开始\s*-->(?P<body>.*?)<!--\s*正文结束\s*-->", re.I | re.S),
                re.compile(r"<div\b[^>]*(?:id|class)\s*=\s*[\"'][^\"']*(?:mainText|TRS_Editor|TRS_UEDITOR|article|content|detail|text)[^\"']*[\"'][^>]*>(?P<body>.*?)</div>", re.I | re.S),
                re.compile(r"<article\b[^>]*>(?P<body>.*?)</article>", re.I | re.S)):
        for m in pat.finditer(html):
            body = m.group("body"); text = clean_text(body)
            if len(text) >= 40: cds.append(text)
    return cds

def extract_content_from_detail(html: str, max_chars: int = MAX_DETAIL_CHARS) -> str:
    if lxml_html is not None:
        try:
            doc = lxml_html.fromstring(html)
            for bad in doc.xpath("//script|//style|//noscript|//iframe|//nav|//header|//footer|//form"): bad.drop_tree()
            cds: list[Tuple[int, str]] = []
            for xpath in CONTENT_XPATHS:
                for node in doc.xpath(xpath):
                    text = _node_text(node)
                    if len(text) >= 80:
                        pc = len(node.xpath(".//p")) if hasattr(node, "xpath") else 0
                        cds.append((len(text) + pc * 80, text))
            if cds:
                cds.sort(key=lambda x: x[0], reverse=True); return cds[0][1][:max_chars]
            paras = [clean_text(p.text_content()) for p in doc.xpath("//p") if len(clean_text(p.text_content())) >= 20]
            if paras: return clean_text(" ".join(paras))[:max_chars]
        except Exception as exc: log.debug("lxml content parse failed: %s", str(exc)[:60])
    cds = regex_content_candidates(html)
    if cds: cds.sort(key=len, reverse=True); return cds[0][:max_chars]
    return clean_text(TAG_RE.sub(" ", html))[:max_chars]

def extract_date_from_html(html: str) -> str:
    if lxml_html is not None:
        try:
            doc = lxml_html.fromstring(html)
            for xpath in ("//*[@name='PubDate']/@content", "//*[@name='publishdate']/@content", "//*[@name='date']/@content", "//*[@property='article:published_time']/@content"):
                for value in doc.xpath(xpath):
                    d = normalize_date(value)
                    if d: return d
        except Exception: pass
    return extract_date_from_text(html)

def fetch_detail(article: dict, session: requests.Session, config: CrawlConfig) -> dict:
    url = article.get("url", "")
    if not url: return article
    headers = _random_headers({"Referer": config.base_url + "/"})
    for attempt in range(1, config.max_retries + 1):
        try:
            resp = session.get(url, headers=headers, timeout=config.timeout)
            if resp.status_code == 200:
                html = resp.text
                if not article.get("publish_date"): article["publish_date"] = extract_date_from_html(html)
                if not article.get("title"): article["title"] = extract_title_from_detail(html)
                content = extract_content_from_detail(html, config.max_detail_chars)
                if content: article["content"] = content
                if content and not article.get("summary"): article["summary"] = content[:300]
                break
        except requests.RequestException as e:
            log.warning("  Detail failed (attempt %d/%d): %s", attempt, config.max_retries, str(e)[:60])
            if attempt < config.max_retries: polite_sleep(config, factor=attempt)
    return article
# ============================================================
#  文章合并 & 去重
# ============================================================
def merge_article(existing: dict, new_item: dict) -> dict:
    for f in ("title", "publish_date", "summary", "content", "source"):
        if not existing.get(f) and new_item.get(f): existing[f] = new_item[f]
    old = existing.get("source_keywords") or []; new = new_item.get("source_keywords") or []
    merged = list(old)
    for kw in new:
        if kw and kw not in merged: merged.append(kw)
    existing["source_keywords"] = merged
    return existing

def dedupe_articles(articles: Iterable[dict]) -> list[dict]:
    seen: dict[str, dict] = {}
    for a in articles:
        url = a.get("url", "")
        if not url: continue
        if url in seen: merge_article(seen[url], a)
        else: item = dict(a); item.setdefault("source_keywords", []); seen[url] = item
    return list(seen.values())

# ============================================================
#  站点发现
# ============================================================
def discover_site(base_url: str, timeout: int = 15) -> Optional[dict]:
    log.info("-- Site discovery: %s --", base_url)
    session = requests.Session(); session.headers.update({"User-Agent": _random_ua()})
    html = None; final_url = ""
    for path in ("/so/s", "/search/s", "/site/s", "/search", "/s"):
        try:
            resp = session.get(urljoin(base_url, path) + "?q=test", timeout=timeout)
            if resp.status_code == 200 and len(resp.text) > 500:
                html = resp.text; final_url = resp.url; log.info("  Found: %s", final_url); break
        except requests.RequestException: continue
    if not html: log.warning("  No search page found"); return None
    sc = re.search(r"siteCode[=:]\s*[\"']?(\d+)\"?", html)
    site_code = sc.group(1) if sc else ""
    ab = re.search(r"api\.basic\s*=\s*[\"']([^\"']+)[\"']", html)
    api_basic = ab.group(1) if ab else ""
    if not site_code:
        sm = re.search(r'<meta[^>]*name="SiteIDCode"[^>]*content="(\d+)"', html)
        if sm: site_code = sm.group(1)
    sn = re.search(r'<meta[^>]*name="SiteName"[^>]*content="([^"]+)"', html)
    site_name = sn.group(1) if sn else ""
    if site_code or api_basic:
        search_api = urljoin(final_url, "ss/query/s") if api_basic else urljoin(final_url, "../ss/query/s")
        cfg = {"name": site_name or f"Auto-{urlparse(base_url).netloc}", "domain": urlparse(base_url).netloc,
               "base_url": base_url, "search_page_url": final_url.split("?")[0], "search_api_url": search_api,
               "site_code": site_code or "unknown", "api_type": "trs_json"}
        log.info("  siteCode=%s, api.basic=%s", site_code or "?", api_basic or "?")
        return cfg
    log.warning("  Could not identify search config")
    return None

# ============================================================
#  保存
# ============================================================
def save_results(articles: list[dict], config: CrawlConfig) -> Tuple[Path, Path]:
    config.output_dir.mkdir(parents=True, exist_ok=True)
    unique = dedupe_articles(articles)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jp = config.output_dir / f"{config.site_key}_{ts}.json"
    with jp.open("w", encoding="utf-8") as f: json.dump(unique, f, ensure_ascii=False, indent=2)
    cp = config.output_dir / f"{config.site_key}_{ts}.csv"
    fields = ["title", "url", "publish_date", "source", "source_keywords", "summary", "content"]
    with cp.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader()
        for a in unique:
            r = {f: a.get(f, "") for f in fields}
            if isinstance(r["source_keywords"], list): r["source_keywords"] = ";".join(r["source_keywords"])
            w.writerow(r)
    log.info("Saved: JSON (%d) + CSV (%d)", len(unique), len(unique))
    return jp, cp

# ============================================================
#  主编排
# ============================================================
def crawl(config: CrawlConfig) -> list[dict]:
    session = make_session(config)
    all_r: list[dict] = []
    if config.use_selenium:
        if config.api_type == "jpaas_jsearch":
            return search_jpaas_selenium(config)
        return search_via_selenium(config)
    for kidx, kw in enumerate(config.keywords, 1):

        articles: list[dict] = []

        if not config.force_html:
            if config.api_type == "jpaas_jsearch":
                articles = search_by_jpaas_api(kw, session, config)
            else:
                articles = search_by_api(kw, session, config)
        if not articles: articles = search_by_html(kw, session, config)

        if not articles: log.warning("  No results for '%s'", kw); continue
        for a in articles:
            if kw not in a.setdefault("source_keywords", []): a["source_keywords"].append(kw)
        all_r.extend(articles)
        if kidx < len(config.keywords): polite_sleep(config)
    unique = dedupe_articles(all_r)
    log.info("Global dedup: %d articles", len(unique))
    if config.title_only:
        before = len(unique); unique = [a for a in unique if any(kw in a.get("title", "") for kw in config.keywords)]
        log.info("Title filter: %d -> %d", before, len(unique))
    if config.fetch_details and unique:
        log.info("-- Fetching details --")
        for idx, a in enumerate(unique, 1):
            log.info("  [%d/%d] %s", idx, len(unique), a.get("title", "")[:50])
            fetch_detail(a, session, config)
            if idx < len(unique): polite_sleep(config)
    return unique

# ============================================================
#  自检
# ============================================================
def run_self_tests(config: CrawlConfig, live: bool = False) -> None:
    log.info("-- Self tests --")
    assert clean_text("<em>低空</em>&nbsp;经济") == "低空 经济"
    assert normalize_date("日期：2025年6月7日") == "2025-06-07"
    log.info("  clean_text/normalize_date: OK")
    sample_html = '<div class="item"><a title="低空经济政策" href="/zwgk/foo.html">ignored</a><span>发布时间：2025-05-03</span><p>一条低空经济政策摘要。</p></div>'
    links = extract_links_from_html(sample_html, config.base_url, keywords=("低空",))
    assert len(links) == 1; assert links[0]["title"] == "低空经济政策"; assert links[0]["publish_date"] == "2025-05-03"
    log.info("  HTML extraction: OK")
    detail_html = '<html><head><title>测试文章</title></head><body><div class="nav">首页 导航</div><!--正文开始--><div id="mainText"><p>第一段正文内容足够长，包含低空经济描述。</p><p>第二段正文内容继续。</p></div><!--正文结束--></body></html>'
    detail_text = extract_content_from_detail(detail_html)
    assert "低空经济" in detail_text; assert "导航" not in detail_text
    log.info("  Content extraction: OK")
    if live:
        log.info("  Running live tests...")
        session = make_session(config)
        ar = search_by_api("低空经济", session, config)
        assert ar and ar[0]["url"].startswith("https://")
        detail = fetch_detail(ar[0], session, config)
        assert detail.get("publish_date")
        log.info("  Live API: %d results, first: %s", len(ar), ar[0].get("title", "")[:40])
    log.info("All self-tests passed!")

# ============================================================
#  CLI + 入口
# ============================================================
def crawl_urls(url_list: list[str], output_dir: Path, keywords: tuple = ()) -> None:
    'Fetch articles from a list of URLs and save results.'
    log.info('=== URL Fetch Mode ===')
    log.info('Total URLs: %d', len(url_list))
    articles = []
    for idx, url in enumerate(url_list, 1):
        log.info('  [' + chr(39) + '%d/%d' + chr(39) + '] %s', idx, len(url_list), url[:70])
        try:
            resp = requests.get(url, timeout=15, headers=_random_headers())
            if resp.status_code != 200:
                log.warning('  HTTP %d', resp.status_code)
                continue
            resp.encoding = resp.apparent_encoding or 'utf-8'
            title = extract_title_from_detail(resp.text) or ''
            publish_date = extract_date_from_html(resp.text) or ''
            content = extract_content_from_detail(resp.text, MAX_DETAIL_CHARS)
            articles.append({
                'title': title, 'url': url,
                'publish_date': publish_date,
                'summary': content[:300] if content else '',
                'content': content,
                'source': '',
                'source_keywords': list(keywords),
            })
        except Exception as e:
            log.warning('  Error: %s', str(e)[:60])
    if not articles:
        log.warning('No articles fetched'); return
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    jp = output_dir / f'urls_{ts}.json'
    cp = output_dir / f'urls_{ts}.csv'
    output_dir.mkdir(parents=True, exist_ok=True)
    import json, csv
    with open(jp, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    fields = ['title', 'url', 'publish_date', 'source', 'summary', 'content']
    with open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for a in articles:
            w.writerow({k: a.get(k, '') for k in fields})
    log.info('Saved: JSON (%d) + CSV (%d)', len(articles), len(articles))
    safe_print('')
    safe_print('=' * 60)
    safe_print(f'  [OK] URL mode complete! {len(articles)} articles')
    safe_print(f'      JSON: {jp}')
    safe_print(f'      CSV: {cp}')
    safe_print('=' * 60)

def main() -> None:
    p = argparse.ArgumentParser(description="融合版爬虫 - 低空经济/低空政策/低空监管")
    p.add_argument("--site", default=DEFAULT_SITE, help=f"Site config key (default: {DEFAULT_SITE})")
    p.add_argument("--keywords", nargs="+", default=None, help="Keywords (space separated)")
    p.add_argument("--output", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    p.add_argument("--selenium", action="store_true", help="Use Selenium browser")
    p.add_argument("--with-detail", action="store_true", help="Fetch article details")
    p.add_argument("--title-only", action="store_true", help="Keep only title-matching results")
    p.add_argument("--max-pages", type=int, default=0, help="Max pages per keyword (0=all)")
    p.add_argument("--force-html", action="store_true", help="Skip API, force HTML parsing")
    p.add_argument("--no-dedup", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--discover", metavar="URL", help="Auto-discover site config")
    p.add_argument("--urls", metavar="FILE", help="Fetch articles from URL list file")
    p.add_argument("--self-test", action="store_true", help="Run self-tests")
    p.add_argument("--live-test", action="store_true", help="Include live API in self-tests")
    p.add_argument("--debug", action="store_true", help="Debug logging")
    args = p.parse_args()

    if args.debug: log.setLevel(logging.DEBUG)
    if args.discover:
        cfg = discover_site(args.discover)
        if cfg:
            print(); safe_print("-- Generated config (copy to SITE_CONFIGS) --"); print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return
    if args.self_test:
        cfg = CrawlConfig.from_site(args.site)
        run_self_tests(cfg, live=args.live_test)
        return

    keywords = tuple(args.keywords) if args.keywords else DEFAULT_KEYWORDS
    config = CrawlConfig.from_site(args.site, output_dir=Path(args.output), keywords=keywords,
                                   fetch_details=args.with_detail, title_only=args.title_only,
                                   max_pages=args.max_pages, force_html=args.force_html,
                                   use_selenium=args.selenium)
    log.info("=" * 60)
    log.info("  Site: %s (%s)", config.name or config.site_key, config.domain)
    log.info("  Keywords: %s", ", ".join(config.keywords))
    log.info("=" * 60)

    articles = crawl(config)
    if not articles: log.warning("No results found"); return
    jp, cp = save_results(articles, config)
    safe_print(""); safe_print("=" * 60)
    safe_print(f"  [OK] 采集完成! {len(articles)} 篇")
    safe_print(f"      JSON: {jp}")
    safe_print(f"      CSV:  {cp}")
    safe_print("=" * 60)

# ============================================================
#  JPAAS 动态站点 -- Selenium 浏览器搜索
# ============================================================
def search_jpaas_selenium(config: CrawlConfig) -> list[dict]:
    if not HAS_SELENIUM:
        log.error('Selenium not installed'); return []
    all_r: list[dict] = []; seen: set = set()
    for kw in config.keywords:
        log.info('  [JPAAS Selenium] %s', kw)
        log.info('  Loading homepage and waiting for JS rendering...')
        driver = None
        try:
            opts = Options()
            opts.add_argument('--headless=new')
            opts.add_argument('--disable-blink-features=AutomationControlled')
            opts.add_experimental_option('excludeSwitches', ['enable-automation'])
            opts.add_experimental_option('useAutomationExtension', False)
            opts.add_argument('--disable-gpu'); opts.add_argument('--window-size=1920,1080')
            opts.add_argument('--no-sandbox'); opts.add_argument('--disable-dev-shm-usage')
            if config.proxy_url:
                opts.add_argument('--proxy-server=' + config.proxy_url)
            opts.add_argument(f'--user-agent={_random_ua()}')
            driver = webdriver.Edge(options=opts)
            driver.get(config.search_page_url)
            time.sleep(10)
            # Phase 2a: FIRST, extract ALL article links from the rendered homepage
            def _extract_art_links(d, kw):
                found = []
                for lk in d.find_elements(By.TAG_NAME, 'a'):
                    try:
                        href = lk.get_attribute('href') or ''
                        if 'art_' not in href: continue
                        if href.startswith(('javascript:', '#')): continue
                        title = lk.get_attribute('textContent') or lk.get_attribute('title') or lk.text.strip()
                        if not title and not href: continue
                        url = href if href.startswith('http') else urljoin(config.base_url, href)
                        if url in seen: continue
                        seen.add(url)
                        found.append({
                            'title': clean_text(title), 'url': url,
                            'summary': '', 'content': '',
                            'publish_date': '', 'source': config.name,
                            'source_keywords': [kw],
                        })
                    except: continue
                return found
            all_r.extend(_extract_art_links(driver, kw))
            log.info('  Homepage articles: %d', len(all_r))
            # Phase 2b: Submit search, wait, extract more
            try:
                q_input = driver.find_element(By.NAME, 'q')
                if q_input and q_input.is_enabled():
                    q_input.clear(); q_input.send_keys(kw)
                    try:
                        btn = driver.find_element(By.CSS_SELECTOR,
                            'input[type=image], button[type=submit], .search_btn')
                        btn.click(); time.sleep(3)
                    except Exception:
                        q_input.submit(); time.sleep(3)
            except Exception:
                pass
            # Extract additional article links after search
            all_r.extend(_extract_art_links(driver, kw))
            log.info('  After search total: %d', len(all_r))
            # Phase 2: Explore column/section links to find more articles
            nav_links = driver.find_elements(By.CSS_SELECTOR,
                'a[href*=\"/col/\"]')
            nav_visited = set()
            # Extract col IDs from article URLs
            import re as _cr
            for _a in all_r:
                _u = _a.get('url', '')
                _m = _cr.search(r'/col/(col\d+)|art_(\d+)_\d+\.html', _u)
                if _m:
                    _col_id = _m.group(1) or ('col' + _m.group(2))
                    _cu = config.base_url + '/col/' + _col_id + '/index.html'
                    if _cu not in nav_visited:
                        nav_visited.add(_cu)
                        log.info('  Auto-col: %s', _col_id)

            # Auto-explore discovered columns
            _nav_urls = set()
            for _nv in nav_links:
                try: _nav_urls.add(_nv.get_attribute('href') or '')
                except: pass
            for _vu in list(nav_visited):
                if _vu not in _nav_urls and '/col/' in _vu:
                    try:
                        log.info('  Explore col: %s', _vu.split('/')[-2])
                        driver.get(_vu); time.sleep(4)
                        all_r.extend(_extract_art_links(driver, kw))
                        driver.back(); time.sleep(2)
                    except:
                        pass
            for nv in nav_links:
                try:
                    nv_href = nv.get_attribute('href') or ''
                    if not nv_href or nv_href in nav_visited: continue
                    if nv_href.startswith(('javascript:', '#', 'mailto:')): continue
                    nav_visited.add(nv_href)
                    nv_text = nv.text.strip()
                    if not nv_text or len(nv_text) < 2: continue
                    log.info('  Exploring column: %s', nv_text[:20])
                    original_url = driver.current_url
                    try: nv.click(); time.sleep(5)
                    except Exception: driver.get(nv_href); time.sleep(5)
                    for lk2 in driver.find_elements(By.TAG_NAME, 'a'):
                        try:
                            h2 = lk2.get_attribute('href') or ''
                            t2 = lk2.get_attribute('title') or lk2.text.strip()
                            if not t2 or not h2 or 'art_' not in h2: continue
                            if h2.startswith(('javascript:', '#')): continue
                            u2 = h2 if h2.startswith('http') else urljoin(config.base_url, h2)
                            if u2 in seen: continue
                            seen.add(u2)
                            all_r.append({
                                'title': clean_text(t2), 'url': u2,
                                'summary': '', 'content': '',
                                'publish_date': '', 'source': config.name,
                                'source_keywords': [kw],
                            })
                        except: continue
                    driver.back(); time.sleep(3)
                except: continue
            # Fetch full titles from article HTML
            for a in all_r:
                try:
                    u = a.get('url', '')
                    if not u: continue
                    resp = requests.get(u, timeout=8, headers={'User-Agent': USER_AGENTS[0]})

                    if resp.status_code == 200:


                        resp.encoding = resp.apparent_encoding or 'utf-8'

                        m = __import__('re').search('<title[^>]*>(.*?)</title>', resp.text, __import__('re').I|__import__('re').S)

                        if m:


                            full = clean_text(m.group(1))

                            if len(full) > len(a.get('title', '')):
                                a['title'] = full
                except:
                    pass
            log.info('  Fetched titles from %d article pages', len(all_r))
            # Filter by keyword
            before = len(all_r)
            all_r = [a for a in all_r if any(kw in a.get('title', '') or kw in a.get('url', '') for kw in config.keywords)]
            log.info('  Keyword filter: %d -> %d', before, len(all_r))
        except Exception as e:
            log.error('  JPAAS Selenium error: %s', str(e)[:100])
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass
    return dedupe_articles(all_r)
if __name__ == "__main__":
    if os.name == "nt":
        try: os.system("chcp 65001 > nul 2>nul")
        except Exception: pass
    main()
 
 # ============================================================
 #  JPAAS（浙江统一搜索平台）API
 # ============================================================
def search_by_jpaas_api(keyword: str, session: requests.Session, config: CrawlConfig) -> list[dict]:
    if not config.search_api_url: return []

    log.info("  [JPAAS API] %s", keyword)

    articles: list[dict] = []; page = 1; total_hits: Optional[int] = None

    params = {

        "q": keyword,

        "serviceId": config.jpaas_service_id or config.site_code,

        "websiteid": config.site_code,

        "cateid": "6N89tbnrVTYIQK5jt7q3T",

        "p": str(page), "pg": str(config.page_size), "sortType": "1",

    }

    if config.jpaas_web_id:

        params["_cus_eq_webid"] = config.jpaas_web_id

    while True:

        try:

            headers = {"User-Agent": _random_ua(), "Accept": "application/json",

                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": config.search_page_url or (config.base_url + "/")}
            resp = session.get(config.search_api_url, params=params, timeout=config.timeout, headers=headers)

            if resp.status_code != 200: break

            result = resp.json()

            if not result.get("success"):

                log.warning("  JPAAS error: %s", str(result.get("message", ""))[:60]); break

            data = result.get("data", {})

            total_hits = data.get("totalHits") or total_hits

            docs = data.get("appSearchResultBeanList", [])

            if not docs:

                log.info("  JPAAS returned 0 results -- site may not be indexed in this platform")

                break

            for doc in docs:

                url = doc.get("url") or ""

                title = clean_text(doc.get("title") or "")

                if not title or not url: continue

                articles.append({

                    "title": title, "url": url,

                    "publish_date": normalize_date(doc.get("date") or doc.get("docDate") or ""),

                    "summary": clean_text(doc.get("content") or doc.get("summary") or ""),

                    "content": "", "source": clean_text(doc.get("siteName") or ""),

                    "source_keywords": [keyword] if keyword else [],

                })

            log.info("  Page %d: %d hits", page, len(docs))

            if len(docs) < config.page_size: break

            if total_hits and len(articles) >= int(total_hits): break

            if config.max_pages > 0 and page >= config.max_pages: break

            page += 1; params["p"] = str(page); polite_sleep(config)

        except Exception as e:

            log.warning("  JPAAS request failed: %s", str(e)[:80]); break

    return dedupe_articles(articles)

 
 # ============================================================

 #  使用方法 (Usage)
 # ============================================================
#  # 默认：API 直搜 4 个关键词（低空经济/低空政策/低空监管/低空）
#  python 26-6-19crawler.py
#
#  # 仅保留标题含关键词的精准结果
#  python 26-6-19crawler.py --title-only
#
#  # 补全文章正文（默认不抓详情以提速）
#  python 26-6-19crawler.py --with-detail
#
#  # 自动发现其他政府网站的搜索配置
#  python 26-6-19crawler.py --discover https://example.gov.cn
#
#  # 运行自检
#  python 26-6-19crawler.py --self-test
#  python 26-6-19crawler.py --self-test --live-test  # 包含真实网络请求
#
#  # 浏览器模式（API 不可用时回退）
#  python 26-6-19crawler.py --selenium
#
#  # 指定站点（需先在 SITE_CONFIGS 中定义）
#  python 26-6-19crawler.py --site bj_gov
#
#  # 自定义关键词
#  python 26-6-19crawler.py --keywords 低空经济 低空政策
#
#  # 限制翻页数量（默认 0=全量）
#  python 26-6-19crawler.py --max-pages 2
#
#  # 输出到自定义目录
#  python 26-6-19crawler.py --output my_results
#
#  # 调试日志
#  python 26-6-19crawler.py --debug
