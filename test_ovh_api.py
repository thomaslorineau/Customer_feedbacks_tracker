"""Test script to check what OVH API returns"""
import asyncio
import httpx
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

async def test_ovh_api():
    """Test OVH API endpoint directly"""
    from app.database import pg_get_config
    
    # Get OVH configuration
    ovh_key = pg_get_config('OVH_API_KEY')
    ovh_endpoint = pg_get_config('OVH_ENDPOINT_URL')
    
    # Normalize empty strings
    if ovh_key == '':
        ovh_key = None
    if ovh_endpoint == '':
        ovh_endpoint = None
    
    # Use default endpoint if not configured
    if not ovh_endpoint:
        ovh_endpoint = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
    
    # Set stdout to UTF-8
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print(f"[TEST] Testing OVH API Endpoint: {ovh_endpoint}")
    print(f"[TEST] Endpoint bytes (hex): {ovh_endpoint.encode('utf-8').hex() if ovh_endpoint else 'None'}")
    print(f"[TEST] API Key: {'***' + ovh_key[-4:] if ovh_key and len(ovh_key) > 4 else 'NOT CONFIGURED'}")
    print()
    
    if not ovh_key:
        print("[ERROR] OVH API key not configured!")
        return
    
    # Check for non-ASCII in endpoint
    if ovh_endpoint:
        non_ascii_chars = [c for c in ovh_endpoint if ord(c) > 127]
        if non_ascii_chars:
            print(f"[WARN] Endpoint contains non-ASCII characters: {non_ascii_chars}")
            print(f"[WARN] Endpoint repr: {repr(ovh_endpoint)}")
            print()
    
    # Check for non-ASCII in API key
    if ovh_key:
        non_ascii_chars = [c for c in ovh_key if ord(c) > 127]
        if non_ascii_chars:
            print(f"[WARN] API Key contains non-ASCII characters at positions: {[i for i, c in enumerate(ovh_key) if ord(c) > 127]}")
            print()
    
    try:
        # Safely encode endpoint URL
        endpoint_url = ovh_endpoint.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        # Safely encode API key
        api_key_safe = ovh_key.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            print("[TEST] Calling GET /models endpoint...")
            # Safely encode headers - ensure all values are ASCII-safe
            headers = {
                'Authorization': f'Bearer {api_key_safe}'.encode('ascii', errors='replace').decode('ascii', errors='replace'),
                'Content-Type': 'application/json'
            }
            print(f"[TEST] Headers: {headers}")
            response = await client.get(
                f'{endpoint_url}/models',
                headers=headers
            )
            
            print(f"[RESPONSE] Status Code: {response.status_code}")
            print(f"[RESPONSE] Headers: {dict(response.headers)}")
            print()
            
            # Try to get raw content
            print("[RAW] Raw Response Content:")
            print(f"   Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"   Content Length: {len(response.content)} bytes")
            print()
            
            # Try different decoding methods
            print("[DECODE] Decoding attempts:")
            
            # Method 1: UTF-8 with errors='replace'
            try:
                content_utf8 = response.content.decode('utf-8', errors='replace')
                print(f"   [OK] UTF-8 (errors='replace'): {len(content_utf8)} chars")
                print(f"   Preview (first 500 chars): {content_utf8[:500]}")
                print()
            except Exception as e:
                print(f"   [FAIL] UTF-8 failed: {e}")
            
            # Method 2: Try to parse JSON directly
            try:
                result = response.json()
                print(f"   [OK] response.json() succeeded")
                print(f"   Type: {type(result)}")
                if isinstance(result, dict):
                    print(f"   Keys: {list(result.keys())}")
                    if 'data' in result:
                        print(f"   Models count: {len(result['data'])}")
                        print(f"   First 3 models: {[m.get('id', 'N/A') for m in result['data'][:3]]}")
                elif isinstance(result, list):
                    print(f"   List length: {len(result)}")
                    print(f"   First 3 items: {result[:3]}")
                print()
            except Exception as e:
                print(f"   [FAIL] response.json() failed: {type(e).__name__}: {e}")
                print()
            
            # Method 3: Manual JSON parsing after UTF-8 decode
            try:
                content_utf8 = response.content.decode('utf-8', errors='replace')
                result_manual = json.loads(content_utf8)
                print(f"   [OK] json.loads(utf8_decoded) succeeded")
                print(f"   Type: {type(result_manual)}")
                if isinstance(result_manual, dict):
                    print(f"   Keys: {list(result_manual.keys())}")
                    if 'data' in result_manual:
                        print(f"   Models count: {len(result_manual['data'])}")
                        # Check for non-ASCII characters in model names
                        model_names = [m.get('id', '') for m in result_manual['data']]
                        non_ascii_models = [m for m in model_names if any(ord(c) > 127 for c in m)]
                        if non_ascii_models:
                            print(f"   [WARN] Models with non-ASCII chars: {non_ascii_models[:5]}")
                        else:
                            print(f"   [OK] All model names are ASCII-safe")
                print()
            except Exception as e:
                print(f"   [FAIL] json.loads(utf8_decoded) failed: {type(e).__name__}: {e}")
                print()
            
    except httpx.TimeoutException:
        print("[ERROR] Request timeout!")
    except httpx.HTTPStatusError as e:
        print(f"[ERROR] HTTP Error {e.response.status_code}")
        try:
            error_text = e.response.content.decode('utf-8', errors='replace')
            print(f"Error response: {error_text[:500]}")
        except Exception:
            print(f"Error response (raw): {e.response.content[:500]}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ovh_api())
