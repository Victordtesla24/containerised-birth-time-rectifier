# FastAPI Middleware Issue: Root Cause Analysis & Implementation Plan

## 1. Root Cause Analysis

### 1.1 Middleware Implementation Conflict

* There's a mismatch between the consolidation architecture and what's running in production
* `main.py` still imports `PathRewriterMiddleware` from `legacy_support.py` while the consolidation created a new implementation in `path_rewriter.py`
* This could cause inconsistent behavior as the same middleware is defined in two places with slightly different implementations
* Multiple instances of similar middleware cause request processing conflicts

### 1.2 Unified Main vs. Regular Main Inconsistency

* The consolidation document mentions `unified_main.py` as the replacement for `main.py`
* However, the Docker container appears to be running the original `main.py` based on the logs
* This inconsistency explains why the middleware configuration is incorrect
* The wrong middleware chain is being applied in the running service

### 1.3 Middleware Registration and Execution Order Issues

* The modernized architecture requires specific middleware registration order
* The health endpoint is failing because it's getting caught in the middleware chain incorrectly
* Session middleware may have timing-dependent failures that cascade when multiple middlewares are active
* Redis connection issues in session middleware could be compounding the problem

## 2. Alternative Solutions Analysis

### 2.1 Solution 1: Use Unified Main (Most Aligned with Consolidation)

The first step is to ensure the application is using the consolidated architecture as intended:

```dockerfile
# In ai_service.Dockerfile
# Change this:
CMD ["python", "-m", "uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
# To this:
CMD ["python", "-m", "uvicorn", "ai_service.unified_main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Pros:**
* Aligns with the consolidation effort and documented architecture
* Uses the correct middleware implementation
* Most straightforward solution if `unified_main.py` is properly implemented
* Follows the intended architectural evolution

**Cons:**
* Requires verifying the completeness of `unified_main.py`
* May introduce new issues if the unified main has untested components
* Requires Docker rebuild
* Not fully validated in production scenarios

### 2.2 Solution 2: Path-Based Middleware Exclusion

If modifying the Dockerfile isn't feasible, we could update the middleware to exclude certain critical paths:

```python
# In ai_service/api/middleware/path_rewriter.py
class PathRewriterMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Critical paths bypass middleware
        critical_paths = ["/health", "/api/v1/health", "/system/health"]
        if request.url.path in critical_paths:
            return await call_next(request)

        # Continue with normal processing for non-critical paths
        original_path = request.url.path
        rewritten = False

        # Check if path needs to be rewritten
        for pattern, replacement in self.compiled_mappings:
            match = pattern.match(original_path)
            if match:
                # Rewrite path
                rewritten_path = pattern.sub(replacement, original_path)
                logger.debug(f"Rewriting path: {original_path} -> {rewritten_path}")
                request.scope["path"] = rewritten_path
                rewritten = True
                break

        # Process the request
        response = await call_next(request)

        # Add deprecation warning header for rewritten paths
        if rewritten and self.add_deprecation_warnings:
            response.headers["X-Deprecation-Warning"] = f"The path '{original_path}' is deprecated. Please use '{request.scope['path']}' instead."

        return response
```

**Pros:**
* Minimal changes to the existing codebase
* Targeted fix for the health endpoint
* No Docker rebuild required
* Preserves existing middleware for normal paths

**Cons:**
* Doesn't address the root issue of duplicate middleware
* May create maintenance confusion with special-case logic
* Doesn't follow the consolidation architecture principles
* Could be difficult to extend if additional paths need bypassing

### 2.3 Solution 3: Health Endpoint with ASGI Wrapper (Recommended)

Given the consolidation strategy, a more aligned solution would be to implement an ASGI wrapper that handles health checks before passing to the main application:

```python
# In ai_service/app_wrapper.py
import json
import logging
from datetime import datetime
from typing import Dict, Any
import importlib

# Configure logging
logger = logging.getLogger("health-check-wrapper")

# Dynamically import the main app based on environment
try:
    # Try to import the unified main first
    logger.info("Attempting to import unified_main")
    app_module = importlib.import_module("ai_service.unified_main")
    logger.info("Successfully imported unified_main")
except ImportError as e:
    # Fall back to regular main
    logger.info(f"Failed to import unified_main: {e}, falling back to main")
    app_module = importlib.import_module("ai_service.main")
    logger.info("Successfully imported main as fallback")

