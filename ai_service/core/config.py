"""
Configuration settings for the Birth Time Rectifier API.
Loads environment variables and provides default values.
"""

import os
from typing import Optional, Dict, Any, List
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator

# Load .env file
load_dotenv()

# Configure logging
logger = logging.getLogger("birth-time-rectifier.config")

class Settings(BaseSettings):
    """Application settings loaded from environment variables with defaults"""

    # API settings
    API_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "Birth Time Rectifier API"
    VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ["true", "1", "t"]

    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    CORS_HEADERS: List[str] = ["*"]

    # Authentication settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev_secret_key_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Database settings
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
    DB_NAME: str = os.getenv("DB_NAME", "birth_time_rectifier")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Media and export settings
    MEDIA_ROOT: str = os.getenv("MEDIA_ROOT", "/app/media")
    UPLOADS_DIR: str = os.path.join(MEDIA_ROOT, "uploads")
    EXPORTS_DIR: str = os.path.join(MEDIA_ROOT, "exports")

    # OpenAI API settings (for AI integration)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_ORG_ID: str = os.getenv("OPENAI_ORG_ID", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    # GPU settings
    # Handle potential comments in environment variables by stripping everything after #
    GPU_MEMORY_FRACTION: float = float(os.getenv("GPU_MEMORY_FRACTION", "0.7").split('#')[0].strip())

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Session settings
    SESSION_DIR: str = os.getenv("SESSION_DIR", "/app/sessions")
    SESSION_EXPIRY_DAYS: int = int(os.getenv("SESSION_EXPIRY_DAYS", "30"))

    # Chart calculation settings
    EPHEMERIS_PATH: str = os.getenv("EPHEMERIS_PATH", "/app/ephemeris")
    DEFAULT_HOUSE_SYSTEM: str = os.getenv("DEFAULT_HOUSE_SYSTEM", "P")
    DEFAULT_ZODIAC_TYPE: str = os.getenv("DEFAULT_ZODIAC_TYPE", "sidereal")
    DEFAULT_AYANAMSA: float = float(os.getenv("DEFAULT_AYANAMSA", "23.6647"))

    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: Optional[str], values: Dict[str, Any]) -> str:
        if v and len(v) > 0:
            return v

        # Build the URL from separate components
        return f"postgresql://{values.get('DB_USER')}:{values.get('DB_PASSWORD')}@{values.get('DB_HOST')}:{values.get('DB_PORT')}/{values.get('DB_NAME')}"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def dict_with_secrets_hidden(self) -> Dict[str, Any]:
        """Returns settings dict with sensitive values hidden"""
        settings_dict = self.model_dump()
        sensitive_keys = ["SECRET_KEY", "OPENAI_API_KEY"]

        for key in sensitive_keys:
            if key in settings_dict and settings_dict[key]:
                settings_dict[key] = "**HIDDEN**"

        return settings_dict

# Create global settings instance
settings = Settings()

# Log non-sensitive settings in debug mode
if settings.DEBUG:
    logger.debug(f"Loaded settings: {settings.dict_with_secrets_hidden()}")

# Ensure necessary directories exist
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
os.makedirs(settings.SESSION_DIR, exist_ok=True)
os.makedirs(settings.EPHEMERIS_PATH, exist_ok=True)
