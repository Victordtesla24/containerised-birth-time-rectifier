"""
Birth Time Rectifier API - API Module Main Entry Point

This module re-exports the FastAPI app from the root main.py file.
"""

from ai_service.main import app

# Re-export the app
__all__ = ['app']
