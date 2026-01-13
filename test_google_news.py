#!/usr/bin/env python3
"""Test Google News scraper"""

import sys
sys.path.insert(0, 'backend')

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.scraper.news import scrape_google_news

print("🔍 Testing Google News scraper...")
posts = scrape_google_news('OVH domain', limit=5)

print(f"\n✅ Found {len(posts)} posts from Google News\n")

if posts:
    for i, post in enumerate(posts[:3], 1):
        print(f"{i}. Author: {post['author']}")
        print(f"   Content: {post['content'][:100]}...")
        print(f"   Date: {post['created_at']}\n")
else:
    print("⚠️ No posts found. Google News RSS might be unavailable.")
    print("This is normal - Google News RSS requires internet connection.")
