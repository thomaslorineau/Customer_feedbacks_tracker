"""
Configuration routes for API keys, LLM settings, and keywords.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import os

from .. import db
from ..auth.dependencies import require_auth
from ..auth.models import TokenData

logger = logging.getLogger(__name__)

router = APIRouter()


class LLMConfigResponse(BaseModel):
    provider: str = Field(..., description="LLM provider (openai, anthropic, local)")
    model: Optional[str] = Field(None, description="Model name")
    api_key_set: bool = Field(..., description="Whether API key is set")
    available: bool = Field(..., description="Whether LLM is available")
    # Legacy fields for backward compatibility
    openai_api_key_set: Optional[bool] = None
    anthropic_api_key_set: Optional[bool] = None
    llm_provider: Optional[str] = None
    status: Optional[str] = None


def get_version():
    """
    Get application version from VERSION file, .version_minor, and git commit count.
    
    Returns:
        Version string in format "MAJOR.MINOR.PATCH" (e.g., "1.5.77")
    """
    import subprocess
    from pathlib import Path
    
    # Read MAJOR from VERSION file
    version_path = Path(__file__).resolve().parents[2] / "VERSION"
    try:
        if version_path.exists():
            with open(version_path, "r", encoding="utf-8") as f:
                major = f.read().strip()
                if not major:
                    major = "1"
        else:
            major = "1"
    except Exception:
        major = "1"
    
    # Read MINOR from .version_minor file (auto-incremented on push)
    minor = "0"
    version_minor_path = version_path.parent / ".version_minor"
    try:
        if version_minor_path.exists():
            with open(version_minor_path, "r", encoding="utf-8") as f:
                minor = f.read().strip()
                if not minor or not minor.isdigit():
                    minor = "0"
        else:
            minor = "0"
    except Exception:
        minor = "0"
    
    # Calculate PATCH from commit count (last 2 digits to keep it short)
    patch = "00"
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            cwd=version_path.parent,
            timeout=5
        )
        if result.returncode == 0:
            commit_count = result.stdout.strip()
            if commit_count and commit_count.isdigit():
                # Prendre les 2 derniers chiffres (ex: 177 -> 77, 5 -> 05)
                patch = str(int(commit_count) % 100).zfill(2)
            else:
                patch = "00"
        else:
            patch = "00"
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        patch = "00"
    
    # Return format: MAJOR.MINOR.PATCH
    return f"{major}.{minor}.{patch}"


@router.get(
    "/api/version",
    summary="Get Application Version",
    description="""
    Returns the current application version and build date.
    
    **Version Format:**
    - Format: `MAJOR.MINOR.PATCH` (e.g., "1.5.77")
    - MAJOR: From VERSION file
    - MINOR: From .version_minor file (auto-incremented)
    - PATCH: Last 2 digits of git commit count
    
    **Returns:**
    - `version`: Version string
    - `build_date`: ISO timestamp of when the version was retrieved
    
    **Example Response:**
    ```json
    {
        "version": "1.5.77",
        "build_date": "2026-01-20T10:30:00"
    }
    ```
    """,
    tags=["Configuration", "System"]
)
async def get_app_version():
    """Get application version and build information."""
    import datetime
    return {
        "version": get_version(),
        "build_date": datetime.datetime.now().isoformat()
    }


@router.get(
    "/api/config",
    summary="Get Application Configuration",
    description="""
    Returns the current application configuration including API keys status, rate limiting settings, and environment.
    
    **Security:**
    - API keys are masked for security (only first 4 and last 4 characters shown)
    - Shows configuration status without exposing sensitive data
    
    **Returns:**
    - `environment`: Current environment (development, staging, production)
    - `llm_provider`: Current LLM provider (openai, anthropic)
    - `api_keys`: Status of all API keys (configured, masked value, length)
    - `rate_limiting`: Rate limiting configuration
    
    **Supported API Keys:**
    - OpenAI, Anthropic, Google, GitHub, Trustpilot, LinkedIn, Twitter
    
    **Example Response:**
    ```json
    {
        "environment": "production",
        "llm_provider": "openai",
        "api_keys": {
            "openai": {
                "configured": true,
                "masked": "sk-1••••••••abcd",
                "length": 51
            }
        },
        "rate_limiting": {
            "requests_per_window": 100,
            "window_seconds": 60
        }
    }
    ```
    """,
    tags=["Configuration"]
)
async def get_config():
    """Get full configuration including API keys status, rate limiting, and environment."""
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')
    github_token = os.getenv('GITHUB_TOKEN')
    trustpilot_key = os.getenv('TRUSTPILOT_API_KEY')
    linkedin_client_id = os.getenv('LINKEDIN_CLIENT_ID')
    linkedin_client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
    twitter_bearer = os.getenv('TWITTER_BEARER_TOKEN')
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    environment = os.getenv('ENVIRONMENT', 'development')
    
    def mask_key(key):
        """Mask API key for display."""
        if not key:
            return None
        if len(key) <= 8:
            return '••••••••'
        return f"{key[:4]}••••{key[-4:]}"
    
    linkedin_configured = bool(linkedin_client_id and linkedin_client_secret)
    linkedin_masked = mask_key(linkedin_client_id) if linkedin_client_id else None
    linkedin_length = len(linkedin_client_id) if linkedin_client_id else 0
    
    return {
        "environment": environment,
        "llm_provider": provider,
        "api_keys": {
            "openai": {
                "configured": bool(openai_key),
                "masked": mask_key(openai_key),
                "length": len(openai_key) if openai_key else 0
            },
            "anthropic": {
                "configured": bool(anthropic_key),
                "masked": mask_key(anthropic_key),
                "length": len(anthropic_key) if anthropic_key else 0
            },
            "google": {
                "configured": bool(google_key),
                "masked": mask_key(google_key),
                "length": len(google_key) if google_key else 0
            },
            "github": {
                "configured": bool(github_token),
                "masked": mask_key(github_token),
                "length": len(github_token) if github_token else 0
            },
            "trustpilot": {
                "configured": bool(trustpilot_key),
                "masked": mask_key(trustpilot_key),
                "length": len(trustpilot_key) if trustpilot_key else 0
            },
            "linkedin": {
                "configured": linkedin_configured,
                "masked": linkedin_masked,
                "length": linkedin_length
            },
            "twitter": {
                "configured": bool(twitter_bearer),
                "masked": mask_key(twitter_bearer),
                "length": len(twitter_bearer) if twitter_bearer else 0
            }
        },
        "rate_limiting": {
            "requests_per_window": 100,
            "window_seconds": 60
        }
    }


class LLMConfigPayload(BaseModel):
    """Request model for LLM configuration."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic)$", description="LLM provider")


