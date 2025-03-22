"""
JSON encoder utilities for handling datetime objects in serialization.

This module provides a shared DateTimeEncoder for use across the application.
"""

import json
from datetime import datetime, date
from typing import Any


class DateTimeEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that can handle datetime and date objects.
    Dates and datetimes are converted to ISO format strings.
    """
    def default(self, obj: Any) -> Any:
        """
        Encode datetime and date objects as ISO format strings.

        Args:
            obj: The object to encode

        Returns:
            ISO format string for datetime/date objects, or super().default() for other types
        """
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)
