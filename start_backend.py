#!/usr/bin/env python3
"""Start the backend server."""
import subprocess
import sys
import os

# Change to backend directory
os.chdir(os.path.join(os.path.dirname(__file__), 'backend'))

# Run uvicorn
subprocess.run([
    sys.executable, '-m', 'uvicorn',
    'app.main:app',
    '--host', '127.0.0.1',
    '--port', '8000'
])
