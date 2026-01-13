def scrape_linkedin(query: str, limit: int = 50):
    """LinkedIn scraping is NOT IMPLEMENTED due to:
    
    1. ToS Violations: LinkedIn prohibits scraping in their ToS.
    2. Login Required: Need authenticated session (Selenium + browser automation).
    3. Rate Limiting: Aggressive bot detection and IP blocking.
    4. Legal Risks: LinkedIn has sued scrapers before.
    
    ALTERNATIVES:
    
    A) Use LinkedIn API (Jobs, Recruiter APIs): Requires enterprise access.
    
    B) Selenium + headless browser:
       - Install: pip install selenium
       - Use webdriver (Chrome, Firefox) with logged-in session
       - Fragile & slow, easy to break on UI changes
       - Still violates ToS
    
    C) Manual Export:
       - Export LinkedIn posts manually as CSV
       - Import them into the DB
       - Safest legal option
    
    D) Third-party LinkedIn scraping services:
       - RocketReach, Phantom Buster, etc.
       - Costs money
    
    For now, this returns empty list. Recommend using Option C (manual export).
    """
    return []
