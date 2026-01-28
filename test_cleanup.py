"""Test the cleanup of OVH API key"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.database import pg_get_config

key = pg_get_config('OVH_API_KEY')
print(f'Raw key: {repr(key)}')
print(f'Length: {len(key) if key else 0}')

if key:
    cleaned = ''.join(c for c in key if ord(c) < 128 and (c.isalnum() or c in '+-/=_'))
    print(f'Cleaned: {repr(cleaned)}')
    print(f'Length cleaned: {len(cleaned) if cleaned else 0}')
    
    bearer_header = f'Bearer {cleaned}' if cleaned else 'Bearer '
    print(f'Bearer header: {repr(bearer_header)}')
    
    try:
        bearer_header.encode('ascii')
        print('[OK] Can encode Bearer header as ASCII')
    except UnicodeEncodeError as e:
        print(f'[ERROR] Cannot encode Bearer header as ASCII: {e}')
        print(f'Problematic positions: {e.start}-{e.end}')
        if e.start is not None and e.end is not None:
            problematic = bearer_header[e.start:e.end]
            print(f'Problematic chars: {repr(problematic)}')
            print(f'Codes: {[ord(c) for c in problematic]}')
