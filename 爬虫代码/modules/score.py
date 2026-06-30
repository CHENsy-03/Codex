import re
import logging

log = logging.getLogger('crawler.score')

DEFAULT_WEIGHTS = {'title': 5, 'body': 2, 'url': 1}
DEFAULT_THRESHOLD = 6

def score_article(article, keywords, weights=None, threshold=None):
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if threshold is None:
        threshold = DEFAULT_THRESHOLD

    title = article.get('title', '') or ''
    body = article.get('content', '') or article.get('summary', '') or ''
    url = article.get('url', '') or ''

    total_score = 0
    matched_kws = set()

    for kw in keywords:
        kw_score = 0
        if kw in title:
            kw_score += weights.get('title', 5)
        if kw in body:
            kw_score += weights.get('body', 2)
        if kw in url:
            kw_score += weights.get('url', 1)
        if kw_score > 0:
            matched_kws.add(kw)
            total_score += kw_score

    return {
        'score': total_score,
        'matched': len(matched_kws) > 0,
        'matched_keywords': list(matched_kws),
    }


def filter_by_score(articles, keywords, weights=None, threshold=None):
    if weights is None:
        weights = DEFAULT_WEIGHTS
    if threshold is None:
        threshold = DEFAULT_THRESHOLD

    results = []
    for a in articles:
        result = score_article(a, keywords, weights, threshold)
        if result['matched']:
            a['score'] = result['score']
            a['matched_keywords'] = result['matched_keywords']
            results.append(a)

    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results
