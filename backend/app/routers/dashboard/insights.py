"""LLM-based insights and recommendations endpoints."""
import os
import json
import re
import logging
from typing import List
from fastapi import APIRouter, HTTPException
import httpx

from .models import (
    ImprovementIdea, ImprovementIdeasResponse, ImprovementIdeaRequest,
    RecommendedAction, RecommendedActionsResponse, RecommendedActionRequest,
    WhatsHappeningInsight, WhatsHappeningResponse, WhatsHappeningRequest
)
from .analytics import get_pain_points

logger = logging.getLogger(__name__)

router = APIRouter()


async def generate_ideas_with_llm(posts: List[dict], max_ideas: int = 5) -> List[ImprovementIdea]:
    """Generate improvement ideas using LLM API."""
    posts_summary = []
    for post in posts[:20]:
        posts_summary.append({
            'content': post.get('content', '')[:500],
            'sentiment': post.get('sentiment_label', 'neutral'),
            'source': post.get('source', 'Unknown')
        })
    
    prompt = f"""Analyze the following customer feedback posts about OVH products and generate {max_ideas} concrete product improvement ideas.

Posts to analyze:
{json.dumps(posts_summary, indent=2, ensure_ascii=False)}

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
    llm_provider = os.getenv('LLM_PROVIDER', '').lower()
    
    # Determine which provider to use
    # Priority: LLM_PROVIDER env var > available API keys
    if not openai_key and not anthropic_key:
        return generate_ideas_fallback(posts, max_ideas)
    
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
                        ideas_data = json.loads(json_match.group())
                        return [ImprovementIdea(**idea) for idea in ideas_data]
        
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
                                {'role': 'system', 'content': 'You are a product improvement analyst. Generate actionable improvement ideas based on customer feedback.'},
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
                        ideas_data = json.loads(json_match.group())
                        return [ImprovementIdea(**idea) for idea in ideas_data]
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            logger.warning(f"LLM API authentication failed (401): Invalid or expired API key. Using fallback.")
        else:
            logger.warning(f"LLM API error ({e.response.status_code}): {e}. Using fallback.")
        return generate_ideas_fallback(posts, max_ideas)
    except Exception as e:
        logger.warning(f"LLM API error: {type(e).__name__}: {e}. Using fallback.")
        return generate_ideas_fallback(posts, max_ideas)
    
    return generate_ideas_fallback(posts, max_ideas)


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




