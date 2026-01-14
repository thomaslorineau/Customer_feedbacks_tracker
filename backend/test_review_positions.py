"""Debug which articles have review text."""
import httpx
from bs4 import BeautifulSoup

TRUSTPILOT_WEB = "https://fr.trustpilot.com/review/ovhcloud.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}

response = httpx.get(TRUSTPILOT_WEB, headers=DEFAULT_HEADERS, timeout=15, follow_redirects=True)
soup = BeautifulSoup(response.text, 'html.parser')

articles = soup.find_all('article', {'data-service-review-card-paper': True})
print(f"Total articles: {len(articles)}\n")

for i, article in enumerate(articles[:25], 1):
    # Check for review text
    text_elem = article.find('p', {'data-service-review-text-typography': True})
    has_text = "✓" if text_elem else "✗"
    text_preview = text_elem.get_text()[:50] if text_elem else "NO TEXT"
    
    # Check class
    classes = article.get('class', [])
    is_carousel = 'carousel' in ' '.join(classes).lower()
    
    print(f"{i}. {has_text} {'[CAROUSEL]' if is_carousel else '[MAIN]'} - {text_preview}")
