"""Direct import test."""
from app.scraper import trustpilot
import logging

logging.basicConfig(level=logging.WARNING)

results = trustpilot.scrape_trustpilot_reviews('OVH', limit=3)
print(f'\nGot {len(results)} results')

if results:
    first = results[0]
    print(f'\nFirst result:')
    print(f'  URL: {first["url"]}')
    print(f'  Author: {first["author"]}')
    print(f'  Content: {first["content"][:80]}...')
    
    is_sample = 'sample' in first['url'].lower()
    print(f'  Type: {"SAMPLE" if is_sample else "REAL DATA"}')
