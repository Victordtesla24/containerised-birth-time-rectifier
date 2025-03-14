# API Router Consolidation Guide

## Overview

This guide details the process of consolidating the dual-registration API architecture to a unified single-registration pattern with path rewriting middleware. This approach maintains backward compatibility while significantly reducing code duplication and maintenance overhead.

## Current Dual-Registration Architecture

The current dual-registration pattern registers each router multiple times with different prefixes:

```python
# Register with /api/ prefix (primary endpoints)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(chart_router, prefix=f"{API_PREFIX}/chart")

# Also register at root level (alternative endpoints)
app.include_router(health_router)
app.include_router(chart_router, prefix="/chart")
```

## Consolidated Architecture

The new architecture uses a single registration pattern with the `/api/v1/` prefix and path rewriting middleware:

```python
# Register only once with /api/v1/ prefix
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(chart_router, prefix="/chart", tags=["Chart"])

# Include the v1 router in the app
app.include_router(v1_router)

# Add middleware for legacy route support
app.add_middleware(PathRewriterMiddleware)
```

## Implementation Steps

### 1. Create Path Rewriting Middleware

Create a middleware that transparently rewrites legacy paths to the standardized format:

```python
# ai_service/api/middleware/path_rewriter.py
class PathRewriterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, add_deprecation_warnings: bool = True):
        super().__init__(app)
        self.add_deprecation_warnings = add_deprecation_warnings

        # Define path mapping rules
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            # ... other mappings
        ]

    async def dispatch(self, request: Request, call_next):
        original_path = request.url.path

        # Check if path needs to be rewritten
        for pattern, replacement in self.compiled_mappings:
            if pattern.match(original_path):
                # Rewrite path and update request
                rewritten_path = pattern.sub(replacement, original_path)
                request.scope["path"] = rewritten_path
                rewritten = True
                break

        # Process the request
        response = await call_next(request)

        # Add deprecation warning if needed
        if rewritten and self.add_deprecation_warnings:
            response.headers["X-Deprecation-Warning"] = f"The path '{original_path}' is deprecated."

        return response
```

### 2. Update Main Application

Update the main FastAPI application to use a single registration pattern:

```python
# ai_service/main.py
# Create the v1 API router with proper prefix
v1_router = APIRouter(prefix="/api/v1")

# Register all routers with the v1 API router
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(session_router, prefix="/session", tags=["Session"])
v1_router.include_router(geocode_router, prefix="/geocode", tags=["Geocoding"])
v1_router.include_router(chart_router, prefix="/chart", tags=["Chart"])
# ... register other routers

# Include the v1 router in the app
app.include_router(v1_router)

# Add path rewriter middleware (before other middleware)
app.add_middleware(PathRewriterMiddleware)
```

### 3. Test Both Route Patterns

Verify that both the new standardized routes and legacy routes work correctly:

```bash
# Test new routes
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/chart/generate -d '{...}'

# Test legacy routes
curl http://localhost:8000/health
curl http://localhost:8000/chart/generate -d '{...}'
```

## Migration Strategy

To ensure a smooth transition for existing clients, implement a phased migration:

1. **Phase 1**: Legacy routes work with deprecation warnings
   - Legacy routes continue to function normally
   - Response headers include `X-Deprecation-Warning`
   - Documentation updated to recommend new routes

2. **Phase 2**: Legacy routes return 301 redirects (after 3 months)
   - Update middleware to return 301 redirects to new routes
   - Clients will be automatically redirected to new endpoints
   - Some clients may need manual updates if they don't follow redirects

3. **Phase 3**: Legacy routes return 410 Gone status (after 6 months)
   - Update middleware to return 410 Gone status for legacy routes
   - Include message directing to new documentation
   - All clients must be updated to use new routes

## Benefits

1. **Reduced Code Duplication**
   - Each endpoint is registered only once
   - Single implementation point for each feature
   - Clearer codebase organization

2. **Simplified Maintenance**
   - Changes made in one place apply consistently
   - Easier to add new endpoints or features
   - More predictable behavior across all endpoints

3. **Improved Developer Experience**
   - Consistent URL pattern for all endpoints
   - Clear versioning strategy for future updates
   - Better separation of concerns

4. **Enhanced Error Handling**
   - Standardized error format across all endpoints
   - More detailed error context for debugging
   - Consistent HTTP status codes

## Example Path Mappings

| Legacy Path | New Standardized Path |
|-------------|----------------------|
| `/health` | `/api/v1/health` |
| `/geocode` | `/api/v1/geocode` |
| `/chart/validate` | `/api/v1/chart/validate` |
| `/chart/generate` | `/api/v1/chart/generate` |
| `/chart/{id}` | `/api/v1/chart/{id}` |
| `/chart/rectify` | `/api/v1/chart/rectify` |
| `/chart/export` | `/api/v1/chart/export` |
| `/questionnaire` | `/api/v1/questionnaire` |
| `/api/geocode` | `/api/v1/geocode` |
| `/api/chart/generate` | `/api/v1/chart/generate` |

## Troubleshooting

### Missing Routes

If a route appears to be missing after consolidation:

1. Check the path rewriting middleware mapping
2. Verify the router is included in the `v1_router`
3. Test the route directly with curl or Postman

### Middleware Order

Middleware order is important - ensure the `PathRewriterMiddleware` is added before other middleware that may process the request path:

```python
# Add path rewriter middleware first
app.add_middleware(PathRewriterMiddleware)

# Then add other middleware
app.add_middleware(OtherMiddleware)
```

### Debugging Paths

To debug path rewriting, add extra logging to the middleware:

```python
# In the dispatch method
original_path = request.url.path
logger.debug(f"Original path: {original_path}")

# After rewriting
if rewritten:
    logger.debug(f"Rewritten path: {request.scope['path']}")
```

## Conclusion

The consolidation of API routers to a single registration pattern with path rewriting middleware provides significant benefits while maintaining backward compatibility. This approach follows industry best practices for API design and versioning, creating a more maintainable and developer-friendly architecture.
