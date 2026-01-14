"""Check latest Trustpilot posts with unique URLs."""
import httpx

response = httpx.get('http://127.0.0.1:8000/posts?source=Trustpilot&limit=5')
posts = response.json()

print(f"Latest {len(posts)} Trustpilot posts:\n")

for i, post in enumerate(posts, 1):
    print(f"{i}. {post['author']}")
    print(f"   URL: {post['url']}")
    print(f"   Content: {post['content'][:70]}...")
    print()
