"""
Test sequence utility module for ensuring tests run in a specific order.

This module provides decorators and utilities for maintaining state across test runs
and ensuring tests execute in a specific sequence.
"""

import os
import json
import logging
import inspect
import functools
from typing import Dict, Any, Optional, Callable
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

# File for storing session state between test runs
STATE_FILE = Path.home() / ".birth_rectifier_test_state.json"

def get_session_state() -> Dict[str, Any]:
    """
    Get the current session state from the state file.

    Returns:
        Dict with session state
    """
    try:
        if not STATE_FILE.exists():
            return {}

        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading session state: {e}")
        return {}

def update_session_state(**kwargs) -> None:
    """
    Update the session state with new values.

    Args:
        **kwargs: Values to add to the session state
    """
    try:
        # Get current state
        state = get_session_state()

        # Update with new values
        state.update(kwargs)

        # Save updated state
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)

        logger.info(f"Updated session state: {list(kwargs.keys())}")
    except Exception as e:
        logger.error(f"Error updating session state: {e}")

def clear_session_state() -> None:
    """Clear the test session state file."""
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            logger.info("Session state file cleared")
    except Exception as e:
        logger.error(f"Error clearing session state: {e}")

def sequence(order: int):
    """
    Decorator to ensure tests run in a specific order.

    Args:
        order: The sequence number for this test

    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current state to check prior tests
            state = get_session_state()

            # Check if this is the correct test in sequence
            current_sequence = state.get("current_sequence", 0)

            if order != current_sequence + 1 and order > 1:
                logger.warning(f"Test sequence error: Expected test {current_sequence + 1}, but got {order}")

                # Check if previous test completed
                if order - 1 > current_sequence:
                    logger.error(f"Test {order-1} hasn't run yet! Cannot run test {order}")
                    raise ValueError(f"Test sequence error: Test {order-1} must run before test {order}")

            # Log test sequence
            logger.info(f"Running test sequence {order}: {func.__name__}")

            # Call the original function
            result = await func(*args, **kwargs)

            # Update sequence in state
            update_session_state(current_sequence=order)

            return result

        # Add sequence attribute for sorting/reporting
        wrapper.sequence_order = order

        return wrapper

    return decorator

def with_previous_state(key: str, required: bool = True):
    """
    Decorator to ensure a test has access to state from previous tests.

    Args:
        key: The state key to look for
        required: Whether this state is required for the test

    Returns:
        Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current state
            state = get_session_state()

            # Check if required key exists
            if key not in state and required:
                logger.error(f"Missing required state key: {key}")
                raise ValueError(f"Test requires state key '{key}' from previous test")

            # Add state to kwargs
            if key in state:
                kwargs[key] = state[key]

            # Call the original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator
