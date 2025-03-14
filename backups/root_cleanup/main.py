"""
Birth Time Rectifier API - Unified Main Application

This is the consolidated FastAPI application that serves the Birth Time Rectifier API
using a single registration pattern with proper versioning.

NOTE: This is the only main.py file used for all purposes:
- Development
- Testing
- Deployment

Previously, this codebase had multiple main files (main_simplified.py, unified_main.py),
but they have been consolidated into this single file following the directory management
protocol.
"""

import uvicorn
from ai_service.main import app

if __name__ == "__main__":
    uvicorn.run("ai_service.main:app", host="0.0.0.0", port=8000, reload=True)
