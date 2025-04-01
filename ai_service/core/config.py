"""
Configuration settings for the Birth Time Rectifier API.
"""

import os
from typing import Optional, Dict, Any, List
import logging
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field, validator

# Load .env file
load_dotenv()

# Configure logging
logger = logging.getLogger("birth-time-rectifier.config")

# Get the current environment
ENV = os.environ.get("ENVIRONMENT", os.environ.get("APP_ENV", "development")).lower()

class Settings(BaseSettings):
    """Application settings loaded from environment variables with defaults"""

    # Environment
    environment: str = Field(default="development")

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
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")  # Default to localhost for testing
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    USE_REDIS: bool = os.getenv("USE_REDIS", "false").lower() in ["true", "1", "t"]

    # If REDIS_URL is not explicitly provided, construct it from components
    if not REDIS_URL and USE_REDIS:
        REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

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

    # Media and export settings
    MEDIA_ROOT: str = os.getenv("MEDIA_ROOT", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "media"))
    UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", os.path.join(MEDIA_ROOT, "uploads"))
    EXPORTS_DIR: str = os.getenv("EXPORTS_DIR", os.path.join(MEDIA_ROOT, "exports"))

    # OpenAI API settings (for AI integration)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_ORG_ID: str = os.getenv("OPENAI_ORG_ID", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")

    # GPU settings
    GPU_MEMORY_FRACTION: Optional[float] = None

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

    # Session settings
    SESSION_DIR: str = os.getenv("SESSION_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions"))
    SESSION_EXPIRY_DAYS: int = int(os.getenv("SESSION_EXPIRY_DAYS", "30"))
    SESSION_EXPIRY: int = SESSION_EXPIRY_DAYS * 24 * 60 * 60  # Convert days to seconds
    SECURE_COOKIES: bool = os.getenv("SECURE_COOKIES", "False").lower() == "true"

    # Chart calculation settings
    EPHEMERIS_PATH: str = os.getenv("EPHEMERIS_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ephemeris"))
    DEFAULT_HOUSE_SYSTEM: str = os.getenv("DEFAULT_HOUSE_SYSTEM", "P")
    DEFAULT_ZODIAC_TYPE: str = os.getenv("DEFAULT_ZODIAC_TYPE", "sidereal")
    DEFAULT_AYANAMSA: float = float(os.getenv("DEFAULT_AYANAMSA", "23.6647"))

    @validator("GPU_MEMORY_FRACTION", pre=True, allow_reuse=True)
    def parse_gpu_memory_fraction(cls, v, values):  # pylint: disable=E0213
        """Parse GPU memory fraction with comment handling"""
        if v is not None:
            return v

        # Get the value from environment or use default
        raw_value = os.getenv("GPU_MEMORY_FRACTION", "0.7")

        # Handle comments (remove everything after #)
        if '#' in raw_value:
            raw_value = raw_value.split('#')[0].strip()

        # Convert to float
        return float(raw_value)

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        validate_assignment = True
        # Note: validate_all has been renamed to validate_default in Pydantic v2
        validate_default = True
        # This property tells Pydantic not to check that all validator fields exist in the model
        # Essential for inheritance scenarios where fields might be added later
        check_fields = False
        # Allow extra fields to be included, fixing the 'extra inputs are not permitted' error
        extra = "allow"

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

# Ensure necessary directories exist
os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
os.makedirs(settings.SESSION_DIR, exist_ok=True)
os.makedirs(settings.EPHEMERIS_PATH, exist_ok=True)