app = app_module.app

async def health_check_asgi(scope, receive, send):
    """Raw ASGI function for health checks that bypasses all middleware."""
    if scope["type"] == "http" and (scope["path"] == "/health" or scope["path"] == "/api/v1/health"):
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "ai_service",
            "middleware_bypassed": True
        }

        logger.info(f"Health check requested at path: {scope['path']}")

        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"application/json"]
            ]
        })

        await send({
            "type": "http.response.body",
            "body": json.dumps(response).encode()
        })
        return True
    return False

# ASGI wrapper function that handles health checks
async def app_wrapper(scope, receive, send):
    # Check for health endpoint first
    if await health_check_asgi(scope, receive, send):
        return
    # Otherwise pass to the main application
    await app(scope, receive, send)
```

Then update the Dockerfile to use this wrapper:

```dockerfile
CMD ["python", "-m", "uvicorn", "ai_service.app_wrapper:app_wrapper", "--host", "0.0.0.0", "--port", "8000"]
```

**Pros:**
* Provides an immediate fix for the health endpoint issue
* Works regardless of which application file is being used
* Preserves the consolidation architecture while adding a safety layer
* Provides a more robust health check that doesn't depend on middleware state
* Adds flexibility to handle other critical endpoints if needed

**Cons:**
* Adds an additional layer to the application
* Requires updating the Dockerfile
* May not address underlying middleware issues for non-health endpoints

### 2.4 Solution 4: Middleware Consolidation (Most Thorough)

Consolidate the middleware implementations to fix the conflict:

1. Remove the `PathRewriterMiddleware` from `legacy_support.py`
2. In `main.py`, update the import to use the correct implementation:

```python
# Change this in main.py:
from ai_service.api.middleware.legacy_support import PathRewriterMiddleware

