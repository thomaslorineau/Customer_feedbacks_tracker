"""Test backend endpoint /api/ovh/models"""
import requests
import json
import sys

def test_backend_endpoint():
    """Test the backend /api/ovh/models endpoint"""
    url = "http://localhost:8000/api/ovh/models"
    
    print(f"[TEST] Testing backend endpoint: {url}")
    print()
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"[RESPONSE] Status Code: {response.status_code}")
        print(f"[RESPONSE] Headers: {dict(response.headers)}")
        print()
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"[SUCCESS] Response JSON parsed successfully")
                print(f"   Models count: {len(data.get('models', []))}")
                print(f"   Endpoint: {data.get('endpoint', 'N/A')}")
                print(f"   Error: {data.get('error', 'None')}")
                if data.get('models'):
                    print(f"   First 5 models: {data['models'][:5]}")
                print()
                print("[FULL RESPONSE]")
                print(json.dumps(data, indent=2, ensure_ascii=True))
            except Exception as e:
                print(f"[ERROR] Failed to parse JSON: {e}")
                print(f"[RAW] Response text (first 500 chars): {response.text[:500]}")
        else:
            print(f"[ERROR] HTTP {response.status_code}")
            print(f"[RESPONSE] {response.text[:500]}")
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to backend. Is the server running on http://localhost:8000?")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backend_endpoint()
