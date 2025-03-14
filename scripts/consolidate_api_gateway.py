#!/usr/bin/env python3
"""
API Gateway Consolidation Script

This script helps implement the consolidated API Gateway architecture by:
1. Creating necessary files for the path rewriting middleware
2. Updating main.py to use the new unified approach
3. Removing duplicate router registrations
4. Ensuring alignment with the complete user journey
5. Running tests to verify functionality
"""

import os
import sys
import shutil
import subprocess
import re
import json
from pathlib import Path
from datetime import datetime

def print_step(message):
    """Print a step message with formatting"""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80)

def check_prerequisites():
    """Check that all prerequisites are met before running the script"""
    print_step("Checking prerequisites")

    # Check that required files exist
    required_files = [
        "ai_service/main.py",
        "ai_service/api/middleware/error_handling.py",
        "ai_service/api/middleware/session.py",
        "docs/architecture/application_flow.md"
    ]

    for file in required_files:
        if not os.path.exists(file):
            print(f"ERROR: Required file {file} does not exist.")
            print("Please make sure all required files exist before running this script.")
            sys.exit(1)

    # Check that we have the right Python version
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required.")
        return False

    print("All prerequisites met.")
    return True

def backup_original_files():
    """Create backups of original files"""
    print_step("Backing up original files")

    # Get current timestamp for backup directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backups/consolidation_{timestamp}"
    os.makedirs(backup_dir, exist_ok=True)

    files_to_backup = [
        "ai_service/main.py",
        "ai_service/api/middleware/path_rewriter.py",
        "src/utils/unifiedApiClient.js",
        "tests/test_consolidated_api_flow.py"
    ]

    for filepath in files_to_backup:
        if os.path.exists(filepath):
            backup_path = f"{backup_dir}/{os.path.basename(filepath)}"
            print(f"Backing up {filepath} to {backup_path}")

            # Create directories if needed
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            shutil.copy2(filepath, backup_path)

    print(f"All backups saved to {backup_dir}")
    return backup_dir

def read_application_flow():
    """Read and parse the application flow documentation to ensure API alignment"""
    print_step("Reading application flow documentation")

    flow_path = "docs/architecture/application_flow.md"
    try:
        with open(flow_path, 'r') as f:
            content = f.read()

        print("Successfully read application flow documentation")

        # Extract user journey steps
        user_journey_match = re.search(r'USER JOURNEY.*?\+--+\+(.*?)\+--+\+', content, re.DOTALL)
        if user_journey_match:
            journey_text = user_journey_match.group(1)
            print("\nIdentified user journey steps:")

            # Extract key steps
            steps = re.findall(r'\d+\.\s+(.*?)\s+\|', journey_text)
            for i, step in enumerate(steps, 1):
                print(f"  {i}. {step}")

            # Extract API endpoints
            api_endpoints = re.findall(r'Key APIs:.*?- (/api/.*?)$', journey_text, re.MULTILINE)
            print("\nIdentified key API endpoints:")
            for endpoint in api_endpoints:
                print(f"  • {endpoint}")

        return content
    except Exception as e:
        print(f"ERROR: Failed to read application flow documentation: {str(e)}")
        return None

