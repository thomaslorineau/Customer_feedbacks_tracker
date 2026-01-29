"""
Sentiment analysis module with improved French support.
Uses VADER for English and enhanced heuristics for French.
"""
import re
import logging
from typing import List, Optional
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

# French reversal words (indicate sentiment change)
FRENCH_REVERSAL_WORDS = {
    'mais', 'cependant', 'par contre', 'toutefois', 'néanmoins', 'en revanche',
    'malgré', 'malgré tout', 'quand même', 'tout de même'
}


def _split_into_segments(text: str) -> List[str]:
    """
    Split text into sentences/segments based on punctuation.
    
    Args:
        text: Text to split
        
    Returns:
        List of sentence segments (non-empty)
    """
    if not text:
        return []
    
    # Split by sentence-ending punctuation: . ! ?
    # Use regex to split but keep punctuation
    segments = re.split(r'([.!?]+)', text)
    
    # Recombine segments with their punctuation
    result = []
    i = 0
    while i < len(segments):
        segment = segments[i].strip()
        # If next element is punctuation, add it to the segment
        if i + 1 < len(segments) and re.match(r'^[.!?]+$', segments[i + 1]):
            segment += segments[i + 1]
            i += 2
        else:
            i += 1
        
        if segment:
            result.append(segment)
    
    # If no punctuation found, return the whole text as one segment
    if not result:
        return [text.strip()] if text.strip() else []
    
    return result


def _detect_sentiment_reversal(text: str) -> Optional[int]:
    """
    Detect the position of the first sentiment reversal word in the text.
    
    Args:
        text: Text to analyze
        
    Returns:
        Index of the segment containing the reversal word, or None if not found
    """
    segments = _split_into_segments(text)
    text_lower = text.lower()
    
    # Sort reversal words by length (longest first) to match multi-word phrases first
    sorted_reversals = sorted(FRENCH_REVERSAL_WORDS, key=len, reverse=True)
    
    # Find the position of the first reversal word/phrase
    for reversal_word in sorted_reversals:
        # For multi-word phrases, use simple string search
        # For single words, use word boundary regex
        if ' ' in reversal_word:
            # Multi-word phrase: search for exact phrase
            pos = text_lower.find(reversal_word)
        else:
            # Single word: use word boundary regex
            pattern = r'\b' + re.escape(reversal_word) + r'\b'
            match = re.search(pattern, text_lower)
            pos = match.start() if match else -1
        
        if pos != -1:
            # Find which segment contains this position
            current_pos = 0
            for idx, segment in enumerate(segments):
                segment_end = current_pos + len(segment)
                if current_pos <= pos < segment_end:
                    return idx
                current_pos = segment_end
    
    return None


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


def _analyze_segment_sentiment(segment: str, language: str = 'fr') -> dict:
    """
    Analyze sentiment of a single segment using VADER and French heuristics.
    
    Args:
        segment: Text segment to analyze
        language: Language code
        
    Returns:
        Dictionary with 'score' and 'label'
    """
    if not segment.strip():
        return {'score': 0.0, 'label': 'neutral'}
    
    # Use VADER
    vader_scores = analyzer.polarity_scores(segment)
    vader_compound = vader_scores.get('compound', 0.0)
    
    if language == 'fr':
        # Calculate French-specific negative score
        french_negative = _detect_french_negative_score(segment)
        
        # Combine VADER and French-specific scores
        if vader_compound < 0 and french_negative < 0:
            compound = min(vader_compound, french_negative)
        elif french_negative < -0.3:
            compound = french_negative
        else:
            compound = vader_compound
        
        # Check for positive French words
        text_lower = segment.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        positive_count = len(words & FRENCH_POSITIVE_WORDS)
        
        if positive_count > 0 and compound < 0:
            compound = compound + (positive_count * 0.1)
    else:
        compound = vader_compound
    
    # Determine label
    if compound >= 0.05:
        label = 'positive'
    elif compound <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {'score': compound, 'label': label}