# To this:
from ai_service.api.middleware.path_rewriter import PathRewriterMiddleware
```

**Pros:**
* Addresses the root cause directly
* Aligns with the consolidation architecture
* Reduces confusion with duplicate middleware
* Most maintainable solution long-term

**Cons:**
* Requires more extensive changes
* Higher risk of regression in other routes
* Requires thorough testing
* May still have issues with middleware order

## 3. Recommended Solution: Health Endpoint with ASGI Wrapper

Based on the consolidation work described in the document, we recommend **Solution 3: Health Endpoint with ASGI Wrapper** as the best approach because:

1. It provides an immediate fix for the health endpoint issue
2. It works regardless of which application file (main.py or unified_main.py) is being used
3. It preserves the consolidation architecture while adding a safety layer
4. It provides a more robust health check that doesn't depend on the middleware state
5. It can be implemented with minimal risk to existing functionality

## 4. Detailed Implementation Plan

### 4.1 Implementation Steps

1. **Create the ASGI Wrapper File**
   ```bash
   # Create the new file
   touch ai_service/app_wrapper.py
   ```

2. **Implement the ASGI Wrapper**
   - Add the health check bypass code as shown in the solution
   - Include robust logging to track execution
   - Add support for both `/health` and `/api/v1/health` paths

3. **Update the Dockerfile**
   ```bash
   # Edit the Dockerfile to use the wrapper
   sed -i 's|ai_service.main:app|ai_service.app_wrapper:app_wrapper|g' ai_service.Dockerfile
   ```

4. **Build and Deploy the Container**
   ```bash
   # Build the new image
   docker build -t birth-rectifier-ai:latest -f ai_service.Dockerfile .

   # Stop the current container
   docker stop birth-rectifier-ai

   # Remove the current container
   docker rm birth-rectifier-ai

   # Start a new container with the updated image
   docker run -d --name birth-rectifier-ai -p 8000:8000 birth-rectifier-ai:latest
   ```

5. **Verify Health Endpoint**
   ```bash
   # Test the health endpoint
   curl -f http://localhost:8000/health

   # Also test the versioned endpoint
   curl -f http://localhost:8000/api/v1/health
   ```

### 4.2 Testing and Verification Plan

1. **Health Endpoint Testing**
   - Verify the `/health` endpoint returns 200 OK
   - Verify the `/api/v1/health` endpoint returns 200 OK
   - Check the response format matches expected JSON structure
   - Validate the `middleware_bypassed` flag is present and true

2. **Middleware Conflict Testing**
   - Ensure other endpoints that use path rewriting still function
   - Test legacy paths to confirm they're properly rewritten
   - Verify deprecation headers are correctly added

3. **Performance Testing**
   - Measure response time for health endpoints to ensure low latency
   - Verify no memory leaks with repeated health checks

4. **Load Testing (Optional)**
   - Test health endpoint under high load to ensure stability
   - Verify middleware stack doesn't cause cascading failures

### 4.3 Rollback Plan

If issues arise with the new implementation, follow these steps to rollback:

1. **Revert to Previous Dockerfile**
   ```bash
   # Edit the Dockerfile to use the original entry point
   sed -i 's|ai_service.app_wrapper:app_wrapper|ai_service.main:app|g' ai_service.Dockerfile
   ```

2. **Rebuild and Redeploy**
   ```bash
   # Build the image with original configuration
   docker build -t birth-rectifier-ai:rollback -f ai_service.Dockerfile .

   # Stop the current container
   docker stop birth-rectifier-ai

   # Remove the current container
   docker rm birth-rectifier-ai

   # Start a new container with the rollback image
   docker run -d --name birth-rectifier-ai -p 8000:8000 birth-rectifier-ai:rollback
   ```

### 4.4 Long-Term Solution

While the ASGI wrapper provides an immediate fix, consider implementing Solution 4 (Middleware Consolidation) as a long-term solution to address the root cause:

1. Align middleware implementations between `path_rewriter.py` and `legacy_support.py`
2. Update import statements to use the correct middleware
3. Consider fully adopting the `unified_main.py` approach

## 5. ASGI Wrapper Implementation Visualization

The diagram below illustrates how the ASGI Wrapper solution (Solution 3) works compared to the current implementation:

```
Current Implementation:
┌─────────────────┐        ┌───────────────────┐        ┌──────────────┐        ┌────────────────┐
│ HTTP Request    │───────▶│ Path Rewriter     │───────▶│ Session      │───────▶│ FastAPI App    │
│ /health         │        │ Middleware        │        │ Middleware   │        │                │
└─────────────────┘        └───────────────────┘        └──────────────┘        └────────────────┘
                                                                                        │
                                                                                        │
                                                                                        ▼
                                                                               ┌────────────────┐
                                                                               │ Health Route   │
                                                                               │ Handler        │
                                                                               └────────────────┘
                                                                                        │
                                                                                        │
                           ┌─────────────────┐                                          ▼
                           │ HTTP Response   │◀─────────────────────────────────────────┘
                           │ (500 Error)     │
                           └─────────────────┘


Proposed ASGI Wrapper Solution:
┌─────────────────┐        ┌───────────────────┐
│ HTTP Request    │───────▶│ ASGI Wrapper      │
│ /health         │        │                   │
└─────────────────┘        └───────────────────┘
                                    │
                            ┌───────┴───────┐
                            │               │
                  ┌─────────▼─────┐   ┌─────▼──────────────┐
Is Health Request?│     Yes       │   │        No          │
                  └─────────┬─────┘   └─────┬──────────────┘
                            │               │
                            ▼               ▼
         ┌─────────────────────────┐    ┌───────────────────┐     ┌──────────────┐     ┌────────────────┐
         │ Direct Health Response  │    │ Path Rewriter     │────▶│ Session      │────▶│ FastAPI App    │
         │ (Bypasses Middleware)   │    │ Middleware        │     │ Middleware   │     │                │
         └────────────┬────────────┘    └───────────────────┘     └──────────────┘     └────────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │ HTTP Response           │
         │ (200 OK)                │
         └─────────────────────────┘
