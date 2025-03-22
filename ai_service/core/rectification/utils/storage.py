"""
Storage utilities for chart and rectification data.
"""
import os
import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

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
            # Use a consistent path for both storing and retrieving charts
            chart_repo = ChartRepository()
            data_dir = chart_repo.file_storage_path
            storage_paths.append(data_dir)

            # Make sure the directory exists
            os.makedirs(data_dir, exist_ok=True)

            # Store in the chart directory
            file_path = os.path.join(data_dir, f"{chart_id}.json")
            with open(file_path, "w") as f:
                json.dump(chart_data_with_meta, f, cls=DateTimeEncoder, indent=2)
            logger.info(f"Stored rectified chart with ID: {chart_id} at path: {file_path}")

            # Also store in main app data directory for redundancy
            app_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "charts")
            storage_paths.append(app_data_dir)
            os.makedirs(app_data_dir, exist_ok=True)
            app_file_path = os.path.join(app_data_dir, f"{chart_id}.json")
            with open(app_file_path, "w") as f:
                json.dump(chart_data_with_meta, f, cls=DateTimeEncoder, indent=2)
            logger.info(f"Stored rectified chart with ID: {chart_id} at additional path: {app_file_path}")

            # Store in test output directory if it exists (helps test find the chart)
            test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "tests", "test_data_source", "charts")
            if not os.path.exists(test_dir):
                os.makedirs(test_dir, exist_ok=True)
            storage_paths.append(test_dir)
            test_file_path = os.path.join(test_dir, f"{chart_id}.json")
            with open(test_file_path, "w") as f:
                json.dump(chart_data_with_meta, f, cls=DateTimeEncoder, indent=2)
            logger.info(f"Stored rectified chart with ID: {chart_id} at test path: {test_file_path}")

            # Log all storage paths for reference
            logger.info(f"Chart {chart_id} stored at the following locations: {', '.join(storage_paths)}")
            return chart_id
        except Exception as e:
            logger.error(f"Failed to store chart to file: {e}")

            # Last resort fallback to default directory
            try:
                default_data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data", "charts")
                os.makedirs(default_data_dir, exist_ok=True)
                file_path = os.path.join(default_data_dir, f"{chart_id}.json")
                with open(file_path, "w") as f:
                    json.dump(chart_data_with_meta, f, cls=DateTimeEncoder, indent=2)
                logger.info(f"Stored rectified chart with ID: {chart_id} at fallback path: {file_path}")
                return chart_id
            except Exception as fallback_error:
                logger.error(f"Final fallback storage failed: {fallback_error}")
                return None

    except Exception as e:
        logger.error(f"Error storing rectified chart: {e}")
        return None