def _apply_reversal_logic(segments: List[str], reversal_pos: Optional[int], language: str = 'fr') -> dict:
    """
    Apply sentiment reversal logic when a reversal word is detected.
    
    Args:
        segments: List of text segments
        reversal_pos: Index of segment containing reversal word (None if not found)
        language: Language code
        
    Returns:
        Dictionary with 'score' and 'label'
    """
    if not segments:
        return {'score': 0.0, 'label': 'neutral'}
    
    if reversal_pos is None:
        # No reversal detected, use standard weighted analysis
        # Reconstruct text from segments for _analyze_with_segments
        text = ' '.join(segments)
        return _analyze_with_segments(text, language, apply_reversal=False)
    
    # Analyze each segment
    segment_scores = []
    for segment in segments:
        result = _analyze_segment_sentiment(segment, language)
        segment_scores.append(result['score'])
    
    # Apply reversal logic: reduce weight before reversal, increase after
    weighted_scores = []
    total_weight = 0.0
    
    for idx, score in enumerate(segment_scores):
        if idx < reversal_pos:
            # Before reversal: reduce weight (x0.3)
            weight = 0.3
        elif idx == reversal_pos:
            # Segment with reversal: normal weight but boost positive sentiment
            weight = 1.0
            if score < 0:
                # If negative, reduce it further
                score = score * 0.5
        else:
            # After reversal: increase weight (x1.5)
            weight = 1.5
            if score > 0:
                # Boost positive sentiment after reversal
                score = score * 1.2
        
        weighted_scores.append(score * weight)
        total_weight += weight
    
    # Calculate weighted average
    if total_weight > 0:
        final_score = sum(weighted_scores) / total_weight
    else:
        final_score = sum(segment_scores) / len(segment_scores) if segment_scores else 0.0
    
    # Determine label
    if final_score >= 0.05:
        label = 'positive'
    elif final_score <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {'score': final_score, 'label': label}


def _analyze_with_segments(text: str, language: str = 'fr', apply_reversal: bool = True) -> dict:
    """
    Analyze sentiment by splitting text into segments with temporal weighting.
    
    Args:
        text: Text to analyze
        language: Language code
        apply_reversal: Whether to apply reversal logic
        
    Returns:
        Dictionary with 'score' and 'label'
    """
    if not text:
        return {'score': 0.0, 'label': 'neutral'}
    
    segments = _split_into_segments(text)
    if not segments:
        return {'score': 0.0, 'label': 'neutral'}
    
    # If only one segment, use standard analysis
    if len(segments) == 1:
        return _analyze_segment_sentiment(segments[0], language)
    
    # Detect reversal if requested
    reversal_pos = None
    if apply_reversal:
        reversal_pos = _detect_sentiment_reversal(text)
        if reversal_pos is not None:
            return _apply_reversal_logic(segments, reversal_pos, language)
    
    # Analyze each segment
    segment_scores = []
    for segment in segments:
        result = _analyze_segment_sentiment(segment, language)
        segment_scores.append(result['score'])
    
    # Apply temporal weighting: later segments have more weight (1.5x for last segment)
    num_segments = len(segments)
    weighted_scores = []
    total_weight = 0.0
    
    for idx, score in enumerate(segment_scores):
        # Last segment gets 1.5x weight, others get 1.0x
        if idx == num_segments - 1:
            weight = 1.5
        else:
            weight = 1.0
        
        weighted_scores.append(score * weight)
        total_weight += weight
    
    # Calculate weighted average
    final_score = sum(weighted_scores) / total_weight
    
    # Determine label
    if final_score >= 0.05:
        label = 'positive'
    elif final_score <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {'score': final_score, 'label': label}


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
    
    # For French text, use hybrid analysis (segments + reversal detection + temporal weighting)
    if language == 'fr':
        try:
            # Use hybrid analysis with segment-based approach and reversal detection
            return _analyze_with_segments(text, language='fr', apply_reversal=True)
        except Exception as e:
            logger.warning(f"Error in hybrid sentiment analysis, falling back to standard: {e}")
            # Fallback to standard VADER + French heuristics
            vader_scores = analyzer.polarity_scores(text)
            vader_compound = vader_scores.get('compound', 0.0)
            
            french_negative = _detect_french_negative_score(text)
            
            if vader_compound < 0 and french_negative < 0:
                compound = min(vader_compound, french_negative)
            elif french_negative < -0.3:
                compound = french_negative
            else:
                compound = vader_compound
            
            text_lower = text.lower()
            words = set(re.findall(r'\b\w+\b', text_lower))
            positive_count = len(words & FRENCH_POSITIVE_WORDS)
            
            if positive_count > 0 and compound < 0:
                compound = compound + (positive_count * 0.1)
            
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
