# Development environment variables
DATABASE_URL=sqlite:///./test.db
OPENAI_API_KEY=
ENVIRONMENT=development
DEBUG=true
# API Service configuration
AI_SERVICE_URL=http://localhost:8001
# Redis configuration
USE_REDIS=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_PREFIX=birth_time_rectifier:
REDIS_TIMEOUT=5
REDIS_RETRY_COUNT=3
REDIS_RETRY_DELAY=1

# Session Configuration
SESSION_DIR=sessions
SESSION_COOKIE_NAME=birth_time_rectifier_session
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=lax
SESSION_COOKIE_MAX_AGE=86400
