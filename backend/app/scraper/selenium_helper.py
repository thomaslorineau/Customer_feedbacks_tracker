"""Selenium/Playwright helper for JavaScript-heavy sites with anti-bot protection.

This module provides browser automation as a last resort for sites that:
- Require JavaScript execution
- Use Cloudflare or similar protection
- Block simple HTTP requests

IMPORTANT: Use responsibly and respect robots.txt and ToS.
"""
import logging
import os

logger = logging.getLogger(__name__)

# Check if Selenium is available
SELENIUM_AVAILABLE = False
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not installed. Install with: pip install selenium")

# Check if Playwright is available
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright not installed. Install with: pip install playwright && playwright install")


def create_stealth_chrome_driver(headless: bool = True):
    """Create a Chrome WebDriver with stealth options.
    
    Args:
        headless: Run browser in headless mode
    
    Returns:
        Chrome WebDriver instance
    """
    if not SELENIUM_AVAILABLE:
        raise ImportError("Selenium is not installed")
    
    options = ChromeOptions()
    
    if headless:
        options.add_argument('--headless=new')
    
    # Stealth options
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu')
    
    # Realistic window size
    options.add_argument('--window-size=1920,1080')
    
    # User agent
    from .anti_bot_helpers import get_random_user_agent
    options.add_argument(f'user-agent={get_random_user_agent()}')
    
    try:
        driver = webdriver.Chrome(options=options)
        
        # Execute stealth script
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            '''
        })
        
        return driver
    except WebDriverException as e:
        logger.error(f"Failed to create Chrome driver: {e}")
        logger.info("Make sure ChromeDriver is installed and in PATH")
        raise


def scrape_with_selenium(url: str, wait_selector: str = None, timeout: int = 10):
    """Scrape a URL using Selenium (for JavaScript-heavy sites).
    
    Args:
        url: URL to scrape
        wait_selector: CSS selector to wait for (optional)
        timeout: Timeout in seconds
    
    Returns:
        HTML content as string, or None if failed
    """
    if not SELENIUM_AVAILABLE:
        logger.error("Selenium is not available")
        return None
    
    driver = None
    try:
        driver = create_stealth_chrome_driver(headless=True)
        driver.get(url)
        
        # Wait for content to load
        if wait_selector:
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for selector: {wait_selector}")
        
        # Additional wait for JavaScript
        import time
        time.sleep(2)
        
        html = driver.page_source
        return html
        
    except Exception as e:
        logger.error(f"Selenium scraping failed: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def scrape_with_playwright(url: str, wait_selector: str = None, timeout: int = 10000):
    """Scrape a URL using Playwright (more modern, better stealth).
    
    Args:
        url: URL to scrape
        wait_selector: CSS selector to wait for (optional)
        timeout: Timeout in milliseconds
    
    Returns:
        HTML content as string, or None if failed
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright is not available")
        return None
    
    try:
        with sync_playwright() as p:
            # Launch browser with stealth options
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )
            
            # Create context with realistic settings
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = context.new_page()
            
            # Navigate to URL
            page.goto(url, wait_until='networkidle', timeout=timeout)
            
            # Wait for selector if provided
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=timeout)
                except:
                    logger.warning(f"Timeout waiting for selector: {wait_selector}")
            
            # Get HTML
            html = page.content()
            
            browser.close()
            return html
            
    except Exception as e:
        logger.error(f"Playwright scraping failed: {e}")
        return None


def get_best_scraping_method():
    """Determine the best available scraping method.
    
    Returns:
        'playwright', 'selenium', or 'requests'
    """
    if PLAYWRIGHT_AVAILABLE:
        return 'playwright'
    elif SELENIUM_AVAILABLE:
        return 'selenium'
    else:
        return 'requests'

