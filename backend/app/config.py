"""
Configuration management with secure API key handling using Pydantic Settings.

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
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """Application configuration with secure API key management using Pydantic Settings."""
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env"),  # backend/.env
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Environment
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=True, description="Debug mode")
    
    # Logging
    log_level: str = Field(default="DEBUG", description="Logging level")
    
    # LLM Provider Configuration
    llm_provider: str = Field(default="openai", description="LLM provider to use")
    
    # API Keys (private - never log these!)
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(default=None, description="Anthropic API key")
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral API key")
    trustpilot_api_key: Optional[str] = Field(default=None, description="Trustpilot API key")
    github_token: Optional[str] = Field(default=None, description="GitHub token")
    
    # Third-party API credentials (optional - user provides their own)
    linkedin_client_id: Optional[str] = Field(default=None, description="LinkedIn client ID")
    linkedin_client_secret: Optional[str] = Field(default=None, description="LinkedIn client secret")
    twitter_bearer_token: Optional[str] = Field(default=None, description="Twitter bearer token")
    twitter_api_key: Optional[str] = Field(default=None, description="Twitter API key")
    twitter_api_secret: Optional[str] = Field(default=None, description="Twitter API secret")
    discord_bot_token: Optional[str] = Field(default=None, description="Discord bot token")
    discord_guild_id: Optional[str] = Field(default=None, description="Discord guild (server) ID")
    
    # Rate limiting
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per window")
    rate_limit_window: int = Field(default=60, description="Rate limit window in seconds")
    
    # Database - PostgreSQL is now the only database (DuckDB removed)
    
    @field_validator('debug', mode='before')
    @classmethod
    def set_debug_from_environment(cls, v, info):
        """Set debug mode based on environment if not explicitly set."""
        if v is None:
            env = info.data.get('environment', 'development')
            return env == "development"
        return v
    
    @field_validator('log_level', mode='before')
    @classmethod
    def set_log_level_from_debug(cls, v, info):
        """Set log level based on debug mode if not explicitly set."""
        if v is None:
            debug = info.data.get('debug', True)
            return "DEBUG" if debug else "INFO"
        return v
    
    # Backward compatibility properties
    @property
    def ENVIRONMENT(self) -> str:
        return self.environment
    
    @property
    def DEBUG(self) -> bool:
        return self.debug
    
    @property
    def LOG_LEVEL(self) -> str:
        return self.log_level
    
    @property
    def LLM_PROVIDER(self) -> str:
        return self.llm_provider.lower()
    
    @property
    def RATE_LIMIT_REQUESTS(self) -> int:
        return self.rate_limit_requests
    
    @property
    def RATE_LIMIT_WINDOW(self) -> int:
        return self.rate_limit_window
    
    # Private API key properties for backward compatibility
    @property
    def _OPENAI_API_KEY(self) -> Optional[str]:
        return self.openai_api_key
    
    @property
    def _ANTHROPIC_API_KEY(self) -> Optional[str]:
        return self.anthropic_api_key
    
    @property
    def _MISTRAL_API_KEY(self) -> Optional[str]:
        return self.mistral_api_key
    
    @property
    def _TRUSTPILOT_API_KEY(self) -> Optional[str]:
        return self.trustpilot_api_key
    
    @property
    def _GITHUB_TOKEN(self) -> Optional[str]:
        return self.github_token
    
    @property
    def _LINKEDIN_CLIENT_ID(self) -> Optional[str]:
        return self.linkedin_client_id
    
    @property
    def _LINKEDIN_CLIENT_SECRET(self) -> Optional[str]:
        return self.linkedin_client_secret
    
    @property
    def _TWITTER_BEARER_TOKEN(self) -> Optional[str]:
        return self.twitter_bearer_token
    
    @property
    def _TWITTER_API_KEY(self) -> Optional[str]:
        return self.twitter_api_key
    
    @property
    def _TWITTER_API_SECRET(self) -> Optional[str]:
        return self.twitter_api_secret
    
    @property
    def _DISCORD_BOT_TOKEN(self) -> Optional[str]:
        return self.discord_bot_token
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """
        Get API key for a specific provider.
        
        SECURITY: This method should only be used internally.
        Never log or expose the returned value.
        
        Args:
            provider: Provider name (openai, anthropic, google, trustpilot, github, linkedin_client_id, linkedin_client_secret, twitter_bearer, twitter_api_key, twitter_api_secret, discord)
            
        Returns:
            API key if configured, None otherwise
        """
        provider = provider.lower()
        key_map = {
            "openai": self._OPENAI_API_KEY,
            "anthropic": self._ANTHROPIC_API_KEY,
            "mistral": self._MISTRAL_API_KEY,
            "trustpilot": self._TRUSTPILOT_API_KEY,
            "github": self._GITHUB_TOKEN,
            # Third-party APIs (optional)
            "linkedin_client_id": self._LINKEDIN_CLIENT_ID,
            "linkedin_client_secret": self._LINKEDIN_CLIENT_SECRET,
            "twitter_bearer": self._TWITTER_BEARER_TOKEN,
            "twitter_bearer_token": self._TWITTER_BEARER_TOKEN,
            "twitter_api_key": self._TWITTER_API_KEY,
            "twitter_api_secret": self._TWITTER_API_SECRET,
            "discord": self._DISCORD_BOT_TOKEN,
            "discord_bot_token": self._DISCORD_BOT_TOKEN,
        }
        
        key = key_map.get(provider)
        
        if key:
            # SECURITY: Never log the actual key
            logger.debug(f"[OK] API key for {provider}: configured ({len(key)} chars)")
        else:
            logger.debug(f"[WARNING] API key for {provider}: not configured")
        
        return key
    
    def validate_required_keys(self) -> dict:
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
        llm_key = self.get_api_key(self.LLM_PROVIDER)
        if not llm_key:
            results["errors"].append(
                f"❌ Missing API key for LLM provider '{self.LLM_PROVIDER}'. "
                f"Set {self.LLM_PROVIDER.upper()}_API_KEY in .env"
            )
            results["valid"] = False
        elif len(llm_key) < 10:
            results["warnings"].append(
                f"⚠️ API key for {self.LLM_PROVIDER} seems too short (might be placeholder)"
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
        if not self.get_api_key("github"):
            results["warnings"].append(
                "ℹ️ GitHub token not configured. API rate limits will be lower."
            )
        
        if not self.get_api_key("trustpilot"):
            results["warnings"].append(
                "ℹ️ Trustpilot API key not configured. Will use web scraping (slower)."
            )
        
        return results
    
    def is_api_key_valid_format(self, provider: str) -> bool:
        """
        Check if API key has valid format (basic validation).
        
        Args:
            provider: Provider name
            
        Returns:
            True if format looks valid, False otherwise
        """
        key = self.get_api_key(provider)
        if not key:
            return False
        
        # Basic format validation
        format_rules = {
            "openai": lambda k: k.startswith("sk-") and len(k) > 20,
            "anthropic": lambda k: k.startswith("sk-ant-") and len(k) > 20,
            "mistral": lambda k: len(k) > 10,
            "github": lambda k: (k.startswith("ghp_") or k.startswith("github_pat_")) and len(k) > 20,
            "trustpilot": lambda k: len(k) > 10,
            "linkedin_client_id": lambda k: len(k) > 10,
            "linkedin_client_secret": lambda k: len(k) > 10,
            "twitter_bearer": lambda k: len(k) > 20,
            "twitter_bearer_token": lambda k: len(k) > 20,
            "twitter_api_key": lambda k: len(k) > 10,
            "twitter_api_secret": lambda k: len(k) > 10,
            "discord": lambda k: len(k) > 50,  # Discord bot tokens are typically long
            "discord_bot_token": lambda k: len(k) > 50,
        }
        
        validator = format_rules.get(provider.lower())
        if validator:
            return validator(key)
        
        return len(key) > 10
    
    @staticmethod
    def mask_api_key(key: str) -> str:
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
    
    def get_config_summary(self) -> str:
        """
        Get a summary of current configuration (safe for logging).
        
        Returns:
            Configuration summary string
        """
        summary = []
        summary.append("=" * 50)
        summary.append("🔧 APPLICATION CONFIGURATION")
        summary.append("=" * 50)
        summary.append(f"Environment: {self.ENVIRONMENT}")
        summary.append(f"Debug mode: {self.DEBUG}")
        summary.append(f"Log level: {self.LOG_LEVEL}")
        summary.append(f"LLM Provider: {self.LLM_PROVIDER}")
        summary.append("")
        summary.append("🔑 API Keys Status:")
        
        providers = ["openai", "anthropic", "mistral", "github", "trustpilot"]
        for provider in providers:
            key = self.get_api_key(provider)
            if key:
                masked = self.mask_api_key(key)
                valid = "✅" if self.is_api_key_valid_format(provider) else "⚠️"
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
            ("discord", "Discord Bot Token"),
        ]
        for provider_key, provider_name in third_party_providers:
            key = self.get_api_key(provider_key)
            if key:
                masked = self.mask_api_key(key)
                valid = "✅" if self.is_api_key_valid_format(provider_key) else "⚠️"
                summary.append(f"  {valid} {provider_name:20s}: {masked}")
            else:
                summary.append(f"  ⚪ {provider_name:20s}: Not configured (optional)")
        
        summary.append("")
        summary.append(f"🛡️ Rate Limiting: {self.RATE_LIMIT_REQUESTS} req/{self.RATE_LIMIT_WINDOW}s")
        summary.append(f"💾 Database: PostgreSQL")
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
