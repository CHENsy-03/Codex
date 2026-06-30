#!/usr/bin/env python3
# run.py - 政府网站政策爬虫 入口程序
import sys, os, logging, argparse

os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
os.environ.setdefault('PYTHONUTF8', '1')
for s in (sys.stdout, sys.stderr):
    try: s.reconfigure(encoding='utf-8', errors='replace')
    except: pass

if os.name == 'nt':
    try: os.system('chcp 65001 > nul 2>nul')
    except: pass

sys.path.insert(0, os.path.dirname(__file__))

from modules.crawler import load_config, search_trs, crawl_url, save_results, read_url_list
from modules.fetch import make_session, request_with_retries, polite_sleep
from modules.parse import extract_content, clean_text, extract_date
from modules.score import filter_by_score, DEFAULT_WEIGHTS, DEFAULT_THRESHOLD
from modules.dedup import DedupDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger('run')


def parse_args():
    p = argparse.ArgumentParser(description='政府网站政策爬虫')
    p.add_argument('--site', default='', help='站点配置名')
    p.add_argument('--keywords', nargs='+', default=None, help='搜索关键词（空格分隔）')
    p.add_argument('--urls', metavar='FILE', help='从文件读取URL列表')
    p.add_argument('--output', default='output', help='输出目录')
    p.add_argument('--with-detail', action='store_true', help='抓取文章正文')
    p.add_argument('--selenium', action='store_true', help='Selenium浏览器模式')
    p.add_argument('--max-pages', type=int, default=0, help='最大翻页数')
    p.add_argument('--self-test', action='store_true', help='运行自检')
    p.add_argument('--no-dedup', action='store_true', help='禁用SQLite去重')
    return p.parse_args()


def run_self_test():
    log.info('-- Self tests --')
    assert clean_text('<em>低空</em>&nbsp;经济') == '低空 经济'
    assert extract_date('日期：2025年6月7日') == '2025-06-07'
    log.info('  clean_text/extract_date: OK')
    html = '<div class="TRS_Editor"><p>低空经济政策正文内容。</p></div>'
    content = extract_content(html, 'trs')
    assert '低空经济' in content
    log.info('  Content extraction: OK')
    log.info('All self-tests passed!')
    return True


def main():
    args = parse_args()

    if args.self_test:
        run_self_test()
        return

    keywords = tuple(args.keywords) if args.keywords else ()
    if not keywords and not args.urls:
        log.warning('请指定 --keywords 或 --urls')
        return

    output_dir = os.path.join(os.path.dirname(__file__), args.output)
    site_cfg = load_config(args.site) if args.site else None

    dedup_db = DedupDB() if not args.no_dedup else None

    # Mode 1: URL list
    if args.urls:
        urls = read_url_list(args.urls)
        if not urls:
            log.warning('No URLs found in: %s', args.urls)
            return
        log.info('=== URL Fetch Mode ===')
        log.info('Total URLs: %d', len(urls))
        articles = []
        for idx, url in enumerate(urls, 1):
            log.info('  [%d/%d] %s', idx, len(urls), url[:70])
            article = crawl_url(url, site_cfg or load_config('czj_beijing'), keywords)
            if article:
                articles.append(article)
        if not articles:
            log.warning('No articles fetched'); return
        scored = filter_by_score(articles, keywords) if keywords else articles
        if dedup_db:
            scored = dedup_db.dedup_list(scored)
        jp, cp = save_results(scored, output_dir, 'urls')
        print(f'  [OK] {len(scored)} articles saved')
        print(f'      JSON: {jp}')
        print(f'      CSV:  {cp}')
        return

    # Mode 2: Site search
    if not site_cfg:
        log.warning('请指定 --site 站点名')
        return

    search_type = site_cfg.get('search', {}).get('type', '')
    log.info('=' * 60)
    log.info('  Site: %s (%s)', site_cfg.get('name', args.site), site_cfg.get('domain', ''))
    log.info('  Keywords: %s', ', '.join(keywords))
    log.info('=' * 60)

    all_articles = []
    for kw in keywords:
        log.info('  [%s] %s', search_type.upper(), kw)
        if search_type in ('trs_json', 'trs'):
            articles = search_trs(site_cfg, kw, max_pages=args.max_pages)
        elif search_type in ('jpaas_jsearch', 'html'):
            log.info('  (Selenium or HTML mode not available in lightweight run)')
            articles = []
        else:
            log.info('  Unknown search type: %s', search_type)
            articles = []
        all_articles.extend(articles)
        polite_sleep(site_cfg.get('rate_limit'))  # type: ignore

    if not all_articles:
        log.warning('No results found')
        return

    log.info('Global dedup: %d articles', len(all_articles))
    scored = filter_by_score(all_articles, keywords)
    if dedup_db:
        scored = dedup_db.dedup_list(scored)

    if args.with_detail:
        session = make_session(site_cfg)
        for idx, a in enumerate(scored, 1):
            url = a.get('url', '')
            if not url or a.get('content'):
                continue
            log.info('  [%d/%d] Fetching detail: %s', idx, len(scored), a.get('title', '')[:40])
            resp = request_with_retries(session, 'GET', url, timeout=15)
            if resp:
                a['content'] = extract_content(resp.text, site_cfg.get('extract', {}).get('mode', 'trs'))
                a['summary'] = a['content'][:300] if a['content'] else ''

    jp, cp = save_results(scored, output_dir, args.site or 'result')
    print('')
    print('=' * 60)
    print(f'  [OK] 采集完成! {len(scored)} 篇')
    print(f'      JSON: {jp}')
    print(f'      CSV:  {cp}')
    print('=' * 60)


if __name__ == '__main__':
    main()