def create_path_rewriter_middleware():
    """Create or update the path rewriter middleware"""
    print_step("Creating path rewriter middleware")

    # Ensure the middleware directory exists
    middleware_dir = "ai_service/api/middleware"
    os.makedirs(middleware_dir, exist_ok=True)

    # Check if path_rewriter.py already exists
    middleware_path = f"{middleware_dir}/path_rewriter.py"
    if os.path.exists(middleware_path):
        print("Path rewriter middleware already exists, updating with latest version...")
    else:
        print("Creating new path rewriter middleware...")

    # Create middleware content based on user journey
    middleware_content = """\"\"\"
Path Rewriter Middleware

This middleware handles path rewriting for the API Gateway to ensure
backward compatibility and unified API routing throughout the application.

It implements the complete user journey as documented in application_flow.md:
1. Birth Details Entry
2. Initial Chart Generation
3. Dynamic Questionnaire
4. Birth Time Rectification
5. Results & Export
\"\"\"

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import re
import logging

# Configure logging
logger = logging.getLogger(__name__)

class PathRewriterMiddleware(BaseHTTPMiddleware):
    \"\"\"
    Middleware for rewriting API paths to maintain backward compatibility
    while supporting the consolidated API Gateway architecture.
    \"\"\"

    async def dispatch(self, request: Request, call_next):
        \"\"\"
        Rewrite the request path if it matches a legacy pattern.

        Args:
            request: The incoming request
            call_next: The next middleware or endpoint handler

        Returns:
            The response from the API endpoint
        \"\"\"
        # Store original path for logging
        original_path = request.url.path

        # Define path mapping according to user journey
        path_mapping = {
            # Birth Details Entry
            r'^/api/geocode': '/api/v1/geocode',
            r'^/api/chart/validate': '/api/v1/chart/validate',

            # Chart Generation
            r'^/api/chart/generate': '/api/v1/chart/generate',
            r'^/api/chart/(?P<chart_id>[^/]+)$': '/api/v1/chart/{chart_id}',

            # Questionnaire
            r'^/api/questionnaire$': '/api/v1/questionnaire',
            r'^/api/questionnaire/(?P<question_id>[^/]+)/answer': '/api/v1/questionnaire/{question_id}/answer',

            # Birth Time Rectification
            r'^/api/chart/rectify': '/api/v1/chart/rectify',
            r'^/api/chart/compare': '/api/v1/chart/compare',

            # Results & Export
            r'^/api/chart/export': '/api/v1/chart/export',
            r'^/api/export/(?P<export_id>[^/]+)/download': '/api/v1/export/{export_id}/download',

            # Session Management
            r'^/api/session/init': '/api/v1/session/init',
            r'^/api/session/validate': '/api/v1/session/validate',
            r'^/api/session/refresh': '/api/v1/session/refresh',

            # Health Check
            r'^/api/health': '/api/v1/health',
        }

        # Apply path rewriting
        rewritten_path = original_path
        for pattern, replacement in path_mapping.items():
            if re.match(pattern, original_path):
                # Extract named capture groups if any
                match = re.match(pattern, original_path)
                if match and match.groupdict():
                    # Replace placeholders with captured values
                    rewritten_path = replacement
                    for name, value in match.groupdict().items():
                        rewritten_path = rewritten_path.replace(f'{{{name}}}', value)
                else:
                    rewritten_path = replacement
                break

        # Apply rewriting if path changed
        if rewritten_path != original_path:
            logger.debug(f"Rewrote path: {original_path} -> {rewritten_path}")
            request.scope["path"] = rewritten_path

        # Proceed with the request
        response = await call_next(request)
        return response
"""

    # Write middleware to file
    with open(middleware_path, 'w') as f:
        f.write(middleware_content)

    print(f"Path rewriter middleware created/updated at {middleware_path}")

def update_main_py():
    """Update main.py to use the consolidated API approach based on user journey"""
    print_step("Updating main.py for consolidated API approach")

    main_py_path = "ai_service/main.py"

    # Read existing main.py file
    with open(main_py_path, 'r') as f:
        content = f.read()

    # Create updated main.py content
    updated_content = """\"\"\"
Consolidated API Gateway for Birth Time Rectifier

This module implements the unified API Gateway architecture using FastAPI,
providing consistent endpoints that follow the complete user journey:

1. Birth Details Entry
2. Initial Chart Generation
3. Dynamic Questionnaire
4. Birth Time Rectification
5. Results & Export

All routes are organized to provide a seamless experience that matches
the documented user journey and functional requirements.
\"\"\"

import logging
import uvicorn
from fastapi import FastAPI, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Import routers and middleware
from ai_service.api.middleware.path_rewriter import PathRewriterMiddleware
from ai_service.api.middleware.error_handling import ErrorHandlingMiddleware
from ai_service.api.middleware.session import SessionMiddleware

# Import consolidated routers
from ai_service.api.routers.consolidated_chart import router as chart_router
from ai_service.api.routers.questionnaire import router as questionnaire_router
from ai_service.api.routers.session import router as session_router
from ai_service.api.routers.geocode import router as geocode_router
from ai_service.api.routers.health import router as health_router

# Create FastAPI application
app = FastAPI(
    title="Birth Time Rectifier API",
    description="API for birth time rectification using astrological analysis and AI",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configure CORS to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add path rewriting middleware
app.add_middleware(PathRewriterMiddleware)

# Add error handling middleware
app.add_middleware(ErrorHandlingMiddleware)

# Add session middleware
app.add_middleware(SessionMiddleware)

# Register all routers
# User Journey Step 1: Birth Details Entry
app.include_router(geocode_router, prefix="/api/v1", tags=["geocoding"])
app.include_router(chart_router, prefix="/api/v1", tags=["chart"])

# User Journey Step 2: Chart Generation
# (Already covered by chart_router)

# User Journey Step 3: Dynamic Questionnaire
app.include_router(questionnaire_router, prefix="/api/v1", tags=["questionnaire"])

# User Journey Step 4: Birth Time Rectification
# (Already covered by chart_router)

# User Journey Step 5: Results & Export
# (Already covered by chart_router)

# Session Management (used across all steps)
app.include_router(session_router, prefix="/api/v1", tags=["session"])

# Health Check
app.include_router(health_router, prefix="/api/v1", tags=["health"])

# Define a root endpoint for basic server info
@app.get("/")
async def root():
    \"\"\"Root endpoint returning basic service information\"\"\"
    return {
        "service": "Birth Time Rectifier API",
        "status": "healthy",
        "version": "1.0.0"
    }

# Start the application when run directly
if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))

    # Run with uvicorn
    uvicorn.run("ai_service.main:app", host="0.0.0.0", port=port, reload=True)
"""

    # Write updated content to file
    with open(main_py_path, 'w') as f:
        f.write(updated_content)

    print(f"Updated {main_py_path} with consolidated API approach")

