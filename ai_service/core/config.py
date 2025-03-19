"""
Configuration settings for the Birth Time Rectifier API.
Loads environment variables and provides default values.
"""

import os
from typing import Optional, Dict, Any, List
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configure logging
logger = logging.getLogger("birth-time-rectifier.config")

# Define our own BaseSettings class to avoid Pydantic import issues
class BaseSettings:
    """Simple settings base class to replace Pydantic's BaseSettings"""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def dict(self) -> Dict[str, Any]:
        """Return settings as dictionary"""
        return {k: v for k, v in self.__dict__.items()
                if not k.startswith('_') and not callable(v)}

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

    # OpenAI API settings (for AI integration)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY", None)

    # GPU settings
    # Handle potential comments in environment variables by stripping everything after #
    GPU_MEMORY_FRACTION: float = float(os.getenv("GPU_MEMORY_FRACTION", "0.7").split('#')[0].strip())

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Session settings
    SESSION_TTL: int = 3600  # 1 hour in seconds

    class Config:
        env_file = ".env"
        case_sensitive = True

    def dict_with_secrets_hidden(self) -> Dict[str, Any]:
        """Returns settings dict with sensitive values hidden"""
        settings_dict = self.dict()
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
