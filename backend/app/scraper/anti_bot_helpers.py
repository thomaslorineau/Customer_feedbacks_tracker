"""Helper functions to bypass anti-scraping protections (legitimately)."""
import random
import time
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# Pool of realistic User-Agents
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
]

# Realistic browser headers
BROWSER_HEADERS_TEMPLATE = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
}


def get_random_user_agent() -> str:
    """Get a random User-Agent from the pool."""
    return random.choice(USER_AGENTS)


def get_realistic_headers(referer: str = None, additional: Dict = None) -> Dict[str, str]:
    """Generate realistic browser headers.
    
    Args:
        referer: Optional referer URL
        additional: Additional headers to merge
    
    Returns:
        Dictionary of headers
    """
    headers = BROWSER_HEADERS_TEMPLATE.copy()
    headers['User-Agent'] = get_random_user_agent()
    
    if referer:
        headers['Referer'] = referer
        headers['Sec-Fetch-Site'] = 'same-origin'
    
    if additional:
        headers.update(additional)
    
    return headers


def human_like_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Add a human-like random delay between requests.
    
    Uses a normal distribution to simulate human behavior.
    """
    # Use normal distribution for more realistic delays
    delay = random.normalvariate(
        (min_seconds + max_seconds) / 2,
        (max_seconds - min_seconds) / 4
    )
    # Ensure delay is within bounds
    delay = max(min_seconds, min(max_seconds, delay))
    time.sleep(delay)


def exponential_backoff_delay(attempt: int, base_delay: float = 2.0, max_delay: float = 60.0) -> float:
    """Calculate exponential backoff delay.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
    
    Returns:
        Delay in seconds
    """
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter to avoid thundering herd
    jitter = random.uniform(0, delay * 0.1)
    return delay + jitter


def check_robots_txt(url: str) -> bool:
    """Check if URL is allowed by robots.txt (basic check).
    
    Note: This is a simplified check. For production, use urllib.robotparser
    
    Args:
        url: URL to check
    
    Returns:
        True if likely allowed, False if likely disallowed
    """
    # For now, return True (assume allowed)
    # In production, implement proper robots.txt parsing
    return True


def create_stealth_session():
    """Create a requests session with stealth features.
    
    Returns:
        Configured requests.Session
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
        respect_retry_after_header=True
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set default headers
    session.headers.update(get_realistic_headers())
    
    return session


def rotate_proxy(proxy_list: List[str] = None) -> Dict[str, str]:
    """Get a random proxy from the list (if provided).
    
    Args:
        proxy_list: List of proxy URLs (e.g., ['http://proxy1:8080', 'http://proxy2:8080'])
    
    Returns:
        Proxy dict for requests, or empty dict if no proxies
    """
    if not proxy_list:
        return {}
    
    proxy = random.choice(proxy_list)
    return {
        'http': proxy,
        'https': proxy
    }


def add_cookies_from_browser(session, cookies_dict: Dict[str, str]):
    """Add cookies to session (useful for sites that require authentication).
    
    Args:
        session: requests.Session
        cookies_dict: Dictionary of cookie name:value pairs
    """
    for name, value in cookies_dict.items():
        session.cookies.set(name, value)


def simulate_human_behavior(session, url: str):
    """Simulate human browsing behavior before making the actual request.
    
    This includes:
    - Visiting the main page first
    - Adding delays
    - Setting proper referer
    
    Args:
        session: requests.Session
        url: Target URL
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # Visit main page first (like a human would)
    # But skip if it's the same URL to avoid double request
    if base_url == url:
        return
    
    try:
        session.get(base_url, timeout=3)  # Reduced timeout
        time.sleep(0.5)  # Small delay instead of human_like_delay
    except:
        pass  # Ignore errors on main page visit

