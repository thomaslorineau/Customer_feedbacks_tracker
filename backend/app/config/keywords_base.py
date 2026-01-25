"""
Base de keywords fixe et fiable pour la collecte de données OVHCloud.
Ces keywords sont toujours utilisés, même si l'utilisateur n'en ajoute pas.
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Valeurs par défaut (utilisées si pas de base en DB)
DEFAULT_BRAND_KEYWORDS = [
    "OVH",
    "OVHCloud",
    "OVH Cloud",
    "ovhcloud",
    "ovh cloud",
    "Kimsufi"
]

# Produits OVHcloud.com (liste condensée - produits essentiels uniquement)
DEFAULT_PRODUCT_KEYWORDS = [
    # Core Products (les plus recherchés)
    "OVH domain",
    "OVH hosting",
    "OVH VPS",
    "OVH dedicated",
    "OVH cloud",
    
    # Infrastructure essentielle
    "OVH server",
    "OVH storage",
    "OVH backup",
    
    # Services critiques
    "OVH email",
    "OVH SSL",
    "OVH CDN",
    
    # Support & Billing (utile pour produits spécifiques)
    "OVH support",
    "OVH billing"
]

DEFAULT_PROBLEM_KEYWORDS = [
    "OVH complaint",
    "OVH problem",
    "OVH issue",
    "OVH error",
    "OVH down",
    "OVH outage",
    "OVH slow",
    "OVH support",
    "OVH billing issue",
    "OVH refund"
]

# Direction OVH (liste condensée - dirigeants principaux et termes génériques)
DEFAULT_LEADERSHIP_KEYWORDS = [
    # Dirigeants principaux
    "Michel Paulin",
    "Michel Paulin OVH",
    "Octave Klaba",
    "Octave Klaba OVH",
    
    # Termes génériques (couvrent tous les dirigeants)
    "OVH CEO",
    "OVH founder",
    "OVH management",
    "OVH direction"
]


def get_base_keywords_from_db() -> Dict[str, List[str]]:
    """
    Récupère la base de keywords depuis la DB.
    Si la table n'existe pas ou est vide, retourne les valeurs par défaut.
    """
    try:
        from .. import database as db
        
        conn, _ = db.get_db_connection()
        c = conn.cursor()
        
        # Vérifier si la table existe
        try:
            c.execute("SELECT category, keyword FROM base_keywords ORDER BY category, id")
            rows = c.fetchall()
            conn.close()
            
            if rows:
                # Organiser par catégorie
                result = {
                    'brands': [],
                    'products': [],
                    'problems': [],
                    'leadership': []
                }
                for category, keyword in rows:
                    if category in result:
                        result[category].append(keyword)
                return result
        except Exception:
            # Table n'existe pas encore, retourner defaults
            pass
        
        conn.close()
    except Exception as e:
        logger.warning(f"Could not load base keywords from DB: {e}, using defaults")
    
    # Retourner les valeurs par défaut
    return {
        'brands': DEFAULT_BRAND_KEYWORDS.copy(),
        'products': DEFAULT_PRODUCT_KEYWORDS.copy(),
        'problems': DEFAULT_PROBLEM_KEYWORDS.copy(),
        'leadership': DEFAULT_LEADERSHIP_KEYWORDS.copy()
    }


def get_all_base_keywords() -> List[str]:
    """
    Retourne la liste complète des keywords de base (toutes catégories).
    """
    base = get_base_keywords_from_db()
    all_keywords = []
    for category in base.values():
        all_keywords.extend(category)
    return list(set(all_keywords))  # Dédupliquer


def get_all_keywords(user_keywords: List[str] = None) -> List[str]:
    """
    Combine les keywords de base (fixes) avec les keywords utilisateur.
    
    Args:
        user_keywords: Keywords ajoutés par l'utilisateur (optionnel)
    
    Returns:
        Liste complète des keywords à utiliser pour le scraping
    """
    base = get_all_base_keywords()
    user = user_keywords or []
    
    # Combiner et dédupliquer
    all_keywords = list(set(base + user))
    
    logger.debug(f"Combined keywords: {len(base)} base + {len(user)} user = {len(all_keywords)} total")
    
    return all_keywords


def save_base_keywords(keywords_by_category: Dict[str, List[str]]) -> bool:
    """
    Sauvegarde la base de keywords dans la DB.
    
    Args:
        keywords_by_category: Dict avec clés 'brands', 'products', 'problems', 'leadership'
    
    Returns:
        True si succès, False sinon
    """
    try:
        from .. import database as db
        
        conn, _ = db.get_db_connection()
        c = conn.cursor()
        
        # Vider la table
        c.execute("DELETE FROM base_keywords")
        
        # Insérer les nouveaux keywords
        for category, keywords in keywords_by_category.items():
            for keyword in keywords:
                if keyword and keyword.strip():
                    c.execute(
                        "INSERT INTO base_keywords (category, keyword) VALUES (?, ?)",
                        (category, keyword.strip())
                    )
        
        conn.commit()
        conn.close()
        
        logger.info(f"Saved base keywords: {sum(len(kw) for kw in keywords_by_category.values())} total")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save base keywords: {e}")
        return False

