"""Test the /api/config endpoint"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_api_config():
    """Test /api/config endpoint"""
    response = client.get("/api/config")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Environment: {data.get('environment')}")
        print(f"LLM Provider: {data.get('llm_provider')}")
        print(f"API Keys configured:")
        for provider, info in data.get('api_keys', {}).items():
            configured = info.get('configured')
            masked = info.get('masked')
            print(f"  {provider}: {'✓' if configured else '✗'} {masked}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_api_config()
