#!/usr/bin/env python3
"""QA test for all scrapers"""
import sys

print("Testing all scrapers...")
print("\n1️⃣ Testing GitHub scraper...")
try:
    from app.scraper import github
    result = github.scrape_github_issues(query='OVH', limit=5)
    print(f"   ✅ GitHub: {len(result)} issues found")
    if result:
        print(f"   First issue: {result[0]['content'][:80]}")
except Exception as e:
    print(f"   ❌ GitHub error: {str(e)[:100]}")

print("\n2️⃣ Testing Stack Overflow scraper...")
try:
    from app.scraper import stackoverflow
    result = stackoverflow.scrape_stackoverflow(query='OVH', limit=5)
    print(f"   ✅ Stack Overflow: {len(result)} questions found")
    if result:
        print(f"   First question: {result[0]['content'][:80]}")
except Exception as e:
    print(f"   ❌ Stack Overflow error: {str(e)[:100]}")

print("\n3️⃣ Testing Hacker News scraper...")
try:
    from app.scraper import hackernews
    result = hackernews.scrape_hackernews(query='OVH', limit=5)
    print(f"   ✅ Hacker News: {len(result)} posts found")
    if result:
        print(f"   First post: {result[0]['content'][:80]}")
except Exception as e:
    print(f"   ❌ Hacker News error: {str(e)[:100]}")

print("\n4️⃣ Testing Reddit scraper...")
try:
    from app.scraper import reddit
    result = reddit.scrape_reddit(query='OVH', limit=5)
    print(f"   ✅ Reddit: {len(result)} posts found")
    if result:
        print(f"   First post: {result[0]['content'][:80]}")
except Exception as e:
    print(f"   ❌ Reddit error: {str(e)[:100]}")

print("\n5️⃣ Testing Google News scraper...")
try:
    from app.scraper import news
    result = news.scrape_google_news(query='OVH', limit=5)
    print(f"   ✅ Google News: {len(result)} articles found")
    if result:
        print(f"   First article: {result[0]['content'][:80]}")
except Exception as e:
    print(f"   ❌ Google News error: {str(e)[:100]}")

print("\n✅ Testing completed!")
