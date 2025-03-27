"""
Configuration fixtures for pytest.

This module provides fixtures for dependency injection and mocking in tests.
"""

import pytest
import os
import logging
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, Type, cast, AsyncGenerator, Generator

# Make playwright imports optional for backend-only testing
try:
    from playwright.sync_api import sync_playwright, Page, Browser
    from playwright.async_api import async_playwright, Page as AsyncPage
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    # Create dummy classes for type checking
    class Page:
        def close(self):
            pass
    class Browser:
        def new_page(self):
            dummy_page = Page()
            return dummy_page
        def close(self):
            pass
    class AsyncPage:
        async def close(self):
            pass

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
def browser() -> Generator[Browser, None, None]:
    """
    Set up a Playwright browser for testing.

    Returns:
        Browser: Playwright browser instance
    """
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping browser-based tests")

    with sync_playwright() as p:
        browser_instance = p.chromium.launch(
            headless=True,
            channel="chrome",
        )
        yield browser_instance
        browser_instance.close()

@pytest.fixture()
def page(browser: Browser) -> Generator[Page, None, None]:
    """Create a page instance for testing."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping browser-based tests")

    page = browser.new_page()
    yield page
    page.close()

@pytest.fixture
async def async_page(async_browser) -> AsyncGenerator[AsyncPage, None]:
    """Create a new async page instance for each test."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping browser-based tests")

    page = await async_browser.new_page()
    yield page
    await page.close()

@pytest.fixture(scope="session")
async def async_browser(browser_type_launch_args) -> AsyncGenerator[AsyncPage, None]:
    """Create an async browser instance for testing."""
    if not PLAYWRIGHT_AVAILABLE:
        pytest.skip("Playwright not available, skipping browser-based tests")

    async with async_playwright() as p:
        browser = await p.chromium.launch(**browser_type_launch_args)
        yield browser
        await browser.close()
