"""
Dependency Injection Container

This module provides a simple dependency injection container for managing service dependencies.
It allows for easy mocking during tests while providing real implementations in production.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Generic, Optional, cast

# Setup logging
logger = logging.getLogger(__name__)

T = TypeVar('T')

class DependencyContainer:
    """
    Simple dependency injection container to manage service instances.

    This container allows registering service factories and retrieving instances,
    facilitating both production use and testing with mocks.
    """

    def __init__(self):
        """Initialize the dependency container."""
        self._factories: Dict[str, Any] = {}
        self._instances: Dict[str, Any] = {}
        self._mocks: Dict[str, Any] = {}
        logger.info("Dependency container initialized")

    def register(self, name: str, factory: Any) -> None:
        """
        Register a service factory function.

        Args:
            name: The name of the service
            factory: Factory function that creates the service
        """
        self._factories[name] = factory
        logger.debug(f"Registered factory for '{name}'")

    def register_instance(self, name: str, instance: Any) -> None:
        """
        Register an already instantiated service.

        Args:
            name: The name of the service
            instance: The service instance
        """
        self._instances[name] = instance
        logger.debug(f"Registered instance for '{name}'")

    def register_mock(self, name: str, mock_instance: Any) -> None:
        """
        Register a mock for a service (for testing).

        Args:
            name: The name of the service
            mock_instance: The mock instance
        """
        self._mocks[name] = mock_instance
        logger.debug(f"Registered mock for '{name}'")

    def clear_mocks(self) -> None:
        """Clear all registered mocks."""
        self._mocks.clear()
        logger.debug("Cleared all mocks")

    def get(self, name: str) -> Any:
        """
        Get a service instance.

        Args:
            name: The name of the service to retrieve

        Returns:
            The service instance or None if not found

        Raises:
            ValueError: If the service is not registered
        """
        # Check if there's a mock registered for this service
        if name in self._mocks:
            logger.debug(f"Returning mock for '{name}'")
            return self._mocks[name]

        # Check if there's an existing instance
        if name in self._instances:
            return self._instances[name]

        # Create a new instance using the factory
        if name in self._factories:
            try:
                instance = self._factories[name]()
                # Cache the instance
                self._instances[name] = instance
                logger.debug(f"Created and cached instance for '{name}'")
                return instance
            except Exception as e:
                logger.error(f"Error creating instance for '{name}': {e}")
                raise ValueError(f"Error creating service '{name}': {e}")

        # Service not found
        logger.error(f"Service '{name}' not registered")
        raise ValueError(f"Service '{name}' not registered")

    def has_service(self, name: str) -> bool:
        """
        Check if a service is registered in the container.

        Args:
            name: The name of the service to check

        Returns:
            True if the service is registered, False otherwise
        """
        return name in self._factories or name in self._instances or name in self._mocks

    def register_service(self, name: str, service: Any) -> None:
        """
        Register a service in the container.

        Args:
            name: The name of the service
            service: The service instance
        """
        self.register_instance(name, service)
        logger.debug(f"Registered service '{name}'")

# Create a global container instance
container = DependencyContainer()

def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    return container

def register_openai_service():
    """Register the OpenAI service in the dependency container."""
    from ai_service.api.services.openai.service import OpenAIService

    container = get_container()
    if not container.has_service("openai_service"):
        openai_service = OpenAIService()
        container.register_service("openai_service", openai_service)

def register_chart_service():
    """Register the Chart service in the dependency container."""
    container = get_container()
    if not container.has_service("chart_service"):
        try:
            # Import here to avoid circular imports
            from ai_service.services.chart_service import create_chart_service

            # First register the factory
            container.register("chart_service", create_chart_service)
            logger.info("Registered chart_service factory")

            # Then immediately create an instance to verify it works
            chart_service = container.get("chart_service")
            logger.info("Successfully initialized chart_service")
        except Exception as e:
            logger.error(f"Failed to register chart_service: {e}")
            # Fallback to a basic implementation if available
            try:
                from ai_service.api.services.chart import get_chart_service
                chart_service = get_chart_service()
                container.register_service("chart_service", chart_service)
                logger.info("Registered fallback chart_service")
            except Exception as fallback_error:
                logger.error(f"Failed to register fallback chart_service: {fallback_error}")
                raise ValueError(f"Chart service registration failed completely: {e} -> {fallback_error}")

# Call this on module import to ensure the services are registered
register_openai_service()
register_chart_service()
