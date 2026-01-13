from datetime import datetime


def scrape_google_news(query: str, limit: int = 50):
    """Scrape Google News using feedparser RSS.
    
    Returns list of dicts: source, author, content, url, created_at
    Raises exception if RSS is unavailable.
    """
    return _scrape_google_news_fallback(query, limit)


def _scrape_google_news_fallback(query: str, limit: int = 50):
    """Scrape Google News using RSS feed.
    
    This fetches articles from Google News RSS endpoint.
    """
    results = []
    
    try:
        import feedparser
        
        # Google News RSS endpoint - searches for articles matching the query
        url = f"https://news.google.com/rss/search?q={query}&hl=en&gl=US&ceid=US:en"
        
        # Parse with timeout
        feed = feedparser.parse(url)
        
        # Check if feed has entries
        if not feed.entries:
            raise RuntimeError("Google News RSS is unavailable or returned no results. This may be due to network issues or rate limiting.")
        
        for i, entry in enumerate(feed.entries):
            if i >= limit:
                break
            
            try:
                # Extract author from the source/author field
                author = entry.get('author', entry.get('source', {}).get('title', 'News Source'))
                
                # Combine title and summary for content
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                content = title + ('\n\n' + summary if summary else '')
                
                results.append({
                    'source': 'Google News',
                    'author': author if author else 'News Source',
                    'content': content,
                    'url': entry.get('link', ''),
                    'created_at': entry.get('published', datetime.now().isoformat()),
                })
            except Exception as e:
                print(f"Error processing article: {e}")
                continue
    
    except Exception as e:
        raise RuntimeError(f"Failed to scrape Google News: {str(e)}")
    
    if not results:
        raise RuntimeError("No Google News articles found. The service may be unavailable or rate-limited.")
    
    return results



