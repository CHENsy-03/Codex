import re
import logging
from html import unescape
from urllib.parse import urljoin

log = logging.getLogger('crawler.parse')

TAG_RE = re.compile(r'(?is)<(script|style|noscript).*?</\1>|<[^>]+>')
SPACE_RE = re.compile(r'\s+')

def clean_text(value):
    if value is None:
        return ''
    text = TAG_RE.sub(' ', str(value))
    text = unescape(text)
    text = text.replace('\xa0', ' ').replace('\u3000', ' ')
    return SPACE_RE.sub(' ', text).strip()

# ===== CSS / XPath / Regex selectors for content extraction =====
CONTENT_SELECTORS = {
    'trs': {
        'title': ['h1', 'title'],
        'date': ['[name=PubDate]', '[name=publishdate]', '[name=date]'],
        'content': [
            '.TRS_Editor', '#mainText', '#UCAP-CONTENT',
            '.article-content', '.content', '.detail-content',
            '#article-content', '.main-content',
        ],
        'content_markers': [
            '<!-- 正文开始 -->', '<!--正文开始-->',
            '<!-- 正文内容 begin -->',
        ],
    },
    'sichuan': {
        'title': ['h1', '.xxgk-font', '.article-title', 'title'],
        'date': ['.xxgk-time', '.article-time', '.date', '[name=PubDate]'],
        'content': [
            '.article-content', '.content-body', '.con_text',
            '#content', '.main-content', '.TRS_Editor',
        ],
    },
    'shandong': {
        'title': ['h1', '.article-title', 'title'],
        'date': ['.article-date', '.date', '[name=PubDate]'],
        'content': [
            '.article-content', '.content', '#UCAP-CONTENT',
            '.TRS_Editor', '#mainText',
        ],
    },
}

# ===== Date patterns =====
DATE_PATTERNS = (
    re.compile(r'(?:发布日期|发布时间|日期)[：:]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}日?)'),
    re.compile(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?'),
    re.compile(r'(\d{4}年\d{1,2}月\d{1,2}日)'),
)

def normalize_date(value):
    text = clean_text(value)
    if not text:
        return ''
    for p in DATE_PATTERNS:
        m = p.search(text)
        if not m:
            continue
        parts = re.findall(r'\d+', m.group(1))
        if len(parts) >= 3:
            return f'{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}'
    return ''

def extract_title(html, mode='trs'):
    m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.S)
    if m:
        t = clean_text(m.group(1))
        if t:
            return t
    selectors = CONTENT_SELECTORS.get(mode, CONTENT_SELECTORS['trs'])
    for sel in selectors.get('title', []):
        pat = re.compile(rf'<{sel}[^>]*>(.*?)</{sel}>', re.I | re.S)
        m = pat.search(html)
        if m:
            t = clean_text(m.group(1))
            if t and len(t) > 5:
                return t
    return ''

def extract_date(html, mode='trs'):
    selectors = CONTENT_SELECTORS.get(mode, CONTENT_SELECTORS['trs'])
    for sel in selectors.get('date', []):
        val = ''
        m = re.search(rf'{sel}\s*content\s*=\s*["\']([^"\']+)["\']', html, re.I)
        if m:
            val = m.group(1)
        if not val:
            m = re.search(rf'<[^>]*{sel}[^>]*>\s*(.*?)\s*</', html, re.I | re.S)
            if m:
                val = m.group(1)
        if val:
            d = normalize_date(val)
            if d:
                return d
    d = normalize_date(html)
    if d:
        return d
    return ''

def extract_content(html, mode='trs', max_chars=3000):
    selectors = CONTENT_SELECTORS.get(mode, CONTENT_SELECTORS['trs'])

    # Method 1: Content markers (HTML comments)
    markers = selectors.get('content_markers', [])
    for mkr in markers:
        pat = re.compile(re.escape(mkr) + r'(.*?)' + re.escape(mkr.replace('开始', '结束')), re.I | re.S)
        m = pat.search(html)
        if m:
            text = clean_text(m.group(1))
            if len(text) >= 40:
                return text[:max_chars]

    # Method 2: CSS selectors (simulated via regex)
    for sel in selectors.get('content', []):
        # Try class-based
        cls_name = sel.lstrip('.')
        pat = re.compile(
            rf'<div[^>]*class\s*=\s*["\'][^"\']*{re.escape(cls_name)}[^"\']*["\'][^>]*>'
            rf'(.*?)</div>',
            re.I | re.S
        )
        m = pat.search(html)
        if m:
            text = clean_text(m.group(1))
            if len(text) >= 80:
                return text[:max_chars]
        # Try id-based
        if sel.startswith('#'):
            id_name = sel.lstrip('#')
            pat = re.compile(
                rf'<div[^>]*id\s*=\s*["\']{re.escape(id_name)}["\'][^>]*>'
                rf'(.*?)</div>',
                re.I | re.S
            )
            m = pat.search(html)
            if m:
                text = clean_text(m.group(1))
                if len(text) >= 80:
                    return text[:max_chars]

    # Method 3: Generic regex fallback - find large text blocks
    texts = []
    for p in re.finditer(r'<p[^>]*>(.*?)</p>', html, re.I | re.S):
        t = clean_text(p.group(1))
        if len(t) >= 30:
            texts.append(t)
    if texts:
        combined = ' '.join(texts)
        return combined[:max_chars]

    # Method 4: Strip all tags, return what's left
    text = clean_text(html)
    return text[:max_chars]

def extract_links(html, base_url, art_pattern=True):
    links = []
    for m in re.finditer(r'<a\b[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        url = m.group(1)
        title = clean_text(m.group(2))
        if not url or url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            continue
        if art_pattern and '/art_' not in url and 'art_' not in url:
            continue
        full_url = urljoin(base_url, url)
        links.append({'title': title, 'url': full_url})
    return links

def extract_title_from_detail(html):
    return extract_title(html)

def extract_date_from_html(html):
    return extract_date(html)

def extract_content_from_detail(html, max_chars=3000):
    return extract_content(html, max_chars=max_chars)
