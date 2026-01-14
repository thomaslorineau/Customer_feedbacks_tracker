"""Test HN API endpoint."""
import httpx

# Test with query that has no results
print("=== Test 1: Query with no results ===")
response = httpx.post('http://127.0.0.1:8000/scrape/hackernews?query=OVHCloud+transfer+Domain&limit=5', timeout=15)
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")

try:
    data = response.json()
    print(f"✅ Valid JSON response")
    print(f"Added: {data.get('added', 0)}")
except Exception as e:
    print(f"❌ JSON parse error: {e}")
    print(f"Response text: {response.text[:200]}")

# Test with query that has results  
print("\n=== Test 2: Query 'OVH' should have results ===")
response = httpx.post('http://127.0.0.1:8000/scrape/hackernews?query=OVH&limit=5', timeout=15)
print(f"Status: {response.status_code}")

try:
    data = response.json()
    print(f"✅ Valid JSON response")
    print(f"Added: {data.get('added', 0)}")
except Exception as e:
    print(f"❌ JSON parse error: {e}")