def create_api_client_module():
    """Create a unified API client module for frontend based on user journey"""
    print_step("Creating unified API client module")

    client_dir = "src/utils"
    os.makedirs(client_dir, exist_ok=True)

    client_path = "src/utils/unifiedApiClient.js"

    # Check if file already exists
    if os.path.exists(client_path):
        print(f"API client module already exists at {client_path}, updating...")
    else:
        print(f"Creating new API client module at {client_path}...")

    client_content = """/**
 * Unified API Client for Birth Time Rectifier
 *
 * This module provides a centralized way to interact with all API endpoints,
 * organized to support the complete user journey:
 *
 * 1. Birth Details Entry
 * 2. Chart Generation
 * 3. Dynamic Questionnaire
 * 4. Birth Time Rectification
 * 5. Results & Export
 */

import axios from 'axios';

// Create API client configuration
const API_VERSION = 'v1';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
const API_PREFIX = `/api/${API_VERSION}`;

// Define endpoints based on user journey
const ENDPOINTS = {
  // Step 1: Birth Details Entry
  chart: {
    validate: () => '/chart/validate',
    generate: () => '/chart/generate',
    get: () => '/chart',
    rectify: () => '/chart/rectify',
    compare: () => '/chart/compare',
    export: () => '/chart/export'
  },
  // Step 1-2: Location & Geocoding
  geocode: {
    geocode: () => '/geocode',
    reverse: () => '/geocode/reverse'
  },
  // Step 3: Dynamic Questionnaire
  questionnaire: {
    init: () => '/questionnaire',
    answer: (questionId) => `/questionnaire/${questionId}/answer`,
    complete: () => '/questionnaire/complete',
  },
  // Step 4-5: Rectification and Results (covered by chart endpoints)
  // Session Management (used across all steps)
  session: {
    init: () => '/session/init',
    validate: () => '/session/validate',
    refresh: () => '/session/refresh',
  },
  // Health Check
  health: {
    check: () => '/health'
  }
};

// Create base API client
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}${API_PREFIX}`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for session management
apiClient.interceptors.request.use(
  async (config) => {
    // Get session ID from localStorage or other storage
    const sessionId = localStorage.getItem('sessionId');

    if (sessionId) {
      config.headers['X-Session-ID'] = sessionId;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Handle 401 Unauthorized errors (session expired)
    if (error.response && error.response.status === 401) {
      // Attempt to refresh session
      try {
        const response = await axios.get(`${API_BASE_URL}${API_PREFIX}/session/refresh`);

        if (response.data && response.data.sessionId) {
          localStorage.setItem('sessionId', response.data.sessionId);

          // Retry the original request
          const config = error.config;
          config.headers['X-Session-ID'] = response.data.sessionId;
          return axios(config);
        }
      } catch (refreshError) {
        console.error('Session refresh failed:', refreshError);
      }
    }

    return Promise.reject(error);
  }
);

/**
 * Chart Service - handles chart-related operations
 */
const chartService = {
  /**
   * Step 1: Validate birth details
   */
  validateBirthDetails: async (birthDetails) => {
    return await apiClient.post(ENDPOINTS.chart.validate(), birthDetails);
  },

  /**
   * Step 2: Generate a birth chart
   */
  generateChart: async (birthDetails) => {
    return await apiClient.post(ENDPOINTS.chart.generate(), birthDetails);
  },

  /**
   * Get a chart by ID (used in multiple steps)
   */
  getChart: async (chartId) => {
    return await apiClient.get(`${ENDPOINTS.chart.get()}/${chartId}`);
  },

  /**
   * Step 4: Rectify a birth chart
   */
  rectifyChart: async (rectifyParams) => {
    return await apiClient.post(ENDPOINTS.chart.rectify(), rectifyParams);
  },

  /**
   * Step 5: Compare two charts
   */
  compareCharts: async (chartId1, chartId2, options = {}) => {
    const queryParams = new URLSearchParams({
      chart1_id: chartId1,
      chart2_id: chartId2,
      ...options
    });
    return await apiClient.get(`${ENDPOINTS.chart.compare()}?${queryParams.toString()}`);
  },

  /**
   * Step 5: Export a chart
   */
  exportChart: async (chartId, options = {}) => {
    return await apiClient.post(`${ENDPOINTS.chart.export()}/${chartId}`, options);
  },
};

/**
 * Geocode Service - handles location operations
 */
const geocodeService = {
  /**
   * Step 1: Geocode a location query
   */
  geocode: async (query) => {
    return await apiClient.post(ENDPOINTS.geocode.geocode(), { query });
  },

  /**
   * Step 1: Reverse geocode coordinates
   */
  reverseGeocode: async (lat, lon) => {
    return await apiClient.get(ENDPOINTS.geocode.reverse(), { params: { lat, lon } });
  },
};

/**
 * Questionnaire Service - handles dynamic questionnaire
 */
const questionnaireService = {
  /**
   * Step 3: Initialize questionnaire
   */
  initialize: async (birthDetails) => {
    return await apiClient.post(ENDPOINTS.questionnaire.init(), birthDetails);
  },

  /**
   * Step 3: Answer a question
   */
  answer: async (questionId, answer, chartId) => {
    return await apiClient.post(ENDPOINTS.questionnaire.answer(questionId), {
      chart_id: chartId,
      answer
    });
  },

  /**
   * Step 3: Complete questionnaire
   */
  complete: async (chartId) => {
    return await apiClient.post(ENDPOINTS.questionnaire.complete(), { chart_id: chartId });
  },
};

/**
 * Session Service - handles session management
 */
const sessionService = {
  init: async () => {
    return await apiClient.get(ENDPOINTS.session.init());
  },
  validate: async (sessionId) => {
    return await apiClient.get(`${ENDPOINTS.session.validate()}?sessionId=${sessionId}`);
  },
  refresh: async (sessionId) => {
    return await apiClient.get(`${ENDPOINTS.session.refresh()}?sessionId=${sessionId}`);
  },
};

/**
 * Health Service - handles health checks
 */
const healthService = {
  check: async () => {
    return await apiClient.get(ENDPOINTS.health.check());
  },
};

/**
 * Error handling helper
 */
const handleApiError = (error) => {
  if (error.response) {
    // The request was made and the server responded with a status code
    // that falls out of the range of 2xx
    console.error('API Error Response:', error.response.data);
    return {
      status: error.response.status,
      message: error.response.data.detail || 'An error occurred',
      data: error.response.data,
    };
  } else if (error.request) {
    // The request was made but no response was received
    console.error('API Error Request:', error.request);
    return {
      status: 0,
      message: 'No response from server',
      data: null,
    };
  } else {
    // Something happened in setting up the request that triggered an Error
    console.error('API Error Setup:', error.message);
    return {
      status: 0,
      message: error.message,
      data: null,
    };
  }
};

// Export the unified API client
export default {
  chartService,
  geocodeService,
  questionnaireService,
  sessionService,
  healthService,
  handleApiError,
};
"""

    with open(client_path, 'w') as f:
        f.write(client_content)

    print(f"Created/updated unified API client module at {client_path}")

