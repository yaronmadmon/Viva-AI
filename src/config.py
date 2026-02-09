"""
Application configuration using pydantic-settings.
Loads from environment variables with .env file support.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/viva_research"
    
    # Security
    secret_key: str = "change-this-in-production-minimum-32-characters-long"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440  # 24 hours
    
    # Email
    smtp_host: str = "smtp.example.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    
    # OpenAI
    openai_api_key: str = ""

    # Application
    debug: bool = False
    environment: str = "development"
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    
    # API Settings
    api_v1_prefix: str = "/api/v1"
    project_name: str = "Research Accountability Platform"
    version: str = "1.0.0-phase1a"

    # Rate limiting (API Gateway)
    rate_limit_auth_per_minute: int = 10   # per IP for login/register
    rate_limit_api_per_minute: int = 100   # per user or IP for general API
    rate_limit_ai_per_hour: int = 20       # per user for AI suggestion endpoints
    rate_limit_tts_per_hour: int = 50      # per user for TTS endpoint
    rate_limit_avatar_per_hour: int = 100  # per user for avatar chat turns
    rate_limit_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
