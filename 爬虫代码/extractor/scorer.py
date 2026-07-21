WEIGHTS = {'title': 5, 'body': 2, 'url': 1}
THRESHOLD = 0


def score_article(article, keywords, weights=None, threshold=None):
    if weights is None:
        weights = WEIGHTS
    if threshold is None:
        threshold = THRESHOLD
    title = article.get('title', '') or ''
    body = article.get('content', '') or article.get('summary', '') or ''
    url = article.get('url', '') or ''
    total_score = 0
    matched_kws = []
    for kw in keywords:
        kw_score = 0
        if kw in title:
            kw_score += weights['title']
        if kw in body:
            kw_score += weights['body']
        if kw in url:
            kw_score += weights['url']
        if kw_score > 0:
            matched_kws.append(kw)
            total_score += kw_score
    return {'score': total_score, 'passed': total_score >= threshold, 'matched_keywords': matched_kws}


def filter_by_score(articles, keywords, weights=None, threshold=None):
    results = []
    for a in articles:
        r = score_article(a, keywords, weights, threshold)
        if r['passed']:
            a['score'] = r['score']
            a['matched_keywords'] = r['matched_keywords']
            results.append(a)
    results.sort(key=lambda x: x.get('score', 0), reverse=True)
    return results
