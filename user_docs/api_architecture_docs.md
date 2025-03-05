# API Endpoint Architecture Documentation

## Overview

This document details the API endpoint architecture for the Astrological Chart Application. The application uses a dual-registration pattern for endpoints, providing both consistency and backward compatibility.

## API Endpoint Registration Pattern

### Dual-Registration Architecture

The application implements a dual-registration pattern for API endpoints:

1. **Primary Endpoints** - Registered with `/api/` prefix:
   - Chart-related endpoints follow the pattern: `/api/chart/...`
   - Other services follow the pattern: `/api/geocode`, `/api/health`, etc.

2. **Alternative Endpoints** - Registered without `/api/` prefix:
   - Chart-related endpoints: `/chart/...`
   - Other direct endpoints: `/geocode`, `/health`, etc.

This architecture ensures backward compatibility with existing clients while following modern API design principles.

## Implementation Details

### Registration in FastAPI Application

The endpoint registration is implemented in `ai_service/main.py`:

```python
# Standard API prefix for all endpoints
API_PREFIX = "/api"

# Register all routers with the /api prefix (primary endpoints)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(validate_router, prefix=f"{API_PREFIX}/chart")
app.include_router(geocode_router, prefix=API_PREFIX)
app.include_router(chart_router, prefix=f"{API_PREFIX}/chart")
app.include_router(questionnaire_router, prefix=f"{API_PREFIX}/questionnaire")
app.include_router(rectify_router, prefix=f"{API_PREFIX}/chart")
app.include_router(export_router, prefix=f"{API_PREFIX}/chart")

# Also register routers at root level for backward compatibility (alternative endpoints)
app.include_router(health_router)
app.include_router(validate_router, prefix="/chart")
app.include_router(geocode_router)
app.include_router(chart_router, prefix="/chart")
app.include_router(questionnaire_router, prefix="/questionnaire")
app.include_router(rectify_router, prefix="/chart")
app.include_router(export_router, prefix="/chart")
```

### Router Organization

All routers are organized in the `ai_service/api/routers/` directory:

- `health.py` - Health check endpoints
- `validate.py` - Birth details validation endpoints
- `geocode.py` - Location geocoding endpoints
- `chart.py` - Chart generation and retrieval endpoints
- `questionnaire.py` - Dynamic questionnaire endpoints
- `rectify.py` - Birth time rectification endpoints
- `export.py` - Chart export endpoints

### Router Implementation

Each router is implemented with its own path segments that are combined with the prefixes at registration time:

```python
# In ai_service/api/routers/chart.py
router = APIRouter(
    tags=["chart"],
    responses={404: {"description": "Not found"}},
)

@router.post("/generate", response_model=ChartResponse)
async def generate_charts(...):
    ...
```

When registered, this becomes:
- Primary: `/api/chart/generate`
- Alternative: `/chart/generate`

## Standard Endpoint Mapping

| Frontend Component | Primary API Endpoint | Alternative Endpoint | Backend Service |
|--------------------|---------------------|----------------------|-----------------|
| Birth Details Form | `/api/chart/validate` | `/chart/validate` | Validation Service |
| Birth Details Form | `/api/geocode` | `/geocode` | Geocoding Service |
| Initial Chart Gen | `/api/chart/generate` | `/chart/generate` | Chart Calculation Service |
| Chart Visualization | `/api/chart/{id}` | `/chart/{id}` | Chart Retrieval Service |
| Questionnaire | `/api/questionnaire` | `/questionnaire` | Dynamic Questionnaire Service |
| Results | `/api/chart/rectify` | `/chart/rectify` | Birth Time Rectification Service |
| Export/Share | `/api/chart/export` | `/chart/export` | Export Service |
| Health Check | `/api/health` | `/health` | Health Monitoring |

## Standardized Response Structure

All API endpoints follow a standardized response structure:

1. **Success Responses**:
   - Appropriate HTTP status code (200, 201, etc.)
   - Consistent JSON structure with data payload
   - Metadata when applicable (pagination, timestamps, etc.)

2. **Error Responses**:
   - Appropriate HTTP status code (400, 404, 500, etc.)
   - Consistent error format:
     ```json
     {
       "error": {
         "code": "ERROR_CODE",
         "message": "Human-readable error message",
         "details": { /* Additional error details */ }
       }
     }
     ```
   - Validation errors with field-specific information

## Frontend Implementation

The frontend uses constants to manage these endpoints, as defined in `tests/e2e/constants.js`:

```javascript
export const API_ENDPOINTS = {
    // Primary endpoints (with /api/ prefix)
    validate: '/api/chart/validate',
    geocode: '/api/geocode',
    chartGenerate: '/api/chart/generate',
    chartGet: '/api/chart/',
    questionnaire: '/api/questionnaire',
    rectify: '/api/chart/rectify',
    export: '/api/chart/export',
    health: '/api/health',

    // Alternative endpoints without /api/ prefix (for backward compatibility)
    validateAlt: '/chart/validate',
    geocodeAlt: '/geocode',
    chartGenerateAlt: '/chart/generate',
    chartGetAlt: '/chart/',
    questionnaireAlt: '/questionnaire',
    rectifyAlt: '/chart/rectify',
    exportAlt: '/chart/export',
    healthAlt: '/health'
}
```

## Benefits of Dual Registration

1. **Backward Compatibility**: Ensures existing clients continue to work
2. **Modern API Design**: Follows RESTful conventions with `/api` prefix
3. **Flexibility**: Allows gradual migration to preferred endpoint patterns
4. **Testing Simplicity**: Makes testing more robust by supporting multiple paths
5. **Clear Organization**: Provides logical grouping of related endpoints

## Recommendations for Development

1. **Prefer Primary Endpoints**: When writing new code, use the primary `/api/...` endpoints
2. **Document Both Options**: In API documentation, note both endpoint patterns
3. **Test Both Patterns**: Ensure testing covers both primary and alternative endpoints
4. **Use Constants**: Reference endpoints via the constants file rather than hardcoding
5. **Follow Response Standards**: Adhere to the standardized response structure

## Testing Considerations

The test suite in `consolidated-app-flow-test.sh` is configured to check and validate both endpoint patterns, ensuring that the dual-registration system continues to function correctly.

The test suite uses the centralized endpoint definitions from `tests/e2e/constants.js` to ensure consistency across all tests.

## Future Considerations

1. **API Versioning**: If needed, version prefixes can be added (e.g., `/api/v1/chart/generate`)
2. **Deprecation Strategy**: A plan for eventually deprecating alternative endpoints
3. **API Documentation**: Integration with tools like Swagger/OpenAPI for interactive documentation
4. **Rate Limiting**: Implementation of rate limiting on endpoints as needed
5. **Authentication**: Addition of authentication mechanisms for protected endpoints
