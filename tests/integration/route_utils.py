"""
Advanced route matcher utility for Playwright tests.
Provides robust matching for dynamic URL patterns with path parameters.
"""

import re
from typing import Any, Callable, Dict, List, Optional, Union
from playwright.sync_api import Route, Request

def extract_params(url: str, pattern: str) -> Dict[str, str]:
    """
    Extract named parameters from a URL based on a regex pattern.

    Args:
        url: The URL string to extract from
        pattern: Regex pattern with capture groups

    Returns:
        Dictionary of extracted parameters
    """
    match = re.search(pattern, url)
    if match:
        if match.groups():
            # If there are numbered capture groups, convert to a dict
            return {str(i): val for i, val in enumerate(match.groups())}
        elif match.groupdict():
            # If there are named capture groups, return them directly
            return match.groupdict()
    return {}

def extract_param_from_path(url: str, index: int) -> Optional[str]:
    """
    Extract a parameter from a URL path at a specific segment index.

    Args:
        url: Full URL string
        index: Index of the path segment to extract (0-based)

    Returns:
        Extracted parameter or None if index is out of bounds
    """
    try:
        # Remove protocol and domain if present
        path = url
        if '://' in url:
            path = url.split('://', 1)[1]
            if '/' in path:
                path = '/' + path.split('/', 1)[1]

        # Strip query string and hash
        clean_path = path.split('?')[0].split('#')[0]

        # Normalize path by removing trailing slashes
        normalized_path = clean_path.rstrip('/')

        # Split path into segments and get the requested index
        segments = normalized_path.strip('/').split('/')

        if 0 <= index < len(segments):
            return segments[index]
        return None
    except Exception as e:
        print(f"Error extracting path parameter: {e}")
        return None

def debug_route_match(url: str, pattern: str) -> bool:
    """
    Check if a URL matches a pattern and log debugging info.

    Args:
        url: The URL to check
        pattern: Regex pattern string

    Returns:
        True if there's a match, False otherwise
    """
    match = re.search(pattern, url)
    result = bool(match)
    print(f"DEBUG: URL {url}")
    print(f"DEBUG: Pattern {pattern}")
    print(f"DEBUG: Match result: {result}")

    if result and match.groups():
        print(f"DEBUG: Captured groups: {match.groups()}")
    if result and match.groupdict():
        print(f"DEBUG: Captured named groups: {match.groupdict()}")

    return result

def create_chart_id_matcher():
    """Create a matcher function for chart ID endpoints."""
    pattern = re.compile(r"/api/chart/([^/?#]+)(?:\?|#|$)")
    return lambda url: bool(pattern.search(url))

def create_questionnaire_answer_matcher():
    """Create a matcher function for questionnaire answer endpoints."""
    pattern = re.compile(r"/api/questionnaire/([^/?#]+)/answer(?:\?|#|$)")
    return lambda url: bool(pattern.search(url))

def create_export_download_matcher():
    """Create a matcher function for export download endpoints."""
    pattern = re.compile(r"/api/export/([^/?#]+)/download(?:\?|#|$)")
    return lambda url: bool(pattern.search(url))
