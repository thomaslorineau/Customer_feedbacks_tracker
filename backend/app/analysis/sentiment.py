"""
Sentiment analysis module with improved French support.
Uses VADER for English and enhanced heuristics for French.
"""
import re
import logging
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

analyzer = SentimentIntensityAnalyzer()

# French negative words and phrases (to boost negative sentiment)
FRENCH_NEGATIVE_WORDS = {
    'mauvais', 'mauvaise', 'mal', 'problème', 'problèmes', 'dysfonctionnel', 'dysfonctionnelle',
    'défaillant', 'défaillante', 'erreur', 'erreurs', 'bug', 'bugs', 'panne', 'pannes',
    'lent', 'lente', 'lenteur', 'lenteurs', 'attente', 'attendre', 'attendu',
    'insatisfait', 'insatisfaite', 'insatisfaction', 'déçu', 'déçue', 'déception',
    'frustré', 'frustrée', 'frustration', 'énervé', 'énervée', 'énervant',
    'horrible', 'terrible', 'catastrophique', 'nul', 'nulle', 'nulle part',
    'impossible', 'inacceptable', 'inadmissible', 'ridicule', 'absurde',
    'complaint', 'plainte', 'plaintes', 'réclamation', 'réclamations',
    'remboursement', 'remboursements', 'facturé', 'facturée', 'double facturation',
    'expiré', 'expirée', 'expiration', 'offline', 'hors ligne', 'indisponible'
}

# French positive words and phrases
FRENCH_POSITIVE_WORDS = {
    'bon', 'bonne', 'bien', 'excellent', 'excellente', 'parfait', 'parfaite',
    'satisfait', 'satisfaite', 'satisfaction', 'content', 'contente', 'heureux', 'heureuse',
    'rapide', 'rapidement', 'efficace', 'efficacement', 'fonctionne', 'fonctionnel',
    'recommandé', 'recommandée', 'recommandation', 'merci', 'mercis', 'super', 'génial'
}

# French intensifiers (to boost sentiment strength)
FRENCH_INTENSIFIERS = {
    'très', 'vraiment', 'extrêmement', 'complètement', 'totalement', 'absolument',
    'énormément', 'beaucoup', 'trop', 'tellement', 'si', 'aussi'
}


def _detect_french_negative_score(text: str) -> float:
    """
    Calculate negative sentiment score for French text.
    Returns a score between -1.0 and 0.0.
    """
    text_lower = text.lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    
    # Count negative words
    negative_count = len(words & FRENCH_NEGATIVE_WORDS)
    
    # Check for intensifiers near negative words
    has_intensifier = any(intensifier in text_lower for intensifier in FRENCH_INTENSIFIERS)
    
    # Calculate base score
    if negative_count == 0:
        return 0.0
    
    # Base negative score (more negative words = more negative)
    base_score = -0.3 - (negative_count * 0.15)
    
    # Boost with intensifiers
    if has_intensifier:
        base_score *= 1.5
    
    # Check for explicit negative phrases
    negative_phrases = [
        'tout est mauvais', 'tout est mal', 'rien ne fonctionne', 'ne fonctionne pas',
        'ne marche pas', 'ça ne marche pas', 'c\'est nul', "c'est nul",
        'double facturé', 'double facturation', 'site offline', 'site hors ligne'
    ]
    
    for phrase in negative_phrases:
        if phrase in text_lower:
            base_score -= 0.2
    
    # Normalize to -1.0 to 0.0 range
    return max(-1.0, min(0.0, base_score))


def analyze(text: str, language: str = None) -> dict:
    """
    Analyze sentiment of text with improved French support.
    
    Args:
        text: Text to analyze
        language: Optional language code ('fr', 'en', etc.). If None, will try to detect.
    
    Returns:
        Dictionary with 'score' (float, -1.0 to 1.0) and 'label' ('positive', 'negative', 'neutral')
    """
    if not text:
        return {'score': 0.0, 'label': 'neutral'}
    
    # Detect language if not provided
    if not language:
        try:
            from .language_detection import detect_language
            language = detect_language(text)
        except Exception:
            language = 'unknown'
    
    # For French text, use enhanced detection
    if language == 'fr':
        # Try VADER first (sometimes works for French)
        vader_scores = analyzer.polarity_scores(text)
        vader_compound = vader_scores.get('compound', 0.0)
        
        # Calculate French-specific negative score
        french_negative = _detect_french_negative_score(text)
        
        # Combine VADER and French-specific scores
        # If both indicate negative, use the more negative one
        if vader_compound < 0 and french_negative < 0:
            compound = min(vader_compound, french_negative)
        elif french_negative < -0.3:  # Strong French negative signal
            compound = french_negative
        else:
            compound = vader_compound
        
        # Check for positive French words
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        positive_count = len(words & FRENCH_POSITIVE_WORDS)
        
        if positive_count > 0 and compound < 0:
            # Positive words might mitigate negativity
            compound = compound + (positive_count * 0.1)
        
        # Determine label
        if compound >= 0.05:
            label = 'positive'
        elif compound <= -0.05:
            label = 'negative'
        else:
            label = 'neutral'
        
        return {'score': compound, 'label': label}
    
    # For other languages, use standard VADER
    scores = analyzer.polarity_scores(text)
    compound = scores.get('compound', 0.0)
    
    if compound >= 0.05:
        label = 'positive'
    elif compound <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {'score': compound, 'label': label}
