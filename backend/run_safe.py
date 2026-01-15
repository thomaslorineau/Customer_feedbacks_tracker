#!/usr/bin/env python3
"""Run the app in safe mode (scrapers disabled) for fast, stable startup."""
import os
import uvicorn

# Disable scrapers to avoid import/runtime side-effects during debugging
os.environ['ENABLE_SCRAPERS'] = '0'

print("Starting safe server (scrapers disabled) on port 8000...")
uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info", reload=False)
