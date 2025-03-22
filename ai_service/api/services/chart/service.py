"""
Chart service implementation.
"""

import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

class ChartService:
    """Service for accessing and managing chart data."""

    def __init__(self, db_connection=None):
        """
        Initialize the chart service.

        Args:
            db_connection: Database connection (required)
        """
        if db_connection is None:
            raise ValueError("Database connection is required for chart service")

        self.db_connection = db_connection
        logger.info("Chart service initialized with database connection")

        # Initialize cache for improved performance
        # Note: This is not a fallback - just a performance optimization
        self.chart_cache = {}

    async def get_chart(self, chart_id: str) -> Dict[str, Any]:
        """
        Retrieve chart data from database.

        Args:
            chart_id: Unique identifier for the chart

        Returns:
            Dictionary containing chart data

        Raises:
            ValueError: If chart not found
            Exception: For database errors
        """
        try:
            # Check if chart is in cache
            if chart_id in self.chart_cache:
                logger.debug(f"Retrieved chart {chart_id} from cache")
                return self.chart_cache[chart_id]

            # Get chart from database
            logger.info(f"Retrieving chart {chart_id} from database")

            # Execute database query
            query = "SELECT chart_data FROM charts WHERE chart_id = %s"
            result = await self.db_connection.fetch_one(query, chart_id)

            if not result:
                logger.error(f"Chart {chart_id} not found in database")
                raise ValueError(f"Chart not found: {chart_id}")

            # Parse chart data from database safely
            if result and isinstance(result, dict) and 'chart_data' in result:
                chart_data = json.loads(result['chart_data'])
            else:
                logger.error("Invalid database result format")
                raise ValueError("Invalid database result format")

            # Add to cache for future requests
            self.chart_cache[chart_id] = chart_data

            # Manage cache size to prevent memory issues
            if len(self.chart_cache) > 1000:  # Limit cache to 1000 entries
                # Remove oldest entries (first 200)
                keys_to_remove = list(self.chart_cache.keys())[:200]
                for key in keys_to_remove:
                    del self.chart_cache[key]

            return chart_data

        except ValueError:
            # Re-raise ValueError for not found charts
            raise
        except Exception as e:
            logger.error(f"Database error retrieving chart {chart_id}: {str(e)}")
            raise

    async def save_chart(self, chart_data: Dict[str, Any]) -> str:
        """
        Save chart data to database.

        Args:
            chart_data: Chart data to save

        Returns:
            Chart ID

        Raises:
            Exception: For database errors
        """
        try:
            # Generate a chart ID if not provided
            chart_id = chart_data.get("chart_id", f"chrt_{datetime.now().strftime('%Y%m%d%H%M%S')}")

            # Ensure chart_id is in the chart data
            chart_data["chart_id"] = chart_id

            # Add timestamp if not present
            if "generated_at" not in chart_data:
                chart_data["generated_at"] = datetime.now().isoformat()

            # Convert chart data to JSON
            chart_json = json.dumps(chart_data)

            # Insert or update in database
            logger.info(f"Saving chart {chart_id} to database")
            query = """
                INSERT INTO charts (chart_id, chart_data, created_at, updated_at)
                VALUES (%s, %s, NOW(), NOW())
                ON CONFLICT (chart_id)
                DO UPDATE SET chart_data = %s, updated_at = NOW()
            """
            await self.db_connection.execute(query, chart_id, chart_json, chart_json)

            # Store in cache for future requests
            self.chart_cache[chart_id] = chart_data

            return chart_id
        except Exception as e:
            logger.error(f"Database error saving chart: {str(e)}")
            raise

    async def delete_chart(self, chart_id: str) -> bool:
        """
        Delete a chart from the database.

        Args:
            chart_id: The ID of the chart to delete

        Returns:
            True if deleted successfully

        Raises:
            Exception: For database errors
        """
        try:
            logger.info(f"Deleting chart {chart_id} from database")

            # Delete from database
            query = "DELETE FROM charts WHERE chart_id = %s"
            result = await self.db_connection.execute(query, chart_id)

            # Remove from cache if present
            if chart_id in self.chart_cache:
                del self.chart_cache[chart_id]

            # Check if any rows were affected
            return result > 0
        except Exception as e:
            logger.error(f"Database error deleting chart {chart_id}: {str(e)}")
            raise

    async def get_charts_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all charts for a specific user.

        Args:
            user_id: The ID of the user

        Returns:
            List of chart data dictionaries

        Raises:
            Exception: For database errors
        """
        try:
            logger.info(f"Retrieving charts for user {user_id}")

            # Execute database query
            query = "SELECT chart_data FROM charts WHERE user_id = %s ORDER BY created_at DESC"
            results = await self.db_connection.fetch_all(query, user_id)

            # Parse chart data from database safely
            charts = []
            for row in results:
                if isinstance(row, dict) and 'chart_data' in row:
                    try:
                        chart_data = json.loads(row['chart_data'])
                        charts.append(chart_data)
                    except json.JSONDecodeError:
                        logger.warning(f"Skipped invalid chart data format for user {user_id}")

            return charts
        except Exception as e:
            logger.error(f"Database error retrieving charts for user {user_id}: {str(e)}")
            raise

    async def generate_chart(
        self,
        birth_date: str,
        birth_time: str,
        latitude: float,
        longitude: float,
        timezone: str,
        location: str = "",
        house_system: str = "P",
        zodiac_type: str = "sidereal",
        ayanamsa: float = 23.6647,
        verify_with_openai: bool = True,
        node_type: str = "true",
        chart_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an astrological chart based on birth details with OpenAI verification.

        Args:
            birth_date: Date of birth (YYYY-MM-DD)
            birth_time: Time of birth (HH:MM:SS)
            latitude: Birth latitude
            longitude: Birth longitude
            timezone: Timezone string (e.g., 'America/New_York')
            location: Birth location name
            house_system: House system to use
            zodiac_type: Zodiac type (sidereal/tropical)
            ayanamsa: Ayanamsa value for sidereal calculations
            verify_with_openai: Whether to verify chart with OpenAI
            node_type: Node type (true/mean)
            chart_id: Optional chart ID to use

        Returns:
            Dict containing chart data
        """
        logger.info("ChartService.generate_chart called - using delegated implementation")

        try:
            # Import here to avoid circular imports
            from ai_service.services import get_chart_service

            # Use the complete implementation from the main chart service
            main_chart_service = get_chart_service()

            # Call the main chart service implementation
            chart_data = await main_chart_service.generate_chart(
                birth_date=birth_date,
                birth_time=birth_time,
                latitude=latitude,
                longitude=longitude,
                timezone=timezone,
                location=location,
                house_system=house_system,
                zodiac_type=zodiac_type,
                ayanamsa=ayanamsa,
                verify_with_openai=verify_with_openai,
                node_type=node_type
            )

            # Save the chart in our database as well
            if chart_data and "chart_id" in chart_data:
                await self.save_chart(chart_data)

            return chart_data
        except Exception as e:
            logger.error(f"Error in ChartService.generate_chart: {e}")
            raise

# Singleton instance
_instance = None

def get_chart_service(db_connection=None) -> ChartService:
    """Get or create the chart service singleton."""
    global _instance
    if _instance is None:
        _instance = ChartService(db_connection)
    return _instance
