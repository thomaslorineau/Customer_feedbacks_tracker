import sys
from pathlib import Path

# Ensure backend/app is importable when running from workspace root
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from app import db


def run_test():
    print('Initializing DB...')
    db.init_db()
    print('Inserting sample post...')
    sample = {
        'source': 'test',
        'author': 'tester',
        'content': 'This is a test complaint about OVH domain issues',
        'url': 'https://example.com/test',
        'created_at': '2026-01-13T00:00:00',
        'sentiment_score': 0.0,
        'sentiment_label': 'neutral',
    }
    db.insert_post(sample)
    rows = db.get_posts(5)
    print('Rows:', rows)


if __name__ == '__main__':
    run_test()