class KeywordsPayload(BaseModel):
    """Payload for keywords/queries."""
    keywords: List[str] = Field(..., description="List of keywords")


class BaseKeywordsPayload(BaseModel):
    """Payload for updating base keywords."""
    brands: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    problems: List[str] = Field(default_factory=list)
    leadership: List[str] = Field(default_factory=list)


@router.get(
    "/api/llm-config", 
    response_model=LLMConfigResponse,
    summary="Get LLM Configuration",
    description="""
    Returns the current LLM (Large Language Model) configuration status.
    
    **Features:**
    - Shows which LLM provider is configured (OpenAI or Anthropic)
    - Indicates if API keys are set (without exposing them)
    - Provides availability status
    
    **Returns:**
    - `provider`: LLM provider name (openai, anthropic, local)
    - `model`: Model name if specified
    - `api_key_set`: Whether an API key is configured
    - `available`: Whether LLM is available for use
    
    **Example Response:**
    ```json
    {
        "provider": "openai",
        "model": null,
        "api_key_set": true,
        "available": true
    }
    ```
    """,
    tags=["Configuration", "LLM"]
)
async def get_llm_config():
    """Get current LLM configuration status (without exposing keys)."""
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    provider = os.getenv('LLM_PROVIDER', 'openai').lower()
    
    return LLMConfigResponse(
        provider=provider,
        api_key_set=bool(openai_key or anthropic_key),
        available=bool(openai_key or anthropic_key),
        # Legacy fields for backward compatibility
        openai_api_key_set=bool(openai_key),
        anthropic_api_key_set=bool(anthropic_key),
        llm_provider=provider,
        status="configured" if (openai_key or anthropic_key) else "not_configured"
    )


