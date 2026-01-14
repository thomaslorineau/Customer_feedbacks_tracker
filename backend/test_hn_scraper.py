"""Test HN scraper with different queries."""
import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.WARNING)

from app.scraper import hackernews

# Test 1: Query with no results
print("=== Test 1: No results expected ===")
results = hackernews.scrape_hackernews("OVHCloud transfer Domain", limit=5)
print(f"Results: {len(results)}\n")

# Test 2: Query that should have results
print("=== Test 2: Query 'OVH' should have results ===")
results = hackernews.scrape_hackernews("OVH", limit=5)
print(f"Results: {len(results)}")
if results:
    print(f"\nFirst result:")
    print(f"  Author: {results[0]['author']}")
    print(f"  Content: {results[0]['content'][:80]}...")
    print(f"  URL: {results[0]['url']}")
