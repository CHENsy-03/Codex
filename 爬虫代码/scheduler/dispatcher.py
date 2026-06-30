import logging
from fetcher.http_client import fetch, post_json, get_json
from parser.html_parser import extract_title, extract_date, extract_content
from parser.api_parser import parse_trs_doc
from extractor.scorer import filter_by_score
from dedup.sqlite_cache import DedupDB
from storage.json_store import save_results

log = logging.getLogger('crawler.dispatcher')


def search_trs(site_cfg, keyword, max_pages=0):
    search = site_cfg.get('search', {})
    api_url = search.get('api_url')
    if not api_url:
        return []
    params = search.get('params', {}).copy()
    params['qt'] = keyword
    params['pageSize'] = params.get('pageSize', 20)
    articles = []
    page = 1
    while True:
        params['page'] = page
        result = post_json(api_url, params, site_cfg)
        if not result:
            break
        docs = result.get('resultDocs', [])
        for doc in docs:
            a = parse_trs_doc(doc, keyword)
            if a:
                articles.append(a)
        log.info('  Page %d: %d hits', page, len(docs))
        if len(docs) < params['pageSize'] or (max_pages > 0 and page >= max_pages):
            break
        page += 1
    return articles


def crawl_url(url, site_cfg, keywords=()):
    resp = fetch(url, site_cfg)
    if not resp:
        return None
    return {
        'title': extract_title(resp.text),
        'url': url,
        'publish_date': extract_date(resp.text),
        'summary': '',
        'content': extract_content(resp.text),
        'source': site_cfg.get('name', '') if site_cfg else '',
        'source_keywords': list(keywords),
    }




def search_jpaas(site_cfg, keyword, max_pages=0):
    # JPAAS search (GET with custom headers, used by Zhejiang sites)
    search = site_cfg.get('search', {})
    api_url = search.get('api_url')
    if not api_url:
        return []
    params = search.get('params', {}).copy()
    params['q'] = keyword
    params['p'] = '1'
    params['pg'] = '10'
    params['sortType'] = '1'
    # webId -> _cus_eq_webid
    if 'webId' in params:
        params['_cus_eq_webid'] = params.pop('webId')

    articles = []
    page = 1
    while True:
        params['p'] = str(page)
        result = get_json(api_url, params, site_cfg)
        if not result:
            break
        if not result.get('success'):
            log.warning('  JPAAS error: %s', str(result.get('message', ''))[:60])
            break
        data = result.get('data', {})
        docs = data.get('appSearchResultBeanList', [])
        if not docs:
            log.info('  JPAAS returned 0 results (site may not be indexed)')
            break
        for doc in docs:
            url = doc.get('url', '') or ''
            title = doc.get('title', '') or ''
            if not title or not url:
                continue
            from parser.multi_strategy import clean_text, normalize_date
            articles.append({'title': clean_text(title),
                          'url': url,
                          'publish_date': normalize_date(doc.get('date', '')),
                          'summary': clean_text(doc.get('content', '') or ''),
                          'content': '',
                          'source': site_cfg.get('name', ''),
                          'source_keywords': [keyword]})
        log.info('  Page %d: %d hits', page, len(docs))
        if len(docs) < int(params.get('pg', 10)):
            break
        if max_pages > 0 and page >= max_pages:
            break
        page += 1
    return articles

def run_search(site_cfg, keywords, output_dir, max_pages=0, with_detail=False):
    """完整搜索流程"""
    from extractor.scorer import filter_by_score
    from storage.json_store import save_results
    from dedup.sqlite_cache import DedupDB
    import os

    all_articles = []
    for kw in keywords:
        log.info('  [%s] %s', site_cfg.get('search', {}).get('type', '').upper(), kw)
        stype = site_cfg.get('search', {}).get('type', '')
        if stype in ('jpaas_jsearch',):
            articles = search_jpaas(site_cfg, kw, max_pages)
        else:
            articles = search_trs(site_cfg, kw, max_pages)
        all_articles.extend(articles)

    if not all_articles:
        log.warning('No results found')
        return

    scored = filter_by_score(all_articles, keywords)
    with DedupDB() as dedup:
        scored = dedup.dedup_list(scored)

    if with_detail:
        for a in scored:
            url = a.get('url', '')
            if url and not a.get('content'):
                resp = fetch(url, site_cfg)
                if resp:
                    a['content'] = extract_content(resp.text)
                    a['summary'] = a['content'][:300]

    jp, cp = save_results(scored, output_dir, site_cfg.get('name', 'result'))
    log.info('Saved: JSON (%d) + CSV (%d)', len(scored), len(scored))
    return scored
