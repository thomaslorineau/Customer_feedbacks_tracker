"""Test Trustpilot API endpoint."""
import httpx

response = httpx.post(
    'http://127.0.0.1:8000/scrape/trustpilot?query=OVH&limit=5',
    timeout=30
)

print(f"Status: {response.status_code}")
data = response.json()
print(f"Message: {data.get('message')}")
print(f"Added: {data.get('added')}")
print(f"Total posts in DB: {data.get('total')}")

posts = data.get('posts', [])
print(f"\nPosts returned: {len(posts)}")

for i, post in enumerate(posts[:3], 1):
    print(f"\n{i}. {post['source']} - {post['author']}")
    print(f"   Content: {post['content'][:80]}...")
    print(f"   URL: {post['url']}")
    print(f"   Sentiment: {post['sentiment_label']} ({post['sentiment_score']:.2f})")
    
    # Check if it's sample data
    is_sample = 'sample' in post['url'].lower()
    print(f"   {'⚠️ SAMPLE DATA' if is_sample else '✅ REAL DATA'}")
