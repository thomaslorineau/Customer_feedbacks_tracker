"""Simple test server for settings page"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

# Mount static files
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/v2", StaticFiles(directory=str(frontend_dir / "v2")), name="v2")
app.mount("/css", StaticFiles(directory=str(frontend_dir / "css")), name="css")

@app.get("/settings", response_class=HTMLResponse)
async def serve_settings():
    """Serve the settings page."""
    settings_path = frontend_dir / "v2" / "settings.html"
    print(f"Looking for: {settings_path}")
    print(f"Exists: {settings_path.exists()}")
    
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return HTMLResponse(content=f"<h1>Settings Not Found</h1><p>Path: {settings_path}</p>", status_code=404)

@app.get("/api/config")
async def get_config():
    """Test config endpoint"""
    return {
        "environment": "development",
        "llm_provider": "openai",
        "api_keys": {
            "openai": {"configured": False, "masked": None, "length": 0},
            "anthropic": {"configured": False, "masked": None, "length": 0},
            "google": {"configured": False, "masked": None, "length": 0},
            "github": {"configured": False, "masked": None, "length": 0},
            "trustpilot": {"configured": False, "masked": None, "length": 0}
        },
        "rate_limiting": {
            "requests_per_window": 100,
            "window_seconds": 60
        }
    }

if __name__ == "__main__":
    print(f"Frontend directory: {frontend_dir}")
    print(f"Settings path: {frontend_dir / 'v2' / 'settings.html'}")
    uvicorn.run(app, host="127.0.0.1", port=9007)
