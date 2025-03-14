"""
Dedicated conftest for API error handling tests.
"""

import re
import time
import json
import pytest
import logging
from typing import Dict, Any, List
from playwright.sync_api import Page, Route, Request

logger = logging.getLogger(__name__)

@pytest.fixture
def critical_endpoints_mock(page: Page):
    """
    Fixture to specifically mock critical endpoints for testing error handling.
    This fixture is more focused than the general mock_api_requests fixture.
    """
    def handle_route(route: Route, request: Request):
        url = request.url
        logger.info(f"Intercepted request to: {url}")

        # Chart endpoint - specific pattern for chart ID
        if re.search(r'/api/chart/[^/]+$', url) and not any(x in url for x in ['/validate', '/generate', '/rectify', '/compare', '/export']):
            logger.info(f"Mocking chart ID endpoint: {url}")
            # Extract chart ID from the URL
            chart_id = url.split('/api/chart/')[1].split('?')[0]

            route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "chart_id": chart_id,
                    "ascendant": {"sign": "Virgo", "degree": 15.32},
                    "planets": [
                        {"name": "Sun", "sign": "Capricorn", "degree": 24.5},
                        {"name": "Moon", "sign": "Taurus", "degree": 12.8},
                        {"name": "Mercury", "sign": "Capricorn", "degree": 10.2}
                    ],
                    "houses": [
                        {"number": 1, "sign": "Virgo", "degree": 15.32},
                        {"number": 2, "sign": "Libra", "degree": 10.5},
                        {"number": 3, "sign": "Scorpio", "degree": 8.2}
                    ],
                    "aspects": [
                        {"planet1": "Sun", "planet2": "Moon", "type": "trine", "orb": 1.2},
                        {"planet1": "Mercury", "planet2": "Sun", "type": "conjunction", "orb": 0.8}
                    ]
                })
            )
            return

        # Questionnaire answer endpoint
        elif re.search(r'/api/questionnaire/[^/]+/answer', url):
            logger.info(f"Mocking questionnaire answer endpoint: {url}")
            route.fulfill(
                status=200,
                headers={"Content-Type": "application/json"},
                body=json.dumps({
                    "status": "accepted",
                    "next_question_url": "/api/questionnaire/q_002"
                })
            )
            return

        # Export download endpoint
        elif re.search(r'/api/export/[^/]+/download', url):
            logger.info(f"Mocking export download endpoint: {url}")
            mock_pdf = "PDF-1.7\n%¥±ë\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
            route.fulfill(
                status=200,
                headers={
                    "Content-Type": "application/pdf",
                    "Content-Disposition": "attachment; filename=birth-chart.pdf"
                },
                body=mock_pdf
            )
            return

        # Let other requests pass through
        logger.info(f"Letting request pass through: {url}")
        route.continue_()

    # Register routes with precise patterns
    page.route("**/api/chart/*", handle_route)
    page.route("**/api/questionnaire/*/answer", handle_route)
    page.route("**/api/export/*/download", handle_route)

    yield
