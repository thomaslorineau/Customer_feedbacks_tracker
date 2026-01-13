
def scrape_x(query: str, limit: int = 50):
    """Scrape X (Twitter) using snscrape. Returns list of dicts.

    Each dict: source, author, content, url, created_at
    """
    # First try Python import (fast), otherwise fallback to calling snscrape CLI via subprocess
    results = []
    try:
        from snscrape.modules.twitter import TwitterSearchScraper
        for i, tweet in enumerate(TwitterSearchScraper(query).get_items()):
            if i >= limit:
                break
            try:
                author = getattr(tweet.user, 'username', None) or getattr(tweet, 'username', None) or ''
            except Exception:
                author = ''
            created_at = getattr(tweet, 'date', None)
            url = getattr(tweet, 'url', None)
            results.append({
                'source': 'X/Twitter',
                'author': author,
                'content': getattr(tweet, 'content', '') or getattr(tweet, 'rawContent', ''),
                'url': url,
                'created_at': created_at.isoformat() if created_at else None,
            })
        return results
    except Exception:
        # Fallback: call snscrape CLI and parse json lines
        import subprocess
        import json
        import shlex
        import sys
        cmd = f"{shlex.quote('snscrape')} --jsonl twitter-search {shlex.quote(query)} --max-results {limit}"
        try:
            # Try direct snscrape command
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        except Exception:
            # Try using python -m snscrape if snscrape is not on PATH
            cmd2 = f"{shlex.quote(sys.executable)} -m snscrape --jsonl twitter-search {shlex.quote(query)} --max-results {limit}"
            proc = subprocess.run(cmd2, shell=True, capture_output=True, text=True, check=True)

        for line in proc.stdout.splitlines():
            try:
                t = json.loads(line)
            except Exception:
                continue
            results.append({
                'source': 'X/Twitter',
                'author': t.get('user', {}).get('username') if isinstance(t.get('user'), dict) else t.get('username') or '',
                'content': t.get('content') or t.get('rawContent') or '',
                'url': t.get('url'),
                'created_at': t.get('date'),
            })
        return results


def scrape_x_multi_queries(limit: int = 50):
    """Scrape X for customer complaints about OVH domain services.
    
    Returns combined results from complaint-focused searches:
    - OVH support bad/slow
    - OVH domain expensive/overpriced
    - OVH customer service issues
    - OVH renewal problems
    - OVH interface confusing
    """
    import logging
    logger = logging.getLogger(__name__)
    
    queries = [
        "OVH support bad",
        "OVH domain expensive",
        "OVH customer service",
        "OVH renewal overpriced",
        "OVH interface confusing",
    ]
    
    all_results = []
    seen_urls = set()
    
    for query_term in queries:
        try:
            logger.info(f"Scraping X for: {query_term}")
            results = scrape_x(query_term, limit=limit // len(queries))
            
            # Avoid duplicates by URL
            for post in results:
                url = post.get('url')
                if url and url not in seen_urls:
                    all_results.append(post)
                    seen_urls.add(url)
            
            logger.info(f"✓ Found {len(results)} posts for '{query_term}'")
        except Exception as e:
            logger.warning(f"Error scraping '{query_term}': {e}")
            continue
    
    if not all_results:
        raise RuntimeError("Could not fetch any posts from X/Twitter")
    
    return all_results
