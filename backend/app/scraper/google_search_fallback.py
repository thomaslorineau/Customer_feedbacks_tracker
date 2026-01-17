"""
Google Search Fallback - Universal fallback scraper via Google Search.

This module provides a generic fallback mechanism to search specific sites
via Google Search when primary scraping methods fail.
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus, urlparse
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class GoogleSearchFallback:
    """Fallback universel via Google Search."""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    async def search(self, site: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Rechercher sur un site spécifique via Google.
        
        Args:
            site: Domaine du site (ex: "site:reddit.com")
            query: Terme de recherche
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de dictionnaires avec les résultats
        """
        try:
            # Construire la requête Google Search
            search_query = f"{site} {query}"
            encoded_query = quote_plus(search_query)
            
            # Utiliser Google Search (sans API, scraping HTML)
            search_url = f"https://www.google.com/search?q={encoded_query}&num={min(limit, 100)}"
            
            logger.info(f"[Google Search Fallback] Searching: {search_query}")
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(search_url, headers=self.headers)
                response.raise_for_status()
                
                # Parser les résultats Google
                results = await self.parse_google_results(response.text, limit)
                
                # Récupérer le contenu réel depuis chaque URL trouvée
                posts = []
                for result in results[:limit]:
                    try:
                        content = await self.fetch_result_content(result['url'])
                        if content:
                            posts.append({
                                'source': self._extract_source_from_url(result['url']),
                                'author': result.get('author', 'Unknown'),
                                'content': content[:1000],  # Limiter à 1000 caractères
                                'url': result['url'],
                                'created_at': result.get('created_at'),
                                'language': 'unknown'
                            })
                    except Exception as e:
                        logger.debug(f"[Google Search Fallback] Failed to fetch content from {result['url']}: {e}")
                        continue
                
                logger.info(f"[Google Search Fallback] Found {len(posts)} posts via Google Search")
                return posts
                
        except Exception as e:
            logger.warning(f"[Google Search Fallback] Error searching {site} for '{query}': {e}")
            return []

    async def parse_google_results(self, html: str, limit: int) -> List[Dict[str, Any]]:
        """
        Parser les résultats Google depuis le HTML.
        
        Args:
            html: HTML de la page de résultats Google
            limit: Nombre maximum de résultats
            
        Returns:
            Liste de dictionnaires avec url, title, snippet
        """
        results = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Google Search results are typically in divs with class "g"
            result_divs = soup.find_all('div', class_='g')[:limit]
            
            for div in result_divs:
                try:
                    # Extract URL
                    link = div.find('a', href=True)
                    if not link:
                        continue
                    
                    url = link['href']
                    # Google sometimes prefixes URLs with /url?q=
                    if url.startswith('/url?q='):
                        url = url.split('/url?q=')[1].split('&')[0]
                    
                    # Extract title
                    title_elem = div.find('h3')
                    title = title_elem.get_text(strip=True) if title_elem else 'No title'
                    
                    # Extract snippet
                    snippet_elem = div.find('span', class_='aCOpRe') or div.find('div', class_='VwiC3b')
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    
                    if url and url.startswith('http'):
                        results.append({
                            'url': url,
                            'title': title,
                            'snippet': snippet,
                            'author': self._extract_author_from_title(title),
                            'created_at': None  # Google doesn't provide dates in search results
                        })
                except Exception as e:
                    logger.debug(f"[Google Search Fallback] Error parsing result: {e}")
                    continue
                    
        except Exception as e:
            logger.warning(f"[Google Search Fallback] Error parsing Google results: {e}")
            
        return results

    async def fetch_result_content(self, url: str) -> Optional[str]:
        """
        Récupérer le contenu réel depuis l'URL trouvée.
        
        Args:
            url: URL à récupérer
            
        Returns:
            Contenu textuel de la page ou None
        """
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Essayer de trouver le contenu principal
                # Différentes stratégies selon le site
                content = None
                
                # Strategy 1: Article content
                article = soup.find('article')
                if article:
                    content = article.get_text(separator=' ', strip=True)
                
                # Strategy 2: Main content divs
                if not content:
                    main_content = soup.find('main') or soup.find('div', class_=re.compile(r'content|post|body', re.I))
                    if main_content:
                        content = main_content.get_text(separator=' ', strip=True)
                
                # Strategy 3: Body text (fallback)
                if not content:
                    body = soup.find('body')
                    if body:
                        # Remove script and style elements
                        for script in body(["script", "style", "nav", "header", "footer"]):
                            script.decompose()
                        content = body.get_text(separator=' ', strip=True)
                
                # Limiter la longueur
                if content:
                    content = content[:2000]  # Max 2000 caractères
                    
                return content
                
        except Exception as e:
            logger.debug(f"[Google Search Fallback] Failed to fetch content from {url}: {e}")
            return None

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
                return parts[-2]  # Ex: "reddit" depuis "www.reddit.com"
                
            return 'unknown'
        except:
            return 'unknown'

    def _extract_author_from_title(self, title: str) -> str:
        """Essayer d'extraire l'auteur depuis le titre."""
        # Patterns communs: "Author: Title" ou "Title - Author"
        patterns = [
            r'^(.+?):\s',  # "Author: Title"
            r'\s-\s(.+?)$',  # "Title - Author"
            r'by\s+(.+?)$',  # "Title by Author"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1).strip()
                
        return 'Unknown'


# Instance globale pour réutilisation
_google_search_fallback = GoogleSearchFallback()


async def search_via_google(site: str, query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Fonction helper pour rechercher via Google Search.
    
    Args:
        site: Domaine du site (ex: "site:reddit.com")
        query: Terme de recherche
        limit: Nombre maximum de résultats
        
    Returns:
        Liste de posts trouvés
    """
    return await _google_search_fallback.search(site, query, limit)

