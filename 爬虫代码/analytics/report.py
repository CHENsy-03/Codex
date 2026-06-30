# Report generation module
def generate_report(articles, output_path='report.txt'):
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('Total articles: ' + str(len(articles)) + chr(10))
        f.write('=' * 40 + chr(10))
        for a in articles:
            f.write('  [' + str(a.get('score', 0)) + '] ' + a.get('title', '')[:50] + chr(10))
    return output_path
