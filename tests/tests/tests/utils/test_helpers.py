"""
Test helper functions for Birth Time Rectifier integration tests.
Maintains test sequence state between different test steps.
"""

import os
import json
import pickle
from typing import Dict, Any, Optional
from pathlib import Path

# Define the path for storing test sequence data
TEST_SEQUENCE_FILE = os.environ.get(
    "TEST_SEQUENCE_FILE",
    str(Path(__file__).parent.parent / "test_results" / "test_sequence.pkl")
)

def get_test_sequence() -> Dict[str, Any]:
    """
    Get the current test sequence data.

    Returns:
        Dictionary with test sequence data or empty dict if no sequence exists
    """
    try:
        if os.path.exists(TEST_SEQUENCE_FILE):
            with open(TEST_SEQUENCE_FILE, "rb") as f:
                return pickle.load(f)
    except Exception as e:
        print(f"Error loading test sequence: {e}")

    return {}

def update_test_sequence(data: Dict[str, Any], persist: bool = True) -> None:
    """
    Update the test sequence data.

    Args:
        data: Dictionary with test sequence data to update
        persist: Whether to persist the data to disk
    """
    if persist:
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(TEST_SEQUENCE_FILE), exist_ok=True)

            with open(TEST_SEQUENCE_FILE, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            print(f"Error saving test sequence: {e}")

def clear_test_sequence() -> None:
    """Clear the test sequence data."""
    if os.path.exists(TEST_SEQUENCE_FILE):
        try:
            os.remove(TEST_SEQUENCE_FILE)
        except Exception as e:
            print(f"Error clearing test sequence: {e}")

# Alias for backward compatibility
reset_test_sequence = clear_test_sequence

def initialize_test_sequence(session_id: str) -> Dict[str, Any]:
    """
    Initialize a new test sequence with the given session ID.

    Args:
        session_id: Session ID to use for the test sequence

    Returns:
        Initialized test sequence data
    """
    sequence_data = {
        "session_id": session_id,
        "test_stage": 1,
        "timestamp": {},
        "status": "initialized"
    }

    update_test_sequence(sequence_data)
    return sequence_data
