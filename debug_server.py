"""Debug server startup"""
import sys
from pathlib import Path

# Add parent to path
parent = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(parent))

print(f"Python path: {sys.path[:3]}")
print(f"Working directory: {Path.cwd()}")

try:
    print("\n1. Importing app...")
    from backend.app.main import app
    print("[OK] App imported")
    
    print("\n2. Testing /api/config route...")
    from backend.app.config import config, Config
    print(f"[OK] Config loaded: {config.ENVIRONMENT}")
    
    print(f"\n3. Testing Config.mask_api_key...")
    masked = Config.mask_api_key("sk-test123456789")
    print(f"[OK] Masked: {masked}")
    
    print("\n4. Starting server...")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9006)
    
except Exception as e:
    print(f"\n[ERROR] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
