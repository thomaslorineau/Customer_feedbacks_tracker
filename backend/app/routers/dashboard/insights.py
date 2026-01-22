"""LLM-based insights and recommendations endpoints."""
import os
import json
import re
import logging
import asyncio
from typing import List, Optional
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
from ... import db
from fastapi import Query

logger = logging.getLogger(__name__)

router = APIRouter()


async def generate_ideas_with_llm(posts: List[dict], max_ideas: int = 5) -> List[ImprovementIdea]:
    """Generate improvement ideas using LLM API."""
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Reload .env to get latest values
    backend_path = Path(__file__).resolve().parents[3]
    env_path = backend_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
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

    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    mistral_key = os.getenv('MISTRAL_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', '').lower()
    
    logger.info(f"generate_ideas_with_llm: OpenAI key set: {bool(openai_key)}, Anthropic key set: {bool(anthropic_key)}, Mistral key set: {bool(mistral_key)}, Provider: {llm_provider}")
    
    if not openai_key and not anthropic_key and not mistral_key:
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
        except Exception as e:
            logger.warning(f"{provider} API error: {type(e).__name__}: {e}")
            return None
        return None
    
    # If all 3 LLMs are configured, call them in parallel and summarize with OpenAI
    if openai_key and anthropic_key and mistral_key:
        logger.info("All 3 LLMs configured, calling in parallel and summarizing with OpenAI")
        try:
            # Call all 3 in parallel
            results = await asyncio.gather(
                call_llm('openai', openai_key, prompt),
                call_llm('anthropic', anthropic_key, prompt),
                call_llm('mistral', mistral_key, prompt),
                return_exceptions=True
            )
            
            openai_result, anthropic_result, mistral_result = results
            
            # Collect valid results
            valid_results = []
            if openai_result and not isinstance(openai_result, Exception):
                valid_results.append(('OpenAI', openai_result))
            if anthropic_result and not isinstance(anthropic_result, Exception):
                valid_results.append(('Anthropic', anthropic_result))
            if mistral_result and not isinstance(mistral_result, Exception):
                valid_results.append(('Mistral', mistral_result))
            
            if not valid_results:
                raise HTTPException(status_code=500, detail="All LLM calls failed. Please check your API keys.")
            
            # Use OpenAI to summarize the combined results
            summary_prompt = f"""You are analyzing product improvement ideas from multiple AI models. Below are the ideas generated by {len(valid_results)} different AI models:

{chr(10).join([f'{name} ideas:{chr(10)}{result}' for name, result in valid_results])}

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
            
            summary_content = await call_llm('openai', openai_key, summary_prompt)
            if summary_content:
                json_match = re.search(r'\[.*\]', summary_content, re.DOTALL)
                if json_match:
                    ideas_data = json.loads(json_match.group())
                    logger.info(f"Generated {len(ideas_data)} ideas from summarized LLM results")
                    return [ImprovementIdea(**idea) for idea in ideas_data]
        
        except Exception as e:
            logger.error(f"Error in parallel LLM call or summarization: {type(e).__name__}: {e}", exc_info=True)
            # Fall through to single LLM logic
    
    # Single LLM logic (if not all 3 are configured, or if parallel call failed)
    try:
        if llm_provider == 'anthropic' or (not llm_provider and anthropic_key and not openai_key and not mistral_key):
            # Use Anthropic
            if anthropic_key:
                content = await call_llm('anthropic', anthropic_key, prompt)
                if content:
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        ideas_data = json.loads(json_match.group())
                        return [ImprovementIdea(**idea) for idea in ideas_data]
        
        elif llm_provider == 'mistral' or (not llm_provider and mistral_key and not openai_key and not anthropic_key):
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

    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', '').lower()
    
    if not openai_key and not anthropic_key:
        logger.info("[Recommended Actions] No LLM API key configured, returning empty list")
        return []
    
    try:
        if llm_provider == 'anthropic' or (not llm_provider and anthropic_key and not openai_key):
            # Use Anthropic
            api_key = anthropic_key
            if api_key:
                async with httpx.AsyncClient(timeout=60.0) as client:
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
                    
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        actions_data = json.loads(json_match.group())
                        return [RecommendedAction(**action) for action in actions_data]
        
        elif llm_provider == 'openai' or (not llm_provider and openai_key):
            # Use OpenAI
            api_key = openai_key
            if api_key:
                async with httpx.AsyncClient(timeout=60.0) as client:
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
                    
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        actions_data = json.loads(json_match.group())
                        return [RecommendedAction(**action) for action in actions_data]
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(f"LLM API authentication failed (401): Invalid or expired API key. Using fallback.")
        else:
            logger.warning(f"LLM API error ({e.response.status_code}): {e}. Using fallback.")
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    except Exception as e:
        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback.")
        return generate_recommended_actions_fallback(posts, recent_posts, stats, max_actions)
    
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
    
    return actions[:max_actions]


@router.post("/generate-improvement-ideas", response_model=ImprovementIdeasResponse)
async def generate_improvement_ideas(request: ImprovementIdeaRequest):
    """Generate product improvement ideas based on customer feedback posts using LLM."""
    try:
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        llm_available = bool(api_key) or (llm_provider not in ['openai', 'anthropic'])
        
        ideas = await generate_ideas_with_llm(request.posts, request.max_ideas)
        return ImprovementIdeasResponse(ideas=ideas, llm_available=llm_available)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate ideas: {str(e)}")


@router.post("/api/recommended-actions", response_model=RecommendedActionsResponse)
async def get_recommended_actions(request: RecommendedActionRequest):
    """Generate recommended actions based on customer feedback using LLM."""
    try:
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        llm_available = bool(api_key) or (llm_provider not in ['openai', 'anthropic'])
        
        actions = await generate_recommended_actions_with_llm(
            request.posts, 
            request.recent_posts, 
            request.stats, 
            request.max_actions
        )
        return RecommendedActionsResponse(actions=actions, llm_available=llm_available)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate recommended actions: {str(e)}")


async def generate_whats_happening_insights_with_llm(
    posts: List[dict],
    stats: dict,
    active_filters: str = ""
) -> List[WhatsHappeningInsight]:
    """Generate What's Happening insights using LLM API."""
    # Prepare posts for analysis (focus on negative posts and recent ones)
    negative_posts = [p for p in posts if p.get('sentiment_label') == 'negative']
    recent_posts = [p for p in posts if p.get('created_at')]
    # Sort by date, most recent first
    recent_posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    posts_for_analysis = (negative_posts[:20] if negative_posts else recent_posts[:20])
    
    posts_summary = []
    for post in posts_for_analysis:
        posts_summary.append({
            'content': (post.get('content', '') or '')[:400],
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
    
    prompt = f"""You are an OVHcloud customer feedback analyst. Analyze the following customer feedback posts and generate key insights for the "What's Happening" section.

CONTEXT:
- Active filters: {active_filters if active_filters else "All posts (no filters)"}
- Total posts analyzed: {total} (Positive: {positive}, Negative: {negative}, Neutral: {neutral})
- Recent posts (last 48h): {recent_total} total, {recent_negative} negative
- Spike detected: {spike_detected} {'⚠️ Significant increase in negative feedback!' if spike_detected else ''}

POSTS TO ANALYZE:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

Based on this analysis, generate 2-4 key insights. Focus on:
1. **Top Product Impacted**: Which OVH product/service is most frequently mentioned in negative feedback? Be specific (e.g., "VPS", "Hosting", "Billing", "Support", "API", "Domain", etc.). If multiple products are mentioned, identify the most critical one.
2. **Top Issue**: What is the main problem or concern mentioned across these posts? Extract the core issue, not just keywords. Be specific and actionable (e.g., "Payment processing delays", "Server downtime", "Support response time", etc.).
3. **Spike Alert** (if spike_detected is true): Highlight the spike in negative feedback
4. **Trend** (optional): Any notable trend or pattern you observe

Format your response as a JSON array with this structure:
[
  {{
    "type": "top_product",
    "title": "Top Product Impacted: [Product Name]",
    "description": "[Percentage]% of negative posts relate to [Product Name] issues. [Brief explanation based on actual posts]",
    "icon": "🎁",
    "metric": "[percentage]%",
    "count": [number]
  }},
  {{
    "type": "top_issue",
    "title": "Top Issue: [Issue Name]",
    "description": "[Count] posts mention issues related to [Issue]. [Brief explanation based on actual posts]",
    "icon": "💬",
    "metric": "",
    "count": [number]
  }},
  {{
    "type": "spike",
    "title": "Spike in Negative Feedback",
    "description": "[Percentage]% increase in negative feedback. [Count] negative posts in past 48h.",
    "icon": "⚠️",
    "metric": "+[percentage]%",
    "count": [number]
  }}
]

IMPORTANT:
- Base insights on ACTUAL content from the posts, not assumptions
- Be specific and reference actual issues/products mentioned
- If a filter is active, acknowledge it in the insights
- Use appropriate icons (🎁 for products, 💬 for issues, ⚠️ for alerts, 📊 for trends)
- Ensure percentages and counts are accurate based on the data provided"""

    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', '').lower()
    
    if not openai_key and not anthropic_key:
        return generate_whats_happening_fallback(posts, stats, active_filters)
    
    try:
        if llm_provider == 'anthropic' or (not llm_provider and anthropic_key and not openai_key):
            # Use Anthropic
            api_key = anthropic_key
            if api_key:
                async with httpx.AsyncClient(timeout=60.0) as client:
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
                    
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        insights_data = json.loads(json_match.group())
                        return [WhatsHappeningInsight(**insight) for insight in insights_data]
        
        elif llm_provider == 'openai' or (not llm_provider and openai_key):
            # Use OpenAI
            api_key = openai_key
            if api_key:
                async with httpx.AsyncClient(timeout=60.0) as client:
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
                    
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        insights_data = json.loads(json_match.group())
                        return [WhatsHappeningInsight(**insight) for insight in insights_data]
        
        return generate_whats_happening_fallback(posts, stats, active_filters)
    except Exception as e:
        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback.")
        return generate_whats_happening_fallback(posts, stats, active_filters)
    
    return generate_whats_happening_fallback(posts, stats, active_filters)


def generate_whats_happening_fallback(
    posts: List[dict],
    stats: dict,
    active_filters: str = ""
) -> List[WhatsHappeningInsight]:
    """Fallback rule-based insights generator."""
    insights = []
    
    negative = stats.get('negative', 0)
    recent_negative = stats.get('recent_negative', 0)
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
    
    return insights


@router.post("/api/whats-happening", response_model=WhatsHappeningResponse)
async def get_whats_happening(request: WhatsHappeningRequest):
    """Generate What's Happening insights based on filtered posts using LLM."""
    try:
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        llm_available = bool(api_key) and llm_provider in ['openai', 'anthropic']
        
        insights = await generate_whats_happening_insights_with_llm(
            request.posts,
            request.stats,
            request.active_filters
        )
        return WhatsHappeningResponse(insights=insights, llm_available=llm_available)
    except Exception as e:
        logger.error(f"Failed to generate What's Happening insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate insights: {str(e)}")


@router.get("/api/improvements-summary")
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
        
        openai_key = os.getenv('OPENAI_API_KEY')
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', '').lower()
        
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


@router.get("/api/pain-points", response_model=PainPointsResponse, tags=["Dashboard", "Insights"])
async def get_pain_points_endpoint(
    days: int = Query(30, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(5, description="Maximum number of pain points to return", ge=1, le=50)
):
    """Get recurring pain points from posts in the last N days."""
    try:
        return await get_pain_points(days=days, limit=limit)
    except Exception as e:
        logger.error(f"Error getting pain points: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get pain points: {str(e)}")


@router.get("/api/product-opportunities", response_model=ProductDistributionResponse, tags=["Dashboard", "Insights"])
async def get_product_opportunities():
    """Get product distribution with opportunity scores based on negative feedback."""
    try:
        # Get all posts from database (using a high limit to get all posts)
        posts = db.get_posts(limit=10000, offset=0)
        
        # Product keywords to detect
        product_keywords = {
            'VPS': ['vps', 'virtual private server'],
            'Hosting': ['hosting', 'web hosting', 'shared hosting'],
            'Domain': ['domain', 'domaine', 'dns'],
            'Email': ['email', 'mail', 'smtp', 'imap'],
            'Storage': ['storage', 'object storage', 'backup', 's3'],
            'CDN': ['cdn', 'content delivery'],
            'Public Cloud': ['public cloud', 'publiccloud'],
            'Private Cloud': ['private cloud', 'privatecloud'],
            'Dedicated Server': ['dedicated', 'dedicated server', 'serveur dédié'],
            'Billing': ['billing', 'invoice', 'facture', 'payment', 'paiement'],
            'Support': ['support', 'ticket', 'help', 'assistance'],
            'API': ['api', 'rest api', 'graphql']
        }
        
        # Count posts by product
        product_stats = {}
        for post in posts:
            content = (post.get('content', '') or '').lower()
            is_negative = post.get('sentiment_label') == 'negative'
            
            # Detect products mentioned in post
            for product_name, keywords in product_keywords.items():
                if any(keyword in content for keyword in keywords):
                    if product_name not in product_stats:
                        product_stats[product_name] = {
                            'total': 0,
                            'negative': 0
                        }
                    product_stats[product_name]['total'] += 1
                    if is_negative:
                        product_stats[product_name]['negative'] += 1
        
        # Calculate opportunity scores and create ProductOpportunity objects
        products = []
        colors = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1', '#14b8a6', '#a855f7']
        
        for idx, (product_name, stats) in enumerate(sorted(product_stats.items(), key=lambda x: x[1]['negative'], reverse=True)):
            total = stats['total']
            negative = stats['negative']
            
            # Calculate opportunity score (0-100)
            # Higher score = more negative posts relative to total + volume factor
            # Formula: (negative_ratio * 60) + (volume_factor * 40)
            # This balances both the percentage of negative feedback and the absolute volume
            if total > 0:
                negative_ratio = negative / total
                # Volume factor: more posts = higher score, capped at 40 points
                # Scale: 1 post = 4 points, 10 posts = 20 points, 50+ posts = 40 points
                volume_factor = min(negative / 50.0, 1.0) * 40
                # Ratio factor: percentage of negative posts, capped at 60 points
                ratio_factor = negative_ratio * 60
                opportunity_score = int(min(ratio_factor + volume_factor, 100))
            else:
                opportunity_score = 0
            
            color = colors[idx % len(colors)]
            
            products.append(ProductOpportunity(
                product=product_name,
                opportunity_score=opportunity_score,
                negative_posts=negative,
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
    total_posts: int
) -> ImprovementsAnalysisResponse:
    """Generate improvements analysis with insights and ROI using LLM."""
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Reload .env to get latest values
    backend_path = Path(__file__).resolve().parents[3]
    env_path = backend_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
    # Prepare data for LLM
    pain_points_text = "\n".join([
        f"- {pp.get('title', 'N/A')}: {pp.get('description', '')} ({pp.get('posts_count', 0)} posts)"
        for pp in pain_points[:10]
    ]) if pain_points else "No pain points identified."
    
    products_text = "\n".join([
        f"- {p.get('product', 'N/A')}: {p.get('opportunity_score', 0)}/100 score, {p.get('negative_posts', 0)} negative posts out of {p.get('total_posts', 0)} total"
        for p in products[:10]
    ]) if products else "No product data available."
    
    prompt = f"""You are an OVHcloud product improvement analyst. Analyze the following improvement opportunities and generate key insights with ROI estimates.

CONTEXT:
- Total posts analyzed: {total_posts}
- Pain points identified: {len(pain_points)}
- Products with opportunities: {len(products)}

PAIN POINTS:
{pain_points_text}

PRODUCT OPPORTUNITIES:
{products_text}

Based on this analysis, generate:
1. **Key Findings** (3-5 bullet points): What are the main patterns and issues that emerge?
2. **ROI & Customer Impact**: Estimate the potential ROI and customer impact of addressing these improvements
3. **Priority Insights**: Which improvements would have the highest impact?

Format your response as JSON with this structure:
{{
  "key_findings": [
    "Finding 1: [specific insight]",
    "Finding 2: [specific insight]",
    "Finding 3: [specific insight]"
  ],
  "roi_summary": "[2-3 sentences about ROI and customer impact. Be specific about potential benefits: customer satisfaction improvement, retention, revenue impact, etc.]",
  "insights": [
    {{
      "type": "key_finding",
      "title": "Key Finding Title",
      "description": "Detailed description of the finding",
      "icon": "💡",
      "metric": "",
      "roi_impact": "Potential impact: [specific estimate]"
    }},
    {{
      "type": "roi",
      "title": "ROI & Customer Impact",
      "description": "[Specific ROI estimate and customer impact]",
      "icon": "💰",
      "metric": "",
      "roi_impact": "[ROI estimate]"
    }},
    {{
      "type": "priority",
      "title": "Priority Focus Area",
      "description": "[Which improvements to prioritize and why]",
      "icon": "🎯",
      "metric": "",
      "roi_impact": ""
    }}
  ]
}}

Be specific and actionable. Reference actual products and pain points from the data provided."""

    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    mistral_key = os.getenv('MISTRAL_API_KEY')
    llm_provider = os.getenv('LLM_PROVIDER', '').lower()
    
    if not openai_key and not anthropic_key and not mistral_key:
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
        except Exception as e:
            logger.warning(f"{provider} API error: {type(e).__name__}: {e}")
            return None
        return None
    
    try:
        # Try to use configured provider or any available
        content = None
        if llm_provider == 'anthropic' or (not llm_provider and anthropic_key and not openai_key):
            content = await call_llm('anthropic', anthropic_key, prompt)
        elif llm_provider == 'mistral' or (not llm_provider and mistral_key and not openai_key and not anthropic_key):
            content = await call_llm('mistral', mistral_key, prompt)
        elif llm_provider == 'openai' or (not llm_provider and openai_key):
            content = await call_llm('openai', openai_key, prompt)
        else:
            # Try any available
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
                insights = [ImprovementInsight(**insight) for insight in data.get('insights', [])]
                return ImprovementsAnalysisResponse(
                    insights=insights,
                    roi_summary=data.get('roi_summary', ''),
                    key_findings=data.get('key_findings', []),
                    llm_available=True
                )
    except Exception as e:
        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback.")
    
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


@router.post("/api/improvements-analysis", response_model=ImprovementsAnalysisResponse, tags=["Dashboard", "Insights"])
async def get_improvements_analysis(request: ImprovementsAnalysisRequest):
    """Generate comprehensive improvements analysis with insights and ROI using LLM."""
    try:
        # Convert Pydantic models to dicts for LLM function
        pain_points_dicts = [pp.dict() if hasattr(pp, 'dict') else pp for pp in request.pain_points]
        products_dicts = [p.dict() if hasattr(p, 'dict') else p for p in request.products]
        
        return await generate_improvements_analysis_with_llm(
            pain_points_dicts,
            products_dicts,
            request.total_posts
        )
    except Exception as e:
        logger.error(f"Error generating improvements analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate improvements analysis: {str(e)}")




