#!/usr/bin/env python3
"""Run the FastAPI server."""
import sys
import os
import uvicorn

# Ensure current directory is in path
sys.path.insert(0, os.path.dirname(__file__))

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=False
    )