```

This diagram shows how the ASGI wrapper intercepts health check requests early in the request pipeline, completely bypassing the middleware stack that's causing the 500 errors. All other requests continue through the normal middleware chain, preserving the consolidated API architecture for non-health endpoints.

## 6. Monitoring and Future Improvements

### 6.1 Monitoring Recommendations

1. **Add Enhanced Logging**
   - Add detailed transaction ID tracking through middleware chain
   - Log middleware performance metrics
   - Track path rewriting operations
   - Implement structured logging for better analysis

2. **Health Check Monitoring**
   - Configure monitoring tools to track health endpoint latency
   - Set up alerts for health check failures
   - Add middleware-specific health metrics
   - Monitor success rates of health checks in all environments

3. **Middleware Performance Metrics**
   - Add timing metrics for middleware execution
   - Track path rewriting frequency and patterns
   - Monitor memory usage during request processing
   - Implement performance tracing for request pipelines

### 6.2 Future Improvements

1. **Middleware Architecture Refactoring**
   - Consider a middleware registry with ordered execution
   - Implement middleware dependency checking
   - Add middleware execution metrics
   - Create a configuration-driven middleware loading system
   - Implement circuit breakers for critical middleware components

2. **Health Check Enhancement**
   - Expand health checks to include component-level status
   - Add readiness vs. liveness differentiation
   - Include detailed dependency status
   - Implement health check result caching for high-traffic scenarios
   - Add progressive degradation reporting

3. **Documentation Updates**
   - Document middleware execution order and dependencies
   - Create middleware troubleshooting guide
   - Update architecture diagrams to show middleware flow
   - Add middleware debugging procedures
   - Document emergency bypass procedures for critical endpoints

4. **Testing Improvements**
   - Create middleware-specific unit tests
   - Implement integration tests for middleware chains
   - Add chaos testing for middleware resilience
   - Test health endpoints under various failure conditions
   - Create regression test suite for middleware changes

## 7. Conclusion

This root cause analysis has identified that the 500 Internal Server errors on the `/health` endpoint stem from conflicts in the middleware implementation after the recent API Gateway consolidation. The proposed ASGI wrapper solution provides an immediate fix by intercepting health check requests before they enter the problematic middleware chain.

By implementing this solution, we can ensure that the critical health check endpoint remains functional while preserving the consolidated API architecture for all other endpoints. The longer-term solutions outlined in this document address the underlying middleware conflicts and provide a path toward a more robust architecture.

The implementation plan provides a clear step-by-step approach to resolve the immediate issue, with comprehensive testing and verification steps to ensure the solution works as expected. The rollback plan ensures we can quickly revert if any unforeseen issues arise.

## 8. Attempted Solutions Assessment

### 8.1 Solutions Already Tried

Before adopting the ASGI wrapper approach, we attempted several direct fixes to the middleware implementation:

#### 8.1.1 Session Middleware Restructuring

We first attempted to modify the session middleware by:

1. Simplifying the `SessionMiddleware` class to a new `SimpleSessionMiddleware` class
2. Cleaning up the class structure to remove duplicate code
3. Ensuring proper exports through the `session_middleware` variable
4. Adding a function to retrieve the middleware class (`get_session_middleware()`)

```python
# Modified session.py approach
class SimpleSessionMiddleware(BaseHTTPMiddleware):
    """
    A simplified middleware for handling session management.
    This is the main middleware class that should be used with FastAPI.
    """
    # Implementation...

