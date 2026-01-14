"""Direct test of Trustpilot scraper."""
import sys
sys.path.insert(0, '.')

import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(message)s')

from app.scraper.trustpilot import scrape_trustpilot_reviews

print("=== Testing Trustpilot scraper ===\n")
results = scrape_trustpilot_reviews(query="OVH", limit=10)

print(f"\n=== Results: {len(results)} reviews ===")
for i, review in enumerate(results[:3], 1):
    print(f"\n{i}. {review['source']} - {review['author']}")
    print(f"   Sentiment: {review['sentiment_label']} ({review['sentiment_score']:.2f})")
    print(f"   Content: {review['content'][:100]}...")
    print(f"   URL: {review['url']}")
    print(f"   Date: {review['created_at']}")
