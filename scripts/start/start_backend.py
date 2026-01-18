#!/usr/bin/env python3
"""Start the backend server."""
import subprocess
import sys
import os

# Change to backend directory (go up 2 levels from scripts/start/ to root, then to backend)
backend_path = os.path.join(os.path.dirname(__file__), '..', '..', 'backend')
os.chdir(backend_path)

# Run uvicorn
subprocess.run([
    sys.executable, '-m', 'uvicorn',
    'app.main:app',
    '--host', '127.0.0.1',
    '--port', '8000'
])
