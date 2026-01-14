"""Test with better error handling."""
import httpx

response = httpx.post('http://127.0.0.1:8000/scrape/hackernews?query=NoResultsQuery123456789&limit=1', timeout=15)
print(f"Status: {response.status_code}")
print(f"Headers: {dict(response.headers)}")
print(f"\nFull response text:")
print(response.text)
