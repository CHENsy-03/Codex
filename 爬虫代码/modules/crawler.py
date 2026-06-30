import json, csv, os, logging
from datetime import datetime
from pathlib import Path

from modules.fetch import make_session, request_with_retries, safe_post_json, safe_post_form, polite_sleep
from modules.parse import extract_title, extract_date, extract_content, clean_text, extract_links, normalize_date
from modules.score import filter_by_score
from modules.dedup import DedupDB

log = logging.getLogger('crawler')

def load_config(site_key=None, config_path=None):
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'sites_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        cfg = json.load(f)
    if site_key:
        site = cfg['sites'].get(site_key)
        if not site:
            raise ValueError(f'Site not found: {site_key}')
        return site
    return cfg


def search_trs(site_cfg, keyword, max_pages=0):
    search = site_cfg['search']
    api_url = search.get('api_url')
    if not api_url:
        return []
    params = search.get('params', {}).copy()
    params['qt'] = keyword
    params['pageSize'] = params.get('pageSize', 20)
    session = make_session(site_cfg)
    articles = []
    page = 1
    while True:
        params['page'] = page
        result = safe_post_form(api_url, params)
        if not result:
            break
        docs = result.get('resultDocs', [])
        for doc in docs:
            data = doc.get('data') if isinstance(doc.get('data'), dict) else doc
            title = clean_text(data.get('titleO') or data.get('title') or '')
            url = clean_text(data.get('url') or data.get('URL') or '')
            if not title or not url:
                continue
            articles.append({
                'title': title, 'url': url,
                'publish_date': normalize_date(data.get('docDate') or data.get('publishTime') or ''),
                'summary': clean_text(data.get('summary', '')),
                'content': '', 'source': site_cfg.get('name', ''),
                'source_keywords': [keyword],
            })
        log.info('  Page %d: %d hits', page, len(docs))
        if len(docs) < params['pageSize'] or (max_pages > 0 and page >= max_pages):
            break
        page += 1
        polite_sleep(site_cfg.get('rate_limit'))
    return articles


def crawl_url(url, site_cfg, keywords=()):
    session = make_session(site_cfg)
    resp = request_with_retries(session, 'GET', url, timeout=15)
    if not resp:
        return None
    html = resp.text
    mode = site_cfg.get('extract', {}).get('mode', 'trs')
    return {
        'title': extract_title(html, mode),
        'url': url,
        'publish_date': extract_date(html, mode),
        'summary': '',
        'content': extract_content(html, mode),
        'source': site_cfg.get('name', ''),
        'source_keywords': list(keywords),
    }


def read_url_list(path):
    if not os.path.exists(path):
        log.error('File not found: %s', path)
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]


def save_results(articles, output_dir, prefix='result'):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    jp = output_dir / f'{prefix}_{ts}.json'
    cp = output_dir / f'{prefix}_{ts}.csv'
    with open(jp, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)
    fields = ['title', 'url', 'publish_date', 'source', 'score', 'matched_keywords', 'summary', 'content']
    with open(cp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        for a in articles:
            w.writerow({k: a.get(k, '') for k in fields})
    log.info('Saved: JSON (%d) + CSV (%d)', len(articles), len(articles))
    return jp, cp
