"""
Dependency Injection Container

This module provides a simple dependency injection container for managing service dependencies.
It allows for easy mocking during tests while providing real implementations in production.
"""

import logging
from typing import Dict, Any, Type, TypeVar, Generic, Optional, cast, Union

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

def initialize_container() -> None:
    """
    Initialize the dependency container.
    This resets the container state and prepares it for use.
    """
    global container
    container = DependencyContainer()
    logger.info("Dependency container re-initialized")

def register_openai_service():
    """Register the OpenAI service in the dependency container."""
    # Import inside the function to prevent circular imports
    container = get_container()
    if not container.has_service("openai_service"):
        try:
            # Import the OpenAI service dynamically to avoid circular imports
            from ai_service.api.services.openai import get_openai_service_sync, OpenAIService

            # Try to get an already initialized instance
            openai_service = get_openai_service_sync()

            if openai_service:
                # Register the existing instance
                container.register_service("openai_service", openai_service)
                logger.info("Registered existing OpenAI service instance")
            else:
                # Register a factory function that will properly initialize the service
                async def openai_factory():
                    from ai_service.api.services.openai import get_openai_service
                    service = await get_openai_service()
                    if not service:
                        raise ValueError("Could not initialize OpenAI service")
                    return service

                container.register("openai_service", openai_factory)
                logger.info("Registered OpenAI service factory")
        except Exception as e:
            logger.error(f"Failed to register OpenAI service: {e}")
            # No fallbacks - raise the error
            raise ValueError(f"OpenAI service registration failed: {e}")

def register_chart_service():
    """Register the Chart service in the dependency container."""
    container = get_container()
    if not container.has_service("chart_service"):
        try:
            # Import the real ChartService implementation
            from ai_service.services.chart_service import ChartService, create_chart_service

            # Create a real instance using the factory function
            chart_service = create_chart_service()

            # Register the service
            container.register_service("chart_service", chart_service)
            logger.info("Registered the production ChartService implementation")
        except Exception as e:
            logger.error(f"Failed to register chart_service: {e}")
            # No fallbacks - raise the error
            raise ValueError(f"Chart service registration failed: {e}")

# Call this on module import to ensure the services are registered
register_openai_service()
register_chart_service()

def get_instance(cls_or_name: Union[Type[T], str]) -> Optional[T]:
    """
    Get an instance from the container by class or name.

    Args:
        cls_or_name: The class or name of the instance to retrieve.

    Returns:
        The instance or None if not found.
    """
    container_instance = get_container()

    # If it's a class, try to find by class name first
    if isinstance(cls_or_name, type):
        class_name = cls_or_name.__name__
        try:
            return cast(T, container_instance.get(class_name))
        except ValueError:
            # Try checking if any registered service is an instance of this class
            for name in container_instance._instances:
                instance = container_instance._instances[name]
                if isinstance(instance, cls_or_name):
                    return cast(T, instance)
            return None
    else:
        # It's a string name
        try:
            return cast(T, container_instance.get(cls_or_name))
        except ValueError:
            return None
