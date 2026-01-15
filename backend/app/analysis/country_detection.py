"""
Country detection module for posts.
Uses multiple heuristics to identify the country of origin.
"""
import re
from typing import Optional

# Mapping langue → pays probables (par défaut)
LANGUAGE_TO_DEFAULT_COUNTRY = {
    'fr': 'FR',  # Français → France par défaut
    'en': 'US',  # Anglais → USA par défaut
    'de': 'DE',  # Allemand → Allemagne
    'es': 'ES',  # Espagnol → Espagne
    'it': 'IT',  # Italien → Italie
    'pt': 'PT',  # Portugais → Portugal
    'nl': 'NL',  # Néerlandais → Pays-Bas
    'pl': 'PL',  # Polonais → Pologne
    'ru': 'RU',  # Russe → Russie
    'ja': 'JP',  # Japonais → Japon
    'zh': 'CN',  # Chinois → Chine
}

# Mots-clés de pays/villes → code pays ISO 3166-1 alpha-2
COUNTRY_KEYWORDS = {
    # France
    'france': 'FR', 'paris': 'FR', 'lyon': 'FR', 'marseille': 'FR', 
    'toulouse': 'FR', 'nice': 'FR', 'nantes': 'FR', 'strasbourg': 'FR',
    'bordeaux': 'FR', 'lille': 'FR', 'rennes': 'FR', 'reims': 'FR',
    'french': 'FR', 'français': 'FR', 'francais': 'FR',
    
    # États-Unis
    'united states': 'US', 'usa': 'US', 'u.s.': 'US', 'u.s.a.': 'US',
    'new york': 'US', 'california': 'US', 'texas': 'US', 'florida': 'US',
    'chicago': 'US', 'los angeles': 'US', 'san francisco': 'US',
    'boston': 'US', 'seattle': 'US', 'miami': 'US', 'atlanta': 'US',
    'american': 'US',
    
    # Royaume-Uni
    'united kingdom': 'GB', 'uk': 'GB', 'u.k.': 'GB', 'britain': 'GB',
    'london': 'GB', 'england': 'GB', 'scotland': 'GB', 'wales': 'GB',
    'manchester': 'GB', 'birmingham': 'GB', 'liverpool': 'GB',
    'british': 'GB', 'anglais': 'GB',
    
    # Canada
    'canada': 'CA', 'toronto': 'CA', 'montreal': 'CA', 'montréal': 'CA',
    'vancouver': 'CA', 'ottawa': 'CA', 'calgary': 'CA', 'edmonton': 'CA',
    'quebec': 'CA', 'canadian': 'CA', 'canadien': 'CA',
    
    # Belgique
    'belgium': 'BE', 'belgique': 'BE', 'brussels': 'BE', 'bruxelles': 'BE',
    'antwerp': 'BE', 'ghent': 'BE', 'belgian': 'BE', 'belge': 'BE',
    
    # Suisse
    'switzerland': 'CH', 'suisse': 'CH', 'schweiz': 'CH', 'svizzera': 'CH',
    'zurich': 'CH', 'zürich': 'CH', 'geneva': 'CH', 'genève': 'CH',
    'bern': 'CH', 'basel': 'CH', 'bâle': 'CH', 'swiss': 'CH',
    
    # Allemagne
    'germany': 'DE', 'deutschland': 'DE', 'berlin': 'DE', 'munich': 'DE',
    'münchen': 'DE', 'hamburg': 'DE', 'frankfurt': 'DE', 'cologne': 'DE',
    'köln': 'DE', 'stuttgart': 'DE', 'düsseldorf': 'DE', 'german': 'DE',
    'allemand': 'DE',
    
    # Espagne
    'spain': 'ES', 'espana': 'ES', 'espagne': 'ES', 'madrid': 'ES',
    'barcelona': 'ES', 'barcelone': 'ES', 'valencia': 'ES', 'seville': 'ES',
    'séville': 'ES', 'spanish': 'ES', 'espagnol': 'ES',
    
    # Italie
    'italy': 'IT', 'italia': 'IT', 'italie': 'IT', 'rome': 'IT',
    'roma': 'IT', 'milan': 'IT', 'milano': 'IT', 'naples': 'IT',
    'napoli': 'IT', 'turin': 'IT', 'torino': 'IT', 'italian': 'IT',
    'italien': 'IT',
    
    # Pays-Bas
    'netherlands': 'NL', 'holland': 'NL', 'pays-bas': 'NL', 'amsterdam': 'NL',
    'rotterdam': 'NL', 'the hague': 'NL', 'la haye': 'NL', 'utrecht': 'NL',
    'dutch': 'NL', 'néerlandais': 'NL',
    
    # Autres pays européens
    'poland': 'PL', 'pologne': 'PL', 'warsaw': 'PL', 'varsovie': 'PL',
    'portugal': 'PT', 'lisbon': 'PT', 'lisbonne': 'PT', 'portugais': 'PT',
    'austria': 'AT', 'autriche': 'AT', 'vienna': 'AT', 'vienne': 'AT',
    'sweden': 'SE', 'suède': 'SE', 'stockholm': 'SE',
    'norway': 'NO', 'norvège': 'NO', 'oslo': 'NO',
    'denmark': 'DK', 'danemark': 'DK', 'copenhagen': 'DK', 'copenhague': 'DK',
    'finland': 'FI', 'finlande': 'FI', 'helsinki': 'FI',
    'ireland': 'IE', 'irlande': 'IE', 'dublin': 'IE',
    
    # Autres pays
    'australia': 'AU', 'australie': 'AU', 'sydney': 'AU', 'melbourne': 'AU',
    'new zealand': 'NZ', 'nouvelle-zélande': 'NZ', 'auckland': 'NZ',
    'south africa': 'ZA', 'afrique du sud': 'ZA', 'cape town': 'ZA',
    'japan': 'JP', 'japon': 'JP', 'tokyo': 'JP',
    'china': 'CN', 'chine': 'CN', 'beijing': 'CN', 'pekin': 'CN',
    'singapore': 'SG', 'singapour': 'SG',
    'brazil': 'BR', 'brésil': 'BR', 'brasil': 'BR', 'sao paulo': 'BR',
    'mexico': 'MX', 'mexique': 'MX', 'mexico city': 'MX',
    'argentina': 'AR', 'argentine': 'AR', 'buenos aires': 'AR',
}