@router.post(
    "/api/llm-config", 
    response_model=LLMConfigResponse,
    summary="Set LLM Configuration",
    description="""
    Updates the LLM configuration by saving API keys and provider settings to the .env file.
    
    **Security:**
    - API keys are saved to `.env` file in the backend directory
    - Environment variables are updated for the current session
    
    **Request Body:**
    - `openai_api_key`: OpenAI API key (optional, can be null to remove)
    - `anthropic_api_key`: Anthropic API key (optional, can be null to remove)
    - `llm_provider`: Provider name ("openai" or "anthropic")
    
    **Example Request:**
    ```json
    {
        "openai_api_key": "sk-...",
        "anthropic_api_key": null,
        "llm_provider": "openai"
    }
    ```
    
    **Note:**
    Changes take effect immediately for the current session. Restart required for persistence.
    """,
    tags=["Configuration", "LLM"],
    responses={
        200: {"description": "Configuration updated successfully"}
    }
)
async def set_llm_config(
    payload: LLMConfigPayload
):
    """Set LLM configuration (save to .env file)."""
    from pathlib import Path
    logger.info("LLM configuration updated")
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    
    # Read existing .env if it exists
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    
    # Update with new values
    if payload.openai_api_key is not None:
        if payload.openai_api_key and payload.openai_api_key.strip():
            env_vars['OPENAI_API_KEY'] = payload.openai_api_key.strip()
        elif 'OPENAI_API_KEY' in env_vars:
            del env_vars['OPENAI_API_KEY']
    
    if payload.anthropic_api_key is not None:
        if payload.anthropic_api_key and payload.anthropic_api_key.strip():
            env_vars['ANTHROPIC_API_KEY'] = payload.anthropic_api_key.strip()
        elif 'ANTHROPIC_API_KEY' in env_vars:
            del env_vars['ANTHROPIC_API_KEY']
    
    if payload.llm_provider:
        env_vars['LLM_PROVIDER'] = payload.llm_provider
    
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    # Update environment variables for current session
    if payload.openai_api_key:
        os.environ['OPENAI_API_KEY'] = payload.openai_api_key
    if payload.anthropic_api_key:
        os.environ['ANTHROPIC_API_KEY'] = payload.anthropic_api_key
    if payload.llm_provider:
        os.environ['LLM_PROVIDER'] = payload.llm_provider
    
    return LLMConfigResponse(
        provider=env_vars.get('LLM_PROVIDER', 'openai'),
        api_key_set=bool(env_vars.get('OPENAI_API_KEY') or env_vars.get('ANTHROPIC_API_KEY')),
        available=bool(env_vars.get('OPENAI_API_KEY') or env_vars.get('ANTHROPIC_API_KEY')),
        # Legacy fields
        openai_api_key_set=bool(env_vars.get('OPENAI_API_KEY')),
        anthropic_api_key_set=bool(env_vars.get('ANTHROPIC_API_KEY')),
        llm_provider=env_vars.get('LLM_PROVIDER', 'openai'),
        status="configured"
    )


@router.post("/api/config/set-key")
async def set_api_key(
    payload: dict
):
    """Set a generic API key (for Google, GitHub, Trustpilot, LinkedIn, Twitter, etc.)."""
    from pathlib import Path
    logger.info(f"API key updated for provider: {payload.get('provider')}")
    provider = payload.get('provider')
    keys = payload.get('keys')
    key = payload.get('key')
    
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required")
    
    if keys and isinstance(keys, dict):
        if not keys:
            raise HTTPException(status_code=400, detail="At least one key is required")
    elif key:
        keys = {provider: key}
    else:
        raise HTTPException(status_code=400, detail="Key(s) are required")
    
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    
    # Read existing .env if it exists
    env_vars = {}
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key_name, value = line.split("=", 1)
                    env_vars[key_name.strip()] = value.strip()
    
    # Update the keys
    for key_name, key_value in keys.items():
        env_vars[key_name] = key_value
        os.environ[key_name] = key_value
    
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        for key_name, value in env_vars.items():
            f.write(f"{key_name}={value}\n")
    
    return {"success": True, "message": f"{provider} API key(s) saved successfully"}


# ============================================================================
# SETTINGS ENDPOINTS (QUERIES & KEYWORDS)
# ============================================================================

@router.get(
    '/settings/queries',
    summary="Get Saved User Keywords",
    description="""
    Returns the list of user-defined keywords/queries saved in the database.
    
    **Note:**
    - These are user keywords, separate from base keywords
    - User keywords are combined with base keywords during scraping
    - Returns an empty list if no keywords are saved
    
    **Returns:**
    - `keywords`: List of saved keyword strings
    
    **Example Response:**
    ```json
    {
        "keywords": ["OVH VPS", "OVH domain", "OVH hosting"]
    }
    ```
    """,
    tags=["Configuration", "Keywords"]
)
async def get_saved_queries():
    """Return saved keywords/queries from DB (user keywords only)."""
    return {'keywords': db.get_saved_queries()}


