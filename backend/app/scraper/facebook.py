def scrape_facebook(query: str, limit: int = 50):
    """Facebook scraping is NOT IMPLEMENTED due to:
    
    1. Strong ToS: Facebook explicitly prohibits scraping.
    2. Login Required: Must authenticate to access most content.
    3. Heavy Bot Detection: Aggressive IP blocking, CAPTCHA, etc.
    4. API Limitations: Graph API doesn't support public search.
    5. Legal/Privacy Concerns: Facebook has enforced ToS strictly.
    
    ALTERNATIVES:
    
    A) Use Facebook Graph API (official):
       - Requires app approval and business verification
       - Limited public data access
       - Mainly for your own pages/groups
    
    B) Use Meta Business Suite API:
       - For managing Meta business accounts
       - Not for general monitoring
    
    C) Third-party tools:
       - Brandwatch, Sprout Social, etc.
       - Pay per month
    
    D) Manual monitoring:
       - Search OVH-related groups/communities manually
       - Export insights as CSV
    
    For this project, recommend alternatives or manual data collection.
    """
    return []