# Subreddits Reddit → pays
REDDIT_SUBREDDITS = {
    'france': 'FR',
    'canada': 'CA',
    'unitedkingdom': 'GB',
    'uk': 'GB',
    'de': 'DE',
    'spain': 'ES',
    'italy': 'IT',
    'netherlands': 'NL',
    'australia': 'AU',
    'newzealand': 'NZ',
    'brasil': 'BR',
    'mexico': 'MX',
    'argentina': 'AR',
    'poland': 'PL',
    'portugal': 'PT',
    'belgium': 'BE',
    'switzerland': 'CH',
}


def detect_country_from_post(post: dict) -> Optional[str]:
    """
    Détecte le pays d'origine d'un post en utilisant plusieurs heuristiques.
    Retourne un code pays ISO 3166-1 alpha-2 (ex: 'FR', 'US', 'GB').
    Retourne None si aucun pays ne peut être déterminé.
    """
    content = (post.get('content', '') or '').lower()
    language = post.get('language', 'unknown')
    source = post.get('source', '')
    author = post.get('author', '')
    url = (post.get('url', '') or '').lower()
    
    # 1. Détection par subreddit (Reddit) - très fiable
    if source == 'Reddit' or 'reddit.com' in url:
        for subreddit, country_code in REDDIT_SUBREDDITS.items():
            if f'/r/{subreddit}' in url or f'r/{subreddit}' in content:
                return country_code
    
    # 2. Détection par mentions de pays/villes dans le contenu
    for keyword, country_code in COUNTRY_KEYWORDS.items():
        # Recherche de mots complets (pas de sous-chaînes)
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, content, re.IGNORECASE):
            return country_code
    
    # 3. Détection par devise
    if '€' in content or 'euro' in content or 'eur' in content:
        # Probablement Europe, affiner avec langue
        if language == 'fr':
            # Français + € → probablement France, mais pourrait être BE, CH, CA
            # Vérifier s'il y a des indices belges/suisses
            if any(kw in content for kw in ['belgique', 'belgium', 'bruxelles', 'brussels']):
                return 'BE'
            elif any(kw in content for kw in ['suisse', 'switzerland', 'zurich', 'genève']):
                return 'CH'
            elif any(kw in content for kw in ['canada', 'montreal', 'quebec', 'toronto']):
                return 'CA'
            return 'FR'
        elif language == 'de':
            return 'DE'
        elif language == 'es':
            return 'ES'
        elif language == 'it':
            return 'IT'
        elif language == 'nl':
            return 'NL'
        # Don't return 'EU' - try to be more specific based on language
        # If we can't determine, return None
        return None
    elif '$' in content:
        # Dollar - vérifier si c'est USD, CAD, AUD
        if any(kw in content for kw in ['cad', 'canadian dollar', 'canada']):
            return 'CA'
        elif any(kw in content for kw in ['aud', 'australian dollar', 'australia']):
            return 'AU'
        elif language == 'fr' and any(kw in content for kw in ['canada', 'montreal', 'quebec']):
            return 'CA'
        return 'US'  # Par défaut USD
    elif '£' in content or 'pound' in content or 'gbp' in content:
        return 'GB'
    elif '¥' in content or 'yen' in content:
        return 'JP'
    elif 'chf' in content or 'franc suisse' in content:
        return 'CH'
    
    # 4. Détection par format de date (heuristique faible)
    # DD/MM/YYYY → probablement Europe
    if re.search(r'\d{1,2}/\d{1,2}/\d{4}', content):
        if language == 'fr':
            return 'FR'
        elif language == 'en':
            # UK utilise aussi DD/MM/YYYY
            if any(kw in content for kw in ['uk', 'britain', 'london']):
                return 'GB'
            return 'US'  # Par défaut
    
    # 5. Détection par langue (fallback)
    # Utiliser le mapping langue → pays par défaut
    if language in LANGUAGE_TO_DEFAULT_COUNTRY:
        return LANGUAGE_TO_DEFAULT_COUNTRY[language]
    
    # 6. Détection par source spécifique
    if source == 'Trustpilot':
        # Trustpilot peut avoir des indices dans l'URL
        # Ex: trustpilot.com/review/ovh.fr → France
        if '.fr' in url:
            return 'FR'
        elif '.com' in url and 'ca' in url:
            return 'CA'
        elif '.co.uk' in url:
            return 'GB'
        elif '.de' in url:
            return 'DE'
        elif '.es' in url:
            return 'ES'
        elif '.it' in url:
            return 'IT'
    
    # Aucun pays détecté
    return None


def get_country_name(country_code: str) -> str:
    """Convertit un code pays ISO en nom complet."""
    country_names = {
        'FR': 'France',
        'US': 'United States',
        'GB': 'United Kingdom',
        'CA': 'Canada',
        'BE': 'Belgium',
        'CH': 'Switzerland',
        'DE': 'Germany',
        'ES': 'Spain',
        'IT': 'Italy',
        'NL': 'Netherlands',
        'PL': 'Poland',
        'PT': 'Portugal',
        'AT': 'Austria',
        'SE': 'Sweden',
        'NO': 'Norway',
        'DK': 'Denmark',
        'FI': 'Finland',
        'IE': 'Ireland',
        'AU': 'Australia',
        'NZ': 'New Zealand',
        'ZA': 'South Africa',
        'JP': 'Japan',
        'CN': 'China',
        'SG': 'Singapore',
        'BR': 'Brazil',
        'MX': 'Mexico',
        'AR': 'Argentina',
        'EU': 'Europe',
    }
    return country_names.get(country_code, country_code)

