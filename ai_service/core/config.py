"""
Configuration settings for the Birth Time Rectifier API.
"""

import os
from typing import Optional, Dict, Any, List, Union
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from ai_service.utils.env_loader import get_env_with_fallback

# Load .env file
load_dotenv()

# Configure logging
logger = logging.getLogger("birth-time-rectifier.config")

# Get the current environment
ENV = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()

class RedisSettings(BaseSettings):
    """Redis connection settings."""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    prefix: str = Field(default="birth_time_rectifier:")
    use_redis: bool = Field(default=False)
    connection_timeout: int = Field(default=5)
    retry_count: int = Field(default=3)
    retry_delay: int = Field(default=1)

    @validator('use_redis', pre=True)
    def validate_use_redis(cls, v):
        """Validate and convert use_redis to boolean."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ('true', '1', 'yes', 'y', 't')
        return bool(v)

    model_config = {
        "env_prefix": "REDIS_",
        "env_file": ".env",
        "extra": "allow"
    }

class SessionSettings(BaseSettings):
    """Session management settings."""
    secret_key: str = Field(default="your-secret-key-here")
    cookie_name: str = Field(default="birth_time_rectifier_session")
    cookie_secure: bool = Field(default=False)
    cookie_httponly: bool = Field(default=True)
    cookie_samesite: str = Field(default="lax")
    cookie_max_age: int = Field(default=86400)  # 24 hours
    session_dir: str = Field(default="sessions")

    model_config = {
        "env_prefix": "SESSION_",
        "env_file": ".env",
        "extra": "allow"
    }

class Settings(BaseSettings):
    """Application settings loaded from environment variables with defaults"""

    # Environment
    environment: str = Field(default="development")

    # API settings
    API_PREFIX: str = Field(default="/api/v1")
    PROJECT_NAME: str = "Birth Time Rectifier API"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False)

    # CORS settings
    CORS_ORIGINS: List[str] = Field(default=["*"])
    CORS_HEADERS: List[str] = ["*"]

    # Authentication settings
    SECRET_KEY: str = Field(default="dev_secret_key_change_in_production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis settings
    redis: RedisSettings = Field(default_factory=RedisSettings)

    # Database settings with safe defaults
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = ""
    DB_NAME: str = "birth_time_rectifier"
    DB_SSL: bool = False
    DATABASE_URL: Optional[str] = None  # Add this field for the validator

    # Add a flag to skip DB initialization if needed - default to True in development
    DB_SKIP_INIT: bool = True if ENV in ("development", "test") else False

    # Media and export settings - use absolute paths with proper defaults
    @property
    def MEDIA_ROOT(self) -> str:
        """Get the media root directory with proper default path."""
        media_path = os.environ.get("MEDIA_ROOT")
        if media_path:
            return media_path
        # Default to a 'media' directory in the project root
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media")

    @property
    def UPLOADS_DIR(self) -> str:
        """Get the uploads directory with fallback to MEDIA_ROOT/uploads."""
        uploads_path = os.environ.get("UPLOADS_DIR")
        if uploads_path:
            return uploads_path
        return os.path.join(self.MEDIA_ROOT, "uploads")

    @property
    def EXPORTS_DIR(self) -> str:
        """Get the exports directory with fallback to MEDIA_ROOT/exports."""
        exports_path = os.environ.get("EXPORTS_DIR")
        if exports_path:
            return exports_path
        return os.path.join(self.MEDIA_ROOT, "exports")

    # OpenAI API settings (for AI integration)
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_ORG_ID: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4-turbo-preview")

    # GPU settings
    GPU_MEMORY_FRACTION: Optional[float] = None

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)

    # Session settings
    session: SessionSettings = Field(default_factory=SessionSettings)

    # Chart calculation settings
    DEFAULT_HOUSE_SYSTEM: str = Field(default="P")
    DEFAULT_ZODIAC_TYPE: str = Field(default="sidereal")
    DEFAULT_AYANAMSA: float = Field(default=23.6647)

    @validator("GPU_MEMORY_FRACTION", pre=True, allow_reuse=True)
    def parse_gpu_memory_fraction(cls, v, values):  # pylint: disable=E0213
        """Parse GPU memory fraction with comment handling"""
        if v is not None:
            return v

        # Get the value from environment or use default
        raw_value = os.environ.get("GPU_MEMORY_FRACTION", "0.7")

        if raw_value is None:
            return 0.7

        # Handle comments (remove everything after #)
        if isinstance(raw_value, str) and '#' in raw_value:
            raw_value = raw_value.split('#')[0].strip()

        # Convert to float
        try:
            return float(raw_value)
        except (ValueError, TypeError):
            return 0.7

    @validator("DATABASE_URL", pre=True)
    def assemble_db_url(cls, v: Optional[str], values) -> Optional[str]:  # pylint: disable=E0213
        """
        Build a database URL from individual components if not explicitly provided
        """
        if v and len(v) > 0:
            return v

        # Default to None if any required value is missing
        required_fields = ['DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT', 'DB_NAME']
        for field in required_fields:
            if field not in values or values.get(field) is None:
                return None

        # Build the URL from separate components
        db_user = values.get('DB_USER')
        db_password = values.get('DB_PASSWORD')
        db_host = values.get('DB_HOST')
        db_port = values.get('DB_PORT')
        db_name = values.get('DB_NAME')

        # Return PostgreSQL connection string
        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    @property
    def EPHEMERIS_PATH(self) -> str:
        """Get the ephemeris directory with proper default path."""
        ephemeris_path = os.environ.get("EPHEMERIS_PATH")
        if ephemeris_path:
            return ephemeris_path
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ephemeris")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "validate_assignment": True,
        "extra": "allow"  # Allow extra fields to be included
    }

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

# Ensure necessary directories exist - use the property getters
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
os.makedirs(settings.session.session_dir, exist_ok=True)
os.makedirs(settings.EPHEMERIS_PATH, exist_ok=True)
