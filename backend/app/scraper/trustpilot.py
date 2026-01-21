"""Trustpilot scraper for real customer reviews and complaints about OVH."""
import httpx
import os
import asyncio
from datetime import datetime
import logging
import json
from httpx import Timeout
import time
import re
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from .base_scraper import BaseScraper
from .scraper_logging import ScrapingLogger

logger = logging.getLogger(__name__)

TRUSTPILOT_API = "https://api.trustpilot.com/v1"
TRUSTPILOT_WEB = "https://fr.trustpilot.com/review/ovhcloud.com"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
}
# If an API key is provided via environment, include it in headers
TP_API_KEY = os.getenv('TRUSTPILOT_API_KEY')
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


class TrustpilotScraper(BaseScraper):
    """Async Trustpilot scraper with improved error handling."""
    
    def __init__(self):
        super().__init__("Trustpilot")
    
    async def scrape(self, query: str = "OVH", limit: int = 20) -> List[Dict[str, Any]]:
        """
        Scrape Trustpilot reviews for OVH customer feedback.
        First tries HTML scraping, then falls back to API if available.
        Returns a list of review dictionaries ready for insertion.
        """
        import time
        start_time = time.time()  # Use time.time() instead of asyncio.get_event_loop().time()
        self.logger.log_scraping_start(query, limit)
        
        try:
            # Try HTML scraping first (most reliable)
            try:
                reviews = await self._scrape_html(limit)
                if reviews:
                    duration = time.time() - start_time
                    self.logger.log_scraping_success(len(reviews), duration)
                    return reviews
            except Exception as e:
                self.logger.log("warning", f"HTML scraping failed: {e}", error_type=type(e).__name__)
            
            # Fallback to API if key is provided
            if TP_API_KEY:
                try:
                    reviews = await self._scrape_api(query, limit)
                    if reviews:
                        duration = time.time() - start_time
                        self.logger.log_scraping_success(len(reviews), duration)
                        return reviews
                except Exception as e:
                    self.logger.log("warning", f"API scraping failed: {e}", error_type=type(e).__name__)
            
            # All methods failed
            duration = time.time() - start_time
            self.logger.log("warning", "All scraping methods failed, returning empty list", duration=duration)
            return []
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.log_scraping_error(e, duration)
            return []
    
    async def _scrape_html(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Scrape Trustpilot reviews directly from HTML page with pagination."""
        reviews = []
        page = 1
        max_pages = (limit // 20) + 2  # Estimate pages needed, add buffer
        
        self.logger.log("info", f"Starting HTML scrape with pagination (limit: {limit}, max_pages: {max_pages})")
        
        while len(reviews) < limit and page <= max_pages:
            # Build URL with pagination
            if page == 1:
                url = TRUSTPILOT_WEB
            else:
                url = f"{TRUSTPILOT_WEB}?page={page}"
            
            self.logger.log("info", f"Scraping page {page}: {url}")
            
            try:
                # Use longer timeout for Trustpilot (pagination can be slow)
                response = await self._fetch_get(
                    url,
                    headers=DEFAULT_HEADERS,
                    timeout=60.0  # 60 seconds timeout for Trustpilot requests
                )
                
                self.logger.log("info", f"Got response: {response.status_code}, length: {len(response.text)}")
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find ALL review cards - Trustpilot uses article tags with data-service-review-card-paper
                all_cards = soup.find_all('article', {'data-service-review-card-paper': True})
                
                self.logger.log("info", f"Found {len(all_cards)} total article cards on page {page}")
                
                # Filter to only cards with review text (skip carousel cards)
                # Use multiple selectors to be more robust
                review_cards = []
                for card in all_cards:
                    # Try multiple ways to find review text
                    text_elem = (card.find('p', {'data-service-review-text-typography': True}) or
                               card.find('div', {'data-service-review-text-typography': True}) or
                               card.find('p', class_=re.compile(r'review.*text|text.*review', re.I)) or
                               card.find('div', class_=re.compile(r'review.*content|content.*review', re.I)) or
                               card.find('p', class_=re.compile(r'review__text')))
                    
                    if text_elem:
                        review_text = text_elem.get_text(strip=True)
                        if review_text:
                            review_cards.append(card)
                        else:
                            # Try to find text in any paragraph or div within the card
                            all_text_elements = card.find_all(['p', 'div'], string=re.compile(r'.{20,}'))
                            if all_text_elements:
                                review_cards.append(card)
                
                self.logger.log("info", f"Filtered to {len(review_cards)} cards with review text on page {page}")
                
                # Debug: log if no cards found on first page
                if page == 1 and len(review_cards) == 0:
                    self.logger.log("warning", f"No review cards found on first page. Total cards: {len(all_cards)}")
                    # Log a sample of the HTML structure for debugging
                    if all_cards:
                        sample_card = all_cards[0]
                        self.logger.log("debug", f"Sample card HTML structure: {str(sample_card)[:500]}")
                
                # If no review cards found, we've reached the end
                if not review_cards:
                    self.logger.log("info", f"No more reviews found on page {page}, stopping pagination")
                    break
                
                parsed_count = 0
                skipped_count = 0
                
                for card in review_cards:
                    if len(reviews) >= limit:
                        break
                    try:
                        # Extract rating (stars)
                        rating_elem = card.find('div', {'data-service-review-rating': True})
                        rating = 3  # default neutral
                        if rating_elem:
                            rating_img = rating_elem.find('img')
                            if rating_img and rating_img.get('alt'):
                                # Extract "Noté 5 sur 5 étoiles" -> 5
                                match = re.search(r'(\d+)', rating_img['alt'])
                                if match:
                                    rating = int(match.group(1))
                        
                        # Extract review text - use multiple selectors for robustness
                        text_elem = (card.find('p', {'data-service-review-text-typography': True}) or
                                   card.find('div', {'data-service-review-text-typography': True}) or
                                   card.find('p', class_=re.compile(r'review.*text|text.*review', re.I)) or
                                   card.find('div', class_=re.compile(r'review.*content|content.*review', re.I)) or
                                   card.find('p', class_=re.compile(r'review__text')))
                        
                        review_text = text_elem.get_text(strip=True) if text_elem else ""
                        
                        # If still no text, try to find any substantial text in the card
                        if not review_text:
                            # Look for any paragraph or div with substantial text (at least 20 chars)
                            all_text_elements = card.find_all(['p', 'div'], string=re.compile(r'.{20,}'))
                            if all_text_elements:
                                review_text = ' '.join([elem.get_text(strip=True) for elem in all_text_elements[:3]])
                        
                        if not review_text or len(review_text.strip()) < 10:
                            skipped_count += 1
                            self.logger.log("debug", f"Skipped card: no review text found (author: {author if 'author' in locals() else 'unknown'})")
                            continue
                        
                        # Extract author - try multiple selectors
                        author_elem = (card.find('span', {'data-consumer-name-typography': True}) or
                                     card.find('div', {'data-consumer-name-typography': True}) or
                                     card.find('span', class_=re.compile(r'consumer.*name|name.*consumer', re.I)) or
                                     card.find('div', class_=re.compile(r'consumer.*name|name.*consumer', re.I)) or
                                     card.find('a', class_=re.compile(r'consumer.*name|name.*consumer', re.I)))
                        author = author_elem.get_text(strip=True) if author_elem else "Client"
                        
                        # If author is still "Client", try to find any name-like text in the card header
                        if author == "Client":
                            header = card.find('header') or card.find('div', class_=re.compile(r'header|review.*header', re.I))
                            if header:
                                name_candidates = header.find_all(['span', 'div', 'a'], string=re.compile(r'^[A-Z][a-z]+'))
                                if name_candidates:
                                    author = name_candidates[0].get_text(strip=True)
                        
                        # Extract date
                        date_elem = card.find('time')
                        created_at = datetime.now().isoformat()
                        if date_elem and date_elem.get('datetime'):
                            created_at = date_elem['datetime']
                        
                        # Extract review-specific URL - try multiple selectors
                        review_url = TRUSTPILOT_WEB  # fallback to general page
                        review_link = (card.find('a', {'data-review-title-typography': True}) or
                                     card.find('a', href=re.compile(r'/review/|/users/', re.I)) or
                                     card.find('a', class_=re.compile(r'review.*link|link.*review', re.I)))
                        
                        if review_link and review_link.get('href'):
                            # Convert relative URL to absolute
                            relative_url = review_link['href']
                            if relative_url.startswith('http'):
                                review_url = relative_url
                            elif relative_url.startswith('/'):
                                review_url = f"https://fr.trustpilot.com{relative_url}"
                            else:
                                review_url = f"https://fr.trustpilot.com/{relative_url}"
                        
                        # Map rating to sentiment
                        if rating >= 4:
                            sentiment_label = "positive"
                        elif rating >= 3:
                            sentiment_label = "neutral"
                        else:
                            sentiment_label = "negative"
                        
                        sentiment_score = (rating - 3) / 2  # 1-5 scale -> -1 to 1
                        
                        post = {
                            "source": "Trustpilot",
                            "author": author,
                            "content": review_text[:500],
                            "url": review_url,
                            "created_at": created_at,
                            "sentiment_score": sentiment_score,
                            "sentiment_label": sentiment_label,
                        }
                        reviews.append(post)
                        parsed_count += 1
                        
                        # Log first review for debugging
                        if page == 1 and parsed_count == 1:
                            self.logger.log("info", f"First review parsed: Author={author}, Rating={rating}, URL={review_url}, Content preview={review_text[:100]}")
                        
                    except Exception as e:
                        self.logger.log("warning", f"Could not parse review card: {e}")
                        skipped_count += 1
                        continue
                
                self.logger.log("info", f"Page {page}: parsed {parsed_count} reviews (skipped {skipped_count})")
                
                # Wait 1 second between pages to avoid rate limiting
                if page < max_pages and len(reviews) < limit:
                    await asyncio.sleep(1)
                
                page += 1
                
            except Exception as e:
                self.logger.log("warning", f"Error scraping page {page}: {e}")
                # Continue to next page even if this one fails
                page += 1
                continue
        
        self.logger.log("success", f"Successfully parsed {len(reviews)} reviews from {page - 1} page(s)")
        return reviews[:limit]  # Ensure we don't exceed limit
    
    async def _scrape_api(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Scrape using Trustpilot API (requires API key)."""
        headers = DEFAULT_HEADERS.copy()
        if TP_API_KEY:
            headers['Authorization'] = f'Bearer {TP_API_KEY}'
        
        params = {
            "q": query,
            "businessUnitId": "349d5a8279cb5700019b1b97",  # OVH's business unit ID
            "pageSize": limit,
            "sort": "recency"
        }
        
        response = await self._fetch_get(
            f"{TRUSTPILOT_API}/reviews/search",
            headers=headers,
            params=params
        )
        
        response.raise_for_status()
        data = response.json()
        
        reviews = []
        for review in data.get("reviews", [])[:limit]:
            try:
                review_text = review.get("text", "")[:500]
                rating = review.get("rating", 0)
                
                if rating >= 4:
                    sentiment_label = "positive"
                elif rating >= 3:
                    sentiment_label = "neutral"
                else:
                    sentiment_label = "negative"
                
                sentiment_score = (rating - 3) / 2
                
                post = {
                    "source": "Trustpilot",
                    "author": review.get("consumer", {}).get("displayName", "Anonymous"),
                    "content": review_text,
                    "url": review.get("links", {}).get("self", {}).get("href", TRUSTPILOT_WEB),
                    "created_at": review.get("createdAt", datetime.now().isoformat()),
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                }
                reviews.append(post)
            except Exception as e:
                self.logger.log("warning", f"Could not parse API review: {e}")
                continue
        
        return reviews


# Global scraper instance
_async_scraper = TrustpilotScraper()


async def scrape_trustpilot_reviews_async(query: str = "OVH", limit: int = 20) -> List[Dict[str, Any]]:
    """Async entry point for Trustpilot scraper."""
    return await _async_scraper.scrape(query, limit)


def scrape_trustpilot_reviews(query="OVH", limit=20):
    """
    Synchronous wrapper for async scraper (for backward compatibility).
    
    Scrape Trustpilot reviews for OVH customer feedback.
    First tries HTML scraping, then falls back to API if available.
    Returns a list of review dictionaries ready for insertion.
    """
    try:
        # Try to get running event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we can't use run(), so fall back to sync version
            return _scrape_trustpilot_sync(query, limit)
        else:
            return loop.run_until_complete(scrape_trustpilot_reviews_async(query, limit))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(scrape_trustpilot_reviews_async(query, limit))


def _scrape_trustpilot_sync(query="OVH", limit=20):
    """Synchronous fallback implementation."""
    logger.info(f"[Trustpilot] Scraping reviews for: {query}")
    
    # Try HTML scraping first (most reliable)
    try:
        reviews = _scrape_trustpilot_html(limit)
        if reviews:
            logger.info(f"[Trustpilot] Successfully scraped {len(reviews)} reviews from HTML")
            return reviews
    except Exception as e:
        logger.warning(f"[Trustpilot] HTML scraping failed: {e}")
    
    # Fallback to API if key is provided
    if TP_API_KEY:
        try:
            reviews = _scrape_trustpilot_api(query, limit)
            if reviews:
                logger.info(f"[Trustpilot] Successfully scraped {len(reviews)} reviews from API")
                return reviews
        except Exception as e:
            logger.warning(f"[Trustpilot] API scraping failed: {e}")
    
    # All methods failed - return empty list (no sample data allowed)
    logger.warning("[Trustpilot] All scraping methods failed, returning empty list")
    return []


def _scrape_trustpilot_html(limit=20):
    """Scrape Trustpilot reviews directly from HTML page."""
    logger.info(f"[Trustpilot HTML] Starting HTML scrape of {TRUSTPILOT_WEB}")
    try:
        response = httpx.get(
            TRUSTPILOT_WEB,
            headers=DEFAULT_HEADERS,
            timeout=Timeout(15.0, connect=5.0),
            follow_redirects=True
        )
        logger.info(f"[Trustpilot HTML] Got response: {response.status_code}, length: {len(response.text)}")
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        reviews = []
        
        # Find ALL review cards - Trustpilot uses article tags with data-service-review-card-paper
        # Note: The page has carousel cards (without full text) and main review cards (with full text)
        # We need to get all articles and filter by those that have review text
        all_cards = soup.find_all('article', {'data-service-review-card-paper': True})
        
        logger.info(f"[Trustpilot HTML] Found {len(all_cards)} total article cards")
        
        # Filter to only cards with review text (skip carousel cards)
        review_cards = []
        for card in all_cards:
            text_elem = card.find('p', {'data-service-review-text-typography': True})
            if text_elem and text_elem.get_text(strip=True):
                review_cards.append(card)
        
        logger.info(f"[Trustpilot HTML] Filtered to {len(review_cards)} cards with review text")
        
        parsed_count = 0
        skipped_count = 0
        
        for card in review_cards[:limit]:
            try:
                # Extract rating (stars)
                rating_elem = card.find('div', {'data-service-review-rating': True})
                rating = 3  # default neutral
                if rating_elem:
                    rating_img = rating_elem.find('img')
                    if rating_img and rating_img.get('alt'):
                        # Extract "Noté 5 sur 5 étoiles" -> 5
                        match = re.search(r'(\d+)', rating_img['alt'])
                        if match:
                            rating = int(match.group(1))
                
                # Extract review text
                text_elem = card.find('p', {'data-service-review-text-typography': True}) or \
                           card.find('div', class_=re.compile(r'review-content')) or \
                           card.find('p', class_=re.compile(r'review__text'))
                review_text = text_elem.get_text(strip=True) if text_elem else ""
                
                if not review_text:
                    skipped_count += 1
                    logger.debug(f"Skipped card {skipped_count}: no review text found")
                    continue
                
                # Extract author
                author_elem = card.find('span', {'data-consumer-name-typography': True}) or \
                             card.find('div', class_=re.compile(r'consumer-name'))
                author = author_elem.get_text(strip=True) if author_elem else "Client"
                
                # Extract date
                date_elem = card.find('time')
                created_at = datetime.now().isoformat()
                if date_elem and date_elem.get('datetime'):
                    created_at = date_elem['datetime']
                
                # Extract review-specific URL
                review_url = TRUSTPILOT_WEB  # fallback to general page
                review_link = card.find('a', {'data-review-title-typography': True})
                if review_link and review_link.get('href'):
                    # Convert relative URL to absolute
                    relative_url = review_link['href']
                    review_url = f"https://fr.trustpilot.com{relative_url}"
                
                # Map rating to sentiment
                if rating >= 4:
                    sentiment_label = "positive"
                elif rating >= 3:
                    sentiment_label = "neutral"
                else:
                    sentiment_label = "negative"
                
                sentiment_score = (rating - 3) / 2  # 1-5 scale -> -1 to 1
                
                post = {
                    "source": "Trustpilot",
                    "author": author,
                    "content": review_text[:500],
                    "url": review_url,
                    "created_at": created_at,
                    "sentiment_score": sentiment_score,
                    "sentiment_label": sentiment_label,
                }
                reviews.append(post)
                parsed_count += 1
                logger.debug(f"[OK] Trustpilot #{parsed_count}: {author} ({rating} stars) - {review_text[:40]}")
            
            except Exception as e:
                logger.warning(f"Could not parse review card: {e}")
                continue
        
        logger.info(f"[Trustpilot HTML] Successfully parsed {len(reviews)} reviews (skipped {skipped_count})")
        return reviews
    
    except Exception as e:
        logger.error(f"HTML scraping error: {e}")
        raise


def _scrape_trustpilot_api(query: str, limit: int):
    """Scrape using Trustpilot API (requires API key)."""
    headers = DEFAULT_HEADERS.copy()
    if TP_API_KEY:
        headers['Authorization'] = f'Bearer {TP_API_KEY}'
    
    last_error = None
    
    for attempt in range(MAX_RETRIES):
        try:
            params = {
                "q": query,
                "businessUnitId": "349d5a8279cb5700019b1b97",  # OVH's business unit ID
                "pageSize": limit,
                "sort": "recency"
            }
            
            response = httpx.get(
                f"{TRUSTPILOT_API}/reviews/search",
                params=params,
                timeout=Timeout(15.0, connect=5.0),
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
            
            reviews = []
            for review in data.get("reviews", [])[:limit]:
                try:
                    review_text = review.get("text", "")[:500]
                    rating = review.get("rating", 0)
                    
                    if rating >= 4:
                        sentiment_label = "positive"
                    elif rating >= 3:
                        sentiment_label = "neutral"
                    else:
                        sentiment_label = "negative"
                    
                    sentiment_score = (rating - 3) / 2
                    
                    post = {
                        "source": "Trustpilot",
                        "author": review.get("consumer", {}).get("displayName", "Anonymous"),
                        "content": review_text,
                        "url": review.get("links", {}).get("self", {}).get("href", TRUSTPILOT_WEB),
                        "created_at": review.get("createdAt", datetime.now().isoformat()),
                        "sentiment_score": sentiment_score,
                        "sentiment_label": sentiment_label,
                    }
                    reviews.append(post)
                except Exception as e:
                    logger.warning(f"Could not parse API review: {e}")
                    continue
            
            return reviews
        
        except (httpx.ReadTimeout, httpx.ConnectError, httpx.NetworkError) as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                logger.warning(f"[Attempt {attempt + 1}/{MAX_RETRIES}] API network error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        except httpx.HTTPStatusError as e:
            logger.error(f"Trustpilot API HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"Trustpilot API error: {e}")
            raise
    
    raise last_error if last_error else Exception("Failed to fetch reviews")


def _get_sample_trustpilot_reviews(limit=10):
    now = datetime.now().isoformat()
    sample = [
        {
            "source": "Trustpilot",
            "author": "Client Vérifié",
            "content": "Service client OVH lent pour les questions de domaine. Beaucoup d'attente.",
            "url": "https://trustpilot.com/sample",
            "created_at": now,
            "sentiment_score": -0.6,
            "sentiment_label": "negative",
        },
        {
            "source": "Trustpilot",
            "author": "Utilisateur",
            "content": "Renouvellement de domaine facturé deux fois, le support est en cours de traitement.",
            "url": "https://trustpilot.com/sample",
            "created_at": now,
            "sentiment_score": -0.4,
            "sentiment_label": "negative",
        },
        {
            "source": "Trustpilot",
            "author": "Entreprise",
            "content": "Expérience correcte, mais interface à améliorer pour les domaines internationaux.",
            "url": "https://trustpilot.com/sample",
            "created_at": now,
            "sentiment_score": 0.2,
            "sentiment_label": "neutral",
        },
    ]
    return sample[:limit]

