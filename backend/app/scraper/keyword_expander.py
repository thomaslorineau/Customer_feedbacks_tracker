"""Keyword expansion module for generating search query variants."""
from typing import List
import logging

logger = logging.getLogger(__name__)

# Terms to add to keywords for better coverage
SEARCH_TERMS = [
    "problem", "issue", "bug", "error", "complaint", "review",
    "feedback", "opinion", "experience", "review", "rating"
]

# OVH product variants
OVH_PRODUCTS = [
    "domain", "hosting", "vps", "cloud", "server", "dedicated",
    "web", "email", "ssl", "cdn", "storage", "backup"
]

# Translation dictionary for multilingual queries
TRANSLATIONS = {
    'fr': {
        'problem': 'problème',
        'issue': 'problème',
        'complaint': 'plainte',
        'review': 'avis',
        'feedback': 'retour',
        'support': 'support',
        'error': 'erreur',
        'bug': 'bug',
    },
    'en': {
        'problem': 'problem',
        'issue': 'issue',
        'complaint': 'complaint',
        'review': 'review',
        'feedback': 'feedback',
        'support': 'support',
        'error': 'error',
        'bug': 'bug',
    },
    'es': {
        'problem': 'problema',
        'issue': 'problema',
        'complaint': 'queja',
        'review': 'reseña',
        'feedback': 'comentario',
        'support': 'soporte',
        'error': 'error',
        'bug': 'bug',
    },
}


def expand_keywords(base_keywords: List[str]) -> List[str]:
    """
    Generate keyword variants by adding search terms and product names.
    
    Args:
        base_keywords: List of base keywords (e.g., ["OVH", "OVH domain"])
    
    Returns:
        Expanded list of keywords with variants
    
    Example:
        >>> expand_keywords(["OVH"])
        ["OVH", "OVH problem", "problem OVH", "OVH domain", "OVH hosting", ...]
    """
    if not base_keywords:
        return []
    
    expanded = []
    seen = set()  # For deduplication
    
    for keyword in base_keywords:
        if not keyword or not isinstance(keyword, str):
            continue
        
        keyword = keyword.strip()
        if not keyword:
            continue
        
        # Add original keyword
        if keyword.lower() not in seen:
            expanded.append(keyword)
            seen.add(keyword.lower())
        
        # Normalize OVH variations
        keyword_normalized = keyword
        if 'ovh' in keyword.lower():
            keyword_normalized = keyword.replace('ovh', 'OVH').replace('Ovh', 'OVH')
            if keyword_normalized.lower() not in seen:
                expanded.append(keyword_normalized)
                seen.add(keyword_normalized.lower())
        
        # Add search terms
        for term in SEARCH_TERMS:
            # Pattern: "keyword term"
            variant1 = f"{keyword} {term}"
            if variant1.lower() not in seen:
                expanded.append(variant1)
                seen.add(variant1.lower())
            
            # Pattern: "term keyword"
            variant2 = f"{term} {keyword}"
            if variant2.lower() not in seen:
                expanded.append(variant2)
                seen.add(variant2.lower())
        
        # Add product variants (only if keyword contains OVH)
        if 'ovh' in keyword.lower():
            for product in OVH_PRODUCTS:
                # Pattern: "OVH product"
                variant1 = f"{keyword} {product}"
                if variant1.lower() not in seen:
                    expanded.append(variant1)
                    seen.add(variant1.lower())
                
                # Pattern: "OVH product term" (combine with search terms)
                for term in SEARCH_TERMS[:5]:  # Limit to first 5 to avoid too many combinations
                    variant2 = f"{keyword} {product} {term}"
                    if variant2.lower() not in seen:
                        expanded.append(variant2)
                        seen.add(variant2.lower())
    
    logger.info(f"[Keyword Expander] Expanded {len(base_keywords)} keywords to {len(expanded)} variants")
    return expanded


def get_multilingual_queries(query: str) -> List[str]:
    """
    Generate multilingual versions of a query.
    
    Args:
        query: Base query string (e.g., "OVH problem")
    
    Returns:
        List of queries in multiple languages
    
    Example:
        >>> get_multilingual_queries("OVH problem")
        ["OVH problem", "OVH problème", "OVH problema"]
    """
    if not query or not isinstance(query, str):
        return [query] if query else []
    
    query = query.strip()
    if not query:
        return []
    
    queries = [query]  # Start with original
    
    # Extract base keyword (assume it's the first word or "OVH")
    base_keyword = "OVH"
    if query.lower().startswith('ovh'):
        base_keyword = "OVH"
        rest = query[3:].strip()
    else:
        # Try to find OVH in the query
        parts = query.split()
        if 'ovh' in [p.lower() for p in parts]:
            base_keyword = "OVH"
            rest = ' '.join([p for p in parts if 'ovh' not in p.lower()])
        else:
            # No OVH found, just translate the whole query
            rest = query
    
    # Generate translations for each language
    for lang_code, translations in TRANSLATIONS.items():
        translated_rest = rest
        for en_term, translated_term in translations.items():
            # Simple word replacement (case-insensitive)
            translated_rest = translated_rest.replace(en_term, translated_term)
            translated_rest = translated_rest.replace(en_term.capitalize(), translated_term.capitalize())
        
        if translated_rest != rest or lang_code == 'en':
            multilingual_query = f"{base_keyword} {translated_rest}".strip()
            if multilingual_query.lower() != query.lower():
                queries.append(multilingual_query)
    
    # Deduplicate
    seen = set()
    unique_queries = []
    for q in queries:
        if q.lower() not in seen:
            unique_queries.append(q)
            seen.add(q.lower())
    
    logger.debug(f"[Keyword Expander] Generated {len(unique_queries)} multilingual variants for: {query}")
    return unique_queries


def expand_keywords_with_multilingual(base_keywords: List[str], include_multilingual: bool = True) -> List[str]:
    """
    Combine keyword expansion with multilingual variants.
    
    Args:
        base_keywords: List of base keywords
        include_multilingual: Whether to include multilingual variants
    
    Returns:
        Fully expanded list of keywords
    """
    # First expand with variants
    expanded = expand_keywords(base_keywords)
    
    if not include_multilingual:
        return expanded
    
    # Then add multilingual versions
    multilingual_expanded = []
    seen = set()
    
    for keyword in expanded:
        multilingual_expanded.append(keyword)
        seen.add(keyword.lower())
        
        # Add multilingual variants
        multilingual_variants = get_multilingual_queries(keyword)
        for variant in multilingual_variants:
            if variant.lower() not in seen:
                multilingual_expanded.append(variant)
                seen.add(variant.lower())
    
    logger.info(f"[Keyword Expander] Final expansion: {len(base_keywords)} -> {len(multilingual_expanded)} keywords")
    return multilingual_expanded


