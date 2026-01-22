"""Pydantic models for dashboard endpoints."""
from pydantic import BaseModel, Field
from typing import List, Optional


class PainPoint(BaseModel):
    """Model for a recurring pain point."""
    title: str = Field(..., description="Title of the pain point")
    description: str = Field(..., description="Brief description")
    icon: str = Field(..., description="Emoji icon")
    posts_count: int = Field(..., description="Number of posts mentioning this pain point")
    posts: List[dict] = Field(default=[], description="Sample posts related to this pain point")


class PainPointsResponse(BaseModel):
    """Response model for recurring pain points."""
    pain_points: List[PainPoint] = Field(..., description="List of recurring pain points")
    total_pain_points: int = Field(..., description="Total number of pain points found")


class ProductOpportunity(BaseModel):
    """Model for product opportunity score."""
    product: str = Field(..., description="Product name")
    opportunity_score: int = Field(..., description="Opportunity score (0-100)")
    negative_posts: int = Field(..., description="Number of negative posts")
    total_posts: int = Field(..., description="Total posts for this product")
    color: str = Field(..., description="Color for visualization")


class ProductDistributionResponse(BaseModel):
    """Response model for product distribution."""
    products: List[ProductOpportunity] = Field(..., description="List of products with opportunity scores")


class ImprovementIdeaRequest(BaseModel):
    """Request model for generating improvement ideas."""
    posts: List[dict] = Field(..., description="List of posts to analyze")
    max_ideas: int = Field(default=5, ge=1, le=10, description="Maximum number of ideas to generate")


class ImprovementIdea(BaseModel):
    """Model for a single improvement idea."""
    title: str = Field(..., description="Short title for the idea")
    description: str = Field(..., description="Detailed description of the improvement idea")
    priority: str = Field(..., description="Priority level: high, medium, or low")
    related_posts_count: int = Field(..., description="Number of posts that support this idea")


class ImprovementIdeasResponse(BaseModel):
    """Response model for improvement ideas."""
    ideas: List[ImprovementIdea] = Field(..., description="List of generated improvement ideas")
    llm_available: bool = Field(default=False, description="Whether LLM was available")


class RecommendedActionRequest(BaseModel):
    """Request model for generating recommended actions."""
    posts: List[dict] = Field(..., description="List of posts to analyze")
    recent_posts: List[dict] = Field(default=[], description="Recent posts (last 48h)")
    stats: dict = Field(default={}, description="Statistics about posts")
    max_actions: int = Field(default=5, ge=1, le=10, description="Maximum number of actions to generate")


class RecommendedAction(BaseModel):
    """Model for a single recommended action."""
    icon: str = Field(..., description="Emoji icon for the action")
    text: str = Field(..., description="Action description")
    priority: str = Field(..., description="Priority level: high, medium, or low")


class RecommendedActionsResponse(BaseModel):
    """Response model for recommended actions."""
    actions: List[RecommendedAction] = Field(..., description="List of generated recommended actions")
    llm_available: bool = Field(default=True, description="Whether LLM was used to generate actions")


class WhatsHappeningRequest(BaseModel):
    """Request model for generating What's Happening insights."""
    posts: List[dict] = Field(..., description="List of filtered posts to analyze")
    stats: dict = Field(default={}, description="Statistics about posts")
    active_filters: str = Field(default="", description="Description of active filters")


class WhatsHappeningInsight(BaseModel):
    """Model for a single What's Happening insight."""
    type: str = Field(..., description="Type of insight: 'top_product', 'top_issue', 'spike', 'trend'")
    title: str = Field(..., description="Title of the insight")
    description: str = Field(..., description="Description of the insight")
    icon: str = Field(default="📊", description="Emoji icon for the insight")
    metric: str = Field(default="", description="Metric or percentage if applicable")
    count: int = Field(default=0, description="Count or number if applicable")


class WhatsHappeningResponse(BaseModel):
    """Response model for What's Happening insights."""
    insights: List[WhatsHappeningInsight] = Field(..., description="List of generated insights")
    llm_available: bool = Field(default=True, description="Whether LLM was used to generate insights")


class ImprovementInsight(BaseModel):
    """Model for a single improvement insight."""
    type: str = Field(..., description="Type of insight: 'key_finding', 'roi', 'trend', 'priority'")
    title: str = Field(..., description="Title of the insight")
    description: str = Field(..., description="Description of the insight")
    icon: str = Field(default="💡", description="Emoji icon for the insight")
    metric: str = Field(default="", description="Metric or value if applicable")
    roi_impact: Optional[str] = Field(None, description="ROI or customer impact estimate")


class ImprovementsAnalysisRequest(BaseModel):
    """Request model for improvements analysis."""
    pain_points: List[PainPoint] = Field(default=[], description="List of pain points to analyze")
    products: List[ProductOpportunity] = Field(default=[], description="List of products with opportunity scores")
    total_posts: int = Field(default=0, description="Total number of posts analyzed")


class ImprovementsAnalysisResponse(BaseModel):
    """Response model for improvements analysis."""
    insights: List[ImprovementInsight] = Field(..., description="List of generated insights")
    roi_summary: str = Field(default="", description="Summary of ROI and customer impact")
    key_findings: List[str] = Field(default=[], description="Key findings from the analysis")
    llm_available: bool = Field(default=True, description="Whether LLM was used to generate insights")





