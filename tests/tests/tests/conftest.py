"""
Configuration fixtures for pytest.

This module provides fixtures for dependency injection and mocking in tests.
"""

import pytest
import os
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, Type, cast, AsyncGenerator
from playwright.sync_api import sync_playwright, Page, Browser
from playwright.async_api import async_playwright, Page as AsyncPage

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import dependency container
from ai_service.utils.dependency_container import get_container


# Add Playwright fixtures
@pytest.fixture(scope="session")
def browser_type_launch_args():
    """Define browser launch arguments to use across tests."""
    return {
        "headless": True,
        "args": ["--no-sandbox", "--disable-gpu"]
    }

@pytest.fixture(scope="session")
def browser(browser_type_launch_args):
    """Create a browser instance for testing."""
    with sync_playwright() as p:
        browser = p.chromium.launch(**browser_type_launch_args)
        yield browser
        browser.close()

@pytest.fixture
def page(browser) -> Page:
    """Create a new page instance for each test."""
    page = browser.new_page()
    yield page
    page.close()

@pytest.fixture
async def async_page() -> AsyncGenerator[AsyncPage, None]:
    """Create an async page instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        yield page
        await page.close()
        await browser.close()
