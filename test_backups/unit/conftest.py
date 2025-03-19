"""
Pytest fixtures for unit tests.
"""

import pytest
from ai_service.utils.dependency_container import get_container


@pytest.fixture(scope="function")
def reset_container():
    """Reset the dependency container before and after each test."""
    # Get the container and clear all registered mocks
    container = get_container()

    # Clear any existing mocks
    if hasattr(container, '_mocks'):
        container._mocks = {}

    # Let the test run
    yield

    # Clean up after the test
    if hasattr(container, '_mocks'):
        container._mocks = {}
