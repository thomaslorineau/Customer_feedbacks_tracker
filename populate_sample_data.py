#!/usr/bin/env python3
"""Generate sample posts for testing"""

import sys
sys.path.insert(0, 'backend')

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import db
from app.analysis import sentiment
from datetime import datetime, timedelta
import random

# Initialize database
db.init_db()

# Sample complaints about OVH
sample_posts = [
    {
        'source': 'x',
        'author': '@JohnDoe',
        'content': 'OVH domain transfer is a nightmare! Been trying for 2 weeks with no support response. #frustration',
        'url': 'https://twitter.com/johndoe/status/123',
        'created_at': (datetime.now() - timedelta(days=7)).isoformat(),
    },
    {
        'source': 'reddit',
        'author': 'domain_investor_2025',
        'content': 'Just lost my domain due to OVH renewal failure. Their system is completely broken. Looking for alternatives.',
        'url': 'https://reddit.com/r/domains/comments/abc',
        'created_at': (datetime.now() - timedelta(days=5)).isoformat(),
    },
    {
        'source': 'x',
        'author': '@TechBlogger',
        'content': 'OVH DNS configuration is still giving me issues. Support tickets are ignored. Considering migrating.',
        'url': 'https://twitter.com/techblogger/status/456',
        'created_at': (datetime.now() - timedelta(days=4)).isoformat(),
    },
    {
        'source': 'google_news',
        'author': 'Tech News Daily',
        'content': 'OVH faces customer backlash over domain service outages. Multiple users report lost connections and unresponsive support.',
        'url': 'https://technewsdaily.com/ovh-outage',
        'created_at': (datetime.now() - timedelta(days=3)).isoformat(),
    },
    {
        'source': 'reddit',
        'author': 'web_admin',
        'content': 'OVH domain renewal charged me twice last month. Still waiting for refund after 15 days.',
        'url': 'https://reddit.com/r/webhosting/comments/def',
        'created_at': (datetime.now() - timedelta(days=2)).isoformat(),
    },
    {
        'source': 'x',
        'author': '@SarahWebDev',
        'content': 'Finally migrated away from OVH. Their domain services were unreliable and support was non-existent.',
        'url': 'https://twitter.com/sarahwebdev/status/789',
        'created_at': (datetime.now() - timedelta(days=2)).isoformat(),
    },
    {
        'source': 'google_news',
        'author': 'WebHost Magazine',
        'content': 'Customer complaints surge against OVH domain division. Industry experts question their infrastructure investments.',
        'url': 'https://webhostmag.com/ovh-complaints',
        'created_at': (datetime.now() - timedelta(days=1)).isoformat(),
    },
    {
        'source': 'reddit',
        'author': 'startup_founder',
        'content': 'OVH domain registration was smooth, but renewing is a pain. Auto-renewal failed twice.',
        'url': 'https://reddit.com/r/startups/comments/ghi',
        'created_at': (datetime.now() - timedelta(hours=12)).isoformat(),
    },
    {
        'source': 'x',
        'author': '@CloudArchitect',
        'content': 'Mixed experience with OVH. Domain management UI is outdated and API documentation is poor.',
        'url': 'https://twitter.com/cloudarchitect/status/012',
        'created_at': (datetime.now() - timedelta(hours=6)).isoformat(),
    },
    {
        'source': 'reddit',
        'author': 'positive_customer',
        'content': 'Actually had a good experience renewing my domain with OVH today. Support team was helpful!',
        'url': 'https://reddit.com/r/hosting/comments/jkl',
        'created_at': (datetime.now() - timedelta(hours=3)).isoformat(),
    },
]

print("📝 Inserting sample posts into database...")
added = 0

for post in sample_posts:
    try:
        # Analyze sentiment
        an = sentiment.analyze(post.get('content') or '')
        
        # Insert into database
        db.insert_post({
            'source': post['source'],
            'author': post['author'],
            'content': post['content'],
            'url': post['url'],
            'created_at': post['created_at'],
            'sentiment_score': an['score'],
            'sentiment_label': an['label'],
        })
        added += 1
        print(f"  ✓ {post['author']} ({post['source']}) - {an['label']}")
    except Exception as e:
        print(f"  ✗ Error inserting {post['author']}: {e}")

print(f"\n✅ Successfully added {added}/{len(sample_posts)} sample posts!")

# Display summary
posts = db.get_posts(limit=100)
print(f"\n📊 Database Summary:")
print(f"  Total posts: {len(posts)}")
print(f"  Positive: {len([p for p in posts if p['sentiment_label'] == 'positive'])}")
print(f"  Negative: {len([p for p in posts if p['sentiment_label'] == 'negative'])}")
print(f"  Neutral: {len([p for p in posts if p['sentiment_label'] == 'neutral'])}")

if posts:
    print(f"\n  Latest post: {posts[0]['created_at']}")
    print(f"  Oldest post: {posts[-1]['created_at']}")
