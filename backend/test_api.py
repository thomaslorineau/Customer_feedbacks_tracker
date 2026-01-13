import requests

API_BASE = "http://127.0.0.1:8000"

def test_get_posts():
    resp = requests.get(f"{API_BASE}/posts?limit=2")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    print("/posts endpoint OK, returned", len(data), "posts.")

if __name__ == "__main__":
    test_get_posts()
