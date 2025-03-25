"""
Storage utilities for chart and rectification data.
"""
import os
import logging
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class ChartFileStorage:
    """
    File storage implementation for chart data that follows the Storage pattern.
    Provides consistent access to chart storage locations across the application.
    """
    def __init__(self):
        # Base application directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

        # Primary storage location
        self.file_storage_path = os.path.join(self.base_dir, "data", "charts")

        # Additional storage locations for redundancy
        self.storage_locations = [
            self.file_storage_path,
            os.path.join(self.base_dir, "tests", "test_data_source", "charts")
        ]

        # Ensure all storage directories exist
        for path in self.storage_locations:
            os.makedirs(path, exist_ok=True)

    def get_storage_paths(self) -> List[str]:
        """Returns all available storage paths for charts"""
        return self.storage_locations

    def save(self, chart_id: str, chart_data: Dict[str, Any]) -> List[str]:
        """
        Saves chart data to all storage locations

        Args:
            chart_id: Unique identifier for the chart
            chart_data: Chart data to store

        Returns:
            List of paths where the chart was stored
        """
        saved_paths = []

        for path in self.storage_locations:
            try:
                file_path = os.path.join(path, f"{chart_id}.json")
                with open(file_path, "w") as f:
                    json.dump(chart_data, f, cls=DateTimeEncoder, indent=2)
                saved_paths.append(file_path)
                logger.info(f"Stored chart with ID: {chart_id} at path: {file_path}")
            except Exception as e:
                logger.error(f"Failed to store chart at {path}: {e}")

        return saved_paths

    def exists(self, chart_id: str) -> bool:
        """Check if a chart with the given ID exists in any storage location"""
        for path in self.storage_locations:
            if os.path.exists(os.path.join(path, f"{chart_id}.json")):
                return True
        return False

async def store_rectified_chart(chart_data: Dict[str, Any], rectification_id: str, birth_dt: datetime, rectified_time_dt: datetime) -> Optional[str]:
    """
    Store a rectified chart in the database or file system.

    Args:
        chart_data: Chart data to store
        rectification_id: ID of the rectification request
        birth_dt: Original birth datetime
        rectified_time_dt: Rectified birth datetime

    Returns:
        ID of the newly created chart or None if storage failed
    """
    try:
        # Import here to avoid circular imports
        from ai_service.utils.dependency_container import get_container
        from ai_service.database.repositories import ChartRepository

        # Generate a unique chart ID
        chart_id = f"rectified_chart_{rectification_id}_{uuid.uuid4().hex[:8]}"

        # Prepare chart data with metadata
        chart_data_with_meta = {
            "id": chart_id,
            "chart_data": chart_data,
            "chart_type": "rectified",
            "original_birth_time": birth_dt.isoformat(),
            "rectified_birth_time": rectified_time_dt.isoformat(),
            "adjustment_minutes": round((rectified_time_dt - birth_dt).total_seconds() / 60),
            "created_at": datetime.now().isoformat(),
            "rectification_id": rectification_id
        }

        # List of all possible storage paths to ensure consistency
        storage_paths = []

        # Try to use chart repository if available
        try:
            container = get_container()
            if container.has_service("chart_repository"):
                chart_repository = container.get("chart_repository")
                await chart_repository.store_chart(chart_data_with_meta)
                logger.info(f"Stored rectified chart with ID: {chart_id} using repository")
        except Exception as e:
            logger.warning(f"Failed to use repository, falling back to file storage: {e}")

        # Always use file storage for redundancy, regardless of repository success
        try:
            # Use the ChartFileStorage class for consistent file storage
            chart_storage = ChartFileStorage()
            storage_paths.extend(chart_storage.get_storage_paths())

            # Store the chart in all available locations
            saved_paths = chart_storage.save(chart_id, chart_data_with_meta)

            if saved_paths:
                logger.info(f"Chart {chart_id} stored at the following locations: {', '.join(saved_paths)}")
                return chart_id
            else:
                logger.error("Failed to store chart in any location")
                return None

        except Exception as e:
            logger.error(f"Failed to store chart to file: {e}")

    except Exception as e:
        logger.error(f"Error storing rectified chart: {e}")
        return None
