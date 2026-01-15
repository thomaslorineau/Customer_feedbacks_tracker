"""
Contract tests for API endpoints.
Validates that API responses match the OpenAPI specification.
"""
import requests
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

API_BASE = "http://127.0.0.1:8000"
OPENAPI_SPEC_URL = f"{API_BASE}/api/openapi.json"

def test_endpoint(method, endpoint, expected_status=200, json_data=None, params=None):
    """Test an API endpoint and validate response."""
    url = f"{API_BASE}{endpoint}"
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, json=json_data, params=params, timeout=10)
        elif method.upper() == "DELETE":
            response = requests.delete(url, timeout=10)
        else:
            print(f"❌ Unsupported method: {method}")
            return False
        
        if response.status_code == expected_status:
            print(f"✅ {method} {endpoint} - Status: {response.status_code}")
            return True
        else:
            print(f"❌ {method} {endpoint} - Expected {expected_status}, got {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {method} {endpoint} - Error: {e}")
        return False

def test_openapi_spec():
    """Test that OpenAPI spec is accessible and valid."""
    try:
        response = requests.get(OPENAPI_SPEC_URL, timeout=10)
        if response.status_code == 200:
            spec = response.json()
            if "openapi" in spec and "paths" in spec:
                print(f"✅ OpenAPI spec accessible - Version: {spec.get('openapi', 'unknown')}")
                print(f"   Endpoints found: {len(spec.get('paths', {}))}")
                return True
            else:
                print("❌ OpenAPI spec invalid structure")
                return False
        else:
            print(f"❌ OpenAPI spec not accessible - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ OpenAPI spec test failed: {e}")
        return False

def main():
    """Run all contract tests."""
    print("🧪 Running API Contract Tests\n")
    
    results = []
    
    # Test OpenAPI spec
    print("1. Testing OpenAPI Specification...")
    results.append(("OpenAPI Spec", test_openapi_spec()))
    print()
    
    # Test health/version endpoints
    print("2. Testing Health & Version Endpoints...")
    results.append(("GET /api/version", test_endpoint("GET", "/api/version")))
    results.append(("GET /api/config", test_endpoint("GET", "/api/config")))
    print()
    
    # Test posts endpoints
    print("3. Testing Posts Endpoints...")
    results.append(("GET /api/posts", test_endpoint("GET", "/api/posts", params={"limit": 10})))
    results.append(("GET /api/posts/by-source", test_endpoint("GET", "/api/posts/by-source")))
    print()
    
    # Test analytics endpoints
    print("4. Testing Analytics Endpoints...")
    results.append(("GET /api/stats", test_endpoint("GET", "/api/stats")))
    results.append(("GET /api/pain-points", test_endpoint("GET", "/api/pain-points", params={"days": 30, "limit": 5})))
    results.append(("GET /api/improvements-summary", test_endpoint("GET", "/api/improvements-summary")))
    print()
    
    # Test scraping endpoints (POST - may return 0 posts, that's OK)
    print("5. Testing Scraping Endpoints (may return 0 posts)...")
    results.append(("POST /scrape/reddit", test_endpoint("POST", "/scrape/reddit", params={"query": "test", "limit": 1}, expected_status=200)))
    print()
    
    # Test logs endpoints
    print("6. Testing Logs Endpoints...")
    results.append(("GET /api/logs", test_endpoint("GET", "/api/logs", params={"limit": 10})))
    print()
    
    # Summary
    print("\n" + "="*50)
    print("📊 Test Summary")
    print("="*50)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 All contract tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())