def verify_api_alignment():
    """Verify that API endpoints align with user journey"""
    print_step("Verifying API alignment with user journey")

    # Define the expected endpoints for each step of the user journey
    expected_endpoints = {
        "Birth Details Entry": [
            "/api/geocode",
            "/api/chart/validate"
        ],
        "Chart Generation": [
            "/api/chart/generate",
            "/api/chart/{id}"
        ],
        "Dynamic Questionnaire": [
            "/api/questionnaire",
            "/api/questionnaire/{id}/answer"
        ],
        "Birth Time Rectification": [
            "/api/chart/rectify",
            "/api/chart/compare"
        ],
        "Results & Export": [
            "/api/chart/export",
            "/api/export/{id}/download"
        ]
    }

    # Check middleware for these endpoints
    middleware_path = "ai_service/api/middleware/path_rewriter.py"

    if os.path.exists(middleware_path):
        with open(middleware_path, 'r') as f:
            middleware_content = f.read()

        print("\nVerifying API endpoints in middleware:")
        all_endpoints_found = True

        for step, endpoints in expected_endpoints.items():
            print(f"\n{step}:")
            for endpoint in endpoints:
                # Create a regex-friendly version of the endpoint
                search_pattern = endpoint.replace("{", "(?P<").replace("}", ">[^/]+)")
                if re.search(fr"['\"].*{re.escape(search_pattern)}.*['\"]", middleware_content):
                    print(f"  ✓ Found endpoint: {endpoint}")
                else:
                    print(f"  ✗ Missing endpoint: {endpoint}")
                    all_endpoints_found = False

        if all_endpoints_found:
            print("\nAll expected endpoints are properly configured in the middleware.")
        else:
            print("\nWARNING: Some expected endpoints are missing in the middleware.")
    else:
        print(f"ERROR: {middleware_path} does not exist. Cannot verify API alignment.")

