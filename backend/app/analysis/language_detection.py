"""
Language detection module for posts.
Uses multiple methods to detect language with high accuracy.

Priority order:
1. TextBlob (if available)
2. Google Translate API (if GOOGLE_API_KEY configured)
3. DeepL API (if DEEPL_API_KEY configured)
4. LLM (OpenAI/Anthropic) (if configured)
5. Keyword-based detection (fallback)
6. Character-based heuristics
"""
import re
import logging
import os
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# Common words in different languages (for fallback detection)
FRENCH_WORDS = {
    'le', 'la', 'les', 'de', 'du', 'des', 'et', 'que', 'qui', 'est', 'pas', 'à', 'pour',
    'un', 'une', 'dans', 'sur', 'avec', 'par', 'sont', 'cette', 'ces', 'être', 'avoir',
    'il', 'elle', 'nous', 'vous', 'ils', 'elles', 'mais', 'ou', 'donc', 'car', 'comme',
    'très', 'plus', 'moins', 'tout', 'tous', 'toute', 'toutes', 'bien', 'mal', 'bon',
    'mauvais', 'grand', 'petit', 'nouveau', 'vieux', 'français', 'france', 'français'
}

ENGLISH_WORDS = {
    'the', 'and', 'is', 'to', 'of', 'in', 'a', 'that', 'it', 'you', 'he', 'she', 'we',
    'they', 'this', 'these', 'those', 'but', 'or', 'so', 'because', 'as', 'very',
    'more', 'less', 'all', 'good', 'bad', 'big', 'small', 'new', 'old', 'english',
    'america', 'american', 'british', 'uk', 'usa'
}

GERMAN_WORDS = {
    'der', 'die', 'das', 'und', 'ist', 'zu', 'von', 'in', 'mit', 'für', 'auf', 'sind',
    'eine', 'ein', 'nicht', 'sie', 'er', 'wir', 'ihr', 'deutsch', 'deutschland'
}

SPANISH_WORDS = {
    'el', 'la', 'los', 'las', 'de', 'del', 'y', 'que', 'es', 'en', 'un', 'una', 'con',
    'por', 'para', 'son', 'esta', 'estos', 'español', 'españa'
}

ITALIAN_WORDS = {
    'il', 'la', 'lo', 'gli', 'le', 'di', 'del', 'e', 'che', 'è', 'in', 'un', 'una',
    'con', 'per', 'sono', 'italiano', 'italia'
}

DUTCH_WORDS = {
    'de', 'het', 'een', 'en', 'van', 'is', 'in', 'op', 'voor', 'met', 'zijn', 'nederlands',
    'nederland'
}


def _detect_with_google_translate(text: str) -> Optional[str]:
    """Detect language using Google Translate API."""
    try:
        google_key = os.getenv('GOOGLE_API_KEY')
        if not google_key:
            return None
        
        # Use Google Cloud Translation API v2 (detect language) - sync version
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                'https://translation.googleapis.com/language/translate/v2/detect',
                params={'key': google_key, 'q': text[:500]},  # Limit text length
            )
            response.raise_for_status()
            data = response.json()
            if 'data' in data and 'detections' in data['data']:
                detections = data['data']['detections']
                if detections and len(detections) > 0 and len(detections[0]) > 0:
                    lang_code = detections[0][0].get('language', '').lower()
                    # Map Google language codes to our codes
                    lang_map = {
                        'fr': 'fr', 'en': 'en', 'de': 'de', 'es': 'es', 'it': 'it', 'nl': 'nl',
                        'pt': 'other', 'ru': 'other', 'ja': 'other', 'zh': 'other', 'zh-cn': 'other',
                        'ar': 'other', 'pl': 'other', 'cs': 'other'
                    }
                    return lang_map.get(lang_code, 'other')
    except Exception as e:
        logger.debug(f"Google Translate detection failed: {e}")
        return None


def _detect_with_deepl(text: str) -> Optional[str]:
    """Detect language using DeepL API."""
    try:
        deepl_key = os.getenv('DEEPL_API_KEY')
        if not deepl_key:
            return None
        
        # Use DeepL API - sync version
        with httpx.Client(timeout=5.0) as client:
            response = client.post(
                'https://api-free.deepl.com/v2/translate',
                headers={'Authorization': f'DeepL-Auth-Key {deepl_key}'},
                data={
                    'text': text[:500],  # Limit text length
                    'target_lang': 'EN',  # Dummy target, we just want detection
                    'source_lang': None  # Auto-detect
                }
            )
            response.raise_for_status()
            data = response.json()
            if 'translations' in data and len(data['translations']) > 0:
                detected_lang = data['translations'][0].get('detected_source_language', '').lower()
                # Map DeepL language codes to our codes
                lang_map = {
                    'fr': 'fr', 'en': 'en', 'de': 'de', 'es': 'es', 'it': 'it', 'nl': 'nl',
                    'pt': 'other', 'ru': 'other', 'ja': 'other', 'zh': 'other', 'pl': 'other'
                }
                return lang_map.get(detected_lang, 'other')
    except Exception as e:
        logger.debug(f"DeepL detection failed: {e}")
        return None


