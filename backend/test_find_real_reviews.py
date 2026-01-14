"""Find where the real review texts are located."""
import httpx
from bs4 import BeautifulSoup

TRUSTPILOT_WEB = "https://fr.trustpilot.com/review/ovhcloud.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

response = httpx.get(TRUSTPILOT_WEB, headers=DEFAULT_HEADERS, timeout=15, follow_redirects=True)
soup = BeautifulSoup(response.text, 'html.parser')

# Find all review texts
review_texts = soup.find_all('p', {'data-service-review-text-typography': True})
print(f"Total review texts found: {len(review_texts)}\n")

for i, text_elem in enumerate(review_texts[:10], 1):
    text = text_elem.get_text()[:80]
    # Find parent article
    parent_article = text_elem.find_parent('article')
    if parent_article:
        classes = ' '.join(parent_article.get('class', []))
        attrs = parent_article.attrs
        print(f"{i}. TEXT: {text}")
        print(f"   Parent: <article> with classes: {classes}")
        print(f"   Attrs keys: {list(attrs.keys())}")
    else:
        # Try to find any parent container
        parents = []
        current = text_elem.parent
        depth = 0
        while current and depth < 5:
            tag = current.name
            classes = current.get('class', [])
            parents.append(f"{tag}.{'.'.join(classes[:2]) if classes else 'no-class'}")
            current = current.parent
            depth += 1
        print(f"{i}. TEXT: {text}")
        print(f"   Parent chain: {' <- '.join(parents)}")
    print()