def run_tests():
    """Run API tests to verify functionality"""
    print_step("Running tests to verify functionality")

    try:
        # Run consolidated API tests
        print("Running consolidated API tests...")
        result = subprocess.run(["python", "-m", "pytest", "ai_service/tests/integration/test_api_consolidation.py", "-v"],
                              capture_output=True, text=True)

        print("\nTest output:")
        print(result.stdout)

        if result.returncode == 0:
            print("✓ Consolidated API tests passed!")
        else:
            print("✗ Some tests failed. Please check the test output above.")
            print(f"Error output: {result.stderr}")
            return False

        # Run core functionality tests
        print("\nRunning core functionality tests...")
        result = subprocess.run(["python", "-m", "pytest", "ai_service/tests/test_chart_verification.py", "-v"],
                              capture_output=True, text=True)

        print("\nTest output:")
        print(result.stdout)

        if result.returncode == 0:
            print("✓ Core functionality tests passed!")
        else:
            print("✗ Some tests failed. Please check the test output above.")
            print(f"Error output: {result.stderr}")
            return False

        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Tests failed with return code {e.returncode}")
        print(f"Output: {e.output}")
        return False

def main():
    """Main function to run the consolidation process"""
    print_step("Starting API Gateway Consolidation")

    if not check_prerequisites():
        sys.exit(1)

    # Create backups before making changes
    backup_dir = backup_original_files()

    # Read application flow to understand user journey
    app_flow = read_application_flow()

    # Create or update path rewriter middleware
    create_path_rewriter_middleware()

    # Update main.py
    update_main_py()

    # Create API client module
    create_api_client_module()

    # Verify API alignment with user journey
    verify_api_alignment()

    # Run tests
    tests_passed = run_tests()

    print_step("API Gateway Consolidation Complete")

    if tests_passed:
        print("\n✓ Consolidation successful! All tests passed.")
    else:
        print("\n⚠ Consolidation completed, but some tests failed.")
        print(f"Original files were backed up to {backup_dir}")

    print("\nNext steps:")
    print("1. Verify the API documentation: http://localhost:8000/docs")
    print("2. Run the consolidated test flow: python tests/test_consolidated_api_flow.py")
    print("3. Start the server: uvicorn ai_service.main:app --reload")

    print("\nIf you encounter any issues, you can restore the original files from the backup directory:")
    print(f"  {backup_dir}")

if __name__ == "__main__":
    main()