@router.post(
    '/settings/queries',
    summary="Save User Keywords",
    description="""
    Saves a list of user-defined keywords/queries to the database.
    
    **Features:**
    - Replaces existing user keywords with the new list
    - User keywords are combined with base keywords during scraping
    - Maximum 50 keywords recommended
    
    **Request Body:**
    ```json
    {
        "keywords": ["OVH VPS", "OVH domain", "OVH hosting"]
    }
    ```
    
    **Returns:**
    - `saved`: Number of keywords saved
    
    **Example Response:**
    ```json
    {
        "saved": 3
    }
    ```
    """,
    tags=["Configuration", "Keywords"]
)
async def post_saved_queries(payload: KeywordsPayload):
    """Save provided keywords list. Expects JSON: { "keywords": ["a","b"] } (user keywords only)."""
    db.save_queries(payload.keywords)
    return {'saved': len(payload.keywords)}


@router.get(
    '/settings/base-keywords',
    summary="Get Base Keywords",
    description="""
    Returns base keywords organized by category. These are the default keywords used for scraping.
    
    **Categories:**
    - `brands`: Brand names (OVH, OVHCloud, Kimsufi, etc.)
    - `products`: Product-related keywords (OVH domain, OVH hosting, etc.)
    - `problems`: Problem-related keywords (OVH complaint, OVH support, etc.)
    - `leadership`: Leadership-related keywords (Michel Paulin, Octave Klaba, etc.)
    
    **Features:**
    - Base keywords are editable and stored in the database
    - Automatically combined with user keywords during scraping
    - Fallback to defaults if database is empty
    
    **Example Response:**
    ```json
    {
        "brands": ["OVH", "OVHCloud", "Kimsufi"],
        "products": ["OVH domain", "OVH hosting", "OVH VPS"],
        "problems": ["OVH complaint", "OVH support"],
        "leadership": ["Michel Paulin", "Octave Klaba"]
    }
    ```
    """,
    tags=["Configuration", "Keywords"]
)
async def get_base_keywords():
    """Get base keywords by category (editable base keywords)."""
    try:
        keywords_by_category = db.get_base_keywords()
        return {
            'brands': keywords_by_category.get('brands', []),
            'products': keywords_by_category.get('products', []),
            'problems': keywords_by_category.get('problems', []),
            'leadership': keywords_by_category.get('leadership', [])
        }
    except Exception as e:
        logger.error(f"Error getting base keywords: {e}")
        # Fallback to defaults
        from ..config.keywords_base import get_base_keywords_from_db
        return get_base_keywords_from_db()


@router.post(
    '/settings/base-keywords',
    summary="Update Base Keywords",
    description="""
    Updates base keywords for all categories. Replaces existing base keywords in the database.
    
    **Request Body:**
    ```json
    {
        "brands": ["OVH", "OVHCloud"],
        "products": ["OVH domain", "OVH hosting"],
        "problems": ["OVH complaint"],
        "leadership": ["Michel Paulin"]
    }
    ```
    
    **Features:**
    - All categories are optional (can be empty arrays)
    - Keywords are stored in the database
    - Used automatically during scraping operations
    
    **Returns:**
    - `success`: Boolean indicating success
    - `keywords`: Updated keywords by category
    
    **Example Response:**
    ```json
    {
        "success": true,
        "keywords": {
            "brands": ["OVH", "OVHCloud"],
            "products": ["OVH domain"],
            "problems": [],
            "leadership": []
        }
    }
    ```
    """,
    tags=["Configuration", "Keywords"]
)
async def update_base_keywords(payload: BaseKeywordsPayload):
    """Update base keywords by category."""
    try:
        keywords_by_category = {
            'brands': payload.brands,
            'products': payload.products,
            'problems': payload.problems,
            'leadership': payload.leadership
        }
        db.save_base_keywords(keywords_by_category)
        return {'success': True, 'keywords': keywords_by_category}
    except Exception as e:
        logger.error(f"Error updating base keywords: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update base keywords: {str(e)}")

