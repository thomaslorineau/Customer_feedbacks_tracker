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
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Récupérer depuis la base de données en priorité, puis variables d'environnement
    # IMPORTANT: Load from DB FIRST, then .env (DB takes priority)
    from ..database import pg_get_config
    
    # Get from database first (this is the source of truth)
    openai_key = pg_get_config('OPENAI_API_KEY')
    anthropic_key = pg_get_config('ANTHROPIC_API_KEY')
    mistral_key = pg_get_config('MISTRAL_API_KEY')
    github_token = pg_get_config('GITHUB_TOKEN')
    trustpilot_key = pg_get_config('TRUSTPILOT_API_KEY')
    linkedin_client_id = pg_get_config('LINKEDIN_CLIENT_ID')
    linkedin_client_secret = pg_get_config('LINKEDIN_CLIENT_SECRET')
    twitter_bearer = pg_get_config('TWITTER_BEARER_TOKEN')
    discord_bot_token = pg_get_config('DISCORD_BOT_TOKEN')
    discord_guild_id = pg_get_config('DISCORD_GUILD_ID')
    
    # Fallback to .env only if not in database (don't override DB values)
    # Reload .env to get latest values, but don't override existing env vars
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    if env_path.exists():
        # Load .env but don't override existing env vars (which may have DB values)
        load_dotenv(env_path, override=False)
    
    # Use env vars as fallback only if not in database
    if not openai_key:
        openai_key = os.getenv('OPENAI_API_KEY')
    if not anthropic_key:
        anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not mistral_key:
        mistral_key = os.getenv('MISTRAL_API_KEY')
    if not github_token:
        github_token = os.getenv('GITHUB_TOKEN')
    if not trustpilot_key:
        trustpilot_key = os.getenv('TRUSTPILOT_API_KEY')
    if not linkedin_client_id:
        linkedin_client_id = os.getenv('LINKEDIN_CLIENT_ID')
    if not linkedin_client_secret:
        linkedin_client_secret = os.getenv('LINKEDIN_CLIENT_SECRET')
    if not twitter_bearer:
        twitter_bearer = os.getenv('TWITTER_BEARER_TOKEN')
    if not discord_bot_token:
        discord_bot_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_guild_id:
        discord_guild_id = os.getenv('DISCORD_GUILD_ID')
    provider = pg_get_config('LLM_PROVIDER') or os.getenv('LLM_PROVIDER', 'openai')
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
    llm_provider: Optional[str] = Field(None, pattern="^(openai|anthropic|mistral)$", description="LLM provider")


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
    
    **Query Parameters:**
    - `provider`: Provider name (openai, anthropic, mistral, github, trustpilot, linkedin, twitter)
    """,
    tags=["Configuration"]
)
async def reveal_key(provider: str = Query(..., description="Provider name (openai, anthropic, mistral, github, trustpilot, linkedin, twitter)")):
    """Reveal API key for editing purposes."""
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Reload .env to get latest values
    backend_path = Path(__file__).resolve().parents[2]
    env_path = backend_path / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
    
    # Map provider names to environment variable names
    provider_map = {
        'openai': 'OPENAI_API_KEY',
        'anthropic': 'ANTHROPIC_API_KEY',
        'mistral': 'MISTRAL_API_KEY',
        'github': 'GITHUB_TOKEN',
        'trustpilot': 'TRUSTPILOT_API_KEY',
        'linkedin': 'LINKEDIN_CLIENT_ID',  # Note: LinkedIn has both client_id and client_secret
        'twitter': 'TWITTER_BEARER_TOKEN'
    }
    
    if not provider or provider not in provider_map:
        raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}. Valid providers: {', '.join(provider_map.keys())}")
    
    env_var_name = provider_map[provider]
    key_value = os.getenv(env_var_name)
    
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

