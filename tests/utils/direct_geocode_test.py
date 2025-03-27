#!/usr/bin/env python3
"""
Minimal test script for geocoding functionality.
This script directly tests the nominatim_geocode_direct function.
"""

import asyncio
import logging
import json
import time
import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("direct_geocode_test")

# Import the direct geocode function
from ai_service.api.routers.geocode import nominatim_geocode_direct

async def test_direct_geocode():
    """Test the direct geocode function."""
    query = "New York City"

    start_time = time.time()
    logger.info(f"Testing direct geocode for: {query}")

    # Call the direct geocode function
    results = await nominatim_geocode_direct(query, limit=1)

    elapsed = time.time() - start_time
    logger.info(f"Direct geocode completed in {elapsed:.2f} seconds")

    if results:
        logger.info(f"Found {len(results)} results")
        logger.info(f"First result: {json.dumps(results[0], indent=2)}")
    else:
        logger.error("No results found")

if __name__ == "__main__":
    asyncio.run(test_direct_geocode())
