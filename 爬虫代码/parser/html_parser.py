import re
from lxml.html import fromstring
from parser.multi_strategy import clean_text, normalize_date

# CSS classes for content extraction
_CS = [
    ".TRS_Editor",
    ".article-content",
    ".content",
    "#mainText",
    "#UCAP-CONTENT",
    ".detail-content",
    ".main-content",
]

_XPS = [
    "//div[@class=TRS_Editor]",
    "//div[@class=article-content]",
    "//div[@id=mainText]",
    "//div[contains(@class,content)]",
    "//article",
]

def _cs(s):
    import re as _r
    s=s.strip()
    if _r.match("^[a-zA-Z][a-zA-Z0-9]*$",s):return "//"+s
    if s.startswith("."):return '//*[contains(concat(" ",normalize-space(@class)," ")," "+s[1:]+" ")]'
    if s.startswith("#"):return '//*[@id=""+s[1:]+""]'
    return "//"+s

def extract_title(html):
    m=re.search("<title[^>]*>(.*?)</title>",html,re.I|re.S)
    return clean_text(m.group(1)) if m else ""

def extract_date(html):
    return normalize_date(html)

def extract_content(html,mc=3000):
    # Layer 1: CSS via lxml
    try:
        doc=fromstring(html)
        for s in _CS:
            for el in doc.xpath(_cs(s)):
                t=clean_text(el.text_content())
                if len(t)>=80:return t[:mc]
    except:pass
    # Layer 2: XPath direct
    try:
        doc=fromstring(html)
        for xp in _XPS:
            for el in doc.xpath(xp):
                t=clean_text(el.text_content())
                if len(t)>=80:return t[:mc]
    except:pass
    # Layer 3: Regex fallback
    texts=[]
    for p in re.finditer("<p[^>]*>(.*?)</p>",html,re.I|re.S):
        t=clean_text(p.group(1))
        if len(t)>=30:texts.append(t)
    if texts:return " ".join(texts)[:mc]
    return clean_text(html)[:mc]

def extract_links(html,base_url):
    from urllib.parse import urljoin
    links=[]
    for m in re.finditer("<a\\b[^>]*href\\s*=\\s*""([^""]+)""[^>]*>",html,re.I):
        url=m.group(1)
        if url and not url.startswith(("javascript:","mailto:","tel:","#")):
            links.append({"url":urljoin(base_url,url)})
    return links