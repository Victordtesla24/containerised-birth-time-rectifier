"""
Services package for Birth Time Rectifier

This package contains service implementations for backend functionality,
including geocoding, chart generation, and other core services.
"""

import logging
from typing import Optional, Dict, Any, List
from importlib import import_module
import os
import json

# Configure logging
logger = logging.getLogger(__name__)

# We'll use lazy loading pattern to avoid circular imports
def get_chart_service():
    """
    Get the chart service implementation.

    This function lazily imports the chart service implementation
    to avoid circular imports.

    Returns:
        The chart service implementation
    """
    from ai_service.services.chart_service import create_chart_service
    return create_chart_service()

def get_openai_service():
    """
    Get the OpenAI service implementation.

    This function lazily imports the OpenAI service implementation
    to avoid circular imports.

    Returns:
        The OpenAI service implementation

    Raises:
        RuntimeError: If OpenAI service is not available
    """
    try:
        from ai_service.api.services.openai.service import OpenAIService
        import os
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if not api_key:
            raise ValueError("OpenAI API key is required but not provided in environment variables")
        return OpenAIService(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to get OpenAI service: {e}")
        raise RuntimeError(f"OpenAI service unavailable: {str(e)}")

# Define the service interface classes for type hinting
class ChartService:
    """
    Chart service interface.

    This class provides methods for generating and manipulating astrological charts.
    """
    pass

class OpenAIService:
    """
    OpenAI service interface.

    This class provides methods for interacting with the OpenAI API.
    """
    def __init__(self, api_key):
        if not api_key:
            raise ValueError("API key is required")
        self.api_key = api_key

    async def verify_chart(self, chart_data):
        """
        Verify chart data using OpenAI.

        Args:
            chart_data: Chart data to verify

        Returns:
            Verification result

        Raises:
            NotImplementedError: This is an interface method that should be implemented
        """
        raise NotImplementedError("This method must be implemented by a concrete OpenAI service class")

    async def generate_text(self, prompt, **kwargs):
        """
        Generate text using OpenAI.

        Args:
            prompt: Text prompt
            **kwargs: Additional parameters

        Returns:
            Generated text

        Raises:
            NotImplementedError: This is an interface method that should be implemented
        """
        raise NotImplementedError("This method must be implemented by a concrete OpenAI service class")

    async def rectify_birth_time(self, chart_data, answers):
        """
        Rectify birth time using OpenAI.

        Args:
            chart_data: Chart data
            answers: Questionnaire answers

        Returns:
            Rectification result

        Raises:
            NotImplementedError: This is an interface method that should be implemented
        """
        raise NotImplementedError("This method must be implemented by a concrete OpenAI service class")

# Create a proper API for user_repository that uses the database in production
# and returns appropriate errors when features aren't available
from ai_service.database.connection import get_db_pool

# User repository API that correctly uses the database in production
async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by email - using the database in production.

    Args:
        email: User email

    Returns:
        User object or None if not found
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot get user by email - database connection required")
        return None

    try:
        # Query user from database
        async with pool.acquire() as conn:
            query = """
                SELECT * FROM users WHERE email = $1
            """
            user = await conn.fetchrow(query, email.lower())
            if user:
                return dict(user)
            return None
    except Exception as e:
        logger.error(f"Error getting user by email: {e}")
        return None

async def get_user(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by ID - using the database in production.

    Args:
        user_id: User ID

    Returns:
        User object or None if not found
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot get user - database connection required")
        return None

    try:
        # Query user from database
        async with pool.acquire() as conn:
            query = """
                SELECT * FROM users WHERE user_id = $1
            """
            user = await conn.fetchrow(query, user_id)
            if user:
                return dict(user)
            return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

async def user_exists(user_id: str) -> bool:
    """
    Check if a user exists - using the database in production.

    Args:
        user_id: User ID

    Returns:
        True if the user exists, False otherwise
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot check if user exists - database connection required")
        return False

    try:
        # Query user from database
        async with pool.acquire() as conn:
            query = """
                SELECT EXISTS(SELECT 1 FROM users WHERE user_id = $1)
            """
            exists = await conn.fetchval(query, user_id)
            return bool(exists)
    except Exception as e:
        logger.error(f"Error checking if user exists: {e}")
        return False

async def create_user(user_data: Dict[str, Any]) -> Optional[str]:
    """
    Create a new user - using the database in production.

    Args:
        user_data: User data

    Returns:
        User ID or None if creation failed
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot create user - database connection required")
        return None

    try:
        # Create user in database
        async with pool.acquire() as conn:
            # Check if email already exists
            email = user_data.get("email", "").lower()
            query = """
                SELECT EXISTS(SELECT 1 FROM users WHERE email = $1)
            """
            exists = await conn.fetchval(query, email)
            if exists:
                logger.error(f"User with email {email} already exists")
                return None

            # Insert new user
            query = """
                INSERT INTO users (username, email, password_hash)
                VALUES ($1, $2, $3)
                RETURNING user_id
            """
            user_id = await conn.fetchval(
                query,
                user_data.get("username", ""),
                email,
                user_data.get("password_hash", "")
            )
            return str(user_id)
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None

async def update_preferences(user_id: str, preferences: Dict[str, Any]) -> bool:
    """
    Update user preferences - using the database in production.

    Args:
        user_id: User ID
        preferences: User preferences

    Returns:
        True if successful, False otherwise
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot update preferences - database connection required")
        return False

    try:
        # Update preferences in database
        async with pool.acquire() as conn:
            query = """
                UPDATE users
                SET preferences = $1
                WHERE user_id = $2
            """
            await conn.execute(query, json.dumps(preferences), user_id)
            return True
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        return False

async def get_user_charts(user_id: str) -> List[str]:
    """
    Get charts for a user - using the database in production.

    Args:
        user_id: User ID

    Returns:
        List of chart IDs
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot get user charts - database connection required")
        return []

    try:
        # Query charts from database
        async with pool.acquire() as conn:
            query = """
                SELECT chart_id FROM user_charts WHERE user_id = $1
            """
            rows = await conn.fetch(query, user_id)
            return [row['chart_id'] for row in rows]
    except Exception as e:
        logger.error(f"Error getting user charts: {e}")
        return []

async def add_chart(user_id: str, chart_id: str) -> bool:
    """
    Add a chart to a user - using the database in production.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot add chart - database connection required")
        return False

    try:
        # Add chart to user in database
        async with pool.acquire() as conn:
            query = """
                INSERT INTO user_charts (user_id, chart_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, chart_id) DO NOTHING
            """
            await conn.execute(query, user_id, chart_id)
            return True
    except Exception as e:
        logger.error(f"Error adding chart: {e}")
        return False

async def remove_chart(user_id: str, chart_id: str) -> bool:
    """
    Remove a chart from a user - using the database in production.

    Args:
        user_id: User ID
        chart_id: Chart ID

    Returns:
        True if successful, False otherwise
    """
    # Get database connection
    pool = await get_db_pool()

    # If no database connection, this feature requires a database
    if not pool:
        logger.error("Cannot remove chart - database connection required")
        return False

    try:
        # Remove chart from user in database
        async with pool.acquire() as conn:
            query = """
                DELETE FROM user_charts
                WHERE user_id = $1 AND chart_id = $2
            """
            await conn.execute(query, user_id, chart_id)
            return True
    except Exception as e:
        logger.error(f"Error removing chart: {e}")
        return False

# For backward compatibility, expose as user_repository
user_repository = {
    "get_user_by_email": get_user_by_email,
    "get_user": get_user,
    "user_exists": user_exists,
    "create_user": create_user,
    "update_preferences": update_preferences,
    "get_user_charts": get_user_charts,
    "add_chart": add_chart,
    "remove_chart": remove_chart
}

# Define an async chart service accessor for consistency
async def get_chart_service_async():
    """
    Get an instance of the ChartService asynchronously.

    This function exists for API consistency with other async service accessors.
    It simply returns the result of the synchronous get_chart_service function.

    Returns:
        ChartService: A chart service instance
    """
    return get_chart_service()

__all__ = [
    "ChartService",
    "OpenAIService",
    "get_chart_service",
    "get_chart_service_async",
    "get_openai_service",
    "user_repository"
]
