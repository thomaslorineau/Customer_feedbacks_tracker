"""
Configuration routes for API keys, LLM settings, and keywords.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from .. import database as db
from ..auth.dependencies import require_auth
from ..auth.models import TokenData
from ..utils.jira_client import (
    load_jira_config, is_jira_configured, create_jira_ticket, test_jira_connection
)

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
    mistral_api_key_set: Optional[bool] = None
    llm_provider: Optional[str] = None
    status: Optional[str] = None


def get_version():
    """
    Get application version from VERSION file and commit count.
    
    Returns:
        Version string in format "MAJOR.COMMITS" (e.g., "1.548")
    """
    import subprocess
    from pathlib import Path
    
    # Try multiple paths for Docker and local dev compatibility
    possible_paths = [
        Path("/app"),  # Docker path
        Path(__file__).resolve().parents[2],  # Local dev (backend/)
    ]
    
    major = "1"
    minor = "0"
    
    # Find VERSION file
    for base_path in possible_paths:
        version_path = base_path / "VERSION"
        if version_path.exists():
            try:
                with open(version_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        major = content
                        break
            except Exception:
                pass
    
    # Find COMMIT_COUNT file (for Docker)
    for base_path in possible_paths:
        commit_count_path = base_path / "COMMIT_COUNT"
        if commit_count_path.exists():
            try:
                with open(commit_count_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content and content.isdigit():
                        minor = content
                        break
            except Exception:
                pass
    
    # If COMMIT_COUNT not found, try git (works in local dev)
    if minor == "0":
        try:
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                content = result.stdout.strip()
                if content and content.isdigit():
                    minor = content
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
    
    # Return format: MAJOR.COMMITS (e.g., 1.548)
    return f"{major}.{minor}"


@router.get(
    "/api/version",
    summary="Get Application Version",
    description="""
    Returns the current application version and build date.
    
    **Version Format:**
    - Format: `MAJOR.COMMITS` (e.g., "1.547")
    - MAJOR: From VERSION file
    - COMMITS: Total git commit count
    
    **Returns:**
    - `version`: Version string
    - `build_date`: ISO timestamp of when the version was retrieved
    
    **Example Response:**
    ```json
    {
        "version": "1.547",
        "build_date": "2026-02-02T10:30:00"
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
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Récupérer depuis la base de données en priorité, puis variables d'environnement
    # IMPORTANT: Load from DB FIRST, then .env (DB takes priority)
    from ..database import pg_get_config
    
    # Get from database first (this is the source of truth)
    openai_key = pg_get_config('OPENAI_API_KEY')
    anthropic_key = pg_get_config('ANTHROPIC_API_KEY')
    mistral_key = pg_get_config('MISTRAL_API_KEY')
    ovh_key = pg_get_config('OVH_API_KEY')
    ovh_endpoint = pg_get_config('OVH_ENDPOINT_URL')
    ovh_model = pg_get_config('OVH_MODEL')
    github_token = pg_get_config('GITHUB_TOKEN')
    trustpilot_key = pg_get_config('TRUSTPILOT_API_KEY')
    linkedin_client_id = pg_get_config('LINKEDIN_CLIENT_ID')
    linkedin_client_secret = pg_get_config('LINKEDIN_CLIENT_SECRET')
    twitter_bearer = pg_get_config('TWITTER_BEARER_TOKEN')
    discord_bot_token = pg_get_config('DISCORD_BOT_TOKEN')
    discord_guild_id = pg_get_config('DISCORD_GUILD_ID')
    
    # Normalize empty strings to None (empty string means explicitly deleted from DB)
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
    
    # CRITICAL: Clean OVH API key to ensure correct length calculation
    # This prevents the issue where a corrupted/masked key shows wrong length
    if ovh_key:
        # Check if key appears to be corrupted (too short for a JWT token)
        # OVH JWT tokens are typically 200+ characters
        if len(ovh_key) < 50:
            logger.error(f"OVH API key appears corrupted (only {len(ovh_key)} chars). Expected 200+ chars for JWT token. Key may have been saved as masked value.")
            # Don't use corrupted key - set to None so it shows as not configured
            ovh_key = None
        else:
            # Import cleaning function
            from ..db_postgres import _clean_ovh_api_key
            cleaned_ovh_key = _clean_ovh_api_key(ovh_key)
            # Only use cleaned key if it's different and not empty
            # If cleaned key is significantly shorter, it might be corrupted - log warning
            if cleaned_ovh_key != ovh_key:
                if len(cleaned_ovh_key) < len(ovh_key) * 0.5:
                    # Key was significantly shortened - might be corrupted
                    logger.warning(f"OVH API key length changed significantly during cleaning: {len(ovh_key)} -> {len(cleaned_ovh_key)} chars")
                # Save cleaned version back to database if different
                if cleaned_ovh_key and len(cleaned_ovh_key) >= 50:
                    from ..database import pg_set_config
                    pg_set_config('OVH_API_KEY', cleaned_ovh_key)
                    logger.info(f"OVH API key cleaned in get_config: {len(ovh_key)} -> {len(cleaned_ovh_key)} chars")
            ovh_key = cleaned_ovh_key if cleaned_ovh_key else ovh_key
    if github_token == '':
        github_token = None
    if trustpilot_key == '':
        trustpilot_key = None
    if linkedin_client_id == '':
        linkedin_client_id = None
    if linkedin_client_secret == '':
        linkedin_client_secret = None
    if twitter_bearer == '':
        twitter_bearer = None
    if discord_bot_token == '':
        discord_bot_token = None
    if discord_guild_id == '':
        discord_guild_id = None
    
    # Fallback to .env only if not in database (don't override DB values)
    # Reload .env to get latest values, but don't override existing env vars
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    if env_path.exists():
        # Load .env but don't override existing env vars (which may have DB values)
        load_dotenv(env_path, override=False)
    
    # IMPORTANT: Database is the source of truth. Do NOT use env vars as fallback.
    # If a key is not in the database (None), it means it was never configured or was explicitly deleted.
    # Using env vars as fallback would cause deleted keys to reappear, which is why the badge stays "Configured".
    # Only use defaults for OVH endpoint if OVH key exists but endpoint is not set
    # Do NOT set a default model - user must configure it
    if ovh_key and ovh_endpoint is None:
        ovh_endpoint = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
    
    # Get LLM provider from database, default to 'openai' if not set
    provider = pg_get_config('LLM_PROVIDER')
    if not provider:
        provider = 'openai'
    if provider:
        provider = provider.lower()
    else:
        provider = 'openai'
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
            "mistral": {
                "configured": bool(mistral_key),
                "masked": mask_key(mistral_key),
                "length": len(mistral_key) if mistral_key else 0
            },
            "ovh": {
                "configured": bool(ovh_key),
                "masked": mask_key(ovh_key),
                "length": len(ovh_key) if ovh_key else 0,
                "endpoint": ovh_endpoint if ovh_endpoint else None,
                "model": ovh_model if ovh_model else None
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
            },
            "discord": {
                "configured": bool(discord_bot_token and discord_guild_id),
                "masked": mask_key(discord_bot_token) if discord_bot_token else None,
                "length": len(discord_bot_token) if discord_bot_token else 0,
                "guild_id": discord_guild_id if discord_guild_id else None
            }
        },
        # Ensure Discord is always present in response (even if not configured)
        # This is needed for the frontend to display the Discord card
        "rate_limiting": {
            "requests_per_window": 100,
            "window_seconds": 60
        }
    }


class LLMConfigPayload(BaseModel):
    """Request model for LLM configuration."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    mistral_api_key: Optional[str] = Field(None, description="Mistral API key")
    ovh_api_key: Optional[str] = Field(None, description="OVH AI API key")
    ovh_endpoint_url: Optional[str] = Field(None, description="OVH AI Endpoint URL")
    ovh_model: Optional[str] = Field(None, description="OVH AI Model name")
    llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic|mistral|ovh)$", description="LLM provider")


class KeywordsPayload(BaseModel):
    """Payload for keywords/queries."""
    keywords: List[str] = Field(..., description="List of keywords")


class PainPointPayload(BaseModel):
    """Payload for a single pain point."""
    title: str = Field(..., description="Pain point title")
    icon: str = Field(..., description="Emoji icon")
    keywords: List[str] = Field(..., description="List of keywords for detection")
    enabled: bool = Field(default=True, description="Whether this pain point is enabled")


class PainPointsPayload(BaseModel):
    """Payload for multiple pain points."""
    pain_points: List[PainPointPayload] = Field(..., description="List of pain points")


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
    """Get LLM configuration from database (app_config table)."""
    from ..database import pg_get_config
    import os
    
    # Try to get from database first, fallback to environment variables
    openai_key = pg_get_config('OPENAI_API_KEY') or os.getenv('OPENAI_API_KEY')
    anthropic_key = pg_get_config('ANTHROPIC_API_KEY') or os.getenv('ANTHROPIC_API_KEY')
    mistral_key = pg_get_config('MISTRAL_API_KEY') or os.getenv('MISTRAL_API_KEY')
    llm_provider = pg_get_config('LLM_PROVIDER') or os.getenv('LLM_PROVIDER', 'openai')
    
    return LLMConfigResponse(
        provider=llm_provider or 'openai',
        api_key_set=bool(openai_key or anthropic_key or mistral_key),
        available=bool(openai_key or anthropic_key or mistral_key),
        openai_api_key_set=bool(openai_key),
        anthropic_api_key_set=bool(anthropic_key),
        llm_provider=llm_provider or 'openai',
        status="configured" if (openai_key or anthropic_key or mistral_key) else "not_configured"
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
    """Set LLM configuration (save to PostgreSQL app_config table for persistence)."""
    from ..database import pg_set_config, pg_delete_config, pg_get_config
    import os
    
    logger.info("LLM configuration updated - saving to database")
    
    # Get the payload as dict to check which fields were actually provided
    # Use exclude_unset=True to only get fields explicitly provided in the request
    # Use exclude_none=True to exclude None values (even if explicitly sent as null)
    # This ensures we only process fields that have actual values, not None/null
    payload_dict = payload.model_dump(exclude_unset=True, exclude_none=True)
    logger.info(f"Payload fields with values (exclude_unset+exclude_none): {list(payload_dict.keys())}")
    
    # Also get the raw payload to check for explicit nulls (for deletion purposes)
    raw_payload_dict = payload.model_dump(exclude_unset=True)
    logger.info(f"Payload fields explicitly provided (including nulls): {list(raw_payload_dict.keys())}")
    
    # Log payload values (masked for security)
    for key in payload_dict:
        value = payload_dict[key]
        if value and isinstance(value, str) and len(value) > 10:
            logger.info(f"  {key}: {value[:10]}... (length: {len(value)})")
        else:
            logger.info(f"  {key}: {value}")
    
    # Store in PostgreSQL app_config table (persistent across restarts)
    # CRITICAL: Only update keys that were explicitly provided in the request AND have a non-empty value
    # Use raw_payload_dict to check for explicit nulls/empty strings (for deletion)
    # IMPORTANT: If a key is not in raw_payload_dict, it means it wasn't sent at all - DO NOT TOUCH IT
    if 'openai_api_key' in raw_payload_dict:
        # Key was explicitly provided in the request
        openai_value = payload.openai_api_key.strip() if payload.openai_api_key else None
        if openai_value:
            pg_set_config('OPENAI_API_KEY', openai_value)
            logger.info("OpenAI API key saved to database")
        else:
            # Only delete if explicitly set to empty/null in the request
            pg_delete_config('OPENAI_API_KEY')
            logger.info("OpenAI API key removed from database (explicitly cleared)")
    else:
        # Key was NOT in the request - preserve existing value in database
        logger.debug("OpenAI API key not in request - preserving existing value")
    
    if 'anthropic_api_key' in raw_payload_dict:
        # Key was explicitly provided in the request
        anthropic_value = payload.anthropic_api_key.strip() if payload.anthropic_api_key else None
        if anthropic_value:
            pg_set_config('ANTHROPIC_API_KEY', anthropic_value)
            logger.info("Anthropic API key saved to database")
        else:
            # Only delete if explicitly set to empty/null in the request
            pg_delete_config('ANTHROPIC_API_KEY')
            logger.info("Anthropic API key removed from database (explicitly cleared)")
    else:
        # Key was NOT in the request - preserve existing value in database
        logger.debug("Anthropic API key not in request - preserving existing value")
    
    if 'mistral_api_key' in raw_payload_dict:
        # Key was explicitly provided in the request
        mistral_value = payload.mistral_api_key.strip() if payload.mistral_api_key else None
        if mistral_value:
            pg_set_config('MISTRAL_API_KEY', mistral_value)
            logger.info("Mistral API key saved to database")
        else:
            # Only delete if explicitly set to empty/null in the request
            pg_delete_config('MISTRAL_API_KEY')
            logger.info("Mistral API key removed from database (explicitly cleared)")
    else:
        # Key was NOT in the request - preserve existing value in database
        logger.debug("Mistral API key not in request - preserving existing value")
    
    # Handle OVH AI configuration
    if 'ovh_api_key' in raw_payload_dict:
        ovh_value = payload.ovh_api_key.strip() if payload.ovh_api_key else None
        if ovh_value:
            # CRITICAL: Validate OVH API key before saving
            from ..db_postgres import _clean_ovh_api_key, _validate_ovh_api_key
            
            # Check if key is too short (likely masked/corrupted)
            if len(ovh_value) < 50:
                logger.error(f"OVH API key too short ({len(ovh_value)} chars). Refusing to save masked/corrupted key.")
                raise HTTPException(
                    status_code=400,
                    detail=f"OVH API key appears to be masked or corrupted (only {len(ovh_value)} characters). Please enter the full API key (typically 200+ characters)."
                )
            
            # Clean the key
            cleaned_ovh_value = _clean_ovh_api_key(ovh_value)
            if not cleaned_ovh_value or len(cleaned_ovh_value) < 50:
                logger.error(f"OVH API key cleaning failed or resulted in invalid key (length: {len(cleaned_ovh_value) if cleaned_ovh_value else 0})")
                raise HTTPException(
                    status_code=400,
                    detail="OVH API key is invalid or corrupted. Please enter a valid API key."
                )
            
            # Validate the cleaned key
            if not _validate_ovh_api_key(cleaned_ovh_value):
                logger.error(f"OVH API key validation failed after cleaning (length: {len(cleaned_ovh_value)})")
                raise HTTPException(
                    status_code=400,
                    detail="OVH API key validation failed. Please check your API key format."
                )
            
            if cleaned_ovh_value != ovh_value:
                logger.warning(f"OVH API key cleaned before save: {len(ovh_value)} -> {len(cleaned_ovh_value)} chars")
            
            # Save the cleaned and validated key
            success = pg_set_config('OVH_API_KEY', cleaned_ovh_value)
            if not success:
                logger.error("Failed to save OVH API key to database")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to save OVH API key. Please try again."
                )
            
            # Verify the saved key
            from ..database import pg_get_config
            saved_key = pg_get_config('OVH_API_KEY')
            if not saved_key or len(saved_key) < 50:
                logger.error(f"Saved OVH API key verification failed (length: {len(saved_key) if saved_key else 0})")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to verify saved OVH API key. Please try again."
                )
            
            logger.info(f"OVH API key saved and verified successfully (length: {len(saved_key)})")
        else:
            pg_delete_config('OVH_API_KEY')
            logger.info("OVH API key removed from database")
    
    if 'ovh_endpoint_url' in raw_payload_dict:
        ovh_endpoint_value = payload.ovh_endpoint_url.strip() if payload.ovh_endpoint_url else None
        if ovh_endpoint_value:
            pg_set_config('OVH_ENDPOINT_URL', ovh_endpoint_value)
            logger.info("OVH endpoint URL saved to database")
        else:
            pg_delete_config('OVH_ENDPOINT_URL')
            logger.info("OVH endpoint URL removed from database")
    
    if 'ovh_model' in raw_payload_dict:
        ovh_model_value = payload.ovh_model.strip() if payload.ovh_model else None
        if ovh_model_value:
            pg_set_config('OVH_MODEL', ovh_model_value)
            logger.info(f"OVH model saved to database: {ovh_model_value}")
        else:
            pg_delete_config('OVH_MODEL')
            logger.info("OVH model removed from database")
    
    # Only update llm_provider if it was explicitly provided in the request
    if 'llm_provider' in payload_dict and payload.llm_provider:
        pg_set_config('LLM_PROVIDER', payload.llm_provider)
        logger.info(f"LLM provider set to: {payload.llm_provider}")
    
    # Update environment variables for current session (so it works immediately)
    # CRITICAL: Only update keys that were explicitly provided in the request
    # Use raw_payload_dict to check for explicit nulls (for deletion)
    # Do NOT delete or modify keys that weren't in the payload - they should remain unchanged
    if 'openai_api_key' in raw_payload_dict:
        if payload.openai_api_key and payload.openai_api_key.strip():
            os.environ['OPENAI_API_KEY'] = payload.openai_api_key.strip()
            logger.info("Updated OPENAI_API_KEY in environment")
        else:
            # Only delete if explicitly set to empty/null in the request
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']
                logger.info("Removed OPENAI_API_KEY from environment (explicitly cleared)")
    # Do NOT update ANTHROPIC_API_KEY if it wasn't in the payload
    if 'anthropic_api_key' in raw_payload_dict:
        if payload.anthropic_api_key and payload.anthropic_api_key.strip():
            os.environ['ANTHROPIC_API_KEY'] = payload.anthropic_api_key.strip()
            logger.info("Updated ANTHROPIC_API_KEY in environment")
        else:
            # Only delete if explicitly set to empty/null in the request
            if 'ANTHROPIC_API_KEY' in os.environ:
                del os.environ['ANTHROPIC_API_KEY']
                logger.info("Removed ANTHROPIC_API_KEY from environment (explicitly cleared)")
    # Do NOT update MISTRAL_API_KEY if it wasn't in the payload
    if 'mistral_api_key' in raw_payload_dict:
        if payload.mistral_api_key and payload.mistral_api_key.strip():
            os.environ['MISTRAL_API_KEY'] = payload.mistral_api_key.strip()
            logger.info("Updated MISTRAL_API_KEY in environment")
        else:
            # Only delete if explicitly set to empty/null in the request
            if 'MISTRAL_API_KEY' in os.environ:
                del os.environ['MISTRAL_API_KEY']
                logger.info("Removed MISTRAL_API_KEY from environment (explicitly cleared)")
    
    # Handle OVH AI environment variables
    if 'ovh_api_key' in raw_payload_dict:
        if payload.ovh_api_key and payload.ovh_api_key.strip():
            os.environ['OVH_API_KEY'] = payload.ovh_api_key.strip()
            logger.info("Updated OVH_API_KEY environment variable")
        else:
            if 'OVH_API_KEY' in os.environ:
                del os.environ['OVH_API_KEY']
                logger.info("Removed OVH_API_KEY from environment")
    
    if 'ovh_endpoint_url' in raw_payload_dict:
        if payload.ovh_endpoint_url and payload.ovh_endpoint_url.strip():
            os.environ['OVH_ENDPOINT_URL'] = payload.ovh_endpoint_url.strip()
            logger.info("Updated OVH_ENDPOINT_URL environment variable")
        else:
            if 'OVH_ENDPOINT_URL' in os.environ:
                del os.environ['OVH_ENDPOINT_URL']
                logger.info("Removed OVH_ENDPOINT_URL from environment")
    
    if 'ovh_model' in raw_payload_dict:
        if payload.ovh_model and payload.ovh_model.strip():
            os.environ['OVH_MODEL'] = payload.ovh_model.strip()
            logger.info(f"Updated OVH_MODEL environment variable: {payload.ovh_model}")
        else:
            if 'OVH_MODEL' in os.environ:
                del os.environ['OVH_MODEL']
                logger.info("Removed OVH_MODEL from environment")
    
    # Only update LLM_PROVIDER if it was explicitly provided
    if 'llm_provider' in payload_dict and payload.llm_provider:
        os.environ['LLM_PROVIDER'] = payload.llm_provider
        logger.info(f"Updated LLM_PROVIDER to {payload.llm_provider}")
    
    # Also update the config singleton if it exists
    # IMPORTANT: Only update fields that were explicitly provided in the request AND have values
    # Do NOT overwrite other keys - they should remain unchanged
    try:
        from ..config import config
        # Only update if the key is in payload_dict (has a non-null value)
        if 'openai_api_key' in payload_dict:
            config.openai_api_key = payload.openai_api_key.strip() if payload.openai_api_key else None
        # Do NOT update anthropic_api_key if it wasn't in the payload with a value
        if 'anthropic_api_key' in payload_dict:
            config.anthropic_api_key = payload.anthropic_api_key.strip() if payload.anthropic_api_key else None
        # Do NOT update mistral_api_key if it wasn't in the payload with a value
        if 'mistral_api_key' in payload_dict:
            config.mistral_api_key = payload.mistral_api_key.strip() if payload.mistral_api_key else None
        if 'llm_provider' in payload_dict and payload.llm_provider:
            config.llm_provider = payload.llm_provider
        logger.info(f"Config singleton updated for current session (updated fields with values: {list(payload_dict.keys())})")
    except Exception as e:
        logger.warning(f"Could not update config singleton: {e}")
    
    # Get updated values from database for response
    # IMPORTANT: Always read from database to ensure we return the actual persisted values
    openai_key = pg_get_config('OPENAI_API_KEY')
    anthropic_key = pg_get_config('ANTHROPIC_API_KEY')
    mistral_key = pg_get_config('MISTRAL_API_KEY')
    llm_provider = pg_get_config('LLM_PROVIDER') or 'openai'
    
    # Normaliser les chaînes vides en None
    if openai_key == '':
        openai_key = None
    if anthropic_key == '':
        anthropic_key = None
    if mistral_key == '':
        mistral_key = None
    
    # Log what we're returning to help diagnose persistence issues
    logger.info(f"Returning LLM config - OpenAI: {'set' if openai_key else 'not set'} (length: {len(openai_key) if openai_key else 0}), "
                f"Anthropic: {'set' if anthropic_key else 'not set'} (length: {len(anthropic_key) if anthropic_key else 0}), "
                f"Mistral: {'set' if mistral_key else 'not set'} (length: {len(mistral_key) if mistral_key else 0})")
    
    return LLMConfigResponse(
        provider=llm_provider,
        api_key_set=bool(openai_key or anthropic_key or mistral_key),
        available=bool(openai_key or anthropic_key or mistral_key),
        openai_api_key_set=bool(openai_key),
        anthropic_api_key_set=bool(anthropic_key),
        mistral_api_key_set=bool(mistral_key),
        llm_provider=llm_provider,
        status="configured" if (openai_key or anthropic_key or mistral_key) else "not_configured"
    )


@router.post("/api/config/set-key")
async def set_api_key(
    payload: dict
):
    """Set a generic API key (for Google, GitHub, Trustpilot, LinkedIn, Twitter, Discord, etc.)."""
    from ..database import pg_set_config, pg_delete_config
    import os
    
    logger.info(f"API key updated for provider: {payload.get('provider')}")
    provider = payload.get('provider')
    keys = payload.get('keys')
    key = payload.get('key')
    
    if not provider:
        raise HTTPException(status_code=400, detail="Provider is required")
    
    if keys and isinstance(keys, dict):
        # Pour Discord, vérifier si au moins une clé est fournie OU si Discord est déjà configuré
        if provider == 'discord':
            has_any_value = any(v and v.strip() for v in keys.values())
            if not has_any_value:
                # Si toutes les valeurs sont vides, vérifier si Discord est déjà configuré
                # Si oui, permettre la sauvegarde (les valeurs existantes seront conservées)
                discord_bot_token = pg_get_config('DISCORD_BOT_TOKEN')
                discord_guild_id = pg_get_config('DISCORD_GUILD_ID')
                if discord_bot_token or discord_guild_id:
                    logger.info("Discord already configured, allowing save with empty values (will keep existing)")
                else:
                    # Discord n'est pas configuré et toutes les valeurs sont vides
                    raise HTTPException(status_code=400, detail="At least one Discord key is required (Bot Token or Guild ID)")
        elif not keys:
            raise HTTPException(status_code=400, detail="At least one key is required")
    elif key:
        keys = {provider: key}
    else:
        raise HTTPException(status_code=400, detail="Key(s) are required")
    
    # Sauvegarder dans la base de données PostgreSQL (comme pour les LLM)
    for key_name, key_value in keys.items():
        if key_value and key_value.strip():
            # Sauvegarder dans la base de données
            try:
                pg_set_config(key_name, key_value.strip())
                # Mettre à jour les variables d'environnement pour la session courante
                os.environ[key_name] = key_value.strip()
                logger.info(f"✅ Saved {key_name} to database (length: {len(key_value.strip())})")
            except Exception as e:
                logger.error(f"❌ Failed to save {key_name} to database: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to save {key_name}: {str(e)}")
        else:
            # Si la valeur est vide, vérifier si elle existe déjà dans la base de données
            # Si elle existe, ne pas la supprimer (l'utilisateur n'a peut-être pas modifié ce champ)
            existing_value = pg_get_config(key_name)
            if existing_value:
                logger.info(f"⚠️ Skipping deletion of {key_name} because it exists in database and was not explicitly cleared")
                continue
            
            # Pour Discord, ne pas supprimer automatiquement si l'autre clé existe
            # L'utilisateur doit explicitement vider les deux champs pour supprimer
            if provider == 'discord':
                # Vérifier si l'autre clé Discord existe encore dans la requête
                if key_name == 'DISCORD_BOT_TOKEN':
                    other_key = keys.get('DISCORD_GUILD_ID', '')
                    if other_key and other_key.strip():
                        logger.info(f"⚠️ Skipping deletion of {key_name} because Guild ID is still set")
                        continue
                    # Vérifier aussi dans la base de données
                    other_key_db = pg_get_config('DISCORD_GUILD_ID')
                    if other_key_db:
                        logger.info(f"⚠️ Skipping deletion of {key_name} because Guild ID exists in database")
                        continue
                elif key_name == 'DISCORD_GUILD_ID':
                    other_key = keys.get('DISCORD_BOT_TOKEN', '')
                    if other_key and other_key.strip():
                        logger.info(f"⚠️ Skipping deletion of {key_name} because Bot Token is still set")
                        continue
                    # Vérifier aussi dans la base de données
                    other_key_db = pg_get_config('DISCORD_BOT_TOKEN')
                    if other_key_db:
                        logger.info(f"⚠️ Skipping deletion of {key_name} because Bot Token exists in database")
                        continue
            
            # Supprimer seulement si vraiment vide et pas de conflit
            try:
                pg_delete_config(key_name)
                if key_name in os.environ:
                    del os.environ[key_name]
                logger.info(f"✅ Removed {key_name} from database")
            except Exception as e:
                logger.warning(f"⚠️ Failed to remove {key_name} from database: {e}")
    
    # Mettre à jour le singleton config si disponible
    try:
        from ..config import config
        if provider == 'discord':
            if 'DISCORD_BOT_TOKEN' in keys:
                config.discord_bot_token = keys.get('DISCORD_BOT_TOKEN') or None
            if 'DISCORD_GUILD_ID' in keys:
                config.discord_guild_id = keys.get('DISCORD_GUILD_ID') or None
        elif provider == 'github' and 'GITHUB_TOKEN' in keys:
            config.github_token = keys.get('GITHUB_TOKEN') or None
        elif provider == 'trustpilot' and 'TRUSTPILOT_API_KEY' in keys:
            config.trustpilot_api_key = keys.get('TRUSTPILOT_API_KEY') or None
        elif provider == 'linkedin':
            if 'LINKEDIN_CLIENT_ID' in keys:
                config.linkedin_client_id = keys.get('LINKEDIN_CLIENT_ID') or None
            if 'LINKEDIN_CLIENT_SECRET' in keys:
                config.linkedin_client_secret = keys.get('LINKEDIN_CLIENT_SECRET') or None
        elif provider == 'twitter':
            if 'TWITTER_BEARER_TOKEN' in keys:
                config.twitter_bearer_token = keys.get('TWITTER_BEARER_TOKEN') or None
            if 'TWITTER_API_KEY' in keys:
                config.twitter_api_key = keys.get('TWITTER_API_KEY') or None
            if 'TWITTER_API_SECRET' in keys:
                config.twitter_api_secret = keys.get('TWITTER_API_SECRET') or None
        logger.info("Config singleton updated for current session")
    except Exception as e:
        logger.warning(f"Could not update config singleton: {e}")
    
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
        from ..keywords.keywords_base import get_base_keywords_from_db
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


# ============================================================================
# PAIN POINTS ENDPOINTS
# ============================================================================

@router.get(
    '/settings/pain-points',
    summary="Get Pain Points Configuration",
    description="""
    Returns all configured pain points from the database.
    
    **Features:**
    - Returns all pain points (including disabled ones) for settings management
    - Includes title, icon, and keywords for each pain point
    - Used for detecting recurring issues in customer feedback
    
    **Returns:**
    - `pain_points`: List of pain point configurations
    
    **Example Response:**
    ```json
    {
        "pain_points": [
            {
                "id": 1,
                "title": "Performance Issues",
                "icon": "🐌",
                "keywords": ["slow", "performance", "lag"],
                "enabled": true
            }
        ]
    }
    ```
    """,
    tags=["Configuration", "Pain Points"]
)
async def get_pain_points_config():
    """Get all pain points from database (including disabled ones for settings)."""
    try:
        pain_points = db.get_pain_points(enabled_only=False)
        return {'pain_points': pain_points}
    except Exception as e:
        logger.error(f"Error getting pain points: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pain points: {str(e)}")


@router.post(
    '/settings/pain-points',
    summary="Update Pain Points Configuration",
    description="""
    Updates pain points configuration in the database.
    
    **Features:**
    - Replaces all existing pain points with the provided list
    - Each pain point must have a title, icon, and keywords list
    - Keywords are used to detect mentions in post content
    - A post can match multiple pain points if it contains keywords from different categories
    
    **Request Body:**
    ```json
    {
        "pain_points": [
            {
                "title": "Performance Issues",
                "icon": "🐌",
                "keywords": ["slow", "performance", "lag"],
                "enabled": true
            }
        ]
    }
    ```
    
    **Returns:**
    - `success`: Boolean indicating success
    - `count`: Number of pain points saved
    """,
    tags=["Configuration", "Pain Points"]
)
async def update_pain_points_config(payload: PainPointsPayload):
    """Update pain points configuration."""
    try:
        # Convert to format expected by db.save_pain_points
        pain_points_list = [
            {
                'title': pp.title,
                'icon': pp.icon,
                'keywords': pp.keywords,
                'enabled': pp.enabled
            }
            for pp in payload.pain_points
        ]
        db.save_pain_points(pain_points_list)
        return {'success': True, 'count': len(pain_points_list)}
    except Exception as e:
        logger.error(f"Error updating pain points: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update pain points: {str(e)}")


@router.post(
    "/api/config/reveal-key",
    summary="Reveal API Key",
    description="""
    Returns the full (unmasked) API key for a given provider.
    This endpoint is used when editing API keys to show the current value.
    
    **Security:**
    - Requires authentication
    - Only returns the key if it exists
    - Reads from database (source of truth)
    
    **Query Parameters:**
    - `provider`: Provider name (openai, anthropic, mistral, ovh, github, trustpilot, linkedin, twitter)
    """,
    tags=["Configuration"]
)
async def reveal_key(provider: str = Query(..., description="Provider name (openai, anthropic, mistral, ovh, github, trustpilot, linkedin, twitter)")):
    """Reveal API key for editing purposes. Reads from database."""
    from ..database import pg_get_config
    
    # Normalize provider name to lowercase
    provider = provider.lower().strip() if provider else None
    
    # Map provider names to database config keys
    provider_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
        'ovh': 'OVH_API_KEY',
        'github': 'GITHUB_TOKEN',
        'trustpilot': 'TRUSTPILOT_API_KEY',
        'linkedin': 'LINKEDIN_CLIENT_ID',  # Note: LinkedIn has both client_id and client_secret
        'twitter': 'TWITTER_BEARER_TOKEN'
    }
    
    if not provider:
        raise HTTPException(status_code=400, detail="Provider parameter is required")
    
    if provider not in provider_map:
        raise HTTPException(status_code=400, detail=f"Invalid provider: '{provider}'. Valid providers: {', '.join(sorted(provider_map.keys()))}")
    
    config_key = provider_map[provider]
    key_value = pg_get_config(config_key)
    
    # Normalize empty strings to None
    if key_value == '':
        key_value = None
    
    if not key_value:
        raise HTTPException(status_code=404, detail=f"API key not found for provider: {provider}")
    
    return {
        "provider": provider,
        "key": key_value
    }


# ============================================================================
# JIRA CONFIGURATION ENDPOINTS
# ============================================================================

class JiraConfigPayload(BaseModel):
    """Payload for Jira configuration."""
    server_url: Optional[str] = Field(None, description="Jira server URL (e.g., https://yourcompany.atlassian.net)")
    username: Optional[str] = Field(None, description="Jira username or email")
    api_token: Optional[str] = Field(None, description="Jira API token")
    project_key: Optional[str] = Field(None, description="Jira project key (e.g., PROJ)")


@router.get("/api/jira/config")
async def get_jira_config():
    """Get current Jira configuration (without sensitive data)."""
    config = load_jira_config()
    return {
        "server_url": config['server_url'] if config['server_url'] else '',
        "username": config['username'] if config['username'] else '',
        "project_key": config['project_key'] if config['project_key'] else '',
        "configured": is_jira_configured()
    }


@router.post("/api/jira/config")
async def save_jira_config(payload: JiraConfigPayload):
    """Save Jira configuration to .env file."""
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    
    # Read existing .env file
    env_lines = []
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            env_lines = f.readlines()
    
    # Update or add Jira config variables
    jira_vars = {
        'JIRA_SERVER_URL': payload.server_url or '',
        'JIRA_USERNAME': payload.username or '',
        'JIRA_API_TOKEN': payload.api_token or '',
        'JIRA_PROJECT_KEY': payload.project_key or ''
    }
    
    # Update existing lines or add new ones
    updated_vars = set()
    for i, line in enumerate(env_lines):
        for var_name, var_value in jira_vars.items():
            if line.startswith(f'{var_name}='):
                env_lines[i] = f'{var_name}={var_value}\n'
                updated_vars.add(var_name)
                break
    
    # Add missing variables
    for var_name, var_value in jira_vars.items():
        if var_name not in updated_vars:
            env_lines.append(f'{var_name}={var_value}\n')
    
    # Write back to .env
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(env_lines)
    
    # Update environment variables for current process
    for var_name, var_value in jira_vars.items():
        os.environ[var_name] = var_value
    
    return {
        "success": True,
        "message": "Jira configuration saved successfully",
        "configured": is_jira_configured()
    }


@router.post("/api/jira/test-connection")
async def test_jira():
    """Test Jira connection and authentication."""
    result = await test_jira_connection()
    return result


class CreateJiraTicketPayload(BaseModel):
    """Payload for creating a Jira ticket."""
    title: str = Field(..., description="Ticket title/summary")
    description: str = Field(..., description="Ticket description")
    issue_type: str = Field(default="Bug", description="Issue type (Bug, Task, Story, etc.)")
    priority: str = Field(default="Medium", description="Priority level (Lowest, Low, Medium, High, Highest)")
    labels: Optional[List[str]] = Field(default=None, description="Optional list of labels")


@router.post("/api/jira/create-ticket")
async def create_ticket(payload: CreateJiraTicketPayload):
    """Create a Jira ticket."""
    result = await create_jira_ticket(
        title=payload.title,
        description=payload.description,
        issue_type=payload.issue_type,
        priority=payload.priority,
        labels=payload.labels
    )
    
    if not result.get('success'):
        raise HTTPException(status_code=400, detail=result.get('error', 'Failed to create ticket'))
    
    return result


class OVHModelsResponse(BaseModel):
    """Response model for OVH available models."""
    models: List[str] = Field(..., description="List of available model names")
    endpoint: Optional[str] = Field(None, description="OVH endpoint URL used")
    error: Optional[str] = Field(None, description="Error message if models could not be fetched")


class OVHModelsTestRequest(BaseModel):
    """Request model for testing OVH API key and loading models."""
    api_key: Optional[str] = Field(None, description="OVH API key to test (optional, uses saved key if not provided)")
    endpoint_url: Optional[str] = Field(None, description="OVH endpoint URL (optional, uses saved or default if not provided)")


@router.post(
    "/api/ovh/models/test",
    response_model=OVHModelsResponse,
    summary="Test OVH API Key and Get Available Models",
    description="""
    Tests an OVH API key and retrieves the list of available models.
    Useful for loading models before saving the API key.
    
    **Request Body:**
    ```json
    {
        "api_key": "your-ovh-api-key",
        "endpoint_url": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1"
    }
    ```
    
    **Returns:**
    - `models`: List of available model names
    - `endpoint`: The endpoint URL used to fetch models
    - `error`: Error message if models could not be fetched
    """,
    tags=["Configuration", "LLM", "OVH"]
)
async def test_ovh_models(request: OVHModelsTestRequest):
    """Test OVH API key and get available models."""
    try:
        import httpx
        from ..database import pg_get_config
        from .dashboard.insights import safe_error_text
        
        # Use provided API key or get from database
        ovh_key = request.api_key if request.api_key else pg_get_config('OVH_API_KEY')
        ovh_endpoint = request.endpoint_url if request.endpoint_url else pg_get_config('OVH_ENDPOINT_URL')
        
        # Normalize empty strings
        if ovh_key == '':
            ovh_key = None
        if ovh_endpoint == '':
            ovh_endpoint = None
        
        # Clean API key
        if ovh_key:
            cleaned_key = ''.join(c for c in ovh_key if ord(c) < 128 and (c.isalnum() or c in '+-/=_.'))
            if cleaned_key != ovh_key:
                logger.warning(f"OVH API key contained non-ASCII characters, cleaned: {len(ovh_key)} -> {len(cleaned_key)} chars")
            ovh_key = cleaned_key if cleaned_key else None
        
        # Use default endpoint if not provided
        if not ovh_endpoint:
            ovh_endpoint = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
        
        if not ovh_key:
            endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
            return OVHModelsResponse(
                models=[],
                endpoint=endpoint_safe,
                error="OVH API key is required"
            )
        
        # Call OVH AI Endpoints /models endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            ovh_key_ascii = ''.join(c for c in ovh_key if ord(c) < 128 and (c.isalnum() or c in '+-/=_.'))
            ovh_key_safe = ovh_key_ascii if ovh_key_ascii else ""
            
            if ovh_endpoint:
                ovh_endpoint_ascii = ''.join(c for c in str(ovh_endpoint) if ord(c) < 128)
                ovh_endpoint_safe = ovh_endpoint_ascii if ovh_endpoint_ascii else ""
            else:
                ovh_endpoint_safe = ""
            
            auth_header = f'Bearer {ovh_key_safe}'
            models_url = f'{ovh_endpoint_safe}/models'
            
            try:
                response = await client.get(
                    models_url,
                    headers={
                        'Authorization': auth_header,
                        'Content-Type': 'application/json'
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, dict) and 'data' in data:
                        models = [m.get('id', '') for m in data['data'] if 'id' in m]
                        return OVHModelsResponse(
                            models=models,
                            endpoint=ovh_endpoint_safe,
                            error=None
                        )
                    else:
                        return OVHModelsResponse(
                            models=[],
                            endpoint=ovh_endpoint_safe,
                            error="Invalid response format from OVH endpoint"
                        )
                else:
                    error_text = safe_error_text(response.text, max_length=200)
                    return OVHModelsResponse(
                        models=[],
                        endpoint=ovh_endpoint_safe,
                        error=f"Failed to fetch models: {response.status_code} - {error_text}"
                    )
            except httpx.TimeoutException:
                return OVHModelsResponse(
                    models=[],
                    endpoint=ovh_endpoint_safe,
                    error="Request timeout - OVH endpoint may be unreachable"
                )
            except Exception as e:
                error_msg = safe_error_text(str(e), max_length=200)
                return OVHModelsResponse(
                    models=[],
                    endpoint=ovh_endpoint_safe,
                    error=f"Error fetching models: {error_msg}"
                )
    except Exception as e:
        error_msg = safe_error_text(str(e), max_length=200)
        return OVHModelsResponse(
            models=[],
            endpoint="",
            error=f"Unexpected error: {error_msg}"
        )


@router.get(
    "/api/ovh/models",
    response_model=OVHModelsResponse,
    summary="Get Available OVH AI Models",
    description="""
    Retrieves the list of available models from OVH AI Endpoints.
    
    **Requirements:**
    - OVH API key must be configured
    - OVH endpoint URL must be configured
    
    **Returns:**
    - `models`: List of available model names
    - `endpoint`: The endpoint URL used to fetch models
    - `error`: Error message if models could not be fetched
    
    **Example Response:**
    ```json
    {
        "models": ["Llama-3.1-70B-Instruct", "Qwen-2.5-72B-Instruct"],
        "endpoint": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
        "error": null
    }
    ```
    """,
    tags=["Configuration", "LLM", "OVH"]
)
async def get_ovh_models():
    """Get available models from OVH AI Endpoints."""
    # Wrap ENTIRE function in try/except to catch ANY encoding errors
    try:
        import httpx
        from ..database import pg_get_config
        from .dashboard.insights import safe_error_text
        
        # Get OVH configuration from database
        ovh_key = pg_get_config('OVH_API_KEY')
        ovh_endpoint = pg_get_config('OVH_ENDPOINT_URL')
        
        # Normalize empty strings
        if ovh_key == '':
            ovh_key = None
        if ovh_endpoint == '':
            ovh_endpoint = None
        
        # Clean API key: remove any non-ASCII characters that might have been corrupted
        # This fixes the issue where Unicode characters (like bullet points) get into the key
        # JWT tokens contain: header.payload.signature (dots are required)
        if ovh_key:
            # Keep only ASCII characters that are valid in JWT/base64 (A-Z, a-z, 0-9, +, /, =, -, _, .)
            cleaned_key = ''.join(c for c in ovh_key if ord(c) < 128 and (c.isalnum() or c in '+-/=_.'))
            if cleaned_key != ovh_key:
                try:
                    logger.warning(f"OVH API key contained non-ASCII characters, cleaned: {len(ovh_key)} -> {len(cleaned_key)} chars")
                except Exception:
                    # If logging fails due to encoding, skip it
                    pass
                ovh_key = cleaned_key if cleaned_key else None
        
        # Use default endpoint if not configured
        if not ovh_endpoint:
            ovh_endpoint = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
        
        if not ovh_key:
            endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
            return OVHModelsResponse(
                models=[],
                endpoint=endpoint_safe,
                error="OVH API key not configured. Please configure your OVH API key in Settings."
            )
        
        # Now safe to proceed with API call
        # Call OVH AI Endpoints /models endpoint (OpenAI-compatible)
        # Protect headers against encoding issues - ensure all values are ASCII-safe
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Safely encode API key and endpoint for headers
            # httpx requires ASCII for headers, so we must ensure ASCII encoding
            # The key should already be cleaned, but double-check DIRECTLY without safe_error_text
            # to avoid any encoding issues in safe_error_text itself
            if ovh_key:
                # Ensure key is ASCII-safe (should already be cleaned, but verify)
                # Direct filtering without any string operations that might fail
                # JWT tokens contain: header.payload.signature (dots are required)
                ovh_key_ascii = ''.join(c for c in ovh_key if ord(c) < 128 and (c.isalnum() or c in '+-/=_.'))
                ovh_key_safe = ovh_key_ascii if ovh_key_ascii else ""
            else:
                ovh_key_safe = ""
            
            # Also clean endpoint directly
            if ovh_endpoint:
                ovh_endpoint_ascii = ''.join(c for c in str(ovh_endpoint) if ord(c) < 128)
                ovh_endpoint_safe = ovh_endpoint_ascii if ovh_endpoint_ascii else ""
            else:
                ovh_endpoint_safe = ""
            
            # Double-check: ensure headers are ASCII-safe
            auth_header = f'Bearer {ovh_key_safe}'
            try:
                # Test if it can be encoded as ASCII
                auth_header.encode('ascii')
            except UnicodeEncodeError as e:
                # If not, force ASCII with replacement
                try:
                    auth_header = auth_header.encode('ascii', errors='replace').decode('ascii', errors='replace')
                except Exception as e2:
                    # Ultimate fallback: use only the last 4 chars
                    auth_header = f'Bearer ***{ovh_key_safe[-4:] if len(ovh_key_safe) > 4 else ""}'
            
            # Also ensure endpoint URL is ASCII-safe
            endpoint_url = f'{ovh_endpoint_safe}/models'
            try:
                endpoint_url.encode('ascii')
            except UnicodeEncodeError:
                endpoint_url = endpoint_url.encode('ascii', errors='replace').decode('ascii', errors='replace')
            
            # Build headers with direct ASCII filtering - no string operations that might fail
            safe_headers = {}
            # Authorization header - already cleaned
            auth_value_ascii = ''.join(c for c in auth_header if ord(c) < 128)
            safe_headers['Authorization'] = auth_value_ascii
            
            # Content-Type header - always ASCII
            safe_headers['Content-Type'] = 'application/json'
            
            # Final verification: ensure all header values can be encoded as ASCII
            for header_name, header_value in safe_headers.items():
                try:
                    header_value.encode('ascii')
                except UnicodeEncodeError:
                    # If still can't encode, filter directly
                    safe_headers[header_name] = ''.join(c for c in str(header_value) if ord(c) < 128)
            
            # Final verification: ensure headers can be encoded as ASCII before calling httpx
            # httpx will try to encode headers internally, so we must be 100% sure they're ASCII
            try:
                # Test encoding of each header value
                for header_name, header_value in safe_headers.items():
                    header_value.encode('ascii')
            except UnicodeEncodeError as header_err:
                # If headers still can't be encoded, log and return error
                try:
                    logger.error("Headers still contain non-ASCII after cleaning")
                except Exception:
                    pass
                endpoint_safe = ''.join(c for c in str(ovh_endpoint) if ord(c) < 128) if ovh_endpoint else ""
                return OVHModelsResponse(
                    models=[],
                    endpoint=endpoint_safe,
                    error="Error fetching models: API key contains invalid characters"
                )
            
            # Wrap httpx call in try/except to catch encoding errors during request construction
            try:
                response = await client.get(
                    endpoint_url,
                    headers=safe_headers
                )
            except UnicodeEncodeError as httpx_encoding_err:
                # This error occurs when httpx tries to encode headers internally
                # Return a clean error message without trying to include the exception details
                endpoint_safe = ''.join(c for c in str(ovh_endpoint) if ord(c) < 128) if ovh_endpoint else ""
                return OVHModelsResponse(
                    models=[],
                    endpoint=endpoint_safe,
                    error="Error fetching models: API key contains invalid characters. Please regenerate your API key."
                )
            
            if response.status_code == 401:
                endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
                return OVHModelsResponse(
                    models=[],
                    endpoint=endpoint_safe,
                    error="Authentication failed. Please check your OVH API key."
                )
            
            if response.status_code == 404:
                # Some endpoints might not support /models, try alternative approach
                try:
                    logger.warning("OVH endpoint does not support /models endpoint")
                except Exception:
                    pass
                endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
                return OVHModelsResponse(
                    models=[],
                    endpoint=endpoint_safe,
                    error="Models endpoint not available. Please configure the model manually."
                )
            
            # Safely handle response - protect against encoding errors
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as status_err:
                # Re-raise to be caught by outer handler
                raise status_err
            except Exception as status_err:
                # If raise_for_status fails due to encoding, wrap it
                raise httpx.HTTPStatusError(
                    message=f"HTTP {response.status_code}",
                    request=response.request,
                    response=response
                )
            
            # Safely parse JSON response - protect against encoding issues
            # First decode the response content to UTF-8 with error replacement
            try:
                # Decode response content to UTF-8 first, then parse JSON
                response_content = response.content.decode('utf-8', errors='replace')
                import json
                result = json.loads(response_content)
            except (UnicodeDecodeError, UnicodeEncodeError) as encoding_err:
                # If encoding fails, try with latin-1 as fallback
                try:
                    response_content = response.content.decode('latin-1', errors='replace')
                    import json
                    result = json.loads(response_content)
                except Exception:
                    # If everything fails, return error
                    endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
                    return OVHModelsResponse(
                        models=[],
                        endpoint=endpoint_safe,
                        error="Failed to decode API response. Please check your endpoint configuration."
                    )
            except Exception as json_err:
                # If JSON parsing fails, try to get text safely
                try:
                    try:
                        logger.warning("Failed to parse JSON response")
                    except Exception:
                        pass
                except Exception:
                    pass
                endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
                return OVHModelsResponse(
                    models=[],
                    endpoint=endpoint_safe,
                    error="Failed to parse API response. Please check your endpoint configuration."
                )
            
            # Extract model IDs from the response
            # OpenAI-compatible API returns: {"data": [{"id": "model-name", ...}, ...]}
            models = []
            if isinstance(result, dict) and 'data' in result:
                # Safely extract model IDs - protect against encoding issues
                try:
                    models = [safe_error_text(str(model.get('id', '')), max_length=100) for model in result['data'] if 'id' in model]
                    # Filter out empty strings
                    models = [m for m in models if m]
                except Exception:
                    models = []
            elif isinstance(result, list):
                try:
                    models = [safe_error_text(str(model.get('id', '')), max_length=100) for model in result if isinstance(model, dict) and 'id' in model]
                    models = [m for m in models if m]
                except Exception:
                    models = []
            
            if not models:
                try:
                    logger.warning("No models found in OVH response")
                except Exception:
                    pass
                endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
                return OVHModelsResponse(
                    models=[],
                    endpoint=endpoint_safe,
                    error="No models found in the response. Please check your endpoint configuration."
                )
            
            try:
                logger.info(f"Successfully retrieved {len(models)} models from OVH endpoint")
            except Exception:
                pass
            endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
            return OVHModelsResponse(
                models=sorted(models),  # Sort alphabetically for better UX
                endpoint=endpoint_safe,
                error=None
            )
            
    except httpx.TimeoutException:
        try:
            logger.error("Timeout while fetching models from OVH endpoint")
        except Exception:
            pass
        endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
        return OVHModelsResponse(
            models=[],
            endpoint=endpoint_safe,
            error="Request timeout. Please check your endpoint URL and network connection."
        )
    except httpx.HTTPStatusError as e:
        # Safely extract error text with UTF-8 encoding
        try:
            if hasattr(e.response, 'content'):
                error_text = e.response.content.decode('utf-8', errors='replace')[:200]
            elif hasattr(e.response, 'text'):
                # Safely extract text - protect against encoding issues
                try:
                    response_text = e.response.text
                    if isinstance(response_text, str):
                        error_text = response_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')[:200]
                    else:
                        error_text = str(response_text).encode('utf-8', errors='replace').decode('utf-8', errors='replace')[:200]
                except Exception:
                    error_text = f"HTTP {e.response.status_code} error"
            else:
                try:
                    error_text = str(e).encode('utf-8', errors='replace').decode('utf-8', errors='replace')[:200]
                except Exception:
                    error_text = f"HTTP {e.response.status_code} error"
        except (UnicodeDecodeError, AttributeError, UnicodeEncodeError):
            error_text = f"HTTP {e.response.status_code} error"
        
        # Ensure error_text is safe for JSON serialization
        try:
            error_text_safe = error_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        except (UnicodeEncodeError, UnicodeDecodeError):
            error_text_safe = f"HTTP {e.response.status_code} error"
        
        # Log with safe text (logger might have encoding issues)
        try:
            logger.error(f"HTTP error while fetching OVH models: {e.response.status_code}")
        except Exception:
            pass
        
        endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
        return OVHModelsResponse(
            models=[],
            endpoint=endpoint_safe,
            error=f"HTTP error {e.response.status_code}: {error_text_safe}"
        )
    except Exception as e:
        # Safely encode error message - handle encoding errors during str() conversion
        error_msg_safe = "Error fetching models"
        error_type_name = "Exception"
        
        try:
            error_type_name = type(e).__name__
        except Exception:
            pass
        
        # Try to get error message safely using safe_error_text
        try:
            # For UnicodeEncodeError, don't try to get the message - it may contain non-ASCII
            if isinstance(e, (UnicodeEncodeError, UnicodeDecodeError)):
                error_msg_safe = safe_error_text("Error fetching models: encoding issue", max_length=200)
            else:
                # Use repr() first, which is safer than str()
                try:
                    error_repr = repr(e)
                    # Remove the class name and parentheses if present
                    if error_repr.startswith(error_type_name + '('):
                        error_msg = error_repr[len(error_type_name) + 1:-1]
                    else:
                        error_msg = error_repr
                    
                    # Use safe_error_text to ensure ASCII-safe encoding
                    error_msg_safe = safe_error_text(error_msg, max_length=500)
                    if not error_msg_safe or error_msg_safe == "":
                        error_msg_safe = safe_error_text(f"Error fetching models: {error_type_name}", max_length=200)
                except Exception:
                    # If repr() fails, use type name only
                    error_msg_safe = safe_error_text(f"Error fetching models: {error_type_name}", max_length=200)
        except Exception:
            # If everything fails, use type name only
            try:
                error_msg_safe = safe_error_text(f"Error fetching models: {error_type_name}", max_length=200)
            except Exception:
                error_msg_safe = "Error fetching models"
        
        # Log safely - avoid using the error message in f-string if it might cause issues
        try:
            logger.error("Error fetching OVH models", exc_info=True)
        except Exception:
            pass
        
        # Safely create response - protect against any encoding issues
        try:
            endpoint_safe = safe_error_text(str(ovh_endpoint) if ovh_endpoint else "", max_length=200)
            return OVHModelsResponse(
                models=[],
                endpoint=endpoint_safe,
                error=error_msg_safe
            )
        except Exception as resp_err:
            # Ultimate fallback - return minimal safe response
            try:
                return OVHModelsResponse(
                    models=[],
                    endpoint="",
                    error="Error fetching models"
                )
            except Exception:
                # If even this fails, raise a simple HTTPException
                raise HTTPException(
                    status_code=500,
                    detail="Error fetching OVH models"
                )
    except (UnicodeEncodeError, UnicodeDecodeError) as encoding_err:
        # Catch encoding errors specifically - these can happen anywhere in the function
        # DO NOT try to log or use the exception message - it may contain non-ASCII
        try:
            logger.error("Encoding error in get_ovh_models")
        except Exception:
            pass
        # Return a simple ASCII-safe error message
        return OVHModelsResponse(
            models=[],
            endpoint="",
            error="Error fetching models: encoding issue"
        )
    except Exception as e:
        # Catch ALL other exceptions that might escape
        try:
            logger.error("Unexpected error in get_ovh_models")
        except Exception:
            pass
        return OVHModelsResponse(
            models=[],
            endpoint="",
            error="Error fetching models"
        )


@router.get(
    "/api/ovh/test",
    summary="Test OVH AI Configuration",
    description="""
    Tests the OVH AI configuration by attempting to connect to the endpoint and make a simple API call.
    
    **Returns:**
    - `configured`: Whether OVH is configured (key, endpoint, model)
    - `connection_ok`: Whether the connection to the endpoint is successful
    - `api_call_ok`: Whether a test API call succeeds
    - `error`: Error message if any step fails
    - `details`: Detailed information about each step
    
    **Example Response:**
    ```json
    {
        "configured": true,
        "connection_ok": true,
        "api_call_ok": true,
        "error": null,
        "details": {
            "has_key": true,
            "has_endpoint": true,
            "has_model": true,
            "endpoint": "https://oai.endpoints.kepler.ai.cloud.ovh.net/v1",
            "model": "Mistral-7B-Instruct",
            "key_length": 12
        }
    }
    ```
    """,
    tags=["Configuration", "LLM", "OVH"]
)
async def test_ovh_config():
    """Test OVH AI configuration and connection."""
    import httpx
    from ..database import pg_get_config
    
    result = {
        "configured": False,
        "connection_ok": False,
        "api_call_ok": False,
        "error": None,
        "details": {}
    }
    
    # Get OVH configuration from database
    ovh_key = pg_get_config('OVH_API_KEY')
    ovh_endpoint = pg_get_config('OVH_ENDPOINT_URL')
    ovh_model = pg_get_config('OVH_MODEL')
    
    # Normalize empty strings
    if ovh_key == '':
        ovh_key = None
    if ovh_endpoint == '':
        ovh_endpoint = None
    if ovh_model == '':
        ovh_model = None
    
    # Use default endpoint if not configured
    if not ovh_endpoint:
        ovh_endpoint = 'https://oai.endpoints.kepler.ai.cloud.ovh.net/v1'
    
    result["details"] = {
        "has_key": bool(ovh_key),
        "has_endpoint": bool(ovh_endpoint),
        "has_model": bool(ovh_model),
        "endpoint": ovh_endpoint,
        "model": ovh_model,
        "key_length": len(ovh_key) if ovh_key else 0
    }
    
    # Check if configured
    if not ovh_key:
        result["error"] = "OVH API key not configured. Please configure your OVH API key in Settings."
        return result
    
    if not ovh_model:
        result["error"] = "OVH model not configured. Please select a model in Settings."
        return result
    
    result["configured"] = True
    
    # Test connection
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Test 1: Try to connect to endpoint
            try:
                response = await client.get(
                    f'{ovh_endpoint}/models',
                    headers={
                        'Authorization': f'Bearer {ovh_key}',
                        'Content-Type': 'application/json'
                    }
                )
                result["connection_ok"] = True
                result["details"]["connection_status"] = response.status_code
            except httpx.TimeoutException:
                result["error"] = "Connection timeout. Please check your endpoint URL and network connection."
                return result
            except httpx.ConnectError:
                result["error"] = "Connection failed. Please check your endpoint URL."
                return result
            except Exception as e:
                result["error"] = f"Connection error: {str(e)}"
                return result
            
            # Test 2: Try a simple API call
            try:
                test_response = await client.post(
                    f'{ovh_endpoint}/chat/completions',
                    headers={
                        'Authorization': f'Bearer {ovh_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': ovh_model,
                        'messages': [
                            {'role': 'user', 'content': 'Hello'}
                        ],
                        'max_tokens': 10
                    }
                )
                
                if test_response.status_code == 200:
                    result["api_call_ok"] = True
                    result["details"]["api_call_status"] = 200
                elif test_response.status_code == 401:
                    result["error"] = "Authentication failed. Please check your OVH API key."
                    result["details"]["api_call_status"] = 401
                elif test_response.status_code == 404:
                    # Try to get more details
                    try:
                        error_json = test_response.json()
                        if error_json.get('error', {}).get('code') == 'model_not_found':
                            result["error"] = f"Model '{ovh_model}' not found on your endpoint. Please check available models in Settings."
                        else:
                            result["error"] = f"API call failed (404): {error_json.get('error', {}).get('message', 'Unknown error')}"
                    except:
                        result["error"] = f"API call failed (404): Model or endpoint not found"
                    result["details"]["api_call_status"] = 404
                else:
                    result["error"] = f"API call failed ({test_response.status_code})"
                    result["details"]["api_call_status"] = test_response.status_code
                    try:
                        error_text = test_response.text[:200]
                        result["details"]["api_call_error"] = error_text
                    except:
                        pass
            except httpx.TimeoutException:
                result["error"] = "API call timeout. The endpoint may be slow or unavailable."
            except Exception as e:
                result["error"] = f"API call error: {str(e)}"
            
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result