def _detect_with_llm(text: str) -> Optional[str]:
    """Detect language using LLM (OpenAI/Anthropic)."""
    try:
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        api_key = None
        
        if llm_provider == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
        elif llm_provider == 'anthropic':
            api_key = os.getenv('ANTHROPIC_API_KEY')
        
        if not api_key:
            return None
        
        # Truncate text for LLM (keep first 200 chars)
        text_sample = text[:200]
        
        prompt = f"""What language is this text written in? Respond with ONLY the ISO 639-1 language code (fr, en, de, es, it, nl, etc.) or 'unknown' if you cannot determine.

Text: "{text_sample}"

Language code:"""
        
        # Use sync version
        with httpx.Client(timeout=10.0) as client:
            if llm_provider == 'openai':
                response = client.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                        'messages': [
                            {'role': 'system', 'content': 'You are a language detection assistant. Respond with only the ISO 639-1 language code.'},
                            {'role': 'user', 'content': prompt}
                        ],
                        'temperature': 0.1,
                        'max_tokens': 10
                    }
                )
                response.raise_for_status()
                result = response.json()
                lang_code = result['choices'][0]['message']['content'].strip().lower()
                # Clean up response (remove quotes, etc.)
                lang_code = lang_code.strip('"\'')
                lang_map = {
                    'fr': 'fr', 'en': 'en', 'de': 'de', 'es': 'es', 'it': 'it', 'nl': 'nl',
                    'pt': 'other', 'ru': 'other', 'ja': 'other', 'zh': 'other', 'ar': 'other'
                }
                return lang_map.get(lang_code, 'unknown' if lang_code == 'unknown' else 'other')
            
            elif llm_provider == 'anthropic':
                response = client.post(
                    'https://api.anthropic.com/v1/messages',
                    headers={
                        'x-api-key': api_key,
                        'anthropic-version': '2023-06-01',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                        'max_tokens': 10,
                        'messages': [
                            {'role': 'user', 'content': prompt}
                        ],
                        'system': 'You are a language detection assistant. Respond with only the ISO 639-1 language code.'
                    }
                )
                response.raise_for_status()
                result = response.json()
                lang_code = result['content'][0]['text'].strip().lower()
                lang_code = lang_code.strip('"\'')
                lang_map = {
                    'fr': 'fr', 'en': 'en', 'de': 'de', 'es': 'es', 'it': 'it', 'nl': 'nl',
                    'pt': 'other', 'ru': 'other', 'ja': 'other', 'zh': 'other', 'ar': 'other'
                }
                return lang_map.get(lang_code, 'unknown' if lang_code == 'unknown' else 'other')
    except Exception as e:
        logger.debug(f"LLM detection failed: {e}")
        return None


