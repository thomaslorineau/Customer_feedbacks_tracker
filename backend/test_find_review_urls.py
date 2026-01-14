"""Find review-specific URLs in Trustpilot HTML."""
import httpx
from bs4 import BeautifulSoup

TRUSTPILOT_WEB = "https://fr.trustpilot.com/review/ovhcloud.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

response = httpx.get(TRUSTPILOT_WEB, headers=DEFAULT_HEADERS, timeout=15, follow_redirects=True)
soup = BeautifulSoup(response.text, 'html.parser')

# Get articles with review text
articles = soup.find_all('article', {'data-service-review-card-paper': True})

print(f"Analyzing first 3 articles with review text:\n")

count = 0
for article in articles:
    text_elem = article.find('p', {'data-service-review-text-typography': True})
    if not text_elem:
        continue
    
    count += 1
    if count > 3:
        break
    
    print(f"=== Review {count} ===")
    
    # Look for links in the article
    links = article.find_all('a', href=True)
    print(f"Links found in article: {len(links)}")
    
    for i, link in enumerate(links[:5], 1):
        href = link.get('href')
        text = link.get_text(strip=True)[:50]
        data_attrs = {k: v for k, v in link.attrs.items() if k.startswith('data-')}
        print(f"  {i}. href: {href}")
        print(f"     text: {text}")
        if data_attrs:
            print(f"     data attributes: {data_attrs}")
    
    # Look for data-service-review-url or similar
    review_url_elem = article.find(attrs={'data-service-review-url': True})
    if review_url_elem:
        print(f"Found data-service-review-url: {review_url_elem.get('data-service-review-url')}")
    
    # Check article itself for data attributes
    article_data = {k: v for k, v in article.attrs.items() if 'url' in k.lower() or 'link' in k.lower()}
    if article_data:
        print(f"Article data attrs with url/link: {article_data}")
    
    print()
