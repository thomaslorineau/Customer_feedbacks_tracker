"""Test Trustpilot HTML scraping to debug selectors."""
import httpx
from bs4 import BeautifulSoup

TRUSTPILOT_WEB = "https://fr.trustpilot.com/review/ovhcloud.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

print("Fetching Trustpilot page...")
response = httpx.get(TRUSTPILOT_WEB, headers=DEFAULT_HEADERS, timeout=15, follow_redirects=True)
print(f"Status: {response.status_code}")
print(f"HTML length: {len(response.text)}")

soup = BeautifulSoup(response.text, 'html.parser')

# Test different selectors
print("\n=== Testing selectors ===")
articles = soup.find_all('article')
print(f"1. Total <article> tags: {len(articles)}")

if articles:
    first = articles[0]
    print(f"   First article attributes: {first.attrs}")
    print(f"   First article classes: {first.get('class')}")

# Look for review text
review_texts = soup.find_all('p', attrs={'data-service-review-text-typography': True})
print(f"\n2. Review texts (data-service-review-text-typography): {len(review_texts)}")
if review_texts:
    print(f"   First review text: {review_texts[0].get_text()[:100]}")

# Look for alternative text selectors
alt_texts = soup.find_all('p', class_=lambda x: x and 'review' in str(x).lower())
print(f"\n3. Alternative review texts: {len(alt_texts)}")

# Look for ratings
ratings = soup.find_all('div', attrs={'data-service-review-rating': True})
print(f"\n4. Ratings (data-service-review-rating): {len(ratings)}")
if ratings:
    img = ratings[0].find('img')
    if img:
        print(f"   First rating img alt: {img.get('alt')}")

# Look for authors
authors = soup.find_all('span', attrs={'data-consumer-name-typography': True})
print(f"\n5. Authors (data-consumer-name-typography): {len(authors)}")
if authors:
    print(f"   First author: {authors[0].get_text()}")

# Look for dates
dates = soup.find_all('time')
print(f"\n6. Time elements: {len(dates)}")
if dates:
    print(f"   First date datetime: {dates[0].get('datetime')}")
    print(f"   First date text: {dates[0].get_text()}")

print("\n=== Test complete ===")
