"""LLM-based insights and recommendations endpoints."""
import os
import json
import re
import logging
import asyncio
import math
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
from ... import database as db
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


@router.post("/recommended-actions", response_model=RecommendedActionsResponse)
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
    active_filters: str = "",
    analysis_focus: str = ""
) -> List[WhatsHappeningInsight]:
    """Generate What's Happening insights using LLM API."""
    # Reload .env to get latest API keys (in case they were updated)
    from pathlib import Path
    from dotenv import load_dotenv
    backend_path = Path(__file__).resolve().parents[3]
    env_path = backend_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
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
    
    # Build focus instruction based on analysis_focus setting
    focus_instruction = ""
    if analysis_focus:
        focus_instruction = f"\n\nANALYSIS FOCUS: The user wants to focus the analysis on: {analysis_focus}. Prioritize insights related to this focus area while still providing a comprehensive analysis."
    
    prompt = f"""You are an OVHcloud customer feedback analyst. Your task is to analyze customer feedback and generate ACTIONABLE, PRIORITY-FOCUSED insights that directly identify what needs immediate attention.

IMPORTANT: Generate ALL insights, titles, descriptions, and content in ENGLISH only.

CONTEXT:
- Active filters: {active_filters if active_filters else "All posts (no filters)"}
- Total posts analyzed: {total} (Positive: {positive}, Negative: {negative}, Neutral: {neutral})
- Recent posts (last 48h): {recent_total} total, {recent_negative} negative
- Spike detected: {spike_detected} {'⚠️ Significant increase in negative feedback!' if spike_detected else ''}
{focus_instruction}

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


@router.post("/whats-happening", response_model=WhatsHappeningResponse)
async def get_whats_happening(request: WhatsHappeningRequest):
    """Generate What's Happening insights based on filtered posts using LLM."""
    try:
        # Reload .env to get latest API keys (in case they were updated)
        from pathlib import Path
        from dotenv import load_dotenv
        backend_path = Path(__file__).resolve().parents[3]
        env_path = backend_path / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=True)
        
        api_key = os.getenv('OPENAI_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
        llm_provider = os.getenv('LLM_PROVIDER', 'openai').lower()
        llm_available = bool(api_key) and llm_provider in ['openai', 'anthropic']
        
        logger.info(f"get_whats_happening: OpenAI key set: {bool(os.getenv('OPENAI_API_KEY'))}, Anthropic key set: {bool(os.getenv('ANTHROPIC_API_KEY'))}, Provider: {llm_provider}, LLM available: {llm_available}")
        
        insights = await generate_whats_happening_insights_with_llm(
            request.posts,
            request.stats,
            request.active_filters,
            request.analysis_focus or ""
        )
        return WhatsHappeningResponse(insights=insights, llm_available=llm_available)
    except Exception as e:
        logger.error(f"Failed to generate What's Happening insights: {e}", exc_info=True)
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


@router.get("/pain-points", response_model=PainPointsResponse, tags=["Dashboard", "Insights"])
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
                            # Parse post date (handle various formats)
                            post_date_str = created_at.replace('Z', '+00:00')
                            try:
                                post_date = datetime.fromisoformat(post_date_str)
                            except ValueError:
                                # Try parsing without timezone
                                post_date = datetime.fromisoformat(created_at.split('T')[0])
                            
                            # Compare dates (remove timezone for comparison)
                            post_date_naive = post_date.replace(tzinfo=None) if post_date.tzinfo else post_date
                            if post_date_naive.date() >= cutoff_date.date():
                                filtered_posts.append(post)
                        except (ValueError, AttributeError) as e:
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
            
            if negative_count_calc > 0:
                # Pertinence moyenne des posts négatifs
                avg_relevance = negative_weighted_sum / negative_count_calc
                
                # Score de base : nombre de posts négatifs × pertinence moyenne
                # Plus il y a de posts négatifs, plus le score augmente
                # Facteur de volume : logarithme pour éviter que ça explose
                # 1 post = ~10 points, 5 posts = ~30 points, 10 posts = ~50 points, 20+ posts = ~100 points
                volume_factor = min(math.log(negative_count_calc + 1) * 10, 50)  # Max 50 points pour le volume
                
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
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Reload .env to get latest values
    backend_path = Path(__file__).resolve().parents[3]
    env_path = backend_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
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
                
                return ImprovementsAnalysisResponse(
                    insights=insights_with_posts,
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




