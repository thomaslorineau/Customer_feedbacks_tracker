"""Test on port 8001."""
import httpx

# Scrape with query that should have no results
r = httpx.post('http://127.0.0.1:8001/scrape/hackernews?query=ZZZNoResultsXXX&limit=1', timeout=15)
print(f"Status: {r.status_code}")
data = r.json() if r.status_code == 200 else None
print(f"Response: {data}")

if data:
    print(f"Added: {data.get('added')}")
    
    # Check what was added
    r2 = httpx.get('http://127.0.0.1:8001/posts?source=Hacker News&limit=5')
    posts = r2.json()
    print(f"\nTotal HN posts in DB: {len(posts)}")
    if posts:
        print("\nMost recent:")
        for i, p in enumerate(posts[:2], 1):
            print(f"{i}. {p['content'][:80]}")
