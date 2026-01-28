"""LLM-based insights and recommendations endpoints."""
import os
import json
import re
import logging
import asyncio
import math
from typing import List, Optional, Tuple
from fastapi import APIRouter, HTTPException
import httpx

from .models import (
    ImprovementIdea, ImprovementIdeasResponse, ImprovementIdeaRequest,
    RecommendedAction, RecommendedActionsResponse, RecommendedActionRequest,
    WhatsHappeningInsight, WhatsHappeningResponse, WhatsHappeningRequest,
    PainPointsResponse, ProductDistributionResponse, ProductOpportunity,
    ImprovementInsight, ImprovementsAnalysisRequest, ImprovementsAnalysisResponse
)
from .analytics import get_pain_points
from ... import database as db
from fastapi import Query

logger = logging.getLogger(__name__)

router = APIRouter()


def normalize_ovh_model_name(model: Optional[str]) -> Optional[str]:
    """
    Normalize OVH model name to ensure compatibility.
    Converts deprecated model names to their correct format.
    Returns None if no model is specified (user must configure it).
    """
    if not model:
        return None  # No default model - user must specify
    
    # Convert deprecated model names to None (user must configure a valid model)
    deprecated_models = {
        'Mistral-Large-2407': None,
        'mistral-large-2407': None,
        'mistral-large-latest': None,
        'DeepSeek-R1-Distill-Qwen-32B': None  # This model doesn't exist on all endpoints
    }
    
    if model in deprecated_models:
        logger.warning(f"Model name '{model}' is deprecated or not available. Please configure a valid model in Settings.")
        return None
    
    # Return the model as-is - let the API call fail with a clear error if it's invalid
    return model


