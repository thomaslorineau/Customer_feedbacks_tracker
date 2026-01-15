"""
Configuration management with secure API key handling.

Best practices implemented:
- Environment variables for secrets
- Validation at startup
- No hardcoded credentials
- Graceful error handling
- Support for multiple LLM providers
"""
import os
import logging
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file (should be in backend/ directory)
env_path = Path(__file__).resolve().parents[1] / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"[OK] Loaded environment from {env_path}")
else:
    logger.warning(f"[WARNING] No .env file found at {env_path}")


class Config:
    """Application configuration with secure API key management."""
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO")
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()
    
    # API Keys (private - never log these!)
    _OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    _ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    _GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")
    _TRUSTPILOT_API_KEY: Optional[str] = os.getenv("TRUSTPILOT_API_KEY")
    _GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # Third-party API credentials (optional - user provides their own)
    _LINKEDIN_CLIENT_ID: Optional[str] = os.getenv("LINKEDIN_CLIENT_ID")
    _LINKEDIN_CLIENT_SECRET: Optional[str] = os.getenv("LINKEDIN_CLIENT_SECRET")
    _TWITTER_BEARER_TOKEN: Optional[str] = os.getenv("TWITTER_BEARER_TOKEN")
    _TWITTER_API_KEY: Optional[str] = os.getenv("TWITTER_API_KEY")
    _TWITTER_API_SECRET: Optional[str] = os.getenv("TWITTER_API_SECRET")
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Database
    DB_PATH: Path = Path(__file__).resolve().parents[1] / "data.db"
    
    @classmethod
    def get_api_key(cls, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.
        
        SECURITY: This method should only be used internally.
        Never log or expose the returned value.
        
        Args:
            provider: Provider name (openai, anthropic, google, trustpilot, github, linkedin_client_id, linkedin_client_secret, twitter_bearer, twitter_api_key, twitter_api_secret)
            
        Returns:
            API key if configured, None otherwise
        """
        provider = provider.lower()
        key_map = {
            "openai": cls._OPENAI_API_KEY,
            "anthropic": cls._ANTHROPIC_API_KEY,
            "google": cls._GOOGLE_API_KEY,
            "trustpilot": cls._TRUSTPILOT_API_KEY,
            "github": cls._GITHUB_TOKEN,
            # Third-party APIs (optional)
            "linkedin_client_id": cls._LINKEDIN_CLIENT_ID,
            "linkedin_client_secret": cls._LINKEDIN_CLIENT_SECRET,
            "twitter_bearer": cls._TWITTER_BEARER_TOKEN,
            "twitter_bearer_token": cls._TWITTER_BEARER_TOKEN,
            "twitter_api_key": cls._TWITTER_API_KEY,
            "twitter_api_secret": cls._TWITTER_API_SECRET,
        }
        
        key = key_map.get(provider)
        
        if key:
            # SECURITY: Never log the actual key
            logger.debug(f"[OK] API key for {provider}: configured ({len(key)} chars)")
        else:
            logger.debug(f"[WARNING] API key for {provider}: not configured")
        
        return key
    
    @classmethod
    def validate_required_keys(cls) -> dict:
        """
        Validate that required API keys are configured.
        
        Returns:
            Dict with validation results and warnings
        """
        results = {
            "valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check LLM provider key
        llm_key = cls.get_api_key(cls.LLM_PROVIDER)
        if not llm_key:
            results["errors"].append(
                f"❌ Missing API key for LLM provider '{cls.LLM_PROVIDER}'. "
                f"Set {cls.LLM_PROVIDER.upper()}_API_KEY in .env"
            )
            results["valid"] = False
        elif len(llm_key) < 10:
            results["warnings"].append(
                f"⚠️ API key for {cls.LLM_PROVIDER} seems too short (might be placeholder)"
            )
        elif llm_key == "your_openai_api_key_here" or llm_key.startswith("sk-proj-"):
            if llm_key.startswith("sk-proj-hiswP"):
                results["errors"].append(
                    f"🔥 CRITICAL: Using exposed API key! "
                    f"Regenerate immediately at https://platform.openai.com/api-keys"
                )
                results["valid"] = False
            else:
                results["warnings"].append(
                    f"⚠️ API key looks like a placeholder. Update with real key."
                )
        
        # Optional but recommended keys
        if not cls.get_api_key("github"):
            results["warnings"].append(
                "ℹ️ GitHub token not configured. API rate limits will be lower."
            )
        
        if not cls.get_api_key("trustpilot"):
            results["warnings"].append(
                "ℹ️ Trustpilot API key not configured. Will use web scraping (slower)."
            )
        
        return results
    
    @classmethod
    def is_api_key_valid_format(cls, provider: str) -> bool:
        """
        Check if API key has valid format (basic validation).
        
        Args:
            provider: Provider name
            
        Returns:
            True if format looks valid, False otherwise
        """
        key = cls.get_api_key(provider)
        if not key:
            return False
        
        # Basic format validation
        format_rules = {
            "openai": lambda k: k.startswith("sk-") and len(k) > 20,
            "anthropic": lambda k: k.startswith("sk-ant-") and len(k) > 20,
            "github": lambda k: (k.startswith("ghp_") or k.startswith("github_pat_")) and len(k) > 20,
            "trustpilot": lambda k: len(k) > 10,
            "google": lambda k: len(k) > 10,
            "linkedin_client_id": lambda k: len(k) > 10,
            "linkedin_client_secret": lambda k: len(k) > 10,
            "twitter_bearer": lambda k: len(k) > 20,
            "twitter_bearer_token": lambda k: len(k) > 20,
            "twitter_api_key": lambda k: len(k) > 10,
            "twitter_api_secret": lambda k: len(k) > 10,
        }
        
        validator = format_rules.get(provider.lower())
        if validator:
            return validator(key)
        
        return len(key) > 10
    
    @classmethod
    def mask_api_key(cls, key: str) -> str:
        """
        Mask an API key for safe logging.
        
        Args:
            key: Full API key
            
        Returns:
            Masked version (e.g., "sk-proj-...abc123")
        """
        if not key or len(key) < 8:
            return "***"
        
        # Show first part and last 6 chars
        prefix_len = min(8, len(key) // 3)
        suffix_len = 6
        
        return f"{key[:prefix_len]}...{key[-suffix_len:]}"
    
    @classmethod
    def get_config_summary(cls) -> str:
        """
        Get a summary of current configuration (safe for logging).
        
        Returns:
            Configuration summary string
        """
        summary = []
        summary.append("=" * 50)
        summary.append("🔧 APPLICATION CONFIGURATION")
        summary.append("=" * 50)
        summary.append(f"Environment: {cls.ENVIRONMENT}")
        summary.append(f"Debug mode: {cls.DEBUG}")
        summary.append(f"Log level: {cls.LOG_LEVEL}")
        summary.append(f"LLM Provider: {cls.LLM_PROVIDER}")
        summary.append("")
        summary.append("🔑 API Keys Status:")
        
        providers = ["openai", "anthropic", "google", "github", "trustpilot"]
        for provider in providers:
            key = cls.get_api_key(provider)
            if key:
                masked = cls.mask_api_key(key)
                valid = "✅" if cls.is_api_key_valid_format(provider) else "⚠️"
                summary.append(f"  {valid} {provider:12s}: {masked}")
            else:
                summary.append(f"  ❌ {provider:12s}: Not configured")
        
        # Third-party APIs (optional)
        summary.append("")
        summary.append("🔗 Third-party APIs (optional - user credentials):")
        third_party_providers = [
            ("linkedin_client_id", "LinkedIn Client ID"),
            ("linkedin_client_secret", "LinkedIn Client Secret"),
            ("twitter_bearer", "Twitter Bearer Token"),
        ]
        for provider_key, provider_name in third_party_providers:
            key = cls.get_api_key(provider_key)
            if key:
                masked = cls.mask_api_key(key)
                valid = "✅" if cls.is_api_key_valid_format(provider_key) else "⚠️"
                summary.append(f"  {valid} {provider_name:20s}: {masked}")
            else:
                summary.append(f"  ⚪ {provider_name:20s}: Not configured (optional)")
        
        summary.append("")
        summary.append(f"🛡️ Rate Limiting: {cls.RATE_LIMIT_REQUESTS} req/{cls.RATE_LIMIT_WINDOW}s")
        summary.append(f"💾 Database: {cls.DB_PATH}")
        summary.append("=" * 50)
        
        return "\n".join(summary)


# Singleton instance
config = Config()


def validate_config_on_startup():
    """
    Validate configuration on application startup.
    Logs warnings/errors but doesn't prevent startup.
    """
    logger.info("[VALIDATION] Validating configuration...")
    
    # Print configuration summary
    logger.info("\n" + config.get_config_summary())
    
    # Validate API keys
    validation = config.validate_required_keys()
    
    # Log warnings
    for warning in validation["warnings"]:
        logger.warning(warning)
    
    # Log errors
    for error in validation["errors"]:
        logger.error(error)
    
    if validation["valid"]:
        logger.info("[OK] Configuration validated successfully")
    else:
        logger.error("[ERROR] Configuration has errors - some features may not work")
    
    return validation


# Example usage function
def get_llm_client():
    """
    Get configured LLM client based on provider.
    
    Returns:
        Configured LLM client or None if not available
        
    Raises:
        ValueError: If API key is not configured
    """
    provider = config.LLM_PROVIDER
    api_key = config.get_api_key(provider)
    
    if not api_key:
        raise ValueError(
            f"API key for {provider} not configured. "
            f"Please set {provider.upper()}_API_KEY in .env file"
        )
    
    if provider == "openai":
        try:
            from openai import OpenAI
            # SECURITY: Never log the API key
            logger.info(f"[OK] Initializing OpenAI client")
            return OpenAI(api_key=api_key)
        except ImportError:
            logger.error("[ERROR] OpenAI library not installed. Run: pip install openai")
            return None
    
    elif provider == "anthropic":
        try:
            from anthropic import Anthropic
            logger.info(f"[OK] Initializing Anthropic client")
            return Anthropic(api_key=api_key)
        except ImportError:
            logger.error("[ERROR] Anthropic library not installed. Run: pip install anthropic")
            return None
    
    else:
        logger.warning(f"[WARNING] Unsupported LLM provider: {provider}")
        return None
