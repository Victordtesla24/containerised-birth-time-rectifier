"""
Test helper utilities for the Birth Time Rectifier test suite.
"""

import json
import os
import logging
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_helpers")

# Path for storing test sequence data
SEQUENCE_DATA_PATH = Path(__file__).parent.parent / "results" / "test_sequence.json"

def reset_test_sequence():
    """Reset the test sequence to initial state."""
    os.makedirs(SEQUENCE_DATA_PATH.parent, exist_ok=True)

    # Initial state
    initial_state = {
        "session_id": None,
        "test_stage": 0,
        "started_at": time.time(),
        "last_updated": time.time()
    }

    # Write to file
    with open(SEQUENCE_DATA_PATH, 'w') as f:
        json.dump(initial_state, f, indent=2)

    logger.info(f"Test sequence reset to initial state")
    return initial_state

def get_test_sequence():
    """
    Get the current test sequence data.
    If no test sequence exists, create a new one.
    """
    if not SEQUENCE_DATA_PATH.exists():
        return reset_test_sequence()

    try:
        with open(SEQUENCE_DATA_PATH, 'r') as f:
            data = json.load(f)
        return data
    except (json.JSONDecodeError, FileNotFoundError) as e:
        logger.warning(f"Failed to read test sequence data: {e}")
        return reset_test_sequence()

def update_test_sequence(data, persist=True):
    """
    Update the test sequence with new data.

    Args:
        data: Dictionary of test sequence data
        persist: Whether to write to disk immediately
    """
    # Ensure directory exists
    os.makedirs(SEQUENCE_DATA_PATH.parent, exist_ok=True)

    # Update timestamp
    data["last_updated"] = time.time()

    if persist:
        with open(SEQUENCE_DATA_PATH, 'w') as f:
            json.dump(data, f, indent=2)

    logger.debug(f"Test sequence updated: stage={data.get('test_stage')}")
    return data
