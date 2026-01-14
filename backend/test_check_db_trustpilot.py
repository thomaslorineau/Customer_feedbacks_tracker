"""Get recent Trustpilot posts from DB."""
import httpx

response = httpx.get('http://127.0.0.1:8000/posts?source=Trustpilot&limit=5')
print(f"Status: {response.status_code}\n")

posts = response.json()
print(f"Total Trustpilot posts: {len(posts)}\n")

for i, post in enumerate(posts[:5], 1):
    print(f"{i}. {post['source']} - {post['author']}")
    print(f"   Content: {post['content'][:80]}...")
    print(f"   URL: {post['url']}")
    print(f"   Date: {post['created_at']}")
    
    # Check if it's sample data
    is_sample = 'sample' in post['url'].lower() or post['url'] == 'https://trustpilot.com/sample'
    print(f"   {'⚠️ SAMPLE DATA' if is_sample else '✅ REAL DATA'}")
    print()
