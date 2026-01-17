"""
Système de scoring de pertinence pour déterminer si un post parle vraiment d'OVHCloud.
"""
import logging
import re
from typing import Dict

logger = logging.getLogger(__name__)

# Marques OVH
OVH_BRANDS = {
    'ovh', 'ovhcloud', 'ovh cloud', 'kimsufi', 'soyoustart',
    'runabove', 'hubic', 'ovh.com', 'ovhcloud.com'
}

# Produits OVH
OVH_PRODUCTS = {
    'vps', 'dedicated server', 'dedicated', 'hosting', 'domain',
    'email', 'public cloud', 'private cloud', 'object storage', 'cdn',
    'ssl', 'backup', 'storage'
}

# Direction OVH - Noms de dirigeants
OVH_LEADERSHIP_NAMES = {
    'michel paulin', 'michel-paulin',
    'octave klaba', 'octave-klaba',
    'henryk klaba', 'henryk-klaba',
    'klaba family', 'famille klaba'
}

# Direction OVH - Titres/rôles
OVH_LEADERSHIP_TITLES = {
    'ceo ovh', 'ovh ceo', 'pdg ovh', 'ovh pdg',
    'founder ovh', 'ovh founder', 'fondateur ovh',
    'ovh management', 'ovh direction', 'ovh executives',
    'ovh leadership', 'dirigeant ovh', 'ovh dirigeant'
}

# Patterns de faux positifs
FALSE_POSITIVE_PATTERNS = [
    r'\bovh\b.*(?:not|isn\'t|wasn\'t).*ovh',  # "OVH is not..."
    r'(?:other|different|another).*ovh',  # "other OVH..."
    r'ovh.*(?:competitor|alternative|vs|versus)',  # Comparaisons
]


def calculate_relevance_score(post: Dict) -> float:
    """
    Calcule un score de pertinence 0-1 pour déterminer si un post parle vraiment d'OVHCloud.
    
    Critères:
    - Présence de marques OVH (40% du score)
    - URL OVH (30% du score)
    - Direction OVH (20% du score) - NOUVEAU
    - Produits OVH (10% du score)
    
    Args:
        post: Dict avec 'content', 'url', 'author'
    
    Returns:
        Score de pertinence entre 0.0 et 1.0
    """
    content = (post.get('content', '') or '').lower()
    url = (post.get('url', '') or '').lower()
    author = (post.get('author', '') or '').lower()
    
    score = 0.0
    
    # 1. Marques OVH (40% du score)
    brand_matches = sum(1 for brand in OVH_BRANDS if brand in content)
    if brand_matches > 0:
        score += 0.4 * min(brand_matches / 2, 1.0)  # Max 0.4
    
    # 2. URL OVH (30% du score)
    if any(brand in url for brand in OVH_BRANDS):
        score += 0.3
    
    # 3. Direction OVH (20% du score) - NOUVEAU
    leadership_score = 0.0
    
    # Noms de dirigeants
    for name in OVH_LEADERSHIP_NAMES:
        if name in content:
            leadership_score += 0.1
    
    # Titres/rôles
    for title in OVH_LEADERSHIP_TITLES:
        if title in content:
            leadership_score += 0.1
    
    # Si mention direction + marque OVH = très pertinent
    if leadership_score > 0 and brand_matches > 0:
        score += 0.2 * min(leadership_score, 1.0)
    elif leadership_score > 0:
        # Mention direction seule = modérément pertinent
        score += 0.1 * min(leadership_score, 1.0)
    
    # 4. Produits OVH (10% du score)
    product_matches = sum(1 for product in OVH_PRODUCTS if product in content)
    if product_matches > 0 and brand_matches > 0:  # Produit + marque = plus pertinent
        score += 0.1 * min(product_matches / 3, 1.0)
    
    return min(score, 1.0)


def is_false_positive(post: Dict) -> bool:
    """
    Détecte les faux positifs (posts qui mentionnent "OVH" mais dans un autre contexte).
    
    Args:
        post: Dict avec 'content'
    
    Returns:
        True si c'est probablement un faux positif
    """
    content = (post.get('content', '') or '').lower()
    
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            return True
    
    return False


def is_relevant(post: Dict, threshold: float = 0.3) -> bool:
    """
    Détermine si un post est pertinent pour OVHCloud.
    
    Args:
        post: Dict avec 'content', 'url', 'author'
        threshold: Seuil de pertinence (défaut 0.3)
    
    Returns:
        True si le post est pertinent, False sinon
    """
    # Vérifier d'abord les faux positifs
    if is_false_positive(post):
        return False
    
    # Calculer le score de pertinence
    score = calculate_relevance_score(post)
    
    return score >= threshold


