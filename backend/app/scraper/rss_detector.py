"""
RSS Detector - Automatically detect and parse RSS/Atom feeds.

This module provides functionality to detect RSS/Atom feeds on a page
and parse them to extract posts/articles.
"""
import logging
import httpx
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class RSSDetector:
    """Détecter et parser les feeds RSS/Atom."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    async def detect_feeds(self, base_url: str) -> List[str]:
        """
        Détecter les feeds disponibles sur une URL.
        
        Args:
            base_url: URL de base du site
            
        Returns:
            Liste d'URLs de feeds RSS/Atom trouvés
        """
        feeds = []
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(base_url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Strategy 1: Chercher les liens RSS/Atom dans le HTML
                # <link rel="alternate" type="application/rss+xml" href="...">
                rss_links = soup.find_all('link', {
                    'type': lambda x: x and ('rss' in x.lower() or 'atom' in x.lower() or 'xml' in x.lower()),
                    'rel': lambda x: x and ('alternate' in x.lower() or 'feed' in x.lower())
                })
                
                for link in rss_links:
                    href = link.get('href')
                    if href:
                        feed_url = urljoin(base_url, href)
                        feeds.append(feed_url)
                        logger.info(f"[RSS Detector] Found feed link: {feed_url}")
                
                # Strategy 2: Chercher les liens avec href contenant "feed", "rss", "atom"
                feed_links = soup.find_all('a', href=re.compile(r'(feed|rss|atom)', re.I))
                for link in feed_links:
                    href = link.get('href')
                    if href:
                        feed_url = urljoin(base_url, href)
                        if feed_url not in feeds:
                            feeds.append(feed_url)
                            logger.info(f"[RSS Detector] Found feed link (pattern): {feed_url}")
                
                # Strategy 3: Essayer les URLs communes
                common_feeds = [
                    '/feed',
                    '/rss',
                    '/atom',
                    '/feed.xml',
                    '/rss.xml',
                    '/atom.xml',
                    '/feeds/all',
                    '/blog/feed',
                ]
                
                parsed_url = urlparse(base_url)
                base_path = f"{parsed_url.scheme}://{parsed_url.netloc}"
                
                for feed_path in common_feeds:
                    feed_url = urljoin(base_path, feed_path)
                    if feed_url not in feeds:
                        feeds.append(feed_url)
                        
        except Exception as e:
            logger.warning(f"[RSS Detector] Error detecting feeds on {base_url}: {e}")
            
        return feeds

    async def parse_feed(self, feed_url: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Parser un feed RSS/Atom.
        
        Args:
            feed_url: URL du feed RSS/Atom
            limit: Nombre maximum d'items à retourner
            
        Returns:
            Liste de dictionnaires avec les posts/articles
        """
        posts = []
        try:
            logger.info(f"[RSS Detector] Parsing feed: {feed_url}")
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(feed_url, headers=self.headers)
                response.raise_for_status()
                
                # Parser le feed avec feedparser
                feed = feedparser.parse(response.content)
                
                if feed.bozo and feed.bozo_exception:
                    logger.warning(f"[RSS Detector] Feed parsing warning: {feed.bozo_exception}")
                
                # Extraire les items
                for entry in feed.entries[:limit]:
                    try:
                        # Extraire les champs communs
                        title = entry.get('title', 'No title')
                        link = entry.get('link', '')
                        description = entry.get('description', '') or entry.get('summary', '')
                        
                        # Extraire la date
                        published = None
                        if hasattr(entry, 'published_parsed') and entry.published_parsed:
                            try:
                                published = datetime(*entry.published_parsed[:6]).isoformat()
                            except:
                                pass
                        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                            try:
                                published = datetime(*entry.updated_parsed[:6]).isoformat()
                            except:
                                pass
                        
                        # Extraire l'auteur
                        author = 'Unknown'
                        if hasattr(entry, 'author'):
                            author = entry.author
                        elif hasattr(entry, 'author_detail') and entry.author_detail.get('name'):
                            author = entry.author_detail['name']
                        
                        # Extraire le contenu complet si disponible
                        content = description
                        if hasattr(entry, 'content') and entry.content:
                            # Prendre le premier élément de contenu
                            content = entry.content[0].get('value', description)
                        
                        # Nettoyer le HTML du contenu si nécessaire
                        if content:
                            soup = BeautifulSoup(content, 'html.parser')
                            content = soup.get_text(separator=' ', strip=True)
                        
                        if link:
                            posts.append({
                                'source': self._extract_source_from_url(link),
                                'author': author,
                                'content': f"{title}\n\n{content}"[:1000],  # Limiter à 1000 caractères
                                'url': link,
                                'created_at': published,
                                'language': 'unknown'
                            })
                            
                    except Exception as e:
                        logger.debug(f"[RSS Detector] Error parsing feed entry: {e}")
                        continue
                
                logger.info(f"[RSS Detector] Parsed {len(posts)} items from feed {feed_url}")
                
        except Exception as e:
            logger.warning(f"[RSS Detector] Error parsing feed {feed_url}: {e}")
            
        return posts

    def _extract_source_from_url(self, url: str) -> str:
        """Extraire le nom de la source depuis l'URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Mapping des domaines vers les sources
            domain_mapping = {
                'reddit.com': 'reddit',
                'twitter.com': 'x',
                'x.com': 'x',
                'github.com': 'github',
                'stackoverflow.com': 'stackoverflow',
                'trustpilot.com': 'trustpilot',
                'community.ovh.com': 'ovh-forum',
            }
            
            for key, value in domain_mapping.items():
                if key in domain:
                    return value
                    
            # Extraire le nom de domaine principal
            parts = domain.split('.')
            if len(parts) >= 2:
                return parts[-2]
                
            return 'unknown'
        except:
            return 'unknown'


# Instance globale pour réutilisation
_rss_detector = RSSDetector()


async def detect_and_parse_feeds(base_url: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Détecter et parser les feeds RSS/Atom d'un site.
    
    Args:
        base_url: URL de base du site
        limit: Nombre maximum d'items à retourner
        
    Returns:
        Liste de posts trouvés dans les feeds
    """
    posts = []
    try:
        # Détecter les feeds
        feeds = await _rss_detector.detect_feeds(base_url)
        
        if not feeds:
            logger.info(f"[RSS Detector] No feeds detected on {base_url}")
            return []
        
        # Parser chaque feed trouvé
        for feed_url in feeds[:3]:  # Limiter à 3 feeds max
            try:
                feed_posts = await _rss_detector.parse_feed(feed_url, limit)
                posts.extend(feed_posts)
            except Exception as e:
                logger.debug(f"[RSS Detector] Failed to parse feed {feed_url}: {e}")
                continue
        
        # Dédupliquer par URL
        seen_urls = set()
        unique_posts = []
        for post in posts:
            if post['url'] not in seen_urls:
                seen_urls.add(post['url'])
                unique_posts.append(post)
        
        logger.info(f"[RSS Detector] Found {len(unique_posts)} unique posts from {len(feeds)} feeds")
        return unique_posts[:limit]
        
    except Exception as e:
        logger.warning(f"[RSS Detector] Error detecting/parsing feeds on {base_url}: {e}")
        return []

