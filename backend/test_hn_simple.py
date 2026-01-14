"""Test scraper directly in endpoint."""
import httpx

url = "http://127.0.0.1:8000/scrape/hackernews"

# Test with logging enabled
print("Testing with query that has results:")
r1 = httpx.post(f"{url}?query=OVH&limit=2", timeout=15)
print(f"  Status: {r1.status_code}, Added: {r1.json().get('added') if r1.status_code == 200 else 'error'}")

print("\nTesting with query that has NO results:")
try:
    r2 = httpx.post(f"{url}?query=ZZZNoResultsXXX&limit=1", timeout=15)
    print(f"  Status: {r2.status_code}")
    if r2.status_code == 200:
        print(f"  Response: {r2.json()}")
    else:
        print(f"  Error: {r2.text[:200]}")
except Exception as e:
    print(f"  Exception: {e}")
