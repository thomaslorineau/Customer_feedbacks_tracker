"""Test Hacker News API."""
import httpx

query = "OVHCloud transfer Domain"
url = "https://hn.algolia.com/api/v1/search"
params = {
    "query": query,
    "hitsPerPage": 5,
}

print(f"Testing HN API with query: {query}")
print(f"URL: {url}")
print(f"Params: {params}\n")

try:
    response = httpx.get(url, params=params, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Content-Type: {response.headers.get('content-type')}")
    print(f"Response length: {len(response.text)}")
    print(f"\nFirst 500 chars of response:")
    print(response.text[:500])
    
    if response.status_code == 200:
        try:
            data = response.json()
            print(f"\n✅ Valid JSON received")
            print(f"Hits found: {len(data.get('hits', []))}")
            if data.get('hits'):
                first_hit = data['hits'][0]
                print(f"\nFirst hit:")
                print(f"  Title: {first_hit.get('title', 'N/A')}")
                print(f"  Author: {first_hit.get('author', 'N/A')}")
                print(f"  URL: {first_hit.get('url', 'N/A')}")
        except Exception as e:
            print(f"\n❌ JSON parsing failed: {e}")
    else:
        print(f"\n❌ HTTP error: {response.status_code}")
        
except Exception as e:
    print(f"❌ Request failed: {e}")
