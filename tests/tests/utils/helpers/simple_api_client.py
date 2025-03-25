"""
Simple API client for Birth Time Rectifier integration tests.
"""

import json
import requests
from typing import Dict, Any, Optional, Union


class SimpleAPIClient:
    """
    A simple API client for making requests to the Birth Time Rectifier API.
    """

    def __init__(self, base_url: str = "http://api_gateway:8000"):
        """
        Initialize the client with a base URL.

        Args:
            base_url: Base URL for the API
        """
        self.base_url = base_url.rstrip('/')
        self.headers = {
            "Content-Type": "application/json"
        }

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a GET request to the API.

        Args:
            path: API endpoint path
            params: Query parameters

        Returns:
            HTTP response
        """
        url = f"{self.base_url}{path}"
        response = requests.get(url, params=params, headers=self.headers, timeout=30)
        return response

    def post(self, path: str, json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a POST request to the API.

        Args:
            path: API endpoint path
            json_data: Data to send in the request body

        Returns:
            HTTP response
        """
        url = f"{self.base_url}{path}"
        response = requests.post(url, json=json_data, headers=self.headers, timeout=30)
        return response

    def put(self, path: str, json_data: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Make a PUT request to the API.

        Args:
            path: API endpoint path
            json_data: Data to send in the request body

        Returns:
            HTTP response
        """
        url = f"{self.base_url}{path}"
        response = requests.put(url, json=json_data, headers=self.headers, timeout=30)
        return response

    def delete(self, path: str) -> requests.Response:
        """
        Make a DELETE request to the API.

        Args:
            path: API endpoint path

        Returns:
            HTTP response
        """
        url = f"{self.base_url}{path}"
        response = requests.delete(url, headers=self.headers, timeout=30)
        return response
