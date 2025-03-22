"""
Custom exceptions for the Birth Time Rectifier application.

This module contains all the application-specific exceptions used for error handling
across different services and components.
"""

class BaseServiceError(Exception):
    """Base exception for all service-related errors."""
    def __init__(self, message="Service error occurred", details=None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ChartServiceError(BaseServiceError):
    """Exception raised for errors in the chart service."""
    def __init__(self, message="Error in chart service", details=None):
        super().__init__(f"Chart Service Error: {message}", details)


class GeocodingError(BaseServiceError):
    """Exception raised for errors in geocoding services."""
    def __init__(self, message="Error in geocoding service", details=None):
        super().__init__(f"Geocoding Error: {message}", details)


class RectificationError(BaseServiceError):
    """Exception raised for errors in birth time rectification process."""
    def __init__(self, message="Error in birth time rectification", details=None):
        super().__init__(f"Rectification Error: {message}", details)


class QuestionnaireError(BaseServiceError):
    """Exception raised for errors in questionnaire handling."""
    def __init__(self, message="Error in questionnaire processing", details=None):
        super().__init__(f"Questionnaire Error: {message}", details)


class OpenAIServiceError(BaseServiceError):
    """Exception raised for errors in OpenAI API interactions."""
    def __init__(self, message="Error in OpenAI service", details=None, status_code=None):
        error_details = details or {}
        if status_code:
            error_details["status_code"] = status_code
        super().__init__(f"OpenAI Service Error: {message}", error_details)


class DatabaseError(BaseServiceError):
    """Exception raised for database errors."""
    def __init__(self, message="Database error occurred", details=None):
        super().__init__(f"Database Error: {message}", details)


class EphemerisError(BaseServiceError):
    """Exception raised for errors related to ephemeris data or calculations."""
    def __init__(self, message="Error with ephemeris data or calculations", details=None):
        super().__init__(f"Ephemeris Error: {message}", details)


class ValidationError(BaseServiceError):
    """Exception raised for data validation errors."""
    def __init__(self, message="Data validation error", details=None):
        super().__init__(f"Validation Error: {message}", details)


class ConfigurationError(BaseServiceError):
    """Exception raised for configuration errors."""
    def __init__(self, message="Configuration error", details=None):
        super().__init__(f"Configuration Error: {message}", details)


class ResourceExhaustionError(BaseServiceError):
    """Exception raised when a resource (API limits, memory, etc.) is exhausted."""
    def __init__(self, message="Resource exhaustion", details=None):
        super().__init__(f"Resource Exhaustion Error: {message}", details)
