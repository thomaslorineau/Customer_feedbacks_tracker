"""Reddit scraper - DISABLED.

Reddit uses aggressive anti-scraping (403 Forbidden).
Would require OAuth2 + PRAW library + credentials.
Removed in favor of other sources (X, GitHub, Stack Overflow, Hacker News, Google News).
"""


def scrape_reddit(query: str, limit: int = 50):
    """Reddit scraping is disabled."""
    raise NotImplementedError(
        "Reddit scraping has been disabled due to aggressive anti-scraping measures. "
        "See frontend info panel for details."
    )