def detect_language(text: str) -> str:
    """
    Detect language of text using multiple methods with fallback chain.
    
    Priority:
    1. TextBlob (if available) - most accurate local method
    2. Google Translate API (if GOOGLE_API_KEY configured) - very accurate
    3. DeepL API (if DEEPL_API_KEY configured) - very accurate
    4. LLM (OpenAI/Anthropic) (if configured) - accurate but slower
    5. Keyword-based detection (fallback) - fast but less accurate
    6. Character-based heuristics - last resort
    
    Returns:
        Language code: 'fr', 'en', 'de', 'es', 'it', 'nl', 'other', or 'unknown'
    """
    if not text or len(text.strip()) < 3:
        return 'unknown'
    
    text_lower = text.lower()
    text_words = set(re.findall(r'\b\w+\b', text_lower))
    
    # Method 1: Try TextBlob (most accurate local method)
    try:
        from textblob import TextBlob
        try:
            detected = TextBlob(text).detect_language()
            # Map to our language codes
            lang_map = {
                'fr': 'fr', 'en': 'en', 'de': 'de', 'es': 'es', 'it': 'it', 'nl': 'nl',
                'pt': 'other', 'ru': 'other', 'ja': 'other', 'zh': 'other', 'ar': 'other'
            }
            if detected in lang_map:
                logger.debug(f"Language detected by TextBlob: {detected}")
                return lang_map[detected]
            return 'other'
        except Exception as e:
            logger.debug(f"TextBlob detection failed: {e}")
    except ImportError:
        logger.debug("TextBlob not available, trying other methods")
    
    # Method 2: Try Google Translate API (very accurate)
    detected = _detect_with_google_translate(text)
    if detected and detected != 'unknown':
        logger.debug(f"Language detected by Google Translate: {detected}")
        return detected
    
    # Method 3: Try DeepL API (very accurate)
    detected = _detect_with_deepl(text)
    if detected and detected != 'unknown':
        logger.debug(f"Language detected by DeepL: {detected}")
        return detected
    
    # Method 4: Try LLM (accurate but slower)
    detected = _detect_with_llm(text)
    if detected and detected != 'unknown':
        logger.debug(f"Language detected by LLM: {detected}")
        return detected
    
    # Method 5: Character-based heuristics (check before keywords for better accuracy)
    # French: common characters like é, è, ê, à, ç
    french_chars = len(re.findall(r'[éèêëàâäôöùûüç]', text_lower))
    # German: common characters like ä, ö, ü, ß
    german_chars = len(re.findall(r'[äöüß]', text_lower))
    # Spanish: common characters like ñ, á, é, í, ó, ú
    spanish_chars = len(re.findall(r'[ñáéíóú]', text_lower))
    
    if french_chars >= 1:  # Lower threshold for character detection
        return 'fr'
    elif german_chars >= 1:
        return 'de'
    elif spanish_chars >= 1:
        return 'es'
    
    # Method 6: Keyword-based detection (fallback)
    scores = {
        'fr': len(text_words & FRENCH_WORDS),
        'en': len(text_words & ENGLISH_WORDS),
        'de': len(text_words & GERMAN_WORDS),
        'es': len(text_words & SPANISH_WORDS),
        'it': len(text_words & ITALIAN_WORDS),
        'nl': len(text_words & DUTCH_WORDS),
    }
    
    # Find language with highest score
    max_score = max(scores.values())
    # Lower threshold: at least 2 matching words (or 1 if text is very short)
    threshold = 2 if len(text_words) > 5 else 1
    if max_score >= threshold:
        for lang, score in scores.items():
            if score == max_score:
                return lang
    
    # Method 4: Common phrases
    french_phrases = ['c\'est', 'il est', 'elle est', 'nous avons', 'vous avez', 'très bien', 'pas de']
    english_phrases = ['it is', 'he is', 'she is', 'we have', 'you have', 'very good', 'not a']
    
    text_lower_phrases = text_lower.replace("'", "'").replace("'", "'")
    for phrase in french_phrases:
        if phrase in text_lower_phrases:
            return 'fr'
    for phrase in english_phrases:
        if phrase in text_lower_phrases:
            return 'en'
    
    # Default to unknown if no clear match
    return 'unknown'


def detect_language_from_post(post: dict) -> str:
    """
    Detect language from a post dictionary.
    Uses content, author, and source as hints.
    
    Args:
        post: Dictionary with 'content', 'author', 'source', 'url' keys
        
    Returns:
        Language code
    """
    # Priority 1: Use existing language if set and valid
    existing_lang = post.get('language', '').lower()
    if existing_lang in ['fr', 'en', 'de', 'es', 'it', 'nl', 'other']:
        return existing_lang
    
    # Priority 2: Detect from content
    content = post.get('content', '') or ''
    if content:
        detected = detect_language(content)
        if detected != 'unknown':
            return detected
    
    # Priority 3: Use URL hints (e.g., .fr, .de, .es domains)
    url = (post.get('url', '') or '').lower()
    if '.fr' in url or 'fr.' in url:
        return 'fr'
    elif '.de' in url or 'de.' in url:
        return 'de'
    elif '.es' in url or 'es.' in url:
        return 'es'
    elif '.it' in url or 'it.' in url:
        return 'it'
    elif '.nl' in url or 'nl.' in url:
        return 'nl'
    elif '.co.uk' in url or '.uk' in url:
        return 'en'
    elif '.com' in url and 'trustpilot.com' in url and 'fr.' in url:
        return 'fr'
    
    # Priority 4: Use source hints
    source = (post.get('source', '') or '').lower()
    if 'france' in source or 'français' in source:
        return 'fr'
    elif 'german' in source or 'deutsch' in source:
        return 'de'
    elif 'spanish' in source or 'español' in source:
        return 'es'
    
    return 'unknown'