def get_llm_api_keys():
    """
    Récupère les clés API LLM depuis la base de données en priorité,
    puis depuis les variables d'environnement comme fallback.
    
    Returns:
        tuple: (openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider)
    """
    try:
        from ...database import pg_get_config
        
        # Récupérer depuis la base de données en premier (source de vérité)
        # Ne pas utiliser les variables d'environnement comme fallback car elles peuvent être obsolètes
        openai_key = pg_get_config('OPENAI_API_KEY')
        anthropic_key = pg_get_config('ANTHROPIC_API_KEY')
        mistral_key = pg_get_config('MISTRAL_API_KEY')
        ovh_key = pg_get_config('OVH_API_KEY')
        ovh_endpoint = pg_get_config('OVH_ENDPOINT_URL')
        ovh_model = pg_get_config('OVH_MODEL')
        llm_provider = pg_get_config('LLM_PROVIDER')
        
        # Normaliser les valeurs : convertir les chaînes vides en None
        if openai_key == '':
            openai_key = None
        if anthropic_key == '':
            anthropic_key = None
        if mistral_key == '':
            mistral_key = None
        if ovh_key == '':
            ovh_key = None
        if ovh_endpoint == '':
            ovh_endpoint = None
        if ovh_model == '':
            ovh_model = None
        if llm_provider == '':
            llm_provider = None
        
        # Fallback sur les variables d'environnement UNIQUEMENT si vraiment pas en base (None)
        # Mais ce fallback ne devrait normalement jamais être utilisé car les clés sont en base
        if not openai_key:
            openai_key = os.getenv('OPENAI_API_KEY')
        if not anthropic_key:
            anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        if not mistral_key:
            mistral_key = os.getenv('MISTRAL_API_KEY')
        if not ovh_key:
            ovh_key = os.getenv('OVH_API_KEY')
        if not ovh_endpoint:
            ovh_endpoint = os.getenv('OVH_ENDPOINT_URL', 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1')
        if not ovh_model:
            ovh_model = os.getenv('OVH_MODEL')  # No default - user must configure
        if not llm_provider:
            llm_provider = os.getenv('LLM_PROVIDER', 'openai')
        
        # Normaliser le provider en lowercase
        if llm_provider:
            llm_provider = llm_provider.lower()
        else:
            llm_provider = 'openai'
        
        logger.debug(f"get_llm_api_keys: OpenAI={bool(openai_key)}, Anthropic={bool(anthropic_key)}, Mistral={bool(mistral_key)}, OVH={bool(ovh_key)}, Provider={llm_provider}")
            
        return openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider
    except Exception as e:
        logger.warning(f"Erreur lors de la récupération des clés API depuis la base de données: {e}")
        # Fallback complet sur les variables d'environnement
        return (
            os.getenv('OPENAI_API_KEY'),
            os.getenv('ANTHROPIC_API_KEY'),
            os.getenv('MISTRAL_API_KEY'),
            os.getenv('OVH_API_KEY'),
            os.getenv('OVH_ENDPOINT_URL', 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'),
            os.getenv('OVH_MODEL'),  # No default - user must configure
            os.getenv('LLM_PROVIDER', 'openai').lower()
        )


async def generate_ideas_with_llm(posts: List[dict], max_ideas: int = 5) -> List[ImprovementIdea]:
    """Generate improvement ideas using LLM API."""
    # Récupérer les clés API depuis la base de données (priorité) ou variables d'environnement
    # Ne pas utiliser load_dotenv avec override=True car cela peut écraser les clés en mémoire
    
    # Filter posts to prioritize negative/neutral for improvement ideas
    relevant_posts = [p for p in posts if p.get('sentiment_label') in ['negative', 'neutral']]
    if not relevant_posts:
        logger.info("No negative or neutral posts found, using all posts for ideas.")
        relevant_posts = posts
    
    if not relevant_posts:
        raise HTTPException(status_code=400, detail="No relevant posts found for analysis.")
    
    posts_for_llm = relevant_posts[:20]  # Limit to 20 posts for LLM analysis
    
    posts_summary = []
    for post in posts_for_llm:
        posts_summary.append({
            'content': post.get('content', '')[:500],
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown')
        })
    
    prompt = f"""Analyze the following {len(posts_for_llm)} customer feedback posts about OVH products and generate {max_ideas} concrete product improvement ideas.

Posts to analyze:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

IMPORTANT: Even with few posts, generate meaningful ideas. If you have at least 2-3 posts, you can identify patterns. Do not return an empty array.

For each idea, provide:
1. A clear, concise title (max 60 characters)
2. A detailed description explaining the improvement and why it's needed
3. Priority level (high/medium/low) based on impact and frequency
4. Count of related posts that support this idea

Format your response as a JSON array with this structure:
[
  {{
    "title": "Idea title",
    "description": "Detailed description...",
    "priority": "high|medium|low",
    "related_posts_count": 3
  }}
]

Focus on actionable improvements that address real customer pain points. Be specific and practical."""

    openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
    
    logger.info(f"generate_ideas_with_llm: OpenAI key set: {bool(openai_key)}, Anthropic key set: {bool(anthropic_key)}, Mistral key set: {bool(mistral_key)}, Provider: {llm_provider}")
    
    if not openai_key and not anthropic_key and not mistral_key and not ovh_key:
        raise HTTPException(status_code=400, detail="No LLM API key configured. Please configure at least one API key in Settings.")
    
    # Helper function to call a single LLM
    async def call_llm(provider: str, api_key: str, prompt: str) -> Optional[str]:
        """Call a single LLM and return the response content."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if provider == 'openai':
                    response = await client.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                            'messages': [
                                {'role': 'system', 'content': 'You are a product improvement analyst. Generate actionable improvement ideas based on customer feedback.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['choices'][0]['message']['content']
                
                elif provider == 'anthropic':
                    response = await client.post(
                        'https://api.anthropic.com/v1/messages',
                        headers={
                            'x-api-key': api_key,
                            'anthropic-version': '2023-06-01',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                            'max_tokens': 2000,
                            'messages': [
                                {'role': 'user', 'content': prompt}
                            ]
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['content'][0]['text']
                
                elif provider == 'mistral':
                    response = await client.post(
                        'https://api.mistral.ai/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('MISTRAL_MODEL', 'mistral-small'),
                            'messages': [
                                {'role': 'system', 'content': 'You are a product improvement analyst. Generate actionable improvement ideas based on customer feedback.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['choices'][0]['message']['content']
                
                elif provider == 'ovh':
                    # OVH AI Endpoints uses OpenAI-compatible API
                    url = f"{ovh_endpoint}/chat/completions"
                    model = normalize_ovh_model_name(ovh_model)
                    
                    # Check if model is configured
                    if not model:
                        logger.error("OVH AI model not configured")
                        return None
                    
                    response = await client.post(
                        url,
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': model,
                            'messages': [
                                {'role': 'system', 'content': 'You are a product improvement analyst. Generate actionable improvement ideas based on customer feedback.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['choices'][0]['message']['content']
        except Exception as e:
            logger.warning(f"{provider} API error: {type(e).__name__}: {e}")
            return None
        return None
    
    # Count configured LLMs
    configured_llms = []
    if openai_key:
        configured_llms.append(('openai', openai_key, 'OpenAI'))
    if anthropic_key:
        configured_llms.append(('anthropic', anthropic_key, 'Anthropic'))
    if mistral_key:
        configured_llms.append(('mistral', mistral_key, 'Mistral'))
    if ovh_key:
        configured_llms.append(('ovh', ovh_key, 'OVH AI'))
    
    # If 2 or more LLMs are configured, call them in parallel and summarize
    # Limiter à 2 LLM maximum pour éviter la complexité excessive de la synthèse
    if len(configured_llms) >= 2:
        # Limiter à 2 LLM pour la synthèse (priorité: OpenAI, puis Anthropic, puis Mistral, puis OVH)
        llms_to_use = configured_llms[:2]
        logger.info(f"{len(configured_llms)} LLMs configured, using {len(llms_to_use)} for parallel synthesis (limiting to 2 for better results)")
        try:
            # Call selected LLMs in parallel
            tasks = []
            for provider, key, _ in llms_to_use:
                if provider == 'ovh':
                    tasks.append(call_llm(provider, key, prompt, ovh_endpoint, ovh_model))
                else:
                    tasks.append(call_llm(provider, key, prompt))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect valid results
            valid_results = []
            for i, (provider, _, name) in enumerate(llms_to_use):
                result = results[i]
                if result and not isinstance(result, Exception):
                    valid_results.append((name, result))
                elif isinstance(result, Exception):
                    logger.warning(f"{name} LLM call failed: {type(result).__name__}: {result}")
            
            if not valid_results:
                raise HTTPException(status_code=500, detail="All LLM calls failed. Please check your API keys.")
            elif len(valid_results) == 1:
                # Si un seul LLM a réussi, utiliser directement son résultat sans synthèse
                logger.info(f"Only {valid_results[0][0]} succeeded, using its result directly")
                content = valid_results[0][1]
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        ideas_data = json.loads(json_match.group())
                        logger.info(f"Generated {len(ideas_data)} ideas from {valid_results[0][0]}")
                        return [ImprovementIdea(**idea) for idea in ideas_data]
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        logger.error(f"Error parsing LLM response: {e}. Content: {content[:500]}")
            else:
                # Choose summarizer: prefer OpenAI, then Anthropic, then Mistral
                summarizer = None
                summarizer_key = None
                summarizer_name = None
                
                if openai_key:
                    summarizer = 'openai'
                    summarizer_key = openai_key
                    summarizer_name = 'OpenAI'
                elif anthropic_key:
                    summarizer = 'anthropic'
                    summarizer_key = anthropic_key
                    summarizer_name = 'Anthropic'
                elif ovh_key:
                    summarizer = 'ovh'
                    summarizer_key = ovh_key
                    summarizer_name = 'OVH AI'
                elif mistral_key:
                    summarizer = 'mistral'
                    summarizer_key = mistral_key
                    summarizer_name = 'Mistral'
                
                if summarizer and summarizer_key:
                    # Limiter la longueur du prompt de synthèse pour éviter les problèmes
                    results_text = chr(10).join([f'{name} ideas:{chr(10)}{result[:2000]}' for name, result in valid_results])
                    
                    summary_prompt = f"""You are analyzing product improvement ideas from {len(valid_results)} AI models. Below are the ideas:

{results_text}

Your task is to synthesize these ideas into a single, comprehensive list of {max_ideas} best improvement ideas. 

Rules:
- Combine similar ideas from different models
- Prioritize ideas that appear in multiple models
- Keep the best ideas based on clarity, actionability, and impact
- Ensure each idea has a clear title, description, priority, and related_posts_count
- Do not return an empty array

Format your response as a JSON array with this structure:
[
  {{
    "title": "Idea title",
    "description": "Detailed description...",
    "priority": "high|medium|low",
    "related_posts_count": 3
  }}
]"""
                
                if summarizer == 'ovh':
                    summary_content = await call_llm(summarizer, summarizer_key, summary_prompt, ovh_endpoint, ovh_model)
                else:
                    summary_content = await call_llm(summarizer, summarizer_key, summary_prompt)
                if summary_content:
                    json_match = re.search(r'\[.*\]', summary_content, re.DOTALL)
                    if json_match:
                        ideas_data = json.loads(json_match.group())
                        logger.info(f"Generated {len(ideas_data)} ideas from summarized LLM results using {summarizer_name}")
                        return [ImprovementIdea(**idea) for idea in ideas_data]
        
        except Exception as e:
            logger.error(f"Error in parallel LLM call or summarization: {type(e).__name__}: {e}", exc_info=True)
            # Fall through to single LLM logic
    
    # Single LLM logic (if not all 3 are configured, or if parallel call failed)
    try:
        # Use the configured provider first
        if llm_provider == 'ovh' and ovh_key:
            content = await call_llm('ovh', ovh_key, prompt, ovh_endpoint, ovh_model)
            if content:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
        elif llm_provider == 'anthropic' or (not llm_provider and anthropic_key and not openai_key and not mistral_key and not ovh_key):
            # Use Anthropic
            if anthropic_key:
                content = await call_llm('anthropic', anthropic_key, prompt)
                if content:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        ideas_data = json.loads(json_match.group())
                        return [ImprovementIdea(**idea) for idea in ideas_data]
        
        elif llm_provider == 'mistral' or (not llm_provider and mistral_key and not openai_key and not anthropic_key and not ovh_key):
            # Use Mistral
            if mistral_key:
                content = await call_llm('mistral', mistral_key, prompt)
                if content:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        ideas_data = json.loads(json_match.group())
                        return [ImprovementIdea(**idea) for idea in ideas_data]
        
        elif llm_provider == 'openai' or (not llm_provider and openai_key):
            # Use OpenAI
            if openai_key:
                content = await call_llm('openai', openai_key, prompt)
                if content:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        ideas_data = json.loads(json_match.group())
                        return [ImprovementIdea(**idea) for idea in ideas_data]
        
        # If provider is set but no matching key, try any available key
        if ovh_key:
            content = await call_llm('ovh', ovh_key, prompt, ovh_endpoint, ovh_model)
            if content:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
        if openai_key:
            content = await call_llm('openai', openai_key, prompt)
            if content:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
        if anthropic_key:
            content = await call_llm('anthropic', anthropic_key, prompt)
            if content:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
        if mistral_key:
            content = await call_llm('mistral', mistral_key, prompt)
            if content:
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    return [ImprovementIdea(**idea) for idea in ideas_data]
    
    except Exception as e:
        logger.error(f"LLM API error: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")
    
    raise HTTPException(status_code=500, detail="Failed to generate ideas: No LLM response received.")


def generate_ideas_fallback(posts: List[dict], max_ideas: int = 5) -> List[ImprovementIdea]:
    """Fallback rule-based idea generation when LLM is not available."""
    ideas = []
    
    themes = {
        'Performance': {'keywords': ['slow', 'lag', 'performance', 'speed', 'timeout'], 'posts': []},
        'Reliability': {'keywords': ['down', 'crash', 'error', 'bug', 'broken'], 'posts': []},
        'Support': {'keywords': ['support', 'help', 'ticket', 'response', 'wait'], 'posts': []},
        'Documentation': {'keywords': ['documentation', 'docs', 'guide', 'tutorial'], 'posts': []},
        'UI/UX': {'keywords': ['interface', 'ui', 'ux', 'confusing', 'unclear'], 'posts': []}
    }
    
    for post in posts:
        content_lower = post.get('content', '').lower()
        for theme, data in themes.items():
            if any(kw in content_lower for kw in data['keywords']):
                data['posts'].append(post)
    
    for theme, data in sorted(themes.items(), key=lambda x: len(x[1]['posts']), reverse=True)[:max_ideas]:
        if len(data['posts']) > 0:
            ideas.append(ImprovementIdea(
                title=f"Improve {theme}",
                description=f"Based on {len(data['posts'])} customer feedback posts, there are recurring issues related to {theme.lower()}. Consider reviewing and improving this aspect of the product.",
                priority='high' if len(data['posts']) >= 5 else 'medium' if len(data['posts']) >= 2 else 'low',
                related_posts_count=len(data['posts'])
            ))
    
    return ideas


async def generate_recommended_actions_with_llm(
    posts: List[dict], 
    recent_posts: List[dict], 
    stats: dict,
    max_actions: int = 5
) -> List[RecommendedAction]:
    """Generate recommended actions using LLM API."""
    negative_posts = [p for p in recent_posts if p.get('sentiment_label') == 'negative']
    posts_summary = []
    for post in (negative_posts[:10] if negative_posts else posts[:15]):
        posts_summary.append({
            'content': (post.get('content', '') or '')[:300],
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown'),
            'created_at': post.get('created_at', '')
        })
    
    active_filters = stats.get('active_filters', 'All posts')
    filtered_context = stats.get('filtered_context', False)
    search_term = stats.get('search_term', '')
    
    prompt = f"""You are an OVHcloud customer support analyst. Analyze the following customer feedback posts and generate {max_actions} specific, actionable recommended actions.

CONTEXT:
- Active filters: {active_filters}
- Search term: "{search_term}" {'(user is specifically searching for this)' if search_term else '(no specific search term)'}
- Analysis is based on {'filtered posts' if filtered_context else 'all posts'} in the database
- Total posts analyzed: {stats.get('total', 0)} (Positive: {stats.get('positive', 0)}, Negative: {stats.get('negative', 0)}, Neutral: {stats.get('neutral', 0)})
- Recent posts (last 48h): {stats.get('recent_total', 0)} total, {stats.get('recent_negative', 0)} negative
- Spike detected: {stats.get('spike_detected', False)} {'⚠️ Significant increase in negative feedback!' if stats.get('spike_detected', False) else ''}
- Top product impacted: {stats.get('top_product', 'N/A')} ({stats.get('top_product_count', 0)} negative posts)
- Top issue keyword: "{stats.get('top_issue', 'N/A')}" (mentioned {stats.get('top_issue_count', 0)} times)

POSTS TO ANALYZE:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

IMPORTANT: The recommendations must be SPECIFIC to the actual issues found in these posts. 
- If a search term is provided, prioritize recommendations related to that search term
- If a specific product is mentioned frequently, reference it
- If specific errors or problems appear, mention them
- If the analysis is filtered (e.g., by product, date, or source), acknowledge this context
- Base priorities on the actual data: high for urgent spikes or critical issues, medium for recurring problems, low for minor improvements

Generate {max_actions} recommended actions. Each action should:
1. Be SPECIFIC and ACTIONABLE (not generic like "improve support")
2. Reference actual issues, products, or patterns found in the posts
3. Include an appropriate emoji icon
4. Have a priority level (high/medium/low) based on:
   - High: Spike detected, critical issues, urgent problems
   - Medium: Recurring issues, moderate impact
   - Low: Minor improvements, nice-to-have features

Format your response as a JSON array with this structure:
[
  {{
    "icon": "🔍",
    "text": "Investigate: [specific issue/product] - [specific detail from posts]",
    "priority": "high"
  }}
]

Use appropriate emojis:
- 🔍 for investigate/research
- 📣 for check/announce/verify
- 💬 for communication/prepare responses
- ⚠️ for alerts/urgent issues
- 🔧 for technical fixes
- 📊 for analysis/reporting
- 🎯 for focus areas
- ⚡ for urgent actions

Be specific and reference actual content from the posts when possible."""

    openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
    
    if not openai_key and not anthropic_key and not mistral_key and not ovh_key:
        logger.info("[Recommended Actions] No LLM API key configured, cannot generate actions")
        return []
    
    # Helper function to call a single LLM
    async def call_llm_for_actions(provider: str, api_key: str, prompt: str) -> Optional[str]:
        """Call a single LLM and return the response content."""
        logger.info(f"[Recommended Actions] Calling {provider} API...")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if provider == 'openai':
                    response = await client.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud customer support analyst. Generate specific, actionable recommended actions based on customer feedback.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 1500
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"[Recommended Actions] OpenAI API call successful (response length: {len(content)})")
                    return content
                
                elif provider == 'anthropic':
                    response = await client.post(
                        'https://api.anthropic.com/v1/messages',
                        headers={
                            'x-api-key': api_key,
                            'anthropic-version': '2023-06-01',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                            'max_tokens': 1500,
                            'messages': [
                                {'role': 'user', 'content': prompt}
                            ],
                            'system': 'You are an OVHcloud customer support analyst. Generate specific, actionable recommended actions based on customer feedback.'
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['content'][0]['text']
                    logger.info(f"[Recommended Actions] Anthropic API call successful (response length: {len(content)})")
                    return content
                
                elif provider == 'mistral':
                    response = await client.post(
                        'https://api.mistral.ai/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('MISTRAL_MODEL', 'mistral-small'),
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud customer support analyst. Generate specific, actionable recommended actions based on customer feedback.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 1500
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"[Recommended Actions] Mistral API call successful (response length: {len(content)})")
                    return content
                
                elif provider == 'ovh':
                    # OVH AI Endpoints uses OpenAI-compatible API
                    model = normalize_ovh_model_name(ovh_model)
                    
                    # Check if model is configured
                    if not model:
                        logger.error("[Recommended Actions] OVH AI model not configured")
                        return None
                    
                    response = await client.post(
                        f'{ovh_endpoint}/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': model,
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud customer support analyst. Generate specific, actionable recommended actions based on customer feedback.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 1500
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"[Recommended Actions] OVH AI API call successful (response length: {len(content)})")
                    return content
        except httpx.HTTPStatusError as e:
            logger.error(f"[Recommended Actions] {provider} API HTTP error ({e.response.status_code}): {e}")
            if e.response.status_code == 401:
                logger.error(f"[Recommended Actions] {provider} API authentication failed - check API key")
            return None
        except Exception as e:
            logger.error(f"[Recommended Actions] {provider} API error: {type(e).__name__}: {e}", exc_info=True)
            return None
        return None
    
    # Count configured LLMs
    configured_llms = []
    if openai_key:
        configured_llms.append(('openai', openai_key, 'OpenAI'))
    if anthropic_key:
        configured_llms.append(('anthropic', anthropic_key, 'Anthropic'))
    if mistral_key:
        configured_llms.append(('mistral', mistral_key, 'Mistral'))
    if ovh_key:
        configured_llms.append(('ovh', ovh_key, 'OVH AI'))
    
    # If 2 or more LLMs are configured, call them in parallel and summarize
    # Limiter à 2 LLM maximum pour éviter la complexité excessive de la synthèse
    if len(configured_llms) >= 2:
        # Limiter à 2 LLM pour la synthèse (priorité: OpenAI, puis Anthropic, puis Mistral, puis OVH)
        llms_to_use = configured_llms[:2]
        logger.info(f"[Recommended Actions] {len(configured_llms)} LLMs configured, using {len(llms_to_use)} for parallel synthesis (limiting to 2 for better results)")
        try:
            # Call selected LLMs in parallel
            tasks = []
            for provider, key, _ in llms_to_use:
                if provider == 'ovh':
                    # OVH needs special handling with endpoint and model
                    tasks.append(call_llm_for_actions(provider, key, prompt))
                else:
                    tasks.append(call_llm_for_actions(provider, key, prompt))
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect valid results
            valid_results = []
            for i, (provider, _, name) in enumerate(llms_to_use):
                result = results[i]
                if result and not isinstance(result, Exception):
                    valid_results.append((name, result))
                elif isinstance(result, Exception):
                    logger.warning(f"[Recommended Actions] {name} LLM call failed: {type(result).__name__}: {result}")
            
            if not valid_results:
                logger.warning("[Recommended Actions] All LLM calls failed, falling back to single LLM logic")
            elif len(valid_results) == 1:
                # Si un seul LLM a réussi, utiliser directement son résultat sans synthèse
                logger.info(f"[Recommended Actions] Only {valid_results[0][0]} succeeded, using its result directly")
                content = valid_results[0][1]
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        actions_data = json.loads(json_match.group())
                        logger.info(f"[Recommended Actions] Generated {len(actions_data)} actions from {valid_results[0][0]}")
                        return [RecommendedAction(**action) for action in actions_data]
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        logger.error(f"[Recommended Actions] Error parsing LLM response: {e}. Content: {content[:500]}")
            else:
                # Choose summarizer: prefer OpenAI, then Anthropic, then Mistral
                summarizer = None
                summarizer_key = None
                summarizer_name = None
                
                if openai_key:
                    summarizer = 'openai'
                    summarizer_key = openai_key
                    summarizer_name = 'OpenAI'
                elif anthropic_key:
                    summarizer = 'anthropic'
                    summarizer_key = anthropic_key
                    summarizer_name = 'Anthropic'
                elif mistral_key:
                    summarizer = 'mistral'
                    summarizer_key = mistral_key
                    summarizer_name = 'Mistral'
                
                if summarizer and summarizer_key:
                    # Limiter la longueur du prompt de synthèse pour éviter les problèmes
                    results_text = chr(10).join([f'{name} actions:{chr(10)}{result[:2000]}' for name, result in valid_results])
                    
                    summary_prompt = f"""You are analyzing recommended actions from {len(valid_results)} AI models. Below are the actions:

{results_text}

Your task is to synthesize these actions into a single, comprehensive list of {max_actions} best recommended actions. 

Rules:
- Combine similar actions from different models
- Prioritize actions that appear in multiple models
- Keep the best actions based on clarity, actionability, and priority
- Ensure each action has a clear icon, text, and priority
- Do not return an empty array

Format your response as a JSON array with this structure:
[
  {{
    "icon": "🔍",
    "text": "Investigate: [specific issue/product] - [specific detail from posts]",
    "priority": "high"
  }}
]"""
                    
                    summary_content = await call_llm_for_actions(summarizer, summarizer_key, summary_prompt)
                    if summary_content:
                        json_match = re.search(r'\[.*\]', summary_content, re.DOTALL)
                        if json_match:
                            actions_data = json.loads(json_match.group())
                            logger.info(f"[Recommended Actions] Generated {len(actions_data)} actions from summarized LLM results using {summarizer_name}")
                            return [RecommendedAction(**action) for action in actions_data]
        
        except Exception as e:
            logger.error(f"[Recommended Actions] Error in parallel LLM call or summarization: {type(e).__name__}: {e}", exc_info=True)
            # Fall through to single LLM logic
    
    # Single LLM logic (if only 1 LLM is configured, or if parallel call failed)
    try:
        # Try provider-specific first
        if llm_provider == 'ovh' and ovh_key:
            logger.info("[Recommended Actions] Calling OVH AI LLM (provider-specific)")
            content = await call_llm_for_actions('ovh', ovh_key, prompt)
        elif llm_provider == 'anthropic' and anthropic_key:
            logger.info("[Recommended Actions] Calling Anthropic LLM (provider-specific)")
            content = await call_llm_for_actions('anthropic', anthropic_key, prompt)
        elif llm_provider == 'mistral' and mistral_key:
            logger.info("[Recommended Actions] Calling Mistral LLM (provider-specific)")
            content = await call_llm_for_actions('mistral', mistral_key, prompt)
        elif llm_provider == 'openai' and openai_key:
            logger.info("[Recommended Actions] Calling OpenAI LLM (provider-specific)")
            content = await call_llm_for_actions('openai', openai_key, prompt)
        else:
            # Try any available key (prefer OpenAI, then Anthropic, then OVH, then Mistral)
            if openai_key:
                logger.info("[Recommended Actions] Calling OpenAI LLM (fallback order)")
                content = await call_llm_for_actions('openai', openai_key, prompt)
            elif anthropic_key:
                logger.info("[Recommended Actions] Calling Anthropic LLM (fallback order)")
                content = await call_llm_for_actions('anthropic', anthropic_key, prompt)
            elif ovh_key:
                logger.info("[Recommended Actions] Calling OVH AI LLM (fallback order)")
                content = await call_llm_for_actions('ovh', ovh_key, prompt)
            elif mistral_key:
                logger.info("[Recommended Actions] Calling Mistral LLM (fallback order)")
                content = await call_llm_for_actions('mistral', mistral_key, prompt)
            else:
                logger.warning("[Recommended Actions] No LLM API key available, using fallback")
                content = None
        
        if content:
            logger.info(f"[Recommended Actions] LLM returned content (length: {len(content)})")
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                try:
                    actions_data = json.loads(json_match.group())
                    logger.info(f"[Recommended Actions] Successfully parsed {len(actions_data)} actions from LLM response")
                    return [RecommendedAction(**action) for action in actions_data]
                except json.JSONDecodeError as e:
                    logger.warning(f"[Recommended Actions] Failed to parse JSON from LLM response: {e}. Using fallback.")
                    logger.debug(f"[Recommended Actions] JSON match content: {json_match.group()[:500]}")
            else:
                logger.warning("[Recommended Actions] No JSON array found in LLM response. Using fallback.")
                logger.debug(f"[Recommended Actions] LLM response preview: {content[:500]}")
        else:
            logger.warning("[Recommended Actions] LLM returned None or empty content. Using fallback.")
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(f"[Recommended Actions] LLM API authentication failed (401): Invalid or expired API key. Using fallback.")
        else:
            logger.warning(f"[Recommended Actions] LLM API error ({e.response.status_code}): {e}. Using fallback.")
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    except Exception as e:
        logger.warning(f"[Recommended Actions] LLM API error: {type(e).__name__}: {e}. Using fallback.", exc_info=True)
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    
    logger.info("[Recommended Actions] Falling back to rule-based actions")
    return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)


def generate_recommended_actions_fallback(
    posts: List[dict], 
    recent_posts: List[dict], 
    stats: dict,
    max_actions: int = 5
) -> List[RecommendedAction]:
    """Fallback rule-based recommended actions generator."""
    actions = []
    active_filters = stats.get('active_filters', 'All posts')
    filtered_context = stats.get('filtered_context', False)
    
    recent_negative = stats.get('recent_negative', 0)
    total_negative = stats.get('negative', 0)
    top_product = stats.get('top_product', 'N/A')
    top_product_count = stats.get('top_product_count', 0)
    top_issue = stats.get('top_issue', 'N/A')
    top_issue_count = stats.get('top_issue_count', 0)
    
    if stats.get('spike_detected', False):
        context_note = f" (filtered: {active_filters})" if filtered_context else ""
        actions.append(RecommendedAction(
            icon='⚠️',
            text=f'Investigate: Spike in negative feedback - {recent_negative} posts in last 48h{context_note}',
            priority='high'
        ))
    
    if top_product != 'N/A' and top_product_count > 0:
        context_note = f" (in {active_filters})" if filtered_context else ""
        actions.append(RecommendedAction(
            icon='🎁',
            text=f'Review: {top_product} issues - {top_product_count} negative posts{context_note}',
            priority='high' if stats.get('spike_detected', False) or top_product_count > 5 else 'medium'
        ))
    
    if top_issue != 'N/A' and top_issue_count > 2:
        context_note = f" (filtered context)" if filtered_context else ""
        actions.append(RecommendedAction(
            icon='💬',
            text=f'Address: "{top_issue}" related complaints ({top_issue_count} mentions){context_note}',
            priority='medium'
        ))
    
    if len(actions) < max_actions:
        if recent_negative > 0:
            actions.append(RecommendedAction(
                icon='📣',
                text=f'Check: Status page or ongoing incident ({recent_negative} recent negative posts)',
                priority='high' if recent_negative > 5 else 'medium'
            ))
        
        if total_negative > 10:
            actions.append(RecommendedAction(
                icon='💬',
                text='Prepare: Support macro / canned response for common issues',
                priority='medium'
            ))
        
        if filtered_context and len(actions) < max_actions:
            actions.append(RecommendedAction(
                icon='🔍',
                text=f'Note: Analysis filtered to {active_filters}',
                priority='low'
            ))
    
    # Always return at least one action if there are posts, even if no specific patterns detected
    if len(actions) == 0 and len(posts) > 0:
        actions.append(RecommendedAction(
            icon='📊',
            text=f'Monitor: {total_negative} negative posts out of {len(posts)} total posts analyzed',
            priority='low'
        ))
    
    return actions[:max_actions]


@router.post("/generate-improvement-ideas", response_model=ImprovementIdeasResponse)
async def generate_improvement_ideas(request: ImprovementIdeaRequest):
    """Generate product improvement ideas based on customer feedback posts using LLM."""
    try:
        openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
        api_key = openai_key or anthropic_key or mistral_key
        llm_available = bool(api_key) or (llm_provider not in ['openai', 'anthropic', 'mistral'])
        
        ideas = await generate_ideas_with_llm(request.posts, request.max_ideas)
        return ImprovementIdeasResponse(ideas=ideas, llm_available=llm_available)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")


@router.post("/recommended-actions", response_model=RecommendedActionsResponse)
async def get_recommended_actions(request: RecommendedActionRequest):
    """Generate recommended actions based on customer feedback using LLM."""
    try:
        openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
        api_key = openai_key or anthropic_key or mistral_key
        llm_available = bool(api_key) or (llm_provider not in ['openai', 'anthropic', 'mistral'])
        
        logger.info(f"[Recommended Actions] Generating actions - Posts: {len(request.posts)}, Recent: {len(request.recent_posts)}, LLM available: {llm_available}")
        
        actions = await generate_recommended_actions_with_llm(
            request.posts, 
            request.recent_posts, 
            request.stats, 
            request.max_actions
        )
        
        logger.info(f"[Recommended Actions] Generated {len(actions)} actions")
        for i, action in enumerate(actions):
            logger.info(f"  Action {i+1}: {action.icon} {action.text} (priority: {action.priority})")
        
        return RecommendedActionsResponse(actions=actions, llm_available=llm_available)
    except Exception as e:
        logger.error(f"[Recommended Actions] Error generating actions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate recommended actions: {str(e)}")


async def generate_whats_happening_insights_with_llm(
    posts: List[dict],
    stats: dict,
    active_filters: str = "",
    analysis_focus: str = ""
) -> Tuple[List[WhatsHappeningInsight], bool]:
    """
    Generate What's Happening insights using LLM API.
    Returns: (insights, used_fallback) where used_fallback is True if fallback was used.
    """
    """Generate What's Happening insights using LLM API."""
    # Récupérer les clés API depuis la base de données (priorité) ou variables d'environnement
    # Ne pas utiliser load_dotenv avec override=True car cela peut écraser les clés en mémoire
    
    # Prepare posts for analysis (focus on negative posts and recent ones)
    negative_posts = [p for p in posts if p.get('sentiment_label') == 'negative']
    recent_posts = [p for p in posts if p.get('created_at')]
    # Sort by date, most recent first
    recent_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    posts_for_analysis = (negative_posts[:50] if negative_posts else recent_posts[:50])  # Increased from 20 to 50
    
    posts_summary = []
    for post in posts_for_analysis:
        posts_summary.append({
            'content': (post.get('content', '') or '')[:800],  # Increased from 400 to 800 for more context
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown'),
            'created_at': post.get('created_at', ''),
            'language': post.get('language', 'unknown')
        })
    
    total = stats.get('total', len(posts))
    positive = stats.get('positive', 0)
    negative = stats.get('negative', 0)
    neutral = stats.get('neutral', 0)
    recent_negative = stats.get('recent_negative', 0)
    recent_total = stats.get('recent_total', 0)
    spike_detected = stats.get('spike_detected', False)
    
    # Extract search term from active_filters or stats
    search_term = stats.get('search_term', '')
    if not search_term and active_filters:
        # Try to extract search term from active_filters string (format: 'Search: "term"')
        search_match = re.search(r'Search:\s*"([^"]+)"', active_filters)
        if search_match:
            search_term = search_match.group(1)
    
    # Build focus instruction based on analysis_focus setting
    focus_instruction = ""
    if analysis_focus:
        focus_instruction = f"\n\nANALYSIS FOCUS: The user wants to focus the analysis on: {analysis_focus}. Prioritize insights related to this focus area while still providing a comprehensive analysis."
    
    # Build search term instruction
    search_instruction = ""
    if search_term:
        search_instruction = f"\n\nCRITICAL: The user is searching for posts containing \"{search_term}\". ALL insights must be specifically related to \"{search_term}\" and based ONLY on posts that mention or relate to \"{search_term}\". Do NOT generate insights about topics unrelated to \"{search_term}\"."
    
    prompt = f"""You are an OVHcloud customer feedback analyst. Your task is to analyze customer feedback and generate ACTIONABLE, PRIORITY-FOCUSED insights that directly identify what needs immediate attention.

IMPORTANT: Generate ALL insights, titles, descriptions, and content in ENGLISH only.

CONTEXT:
- Active filters: {active_filters if active_filters else "All posts (no filters)"}
- Search term: "{search_term}" {'(user is specifically searching for this - ALL insights must relate to this term)' if search_term else '(no specific search term)'}
- Total posts analyzed: {total} (Positive: {positive}, Negative: {negative}, Neutral: {neutral})
- Recent posts (last 48h): {recent_total} total, {recent_negative} negative
- Spike detected: {spike_detected} {'⚠️ Significant increase in negative feedback!' if spike_detected else ''}
{focus_instruction}
{search_instruction}

DETAILED POSTS TO ANALYZE (READ EACH ONE CAREFULLY TO EXTRACT CONCRETE PROBLEMS):
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

CRITICAL ANALYSIS REQUIREMENTS - ORIENTED "ACTION":
1. **READ AND PARSE EACH POST**: Understand the ACTUAL problems customers are experiencing. Extract concrete issues, not generic complaints.
2. **IDENTIFY ACTIONABLE PROBLEMS**: Find specific, fixable issues based on what customers are ACTUALLY saying in the posts. Avoid generic categories like "Support issues" or "Product problems" - be specific about what the problem is.
3. **PRIORITIZE BY IMPACT**: Which problems affect the most customers? Which need immediate attention?
4. **BE PRODUCT-SPECIFIC**: Identify the exact product/service causing issues based on what's mentioned in the posts.
5. **BE TIMELINE-SPECIFIC**: Reference the filtered period. Are these recent issues? Is there a trend?

DYNAMIC INSIGHT GENERATION:
Analyze the posts and generate 2-4 insights that reflect what you ACTUALLY find. The insights should be:
- Based on REAL problems mentioned in the posts (not generic categories)
- Actionable and specific (what exactly is the problem?)
- Prioritized by impact and frequency
- Relevant to the filtered context (product, time period, etc.)

Generate insights dynamically based on what you find. Common insight types include:
- Product-specific issues (if a product is frequently mentioned)
- Specific problems or pain points (extracted from actual post content)
- Spike alerts (if spike_detected is true)
- Emerging patterns or trends
- Priority action items

Format your response as a JSON array with this structure (ALL TEXT IN ENGLISH):
[
  {{
    "type": "top_product|top_issue|spike|trend|priority",
    "title": "[ACTIONABLE PROBLEM STATEMENT - be specific about what the problem is, based on actual posts]",
    "description": "[Explain the problem based on ACTUAL post content. Quote or paraphrase what customers are saying. Include counts/percentages if relevant. Explain why this is a priority and what should be done.]",
    "icon": "🎁|💬|⚠️|📊|🎯",
    "metric": "[percentage or count if relevant, empty string otherwise]",
    "count": [actual_number if relevant, 0 otherwise]
  }}
]

CRITICAL INSTRUCTIONS:
- Generate ALL content in ENGLISH only
- READ EACH POST CAREFULLY and extract REAL, ACTIONABLE problems from the actual content
- Base ALL insights on ACTUAL content from the posts provided - quote or reference specific issues mentioned
- Be SPECIFIC and ACTIONABLE: Use exact product names, specific problems, concrete examples from the posts
- Generate insights DYNAMICALLY based on what you find - don't force insights that aren't present in the data
- Calculate percentages and counts ACCURATELY based on the data provided
- If a filter is active, acknowledge it in the insights and ensure insights are specific to the filtered context
- If analysis_focus is provided, prioritize insights related to that focus area
- Use appropriate icons: 🎁 for products, 💬 for issues, ⚠️ for alerts, 📊 for trends, 🎯 for priorities
- DO NOT make generic statements - every insight must reference actual problems from posts
- DO NOT use placeholder examples - generate insights based on what you actually find in the posts
- Prioritize insights that can lead to immediate action"""

    # Récupérer les clés API depuis la base de données en priorité
    openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
    
    logger.info(f"generate_whats_happening_insights_with_llm: OpenAI key set: {bool(openai_key)}, Anthropic key set: {bool(anthropic_key)}, Mistral key set: {bool(mistral_key)}, OVH key set: {bool(ovh_key)}, Provider: {llm_provider}")
    logger.info(f"generate_whats_happening_insights_with_llm: OVH endpoint: {ovh_endpoint}, OVH model: {ovh_model}")
    
    if not openai_key and not anthropic_key and not mistral_key and not ovh_key:
        logger.error("generate_whats_happening_insights_with_llm: No API keys available, raising HTTPException")
        raise HTTPException(
            status_code=503,
            detail="LLM analysis unavailable: No API keys configured. Please configure at least one LLM API key (OpenAI, Anthropic, Mistral, or OVH) in Settings to enable AI-powered insights."
        )
    
    # Helper function to call LLM
    async def call_llm_for_insights(provider: str, api_key: str, prompt: str, endpoint_url: str = None, model_name: str = None) -> Optional[str]:
        """Call a single LLM and return the response content."""
        logger.info(f"call_llm_for_insights: Calling {provider} API (key length: {len(api_key) if api_key else 0})")
        if provider == 'ovh':
            logger.info(f"call_llm_for_insights: OVH endpoint_url={endpoint_url}, model_name={model_name}, ovh_endpoint={ovh_endpoint}, ovh_model={ovh_model}")
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if provider == 'openai':
                    response = await client.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud customer feedback analyst. Generate key insights based on customer feedback posts.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"OpenAI API call successful, content length: {len(content)}")
                    return content
                
                elif provider == 'anthropic':
                    response = await client.post(
                        'https://api.anthropic.com/v1/messages',
                        headers={
                            'x-api-key': api_key,
                            'anthropic-version': '2023-06-01',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                            'max_tokens': 2000,
                            'messages': [
                                {'role': 'user', 'content': prompt}
                            ]
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['content'][0]['text']
                    logger.info(f"Anthropic API call successful, content length: {len(content)}")
                    return content
                
                elif provider == 'mistral':
                    response = await client.post(
                        'https://api.mistral.ai/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('MISTRAL_MODEL', 'mistral-small'),
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud customer feedback analyst. Generate key insights based on customer feedback posts.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"Mistral API call successful, content length: {len(content)}")
                    return content
                
                elif provider == 'ovh':
                    # OVH AI Endpoints uses OpenAI-compatible API
                    url = endpoint_url or ovh_endpoint
                    model = normalize_ovh_model_name(model_name or ovh_model)
                    
                    # Check if model is configured
                    if not model:
                        raise HTTPException(
                            status_code=503,
                            detail="OVH AI model not configured. Please select a valid model in Settings (e.g., Llama-3.1-70B-Instruct, Qwen-2.5-72B-Instruct)."
                        )
                    
                    response = await client.post(
                        f'{url}/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': model,
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud customer feedback analyst. Generate key insights based on customer feedback posts.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    logger.info(f"OVH AI API call successful, content length: {len(content)}")
                    return content
        except httpx.HTTPStatusError as e:
            error_text = e.response.text[:500] if hasattr(e.response, 'text') else str(e)
            logger.error(f"{provider} API HTTP error: {e.response.status_code} - {error_text}")
            
            # Special handling for 404 model_not_found errors
            if e.response.status_code == 404 and provider == 'ovh':
                try:
                    error_json = e.response.json()
                    if error_json.get('error', {}).get('code') == 'model_not_found':
                        model_name = error_json.get('error', {}).get('message', '').split('`')[1] if '`' in error_json.get('error', {}).get('message', '') else 'unknown'
                        raise HTTPException(
                            status_code=503,
                            detail=f"OVH AI model '{model_name}' not found on your endpoint. Please check available models in Settings and update the model name. Common models: Llama-3.1-70B-Instruct, Qwen-2.5-72B-Instruct, or check your OVH AI Endpoints documentation."
                        )
                except (ValueError, KeyError, IndexError):
                    pass
            
            # Propager l'erreur HTTP spécifique au lieu de retourner None
            raise HTTPException(
                status_code=503,
                detail=f"{provider} API error ({e.response.status_code}): {error_text}. Please check your API key and model configuration."
            )
        except httpx.TimeoutException as e:
            logger.error(f"{provider} API timeout error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"{provider} API timeout: The request took too long. Please try again."
            )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"{provider} API error: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"{provider} API error: {str(e)}. Please check your API key and try again."
            )
    
    # If 2 or more LLMs are configured (and no specific provider is set), call them in parallel and summarize
    configured_llms = []
    if openai_key:
        configured_llms.append(('openai', openai_key, 'OpenAI'))
    if anthropic_key:
        configured_llms.append(('anthropic', anthropic_key, 'Anthropic'))
    if mistral_key:
        configured_llms.append(('mistral', mistral_key, 'Mistral'))
    if ovh_key:
        configured_llms.append(('ovh', ovh_key, 'OVH AI'))
    
    # Only use parallel + summarize if 2+ LLMs are configured AND no specific provider is set
    # Limiter à 2 LLM maximum pour éviter la complexité excessive de la synthèse
    if len(configured_llms) >= 2 and not llm_provider:
        # Limiter à 2 LLM pour la synthèse (priorité: OpenAI, puis Anthropic, puis Mistral, puis OVH)
        llms_to_use = configured_llms[:2]
        logger.info(f"{len(configured_llms)} LLMs configured, using {len(llms_to_use)} for parallel synthesis (limiting to 2 for better results)")
        
        try:
            # Call selected LLMs in parallel
            import time
            parallel_start = time.time()
            tasks = []
            for provider, key, _ in llms_to_use:
                if provider == 'ovh':
                    # OVH needs special handling with endpoint and model
                    tasks.append(call_llm_for_insights(provider, key, prompt, ovh_endpoint, ovh_model))
                else:
                    tasks.append(call_llm_for_insights(provider, key, prompt))
            logger.info(f"Calling {len(tasks)} LLMs in parallel...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            parallel_elapsed = time.time() - parallel_start
            logger.info(f"Parallel LLM calls completed in {parallel_elapsed:.2f}s")
            
            # Collect valid results
            valid_results = []
            for i, (provider, _, name) in enumerate(llms_to_use):
                result = results[i]
                if result and not isinstance(result, Exception):
                    valid_results.append((name, result))
                    logger.info(f"{name} LLM call succeeded")
                elif isinstance(result, Exception):
                    logger.warning(f"{name} LLM call failed: {type(result).__name__}: {result}")
            
            if not valid_results:
                logger.warning("All LLM calls failed, falling back to single LLM logic")
            elif len(valid_results) == 1:
                # Si un seul LLM a réussi, utiliser directement son résultat sans synthèse
                logger.info(f"Only {valid_results[0][0]} succeeded, using its result directly")
                content = valid_results[0][1]
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    try:
                        insights_data = json.loads(json_match.group())
                        logger.info(f"Generated {len(insights_data)} insights from {valid_results[0][0]}")
                        if insights_data:
                            return [WhatsHappeningInsight(**insight) for insight in insights_data], False
                    except (json.JSONDecodeError, KeyError, TypeError) as e:
                        logger.error(f"Error parsing LLM response: {e}. Content: {content[:500]}")
            else:
                # Use the first available LLM to summarize (prefer OpenAI, then Anthropic, then OVH, then Mistral)
                summarizer = None
                summarizer_key = None
                summarizer_name = None
                
                if openai_key:
                    summarizer = 'openai'
                    summarizer_key = openai_key
                    summarizer_name = 'OpenAI'
                elif anthropic_key:
                    summarizer = 'anthropic'
                    summarizer_key = anthropic_key
                    summarizer_name = 'Anthropic'
                elif ovh_key:
                    summarizer = 'ovh'
                    summarizer_key = ovh_key
                    summarizer_name = 'OVH AI'
                elif mistral_key:
                    summarizer = 'mistral'
                    summarizer_key = mistral_key
                    summarizer_name = 'Mistral'
                
                if summarizer and summarizer_key:
                    # Limiter la longueur du prompt de synthèse pour éviter les problèmes
                    results_text = chr(10).join([f'{name} insights:{chr(10)}{result[:2000]}' for name, result in valid_results])
                    
                    summary_prompt = f"""You are analyzing customer feedback insights from {len(valid_results)} AI models. Below are the insights:

{results_text}

Your task is to synthesize these insights into a single, comprehensive list of 2-4 best insights. 

Rules:
- Combine similar insights from different models
- Prioritize insights that appear in multiple models
- Keep the best insights based on clarity, actionability, and impact
- Ensure each insight has a clear type, title, description, icon, metric, and count
- Do not return an empty array

Format your response as a JSON array with this structure (ALL TEXT IN ENGLISH):
[
  {{
    "type": "top_product|top_issue|spike|trend|priority",
    "title": "[ACTIONABLE PROBLEM STATEMENT]",
    "description": "[Explain the problem based on the insights. Include counts/percentages if relevant.]",
    "icon": "🎁|💬|⚠️|📊|🎯",
    "metric": "[percentage or count if relevant, empty string otherwise]",
    "count": [actual_number if relevant, 0 otherwise]
  }}
]"""
                    
                    if summarizer == 'ovh':
                        summary_content = await call_llm_for_insights(summarizer, summarizer_key, summary_prompt, ovh_endpoint, ovh_model)
                    else:
                        summary_content = await call_llm_for_insights(summarizer, summarizer_key, summary_prompt)
                    if summary_content:
                        json_match = re.search(r'\[.*\]', summary_content, re.DOTALL)
                        if json_match:
                            try:
                                insights_data = json.loads(json_match.group())
                                logger.info(f"Generated {len(insights_data)} insights from summarized LLM results ({len(valid_results)} models)")
                                if insights_data:
                                    return [WhatsHappeningInsight(**insight) for insight in insights_data], False
                                else:
                                    logger.warning("Summarized LLM response returned empty insights array")
                            except (json.JSONDecodeError, KeyError, TypeError) as e:
                                logger.error(f"Error parsing summarized LLM response: {e}. Content: {summary_content[:500]}")
                        else:
                            logger.warning(f"No JSON array found in summarized LLM response. Content: {summary_content[:500]}")
        
        except Exception as e:
            logger.error(f"Error in parallel LLM call or summarization: {type(e).__name__}: {e}", exc_info=True)
            # Fall through to single LLM logic
    
    # Single LLM logic (if only 1 is configured, or if parallel call failed)
    # Priorité: Si llm_provider est défini, l'utiliser. Sinon, utiliser le premier disponible (OpenAI > Anthropic > Mistral)
    try:
        # Déterminer quel LLM utiliser
        provider_to_use = None
        api_key_to_use = None
        
        # Si un provider spécifique est défini, vérifier s'il a une clé disponible
        if llm_provider:
            if llm_provider == 'ovh' and ovh_key:
                provider_to_use = 'ovh'
                api_key_to_use = ovh_key
            elif llm_provider == 'openai' and openai_key:
                provider_to_use = 'openai'
                api_key_to_use = openai_key
            elif llm_provider == 'anthropic' and anthropic_key:
                provider_to_use = 'anthropic'
                api_key_to_use = anthropic_key
            elif llm_provider == 'mistral' and mistral_key:
                provider_to_use = 'mistral'
                api_key_to_use = mistral_key
            else:
                # Le provider spécifié n'a pas de clé, utiliser le premier disponible
                logger.warning(f"LLM provider '{llm_provider}' specified but no key available, using first available LLM")
                if openai_key:
                    provider_to_use = 'openai'
                    api_key_to_use = openai_key
                elif anthropic_key:
                    provider_to_use = 'anthropic'
                    api_key_to_use = anthropic_key
                elif ovh_key:
                    provider_to_use = 'ovh'
                    api_key_to_use = ovh_key
                elif mistral_key:
                    provider_to_use = 'mistral'
                    api_key_to_use = mistral_key
        else:
            # Sinon, utiliser le premier disponible (priorité: OpenAI > Anthropic > OVH > Mistral)
            if openai_key:
                provider_to_use = 'openai'
                api_key_to_use = openai_key
            elif anthropic_key:
                provider_to_use = 'anthropic'
                api_key_to_use = anthropic_key
            elif ovh_key:
                provider_to_use = 'ovh'
                api_key_to_use = ovh_key
            elif mistral_key:
                provider_to_use = 'mistral'
                api_key_to_use = mistral_key
        
        if provider_to_use and api_key_to_use:
            logger.info(f"Using single LLM: {provider_to_use} (key length: {len(api_key_to_use)}, key starts with: {api_key_to_use[:10] if len(api_key_to_use) > 10 else 'short'})")
            try:
                if provider_to_use == 'ovh':
                    content = await call_llm_for_insights(provider_to_use, api_key_to_use, prompt, ovh_endpoint, ovh_model)
                else:
                    content = await call_llm_for_insights(provider_to_use, api_key_to_use, prompt)
                logger.info(f"LLM call completed, content received: {bool(content)}, content length: {len(content) if content else 0}")
                
                if content:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        try:
                            insights_data = json.loads(json_match.group())
                            logger.info(f"Parsed {len(insights_data)} insights from {provider_to_use} response")
                            if insights_data:
                                logger.info(f"Successfully generated {len(insights_data)} insights from {provider_to_use}, returning with used_fallback=False")
                                return [WhatsHappeningInsight(**insight) for insight in insights_data], False
                            else:
                                logger.warning(f"{provider_to_use} returned empty insights array")
                        except (json.JSONDecodeError, KeyError, TypeError) as e:
                            logger.error(f"Error parsing {provider_to_use} response: {e}. Content: {content[:500]}")
                            raise HTTPException(
                                status_code=503,
                                detail=f"LLM analysis failed: Invalid response format from {provider_to_use}. Please try again."
                            )
                    else:
                        logger.warning(f"No JSON array found in {provider_to_use} response. Content length: {len(content)}, first 500 chars: {content[:500]}")
                        raise HTTPException(
                            status_code=503,
                            detail=f"LLM analysis failed: {provider_to_use} did not return valid JSON. Please check your API key and try again."
                        )
                else:
                    logger.error(f"{provider_to_use} returned None or empty content")
                    raise HTTPException(
                        status_code=503,
                        detail=f"LLM analysis failed: {provider_to_use} returned no content. Please check your API key and try again."
                    )
            except HTTPException:
                # Re-raise HTTP exceptions (from call_llm_for_insights or parsing errors)
                raise
            except Exception as e:
                logger.error(f"Exception during LLM call to {provider_to_use}: {type(e).__name__}: {e}", exc_info=True)
                raise HTTPException(
                    status_code=503,
                    detail=f"{provider_to_use} API error: {str(e)}. Please check your API key and try again."
                )
                raise HTTPException(
                    status_code=503,
                    detail=f"LLM analysis failed: {provider_to_use} API error: {str(e)}. Please check your API key and try again."
                )
        else:
            logger.error(f"No LLM provider selected. provider_to_use: {provider_to_use}, api_key_to_use: {bool(api_key_to_use)}, openai_key: {bool(openai_key)}, anthropic_key: {bool(anthropic_key)}, mistral_key: {bool(mistral_key)}")
            raise HTTPException(
                status_code=503,
                detail="LLM analysis failed: No LLM provider available. Please configure at least one LLM API key in Settings."
            )
    except HTTPException:
        # Re-raise HTTP exceptions (like the one above for no API keys)
        raise
    except Exception as e:
        logger.error(f"LLM API error: {type(e).__name__}: {e}. Raising HTTPException.", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"LLM analysis failed: {str(e)}. Please check your API keys and try again."
        )


def generate_whats_happening_fallback(
    posts: List[dict],
    stats: dict,
    active_filters: str = ""
) -> List[WhatsHappeningInsight]:
    """Fallback rule-based insights generator."""
    logger.warning(f"Using fallback insights generator (no LLM available). Posts: {len(posts)}, Stats: {stats}, Filters: {active_filters}")
    insights = []
    
    negative = stats.get('negative', 0)
    recent_negative = stats.get('recent_negative', 0)
    total = stats.get('total', len(posts))
    spike_detected = stats.get('spike_detected', False)
    
    # Spike alert
    if spike_detected and recent_negative > 0:
        spike_percentage = stats.get('spike_percentage', 0)
        insights.append(WhatsHappeningInsight(
            type="spike",
            title="Spike in Negative Feedback Detected",
            description=f"{spike_percentage if spike_percentage > 0 else 'Significant'}% more than average. {recent_negative} negative posts in past 48h.",
            icon="⚠️",
            metric=f"+{spike_percentage}%" if spike_percentage > 0 else "",
            count=recent_negative
        ))
    
    # Top product (simplified fallback)
    top_product = stats.get('top_product', 'N/A')
    top_product_count = stats.get('top_product_count', 0)
    if top_product != 'N/A' and top_product_count > 0:
        top_product_percentage = stats.get('top_product_percentage', 0)
        insights.append(WhatsHappeningInsight(
            type="top_product",
            title=f"Top Product Impacted: {top_product}",
            description=f"{top_product_percentage}% of negative posts are relating to {top_product} issues.",
            icon="🎁",
            metric=f"{top_product_percentage}%",
            count=top_product_count
        ))
    
    # Top issue (simplified fallback)
    top_issue = stats.get('top_issue', 'N/A')
    top_issue_count = stats.get('top_issue_count', 0)
    if top_issue != 'N/A' and top_issue_count > 0:
        insights.append(WhatsHappeningInsight(
            type="top_issue",
            title=f'Top Issue: "{top_issue.capitalize()}"',
            description=f"{top_issue_count} posts mention issues related to {top_issue}.",
            icon="💬",
            metric="",
            count=top_issue_count
        ))
    
    # Si aucun insight n'a été généré, créer au moins un insight informatif
    if not insights and total > 0:
        positive = stats.get('positive', 0)
        neutral = stats.get('neutral', 0)
        filter_note = f" (filtered: {active_filters})" if active_filters and active_filters != "All posts (no filters)" else ""
        insights.append(WhatsHappeningInsight(
            type="trend",
            title=f"Analysis of {total} posts{filter_note}",
            description=f"Analyzed {total} posts ({positive} positive, {negative} negative, {neutral} neutral). No significant patterns detected at this time.",
            icon="📊",
            metric="",
            count=total
        ))
        logger.info(f"Added default insight for {total} posts with filters: {active_filters}")
    
    logger.info(f"Fallback generated {len(insights)} insights")
    return insights


@router.post("/whats-happening", response_model=WhatsHappeningResponse)
async def get_whats_happening(request: WhatsHappeningRequest):
    """Generate What's Happening insights based on filtered posts using LLM."""
    import time
    start_time = time.time()
    try:
        # Récupérer les clés API depuis la base de données (priorité) ou variables d'environnement
        try:
            openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
        except Exception as e:
            logger.error(f"Error getting LLM API keys: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="LLM analysis unavailable: Error retrieving API keys. Please check your configuration."
            )
        
        api_key = openai_key or anthropic_key or mistral_key or ovh_key
        
        # Si pas de clés API, on lève une exception (pas de fallback)
        if not api_key:
            logger.error("get_whats_happening: No LLM API keys configured, raising HTTPException")
            raise HTTPException(
                status_code=503,
                detail="LLM analysis unavailable: No API keys configured. Please configure at least one LLM API key (OpenAI, Anthropic, Mistral, or OVH) in Settings to enable AI-powered insights."
            )
        
        logger.info(f"get_whats_happening: OpenAI key set: {bool(openai_key)}, Anthropic key set: {bool(anthropic_key)}, Mistral key set: {bool(mistral_key)}, OVH key set: {bool(ovh_key)}, Provider: {llm_provider}")
        logger.info(f"get_whats_happening: OpenAI key length: {len(openai_key) if openai_key else 0}, Anthropic key length: {len(anthropic_key) if anthropic_key else 0}, Mistral key length: {len(mistral_key) if mistral_key else 0}, OVH key length: {len(ovh_key) if ovh_key else 0}, OVH model: {ovh_model}")
        logger.info(f"get_whats_happening: Starting LLM analysis for {len(request.posts)} posts")
        
        # Cette fonction peut lever une HTTPException si pas de clés API ou si les appels LLM échouent
        try:
            insights, _ = await generate_whats_happening_insights_with_llm(
                request.posts,
                request.stats,
                request.active_filters,
                request.analysis_focus or ""
            )
        except HTTPException:
            # Re-raise HTTPException (like 503 for no API keys) without modification
            raise
        except Exception as e:
            logger.error(f"Error in generate_whats_happening_insights_with_llm: {type(e).__name__}: {e}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"LLM analysis failed: {str(e)}. Please check your API keys and try again."
            )
        
        elapsed_time = time.time() - start_time
        logger.info(f"get_whats_happening: LLM analysis completed in {elapsed_time:.2f}s, generated {len(insights)} insights")
        logger.info(f"get_whats_happening: Insight titles: {[insight.title for insight in insights]}")
        
        # Toujours True car on a vérifié qu'il y a des clés API au début et pas de fallback
        logger.info(f"get_whats_happening: Returning response with {len(insights)} insights, llm_available=True")
        return WhatsHappeningResponse(insights=insights, llm_available=True)
    except HTTPException:
        # Re-raise HTTPException (like 503 for no API keys) without modification
        raise
    except Exception as e:
        logger.error(f"Failed to generate What's Happening insights: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


@router.get("/improvements-summary")
async def get_improvements_summary():
    """Generate a concise LLM summary of top improvement opportunities."""
    try:
        pain_points_response = await get_pain_points(days=30, limit=5)
        pain_points = pain_points_response.pain_points if hasattr(pain_points_response, 'pain_points') else []
        
        if not pain_points:
            return {"summary": "No improvement opportunities identified at this time."}
        
        pain_points_text = "\n".join([
            f"- {pp.title}: {pp.description} ({pp.posts_count} posts)"
            for pp in pain_points[:5]
        ])
        
        prompt = f"""Analyze the following improvement opportunities based on OVH customer feedback and generate ONE concise sentence (maximum 120 characters) that summarizes the main improvement ideas.

Identified opportunities:
{pain_points_text}

Generate a sentence in English that summarizes the top improvement ideas in a clear and actionable way. Generate ONLY the sentence, without JSON formatting or quotes."""
        
        openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
        
        # Determine which provider to use
        # Priority: LLM_PROVIDER env var > available API keys
        if llm_provider == 'anthropic' or (not llm_provider and anthropic_key and not openai_key):
            # Use Anthropic
            api_key = anthropic_key
            if api_key:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            'https://api.anthropic.com/v1/messages',
                            headers={
                                'x-api-key': api_key,
                                'anthropic-version': '2023-06-01',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                                'max_tokens': 150,
                                'messages': [
                                    {'role': 'user', 'content': prompt}
                                ]
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        summary = result['content'][0]['text'].strip()
                        summary = summary.strip('"').strip("'")
                        return {"summary": summary}
                except Exception as e:
                    logger.warning(f"Anthropic API error: {type(e).__name__}: {e}. Using fallback summary.")
                    return {"summary": "Analyzing improvement opportunities..."}
        
        elif llm_provider == 'openai' or (not llm_provider and openai_key):
            # Use OpenAI
            api_key = openai_key
            if api_key:
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            'https://api.openai.com/v1/chat/completions',
                            headers={
                                'Authorization': f'Bearer {api_key}',
                                'Content-Type': 'application/json'
                            },
                            json={
                                'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                                'messages': [
                                    {'role': 'system', 'content': 'You are a product analyst. Generate concise and actionable summaries.'},
                                    {'role': 'user', 'content': prompt}
                                ],
                                'temperature': 0.7,
                                'max_tokens': 150
                            }
                        )
                        response.raise_for_status()
                        result = response.json()
                        summary = result['choices'][0]['message']['content'].strip()
                        summary = summary.strip('"').strip("'")
                        return {"summary": summary}
                except Exception as e:
                    logger.warning(f"OpenAI API error: {type(e).__name__}: {e}. Using fallback summary.")
                    return {"summary": "Analyzing improvement opportunities..."}
        
        return {"summary": "Analyzing improvement opportunities..."}
    except Exception as e:
        logger.error(f"Error generating improvements summary: {e}", exc_info=True)
        return {"summary": "Analyzing improvement opportunities..."}


@router.get("/pain-points", response_model=PainPointsResponse, tags=["Dashboard", "Insights"])
async def get_pain_points_endpoint(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(5, description="Maximum number of pain points to return", ge=1, le=50),
    product: Optional[str] = Query(None, description="Filter by product name (e.g., 'Domain', 'VPS', 'Email')")
):
    """Get recurring pain points from posts in the last N days, optionally filtered by product."""
    try:
        return await get_pain_points(days=days, limit=limit, product=product)
    except Exception as e:
        logger.error(f"Error getting pain points: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get pain points: {str(e)}")


@router.get("/product-opportunities", response_model=ProductDistributionResponse, tags=["Dashboard", "Insights"])
async def get_product_opportunities(
    date_from: Optional[str] = Query(None, description="Filter posts from this date (YYYY-MM-DD)")
):
    """Get product distribution with opportunity scores based on negative feedback."""
    try:
        # Get all posts from database (using a high limit to get all posts)
        posts = db.get_posts(limit=10000, offset=0)
        
        # Filter by date if provided
        if date_from:
            from datetime import datetime
            try:
                # Parse date_from (YYYY-MM-DD format)
                cutoff_date = datetime.strptime(date_from, '%Y-%m-%d')
                filtered_posts = []
                for post in posts:
                    created_at = post.get('created_at', '')
                    if created_at:
                        try:
                            # Ensure created_at is a string (handle datetime objects from DB)
                            if isinstance(created_at, datetime):
                                post_date = created_at
                            elif isinstance(created_at, str):
                                # Parse post date (handle various formats)
                                post_date_str = created_at.replace('Z', '+00:00')
                                try:
                                    post_date = datetime.fromisoformat(post_date_str)
                                except ValueError:
                                    # Try parsing without timezone
                                    post_date = datetime.fromisoformat(created_at.split('T')[0])
                            else:
                                # Skip if created_at is not a string or datetime
                                continue
                            
                            # Compare dates (remove timezone for comparison)
                            post_date_naive = post_date.replace(tzinfo=None) if post_date.tzinfo else post_date
                            if post_date_naive.date() >= cutoff_date.date():
                                filtered_posts.append(post)
                        except (ValueError, AttributeError, TypeError) as e:
                            logger.debug(f"Error parsing post date {created_at}: {e}")
                            continue
                posts = filtered_posts
            except ValueError as e:
                logger.warning(f"Invalid date_from format: {date_from}, error: {e}")
                pass  # Invalid date format, use all posts
        
        # Product keywords to detect - based on OVHcloud.com products
        product_keywords = {
            'VPS': ['vps', 'virtual private server', 'ovh vps', 'vps cloud', 'cloud vps'],
            'Hosting': ['hosting', 'web hosting', 'shared hosting', 'ovh hosting', 'web hosting plan'],
            'Domain': ['domain', 'domaine', 'domain name', 'domain registration', 'domain renewal', 'domain transfer', 'domain expiration', 'registrar', 'bureau d\'enregistrement', 'whois', 'domain management', '.ovh', '.com', '.net', '.org', '.fr', '.eu'],
            'DNS': ['dns', 'dns zone', 'dns anycast', 'dnssec', 'dns record', 'dns configuration', 'nameserver', 'ns record', 'a record', 'mx record', 'cname record', 'txt record', 'dns management', 'dns hosting'],
            'Email': ['email', 'mail', 'smtp', 'imap', 'pop3', 'email hosting', 'exchange', 'email account'],
            'Storage': ['storage', 'object storage', 'backup', 's3', 'cloud storage', 'object storage s3', 'high performance storage'],
            'CDN': ['cdn', 'content delivery', 'content delivery network', 'ovh cdn'],
            'Public Cloud': ['public cloud', 'publiccloud', 'ovh public cloud', 'public cloud instance', 'horizon', 'openstack'],
            'Private Cloud': ['private cloud', 'privatecloud', 'ovh private cloud', 'vmware', 'vsphere', 'hosted private cloud'],
            'Dedicated Server': ['dedicated', 'dedicated server', 'serveur dédié', 'bare metal', 'ovh dedicated', 'server', 'serveur'],
            'API': ['api', 'rest api', 'graphql', 'ovh api', 'api ovh', 'ovhcloud api'],
            'Load Balancer': ['load balancer', 'loadbalancer', 'lb', 'ip load balancing'],
            'Failover IP': ['failover ip', 'failover', 'ip failover', 'additional ip'],
            'SSL Certificate': ['ssl', 'ssl certificate', 'certificate', 'tls', 'https certificate'],
            'Managed Kubernetes': ['kubernetes', 'k8s', 'managed kubernetes', 'ovh kubernetes'],
            'Managed Databases': ['database', 'mysql', 'postgresql', 'mongodb', 'redis', 'managed database', 'ovh database'],
            'Network': ['network', 'vrack', 'vrack', 'private network', 'vlan'],
            'IP': ['ip address', 'ipv4', 'ipv6', 'ip block', 'ip range']
        }
        
        # Group posts by product with their relevance scores
        product_posts = {}
        for post in posts:
            content = (post.get('content', '') or '').lower()
            sentiment = post.get('sentiment_label', 'neutral')
            # Ensure relevance is a float (handle string conversion from DB)
            try:
                relevance = float(post.get('relevance_score', 0.3) or 0.3)
            except (ValueError, TypeError):
                relevance = 0.3  # Default if conversion fails
            
            # Detect products mentioned in post
            # A post can match multiple products, so we count it for all matching products
            matched_products = []
            for product_name, keywords in product_keywords.items():
                if any(keyword in content for keyword in keywords):
                    matched_products.append(product_name)
                    if product_name not in product_posts:
                        product_posts[product_name] = []
                    product_posts[product_name].append({
                        'sentiment': sentiment,
                        'relevance': relevance
                    })
        
        # Calculate opportunity scores and create ProductOpportunity objects
        products = []
        colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#a855f7']
        
        for idx, (product_name, post_list) in enumerate(product_posts.items()):
            total = len(post_list)
            negative_count = sum(1 for p in post_list if p['sentiment'] == 'negative')
            
            # Calculate opportunity score (0-100) based on weighted relevance
            # Nouvelle formule : le score augmente avec le nombre de posts négatifs
            # Chaque post négatif contribue selon sa pertinence, avec un bonus pour le volume
            negative_weighted_sum = 0
            negative_count_calc = 0
            
            for post_data in post_list:
                # Ensure relevance is a float (handle string conversion)
                try:
                    relevance = float(post_data.get('relevance', 0.3) or 0.3)
                except (ValueError, TypeError):
                    relevance = 0.3  # Default if conversion fails
                sentiment = post_data['sentiment']
                
                # Seuls les posts négatifs comptent pour l'opportunité
                if sentiment == 'negative':
                    negative_weighted_sum += relevance
                    negative_count_calc += 1
            
            # Ensure negative_count_calc is an integer
            try:
                negative_count_calc = int(negative_count_calc) if negative_count_calc is not None else 0
            except (ValueError, TypeError):
                negative_count_calc = 0
            
            if negative_count_calc > 0:
                # Pertinence moyenne des posts négatifs
                avg_relevance = negative_weighted_sum / negative_count_calc
                
                # Score de base : nombre de posts négatifs × pertinence moyenne
                # Plus il y a de posts négatifs, plus le score augmente
                # Facteur de volume : logarithme pour éviter que ça explose
                # 1 post = ~10 points, 5 posts = ~30 points, 10 posts = ~50 points, 20+ posts = ~100 points
                volume_factor = min(math.log(float(negative_count_calc) + 1) * 10, 50)  # Max 50 points pour le volume
                
                # Pertinence factor : moyenne pondérée (max 50 points)
                relevance_factor = avg_relevance * 50
                
                # Score final : volume + pertinence (plafonné à 100)
                opportunity_score = min(volume_factor + relevance_factor, 100)
            else:
                opportunity_score = 0
            
            opportunity_score = round(opportunity_score, 1)
            
            color = colors[idx % len(colors)]
            
            products.append(ProductOpportunity(
                product=product_name,
                opportunity_score=opportunity_score,
                negative_posts=negative_count,
                total_posts=total,
                color=color
            ))
        
        # Sort by opportunity score (descending)
        products.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        return ProductDistributionResponse(products=products)
    except Exception as e:
        logger.error(f"Error getting product opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get product opportunities: {str(e)}")


async def generate_improvements_analysis_with_llm(
    pain_points: List[dict],
    products: List[dict],
    total_posts: int,
    posts: List[dict] = None,
    analysis_focus: str = None,
    date_from: str = None,
    date_to: str = None,
    product_filter: str = None
) -> ImprovementsAnalysisResponse:
    """Generate improvements analysis with insights and ROI using LLM."""
    # Récupérer les clés API depuis la base de données (priorité) ou variables d'environnement
    # Ne pas utiliser load_dotenv avec override=True car cela peut écraser les clés en mémoire
    
    # Prepare posts for analysis (focus on negative/neutral posts)
    posts_for_analysis = []
    if posts:
        negative_posts = [p for p in posts if p.get('sentiment_label') in ['negative', 'neutral']]
        posts_for_analysis = negative_posts[:50] if negative_posts else posts[:50]
    
    posts_summary = []
    for post in posts_for_analysis:
        posts_summary.append({
            'content': (post.get('content', '') or '')[:800],  # Increased from 400 to 800 for more context
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown'),
            'created_at': post.get('created_at', ''),
            'language': post.get('language', 'unknown')
        })
    
    # Prepare data for LLM
    pain_points_text = "\n".join([
        f"- {pp.get('title', 'N/A')}: {pp.get('description', '')} ({pp.get('posts_count', 0)} posts)"
        for pp in pain_points[:10]
    ]) if pain_points else "No pain points identified."
    
    products_text = "\n".join([
        f"- {p.get('product', 'N/A')}: {p.get('opportunity_score', 0)}/100 score, {p.get('negative_posts', 0)} negative posts out of {p.get('total_posts', 0)} total"
        for p in products[:10]
    ]) if products else "No product data available."
    
    # Build context information
    context_parts = [f"Total posts analyzed: {total_posts}"]
    if date_from:
        context_parts.append(f"Period: from {date_from}" + (f" to {date_to}" if date_to else ""))
    if product_filter:
        context_parts.append(f"Product filter: {product_filter}")
    
    # Use analysis_focus from parameter, fallback to environment
    focus_value = analysis_focus or os.getenv('ANALYSIS_FOCUS', '')
    focus_instruction = ""
    if focus_value:
        focus_instruction = f"\n\nANALYSIS FOCUS: The user wants to focus the analysis on: {focus_value}. Prioritize insights related to this focus area while still providing a comprehensive analysis."
    
    # Build filter context
    filter_context = ""
    if product_filter:
        filter_context = f"\n\nACTIVE FILTER: Analysis is focused on the product '{product_filter}'. All insights must be specific to this product and based on the filtered posts."
    
    prompt = f"""You are an OVHcloud product improvement analyst. Your task is to analyze customer feedback and generate ACTIONABLE, PRIORITY-FOCUSED insights that directly guide product improvement decisions.

IMPORTANT: Generate ALL insights, titles, descriptions, and content in ENGLISH only.

CONTEXT:
- {', '.join(context_parts)}
- Pain points identified: {len(pain_points)}
- Products with opportunities: {len(products)}
{focus_instruction}
{filter_context}

{'DETAILED POSTS TO ANALYZE (READ EACH ONE CAREFULLY TO EXTRACT CONCRETE PROBLEMS):' if posts_summary else ''}
{json.dumps(posts_summary, indent=2, ensure_ascii=False) if posts_summary else 'No detailed posts provided - use pain points and products data below.'}

PAIN POINTS IDENTIFIED:
{pain_points_text}

PRODUCT OPPORTUNITIES:
{products_text}

CRITICAL ANALYSIS REQUIREMENTS - ORIENTED "ACTION":
1. **READ AND PARSE EACH POST**: Understand the ACTUAL problems customers are experiencing. Extract concrete issues, not generic complaints.
2. **IDENTIFY ACTIONABLE PROBLEMS**: Find specific, fixable issues based on what customers are ACTUALLY saying in the posts. Avoid generic categories - be specific about what the problem is.
3. **PRIORITIZE BY IMPACT**: Which problems affect the most customers? Which have the highest business impact?
4. **BE PRODUCT-SPECIFIC**: If a product filter is active, ALL insights must reference that specific product and problems related to it.
5. **BE TIMELINE-SPECIFIC**: Reference the filtered period. Are these recent issues? Is there a trend?

DYNAMIC INSIGHT GENERATION:
Analyze the posts, pain points, and products data and generate 2-4 insights that reflect what you ACTUALLY find. The insights should be:
- Based on REAL problems mentioned in the posts (not generic categories)
- Actionable and specific (what exactly is the problem?)
- Prioritized by impact and frequency
- Relevant to the filtered context (product, time period, etc.)

Generate insights dynamically based on what you find. Common insight types include:
- Priority action items (what should be fixed first)
- Product-specific issues (if filtering by product or if a product stands out)
- Specific problems or pain points (extracted from actual post content)
- ROI & impact estimates (based on the problems identified)
- Key findings (root causes or patterns)

Format your response as JSON with this structure (ALL TEXT IN ENGLISH):
{{
  "key_findings": [
    "Finding 1: [ACTIONABLE problem extracted from actual posts]",
    "Finding 2: [CONCRETE issue with specific context from posts]",
    "Finding 3: [SPECIFIC problem that needs prioritization, based on post analysis]"
  ],
  "roi_summary": "[2-3 sentences about ROI and customer impact. Reference SPECIFIC problems and products found in the posts. Be concrete about potential benefits based on the actual data.]",
  "insights": [
    {{
      "type": "priority|key_finding|roi|product_issue",
      "title": "[ACTIONABLE PROBLEM STATEMENT - be specific about what the problem is, based on actual posts]",
      "description": "[Explain the problem based on ACTUAL post content. Quote or paraphrase what customers are saying. Explain why this is a priority and what should be done.]",
      "icon": "🎯|💡|💰|🎁",
      "metric": "[percentage or count if relevant, empty string otherwise]",
      "roi_impact": "[Potential impact estimate if relevant, empty string otherwise]"
    }}
  ]
}}

CRITICAL INSTRUCTIONS:
- Generate ALL content in ENGLISH only
- READ EACH POST CAREFULLY and extract REAL, ACTIONABLE problems from the actual content
- Base ALL insights on ACTUAL post content - quote or reference specific issues mentioned
- Be SPECIFIC and ACTIONABLE: Use exact product names, specific problems, concrete examples from the posts
- Generate insights DYNAMICALLY based on what you find - don't force insights that aren't present in the data
- If product_filter is provided, ALL insights must be about that product
- If date filters are provided, acknowledge the time period in insights
- DO NOT make generic statements - every insight must reference actual problems from posts
- DO NOT use placeholder examples - generate insights based on what you actually find in the posts
- Prioritize insights that can lead to immediate action
- Include ROI insights only if you can provide meaningful estimates based on the data"""

    openai_key, anthropic_key, mistral_key, ovh_key, ovh_endpoint, ovh_model, llm_provider = get_llm_api_keys()
    
    if not openai_key and not anthropic_key and not mistral_key and not ovh_key:
        return generate_improvements_analysis_fallback(pain_points, products, total_posts)
    
    # Helper function to call LLM
    async def call_llm(provider: str, api_key: str, prompt: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                if provider == 'openai':
                    response = await client.post(
                        'https://api.openai.com/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud product improvement analyst. Generate specific, actionable insights with ROI estimates.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['choices'][0]['message']['content']
                
                elif provider == 'anthropic':
                    response = await client.post(
                        'https://api.anthropic.com/v1/messages',
                        headers={
                            'x-api-key': api_key,
                            'anthropic-version': '2023-06-01',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                            'max_tokens': 2000,
                            'messages': [
                                {'role': 'user', 'content': prompt}
                            ]
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['content'][0]['text']
                
                elif provider == 'mistral':
                    response = await client.post(
                        'https://api.mistral.ai/v1/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': os.getenv('MISTRAL_MODEL', 'mistral-small'),
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud product improvement analyst. Generate specific, actionable insights with ROI estimates.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['choices'][0]['message']['content']
                
                elif provider == 'ovh':
                    # OVH AI Endpoints uses OpenAI-compatible API
                    model = normalize_ovh_model_name(ovh_model)
                    
                    # Check if model is configured
                    if not model:
                        logger.error("[Improvements Analysis] OVH AI model not configured")
                        return None
                    
                    response = await client.post(
                        f'{ovh_endpoint}/chat/completions',
                        headers={
                            'Authorization': f'Bearer {api_key}',
                            'Content-Type': 'application/json'
                        },
                        json={
                            'model': model,
                            'messages': [
                                {'role': 'system', 'content': 'You are an OVHcloud product improvement analyst. Generate specific, actionable insights with ROI estimates.'},
                                {'role': 'user', 'content': prompt}
                            ],
                            'temperature': 0.7,
                            'max_tokens': 2000
                        }
                    )
                    response.raise_for_status()
                    result = response.json()
                    return result['choices'][0]['message']['content']
        except Exception as e:
            logger.warning(f"{provider} API error: {type(e).__name__}: {e}")
            return None
        return None
    
    # Count configured LLMs
    configured_llms = []
    if openai_key:
        configured_llms.append(('openai', openai_key, 'OpenAI'))
    if anthropic_key:
        configured_llms.append(('anthropic', anthropic_key, 'Anthropic'))
    if mistral_key:
        configured_llms.append(('mistral', mistral_key, 'Mistral'))
    if ovh_key:
        configured_llms.append(('ovh', ovh_key, 'OVH AI'))
    
    # If 2 or more LLMs are configured, call them in parallel and summarize
    # Limiter à 2 LLM maximum pour éviter la complexité excessive de la synthèse
    if len(configured_llms) >= 2:
        # Limiter à 2 LLM pour la synthèse (priorité: OpenAI, puis Anthropic, puis Mistral, puis OVH)
        llms_to_use = configured_llms[:2]
        logger.info(f"[Improvements Analysis] {len(configured_llms)} LLMs configured, using {len(llms_to_use)} for parallel synthesis (limiting to 2 for better results)")
        try:
            # Call selected LLMs in parallel
            tasks = [call_llm(provider, key, prompt) for provider, key, _ in llms_to_use]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Collect valid results
            valid_results = []
            for i, (provider, _, name) in enumerate(llms_to_use):
                result = results[i]
                if result and not isinstance(result, Exception):
                    valid_results.append((name, result))
                elif isinstance(result, Exception):
                    logger.warning(f"[Improvements Analysis] {name} LLM call failed: {type(result).__name__}: {result}")
            
            if not valid_results:
                logger.warning("[Improvements Analysis] All LLM calls failed, falling back to single LLM logic")
            elif len(valid_results) == 1:
                # Si un seul LLM a réussi, utiliser directement son résultat sans synthèse
                logger.info(f"[Improvements Analysis] Only {valid_results[0][0]} succeeded, using its result directly")
                content = valid_results[0][1]
                # Parser le résultat directement (le format dépend de la fonction call_llm)
                try:
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis_data = json.loads(json_match.group())
                        logger.info(f"[Improvements Analysis] Generated analysis from {valid_results[0][0]}")
                        return ImprovementsAnalysisResponse(**analysis_data)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.error(f"[Improvements Analysis] Error parsing LLM response: {e}. Content: {content[:500]}")
            else:
                # Choose summarizer: prefer OpenAI, then Anthropic, then Mistral
                summarizer = None
                summarizer_key = None
                summarizer_name = None
                
                if openai_key:
                    summarizer = 'openai'
                    summarizer_key = openai_key
                    summarizer_name = 'OpenAI'
                elif anthropic_key:
                    summarizer = 'anthropic'
                    summarizer_key = anthropic_key
                    summarizer_name = 'Anthropic'
                elif mistral_key:
                    summarizer = 'mistral'
                    summarizer_key = mistral_key
                    summarizer_name = 'Mistral'
                
                if summarizer and summarizer_key:
                    # Limiter la longueur du prompt de synthèse pour éviter les problèmes
                    results_text = chr(10).join([f'{name} analysis:{chr(10)}{result[:2000]}' for name, result in valid_results])
                    
                    summary_prompt = f"""You are analyzing product improvement insights from {len(valid_results)} AI models. Below are the analyses:

{results_text}

Your task is to synthesize these analyses into a single, comprehensive analysis. Extract the best insights, ROI summary, and key findings.

Rules:
- Combine similar insights from different models
- Prioritize insights that appear in multiple models
- Keep the best insights based on clarity, actionability, and impact
- Ensure the response includes insights, roi_summary, and key_findings
- Do not return empty arrays

Format your response as a JSON object with this structure:
{{
  "insights": [
    {{
      "type": "key_finding|improvement|roi",
      "title": "[ACTIONABLE PROBLEM STATEMENT]",
      "description": "[Explain the problem based on the insights. Include counts/percentages if relevant.]",
      "icon": "💡|🎯|💰",
      "metric": "[percentage or count if relevant, empty string otherwise]",
      "roi_impact": "[ROI estimate if relevant, empty string otherwise]"
    }}
  ],
  "roi_summary": "[Overall ROI summary combining insights from all models]",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
}}"""
                    
                    summary_content = await call_llm(summarizer, summarizer_key, summary_prompt)
                    if summary_content:
                        json_match = re.search(r'\{.*\}', summary_content, re.DOTALL)
                        if json_match:
                            data = json.loads(json_match.group())
                            insights_data = data.get('insights', [])
                            
                            # Match posts to insights based on keywords
                            insights_with_posts = []
                            for insight_data in insights_data:
                                # Extract keywords from insight title and description
                                insight_text = (insight_data.get('title', '') + ' ' + insight_data.get('description', '')).lower()
                                insight_keywords = [w for w in insight_text.split() if len(w) > 3]  # Words longer than 3 chars
                                
                                # Find matching posts
                                matching_post_ids = []
                                if posts:
                                    for post in posts:
                                        post_content = (post.get('content', '') or '').lower()
                                        # Check if any keyword appears in post content
                                        if any(keyword in post_content for keyword in insight_keywords):
                                            post_id = post.get('id')
                                            if post_id and post_id not in matching_post_ids:
                                                matching_post_ids.append(post_id)
                                
                                # Limit to 50 posts max per insight
                                matching_post_ids = matching_post_ids[:50]
                                
                                # Add related_post_ids to insight
                                insight_data['related_post_ids'] = matching_post_ids
                                insights_with_posts.append(ImprovementInsight(**insight_data))
                            
                            logger.info(f"[Improvements Analysis] Generated {len(insights_with_posts)} insights from summarized LLM results using {summarizer_name}")
                            return ImprovementsAnalysisResponse(
                                insights=insights_with_posts,
                                roi_summary=data.get('roi_summary', ''),
                                key_findings=data.get('key_findings', []),
                                llm_available=True
                            )
        
        except Exception as e:
            logger.error(f"[Improvements Analysis] Error in parallel LLM call or summarization: {type(e).__name__}: {e}", exc_info=True)
            # Fall through to single LLM logic
    
    # Single LLM logic (if only 1 LLM is configured, or if parallel call failed)
    try:
        # Try to use configured provider or any available
        content = None
        # Si un provider spécifique est défini, vérifier s'il a une clé disponible
        if llm_provider == 'anthropic' and anthropic_key:
            content = await call_llm('anthropic', anthropic_key, prompt)
        elif llm_provider == 'mistral' and mistral_key:
            content = await call_llm('mistral', mistral_key, prompt)
        elif llm_provider == 'openai' and openai_key:
            content = await call_llm('openai', openai_key, prompt)
        else:
            # Le provider spécifié n'a pas de clé, ou aucun provider spécifié
            # Utiliser le premier disponible (priorité: OpenAI > Anthropic > Mistral)
            if llm_provider and not content:
                logger.warning(f"[Improvements Analysis] LLM provider '{llm_provider}' specified but no key available, using first available LLM")
            if openai_key:
                content = await call_llm('openai', openai_key, prompt)
            elif anthropic_key:
                content = await call_llm('anthropic', anthropic_key, prompt)
            elif mistral_key:
                content = await call_llm('mistral', mistral_key, prompt)
        
        if content:
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                insights_data = data.get('insights', [])
                
                # Match posts to insights based on keywords
                insights_with_posts = []
                for insight_data in insights_data:
                    # Extract keywords from insight title and description
                    insight_text = (insight_data.get('title', '') + ' ' + insight_data.get('description', '')).lower()
                    insight_keywords = [w for w in insight_text.split() if len(w) > 3]  # Words longer than 3 chars
                    
                    # Find matching posts
                    matching_post_ids = []
                    if posts:
                        for post in posts:
                            post_content = (post.get('content', '') or '').lower()
                            # Check if any keyword appears in post content
                            if any(keyword in post_content for keyword in insight_keywords):
                                post_id = post.get('id')
                                if post_id and post_id not in matching_post_ids:
                                    matching_post_ids.append(post_id)
                    
                    # Limit to 50 posts max per insight
                    matching_post_ids = matching_post_ids[:50]
                    
                    # Add related_post_ids to insight
                    insight_data['related_post_ids'] = matching_post_ids
                    insights_with_posts.append(ImprovementInsight(**insight_data))
                
                logger.info(f"[Improvements Analysis] Successfully generated {len(insights_with_posts)} insights from LLM")
                return ImprovementsAnalysisResponse(
                    insights=insights_with_posts,
                    roi_summary=data.get('roi_summary', ''),
                    key_findings=data.get('key_findings', []),
                    llm_available=True
                )
            else:
                logger.error("[Improvements Analysis] No JSON found in LLM response")
                raise HTTPException(
                    status_code=500,
                    detail="LLM did not return valid JSON. Please check your API configuration and try again."
                )
        else:
            logger.error("[Improvements Analysis] LLM returned None or empty content")
            raise HTTPException(
                status_code=500,
                detail="LLM returned empty response. Please check your API keys and try again."
            )
    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise
    except Exception as e:
        logger.error(f"[Improvements Analysis] LLM API error: {type(e).__name__}: {e}. LLM is configured but failed.", exc_info=True)
        # Ne pas utiliser le fallback si le LLM est configuré mais a échoué
        # Retourner une erreur explicite au lieu de données en dur
        raise HTTPException(
            status_code=500,
            detail=f"LLM analysis failed: {str(e)}. Please check your API keys and try again."
        )
    
    # Si on arrive ici, c'est qu'aucune clé API n'est disponible
    logger.warning("[Improvements Analysis] No LLM API keys available, using fallback")
    return generate_improvements_analysis_fallback(pain_points, products, total_posts)


def generate_improvements_analysis_fallback(
    pain_points: List[dict],
    products: List[dict],
    total_posts: int
) -> ImprovementsAnalysisResponse:
    """Fallback analysis when LLM is not available."""
    insights = []
    key_findings = []
    
    if pain_points:
        top_pain_point = max(pain_points, key=lambda x: x.get('posts_count', 0))
        insights.append(ImprovementInsight(
            type='key_finding',
            title=f"Top Pain Point: {top_pain_point.get('title', 'N/A')}",
            description=f"{top_pain_point.get('description', '')} ({top_pain_point.get('posts_count', 0)} posts)",
            icon='💡',
            metric=f"{top_pain_point.get('posts_count', 0)} posts",
            roi_impact="Addressing this could improve customer satisfaction"
        ))
        key_findings.append(f"Top pain point: {top_pain_point.get('title', 'N/A')} with {top_pain_point.get('posts_count', 0)} mentions")
    
    if products:
        top_product = max(products, key=lambda x: x.get('opportunity_score', 0))
        insights.append(ImprovementInsight(
            type='priority',
            title=f"Priority Product: {top_product.get('product', 'N/A')}",
            description=f"Highest opportunity score ({top_product.get('opportunity_score', 0)}/100) with {top_product.get('negative_posts', 0)} negative posts",
            icon='🎯',
            metric=f"{top_product.get('opportunity_score', 0)}/100",
            roi_impact="Focus improvements here for maximum impact"
        ))
        key_findings.append(f"Priority product: {top_product.get('product', 'N/A')} needs attention")
    
    roi_summary = f"Based on {total_posts} posts analyzed, addressing the top {len(pain_points)} pain points could significantly improve customer satisfaction and retention."
    
    return ImprovementsAnalysisResponse(
        insights=insights,
        roi_summary=roi_summary,
        key_findings=key_findings,
        llm_available=False
    )


@router.post("/improvements-analysis", response_model=ImprovementsAnalysisResponse, tags=["Dashboard", "Insights"])
async def get_improvements_analysis(request: ImprovementsAnalysisRequest):
    """Generate comprehensive improvements analysis with insights and ROI using LLM."""
    try:
        # Convert Pydantic models to dicts for LLM function
        pain_points_dicts = [pp.dict() if hasattr(pp, 'dict') else pp for pp in request.pain_points]
        products_dicts = [p.dict() if hasattr(p, 'dict') else p for p in request.products]
        
        return await generate_improvements_analysis_with_llm(
            pain_points_dicts,
            products_dicts,
            request.total_posts,
            posts=request.posts if hasattr(request, 'posts') else [],
            analysis_focus=request.analysis_focus if hasattr(request, 'analysis_focus') else None,
            date_from=request.date_from if hasattr(request, 'date_from') else None,
            date_to=request.date_to if hasattr(request, 'date_to') else None,
            product_filter=request.product_filter if hasattr(request, 'product_filter') else None
        )
    except Exception as e:
        logger.error(f"Error generating improvements analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate improvements analysis: {str(e)}")