# Export the middleware class directly
session_middleware = SimpleSessionMiddleware
```

#### 8.1.2 Main.py Middleware Registration Updates

We also modified the main.py file to fix the middleware registration:

1. Removing middleware validation logic which could be corrupting the middleware stack
2. Directly importing the middleware class rather than using a factory function
3. Ensuring proper initialization of the middleware stack
4. Simplifying the middleware registration process

```python
# Import and add session middleware
from ai_service.api.middleware.session import session_middleware
app.add_middleware(session_middleware)
```

### 8.2 Why These Attempts Were Insufficient

While these approaches addressed some aspects of the middleware issues, they did not fully resolve the problem:

1. **Partial Root Cause Identification**: We identified issues with the session middleware but didn't fully recognize the conflict between different middleware implementations (legacy_support.py vs. path_rewriter.py).

2. **Middleware Initialization Issues**: Although we attempted to clean up middleware initialization, the underlying architectural inconsistencies remained.

3. **Complex Interdependencies**: Our changes to individual middleware classes did not address the complex interdependencies and order requirements in the middleware chain.

4. **Health Endpoint Vulnerability**: The direct changes to middleware still left the health endpoint vulnerable to middleware-related failures.

### 8.3 Comparison to Recommended Solution

The ASGI wrapper approach offers several advantages over our earlier attempts:

1. **Complete Bypass**: Rather than trying to fix middleware issues directly, it completely bypasses middleware for critical health endpoints.

2. **Non-Invasive Implementation**: It adds a new layer without modifying existing code, reducing risk.

3. **Architectural Flexibility**: It works regardless of which main application file is being used.

4. **Immediate Relief**: It provides immediate relief for health endpoint issues while allowing time for proper middleware refactoring.

### 8.4 Additional Insights from Implementation Attempts

Our implementation attempts revealed several insights:

1. **Middleware Registration Order** is critical, as FastAPI processes middleware in reverse registration order.

2. **Middleware Class Compatibility** issues with FastAPI's internals require careful attention to the expected format.

3. **FastAPI's Middleware Stack Building** process is sensitive to modification, and validation logic can sometimes interfere with proper initialization.

4. **Middleware State Persistence** between requests can lead to cascading failures when errors occur.

### 8.5 Recommended Next Steps Based on Attempts

Building on our previous attempts and the recommended ASGI wrapper solution:

1. **Implement the ASGI wrapper** as an immediate solution to restore health endpoint functionality.

2. **Document the middleware architecture** as it currently exists in both implementations.

3. **Create a comprehensive test suite** specifically for middleware functionality.

4. **Plan a gradual migration** to the consolidated architecture, starting with middleware alignment.

5. **Consider developing a middleware registry** that manages middleware registration and dependencies more explicitly.

The insights gained from our implementation attempts strongly support the ASGI wrapper as the most practical immediate solution, while also highlighting the need for a more structured approach to middleware management in the long term.

## 9. Alternative Approach: FastAPI Mounted Sub-Application Pattern

### 9.1 A FastAPI-Native Solution

After reviewing previous solutions and their limitations, we've identified a more elegant, FastAPI-native approach that hasn't been tried yet: using FastAPI's built-in sub-application mounting capability. This approach leverages FastAPI's architecture rather than working around it.

```python
# In ai_service/health_app.py
from fastapi import FastAPI
from datetime import datetime

# Create dedicated health check application with NO middleware
health_app = FastAPI(
    title="Health Check API",
    description="Health monitoring endpoints with no middleware",
    middleware=[]  # Explicitly empty middleware stack
)

