import sys
from pathlib import Path

# ensure backend is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from app.scraper import x_scraper
from app.analysis import sentiment
from app import db


def run(query='ovh domain', limit=5):
    db.init_db()
    items = x_scraper.scrape_x(query, limit=limit)
    print(f'Fetched {len(items)} items from X')
    for it in items:
        an = sentiment.analyze(it.get('content') or '')
        it['sentiment_score'] = an['score']
        it['sentiment_label'] = an['label']
        db.insert_post({
            'source': it.get('source'),
            'author': it.get('author'),
            'content': it.get('content'),
            'url': it.get('url'),
            'created_at': it.get('created_at'),
            'sentiment_score': it.get('sentiment_score'),
            'sentiment_label': it.get('sentiment_label'),
        })
    rows = db.get_posts(limit)
    print('Inserted rows sample:')
    for r in rows:
        print(r)


if __name__ == '__main__':
    run()