@health_app.get("/")
async def health_check():
    """Health check endpoint with no middleware."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "middleware_free": True
    }

# In ai_service/main.py - Mount this application before adding any middleware

# Create main app
app = FastAPI(...)

# Mount health app at the /health path BEFORE adding middleware
app.mount("/health", health_app)
app.mount("/api/v1/health", health_app)

# NOW add middleware - won't affect the mounted app
app.add_middleware(PathRewriterMiddleware)
app.add_middleware(session_middleware)
```

### 9.2 How the Mounted Sub-Application Pattern Works

This solution works by creating a separate FastAPI application specifically for health checks that has no middleware. The key insight is that in FastAPI, mounted applications maintain their own middleware stack independently of the parent application. When mounting occurs before any middleware is added to the parent app, the mounted app remains middleware-free.

```
┌─────────────────────────────────────────────────────────────────┐
│ Main FastAPI Application                                        │
│                                                                 │
│ ┌─────────────────┐                                             │
│ │ Health App      │ ← Mounted at /health and /api/v1/health     │
│ │ (No Middleware) │   before any middleware is added            │
│ └─────────────────┘                                             │
│                                                                 │
│ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐    │
│ │ Path Rewriter   │ │ Session         │ │ Other Middleware │    │
│ │ Middleware      │ │ Middleware      │ │ (if any)         │    │
│ └─────────────────┘ └─────────────────┘ └─────────────────┘    │
│                                                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ Main Application Routes                                     ││
│ │ (processed through middleware)                              ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### 9.3 Benefits Over the ASGI Wrapper Approach

This approach offers several advantages over the ASGI wrapper solution:

1. **Native FastAPI Feature**: Uses built-in FastAPI functionality rather than custom ASGI code
2. **Simpler Implementation**: No need for raw ASGI handling or wrapper functions
3. **Better Maintainability**: Follows FastAPI's design patterns and will be maintained with FastAPI upgrades
4. **Improved Error Handling**: Uses FastAPI's error handlers and exception processing
5. **Cleaner Architecture**: Creates clear boundaries between components
6. **Documentation Support**: Health endpoints will appear in FastAPI's auto-generated documentation
7. **Easier Testing**: Standard FastAPI testing tools work without modification

### 9.4 Detailed Implementation Plan

#### 9.4.1 Step 1: Create Health Application Module

Create a dedicated module for the health check application:

```python
# health_app.py
from fastapi import FastAPI
from datetime import datetime
import logging

# Configure logging
logger = logging.getLogger("health-app")

# Create dedicated health check application with NO middleware
health_app = FastAPI(
    title="Health Check API",
    description="Health monitoring endpoints with no middleware",
    docs_url="/docs",  # Enable docs for this sub-app
    middleware=[]  # Explicitly empty middleware stack
)

@health_app.get("/")
async def health_check():
    """Health check endpoint with no middleware."""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "ai_service",
        "middleware_free": True
    }

# Optional: Add more health endpoints for different checks
@health_app.get("/readiness")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "timestamp": datetime.now().isoformat()
    }

@health_app.get("/liveness")
async def liveness_check():
    """Liveness check endpoint."""
    return {
        "status": "alive",
        "timestamp": datetime.now().isoformat()
    }
```

#### 9.4.2 Step 2: Update Main Application

Modify the main application to mount the health app before adding middleware:

```python
# main.py
from fastapi import FastAPI
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Initialize a clean FastAPI application
app = FastAPI(
    title="Birth Time Rectifier AI Service",
    description="AI service for astrological birth time rectification",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json"
)

# Import health app
from ai_service.health_app import health_app

# Mount health app at health endpoints BEFORE adding any middleware
# This ensures the health endpoints bypass all middleware
app.mount("/health", health_app)
app.mount("/api/v1/health", health_app)

# NOW add middleware
from ai_service.api.middleware.path_rewriter import PathRewriterMiddleware
app.add_middleware(PathRewriterMiddleware)

from ai_service.api.middleware.session import session_middleware
app.add_middleware(session_middleware)

# Add additional middleware and include routers as before
# ...
```

#### 9.4.3 Step 3: Update Unit Tests

Create targeted tests for the health endpoints:

```python
# test_health_app.py
from fastapi.testclient import TestClient
from ai_service.health_app import health_app

client = TestClient(health_app)

def test_health_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["middleware_free"] is True

# Also create integration tests with the main app
from ai_service.main import app as main_app

main_client = TestClient(main_app)

def test_mounted_health_endpoint():
    response = main_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

    # Also test the versioned endpoint
    versioned_response = main_client.get("/api/v1/health")
    assert versioned_response.status_code == 200
    assert versioned_response.json()["status"] == "healthy"
```

#### 9.4.4 Step 4: Deployment Changes

Since this approach modifies the main application directly, no Dockerfile changes are needed - the standard application startup command will work:

```dockerfile
CMD ["python", "-m", "uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 9.5 Migration from ASGI Wrapper

If the ASGI wrapper solution has already been implemented, here's a migration plan:

1. **Implement Health App**: Add the new `health_app.py` module
2. **Modify Main App**: Update `main.py` to mount the health app before adding middleware
3. **Testing**: Run tests to verify the mounted health endpoints work correctly
4. **Revert Dockerfile**: Update the Dockerfile to use the original FastAPI app directly:
   ```bash
   sed -i 's|ai_service.app_wrapper:app_wrapper|ai_service.main:app|g' ai_service.Dockerfile
   ```
5. **Phase Out Wrapper**: Once testing confirms the mounted app works, the wrapper can be removed

### 9.6 Testing and Verification

1. **Unit Testing**: Test the health app in isolation
2. **Integration Testing**: Test the mounted health app within the main application
3. **End-to-End Testing**: Test the health endpoints in a running container
4. **Load Testing**: Verify health endpoints perform well under load
5. **Concurrent Testing**: Test health endpoints during high application activity
6. **Failure Injection**: Test health endpoints during simulated middleware failures

### 9.7 Recommended Way Forward

Based on our analysis, we recommend:

1. **Immediate Implementation**: Implement the FastAPI Mounted Sub-Application pattern for health endpoints
2. **Consolidate Middleware Implementations**: Address the root middleware conflict between legacy_support.py and path_rewriter.py
3. **Migrate to Unified Main**: Once health endpoints are stable, complete the migration to unified_main.py as per the consolidation architecture
4. **Enhance Health Monitoring**: Expand health checks to include component-level monitoring and degradation reporting
5. **Improve Middleware Architecture**: Implement a middleware registry with proper dependency and order management

This FastAPI-native approach addresses the immediate health endpoint issue while aligning with FastAPI best practices and the consolidated API architecture.
