# API Endpoint Architecture Documentation

## Complete System Architecture

```
+---------------+      +---------------+      +---------------+      +---------------+
| Client Device |<---->| Frontend      |<---->| API Gateway   |<---->| Backend       |
| Browser       |      | Next.js       |      | Service Layer |      | Services      |
+-------+-------+      +-------+-------+      +-------+-------+      +-------+-------+
        |                      |                      |                      |
        v                      v                      v                      v
+-------+--------+      +-------+--------+      +-------+-------+      +-------+-------+
| User Interface |      | UI Components  |      | Request/Resp. |      | Data Storage  |
| Interactions   |      | Rendering      |      | Processing    |      | Redis/DB      |
+----------------+      +----------------+      +---------------+      +---------------+
```

## Consolidated API Gateway Architecture

```
+------------------------------------------------------+
|                    CLIENT BROWSER                    |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                NEXT.JS FRONTEND (React)              |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                  UNIFIED API CLIENT                  |
|                                                      |
|  +------------------+       +-------------------+    |
|  | Request Pipeline |       | Response Pipeline |    |
|  |                  |       |                   |    |
|  | • Auth Injection |       | • Error Handling  |    |
|  | • Serialization  |       | • Deserialization |    |
|  | • Retry Logic    |       | • Caching         |    |
|  | • Timeout Mgmt   |       | • Data Transform  |    |
|  +------------------+       +-------------------+    |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                NEXT.JS API GATEWAY                   |
|                                                      |
|  +------------------+       +-------------------+    |
|  | Primary Routes   |       | Legacy Routes     |    |
|  | /api/...         |       | /...              |    |
|  +------------------+       +-------------------+    |
|                                                      |
|  +------------------+       +-------------------+    |
|  | Session Manager  |       | Error Formatter   |    |
|  +------------------+       +-------------------+    |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                PYTHON FASTAPI BACKEND                |
|                                                      |
|  +------------+  +----------+  +----------------+    |
|  | Services   |  | Routers  |  | Middleware     |    |
|  +------------+  +----------+  +----------------+    |
|                                                      |
|  +------------+  +----------+  +----------------+    |
|  | Models     |  | Utils    |  | External APIs  |    |
|  +------------+  +----------+  +----------------+    |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                   DATA STORAGE                       |
|  +------------+  +----------+  +----------------+    |
|  | Redis      |  | DB       |  | File Storage   |    |
|  +------------+  +----------+  +----------------+    |
+------------------------------------------------------+
```

## API Gateway & Client Interaction

```
+------------------------------+                +------------------------------+
|      FRONTEND CLIENT         |                |      BACKEND SERVICES        |
|                              |                |                              |
|  +-----------------------+   |                |   +-----------------------+  |
|  |     UI Components     |   |  API Requests  |   |    Service Layer      |  |
|  +-----------+-----------+   |  -----------→  |   +-----------+-----------+  |
|              |               |                |               |              |
|  +-----------v-----------+   |                |   +-----------v-----------+  |
|  |    API Client Layer   |   |                |   |   Controller Layer    |  |
|  |                       |   |                |   |                       |  |
|  | ┌-------------------┐ |   |                |   | ┌-------------------┐ |  |
|  | | Session Manager   | |   |                |   | | Request Handler   | |  |
|  | +-------------------+ |   |                |   | +-------------------+ |  |
|  | | Error Handler     | |   |                |   | | Input Validator   | |  |
|  | +-------------------+ |   |                |   | +-------------------+ |  |
|  | | Request Intercept | |   |                |   | | Auth Middleware   | |  |
|  | +-------------------+ |   |                |   | +-------------------+ |  |
|  | | Response Intercept| |   |  API Responses |   | | Response Builder  | |  |
|  | +-------------------+ |   |  ←-----------+ |   | +-------------------+ |  |
|  +-----------------------+   |                |   +-----------+-----------+  |
|                              |                |               |              |
+------------------------------+                |   +-----------v-----------+  |
                                                |   |   Domain Services      | |
                                                |   |                        | |
                                                |   | ┌-------------------┐  | |
                                                |   | | Chart Service     |  | |
                                                |   | +-------------------+  | |
                                                |   | | Geocode Service   |  | |
                                                |   | +-------------------+  | |
                                                |   | | Question Service  |  | |
                                                |   | +-------------------+  | |
                                                |   | | Rectify Service   |  | |
                                                |   | +-------------------+  | |
                                                |   +-----------+-----------+  |
                                                |               |              |
                                                |   +-----------v-----------+  |
                                                |   |    Persistence Layer  |  |
                                                |   +-----------------------+  |
                                                |                              |
                                                +------------------------------+
```

## API Request Flow Diagram

```
+----------------+     +----------------+     +----------------+
| Frontend       |     | Unified API    |     | Backend        |
| Component      |     | Gateway        |     | Service        |
+-------+--------+     +-------+--------+     +-------+--------+
        |                      |                      |
        | 1. Create Request    |                      |
        |--------------------->|                      |
        |                      | 2. Add Session       |
        |                      |    Token             |
        |                      |-------------+        |
        |                      |             |        |
        |                      |<------------+        |
        |                      |                      |
        |                      | 3. Forward Request   |
        |                      |--------------------->|
        |                      |                      | 4. Process
        |                      |                      |    Request
        |                      |                      |--------+
        |                      |                      |        |
        |                      |                      |<-------+
        |                      | 5. Response          |
        |                      |<---------------------|
        |                      |                      |
        |                      | 6. Transform &       |
        |                      |    Format Response   |
        |                      |-------------+        |
        |                      |             |        |
        |                      |<------------+        |
        | 7. Rendered Result   |                      |
        |<---------------------|                      |
        |                      |                      |
```

## Consolidated Router Implementation

```
+-------------------------------------------------------------+
|                   API ENDPOINT ARCHITECTURE                 |
+-------------------------------------------------------------+
|                                                             |
|   +---------------------+         +---------------------+   |
|   |                     |         |                     |   |
|   |   NEXT.JS ROUTES    |         |   PYTHON ROUTES     |   |
|   |                     |         |                     |   |
|   |  +--------------+   |         |  +--------------+   |   |
|   |  |  /api/*      |   |         |  | Dual-        |   |   |
|   |  |  GATEWAY     |<-------------->| Registration |   |   |
|   |  +--------------+   |         |  +--------------+   |   |
|   |                     |         |                     |   |
|   |  +--------------+   |         |  +--------------+   |   |
|   |  | Session Mgmt |   |         |  | Routers      |   |   |
|   |  +--------------+   |         |  +--------------+   |   |
|   |                     |         |                     |   |
|   |  +--------------+   |         |  +--------------+   |   |
|   |  | Error Format |   |         |  | Controllers  |   |   |
|   |  +--------------+   |         |  +--------------+   |   |
|   |                     |         |                     |   |
|   +---------------------+         +---------------------+   |
|                |                             |              |
|                v                             v              |
|   +---------------------+         +---------------------+   |
|   |                     |         |                     |   |
|   |  SERVICES ACCESSED  |         |  IMPLEMENTATION     |   |
|   |                     |         |                     |   |
|   |  • Geocoding        |         |  • Chart Service    |   |
|   |  • Chart Generation |         |  • Geocoding Service|   |
|   |  • Questionnaire    |         |  • Rectification    |   |
|   |  • Rectification    |         |  • OpenAI Service   |   |
|   |  • Export           |         |  • Export Service   |   |
|   |                     |         |                     |   |
|   +---------------------+         +---------------------+   |
|                                                             |
+-------------------------------------------------------------+
```

## User-System Interaction Flow

```
+---------------+    +---------------+    +---------------+    +---------------+
| User          |    | Frontend UI   |    | API Gateway   |    | Services      |
+-------+-------+    +-------+-------+    +-------+-------+    +-------+-------+
        |                    |                    |                    |
        | 1. Visit App       |                    |                    |
        +------------------->|                    |                    |
        |                    | 2. Init Session    |                    |
        |                    +------------------->|                    |
        |                    |                    | 3. Create Session  |
        |                    |                    +------------------->|
        |                    |                    |                    |
        |                    |                    |     Session Token  |
        |                    |<--------------------------------------- |
        |                    |                    |                    |
        | 4. Input Details   |                    |                    |
        +------------------->|                    |                    |
        |                    | 5. Validate & Send |                    |
        |                    +------------------->|                    |
        |                    |                    | 6. Process Request |
        |                    |                    +------------------->|
        |                    |                    |                    |
        |                    |                    |      Data Response |
        |                    |<--------------------------------------- |
        |                    |                    |                    |
        |    7. Show Results |                    |                    |
        |<-------------------+                    |                    |
        |                    |                    |                    |
```

## OpenAI Integration & Verification Architecture

```
+--------------------------------------------------+
|                         API LAYER                |
+--------------------------------------------------+
                            |
              +-------------v--------------+
              |                            |
   +----------v-----------+   +-----------v-----------+
   | Initial Calculation  |   | OpenAI Verification   |
   |                      |   |                       |
   | • Planetary Position |   | • Verify Accuracy     |
   | • House Cusps        |   | • Apply Corrections   |
   | • Aspect Calculation |   | • Calculate Confidence|
   | • Basic Formatting   |   | • Generate Explanation|
   +----------+-----------+   +-----------+-----------+
              |                            |
              +-------------v--------------+
                            |
                 +----------v----------+
                 | Verified Chart Data |
                 +----------+----------+
                            |
              +-------------v--------------+
              |                            |
   +----------v-----------+   +-----------v----------+
   | Birth Time Rectifier |   | Questionnaire        |
   |                      |   |                      |
   | • OpenAI Analysis    |   | • Dynamic Questions  |
   | • Multi-Technique    |   | • Life Events        |
   | • Confidence Scoring |   | • Answer Analysis    |
   +----------+-----------+   +-----------+----------+
              |                            |
              +-------------v--------------+
                            |
                 +----------v----------+
                 |  Results & Export   |
                 +---------------------+
```

### Verification Process Details

The OpenAI verification process follows these steps:

1. **Initial Chart Calculation**: Standard astronomical calculations produce planetary positions, house cusps, and other chart elements.

2. **OpenAI Verification**: The calculated chart is sent to OpenAI for verification against Vedic astrological standards:
   - The chart data is prepared into a structured prompt
   - The appropriate OpenAI model is selected based on the task type
   - The response is parsed and validated (handles both JSON string and dictionary formats)
   - Corrections are applied if needed

3. **Confidence Scoring**: Each verification includes a confidence score indicating certainty level.

4. **Enhanced Verification**: For low confidence results, a secondary verification using a more powerful model may be triggered automatically.

5. **Reporting**: The verified chart includes metadata about the verification process including:
   - Whether corrections were applied
   - Confidence score
   - Method used (standard or enhanced)

## Implementation Status & Components

```
+--------------------------------------------------+
|                                                  |
|  SYSTEM COMPONENTS AND IMPLEMENTATION STATUS     |
|                                                  |
+---------------------------+----------------------+
|                           |                      |
|  ✅ IMPLEMENTED           |  ❌ PENDING          |
|                           |                      |
|  ┌-------------------┐    |  ┌----------------┐  |
|  | Session Management|    |  | Authentication |  |
|  +-------------------+    |  +----------------+  |
|  | API Client Layer  |    |  | Chart Compare  |  |
|  +-------------------+    |  +----------------+  |
|  | Error Handling    |    |  | WebSockets     |  |
|  +-------------------+    |  +----------------+  |
|  | Chart Retrieval   |    |  | Full-featured  |  |
|  +-------------------+    |  | Interpretation |  |
|  | Basic Geocoding   |    |  +----------------+  |
|  +-------------------+    |                      |
|  | OpenAI Verification|   |                      |
|  +-------------------+    |                      |
|  | Vedic Chart Check |    |                      |
|  +-------------------+    |                      |
|                           |                      |
+---------------------------+----------------------+
|                                                  |
|  🔶 PARTIALLY IMPLEMENTED                        |
|                                                  |
|  ┌------------------------------------------┐    |
|  | Mock Data Generation & Test Mode Support |    |
|  +------------------------------------------+    |
|  | WebGL Rendering with Error Fallbacks     |    |
|  +------------------------------------------+    |
|  | Response Interceptors and Caching        |    |
|  +------------------------------------------+    |
|                                                  |
+--------------------------------------------------+
```

## Overview

This document details the API endpoint architecture for the Astrological Chart Application. The application uses a dual-registration pattern for endpoints, providing both consistency and backward compatibility.

## Centralized API Gateway Architecture

The application implements a centralized API Gateway that handles cross-cutting concerns across all API requests:

```
+----------------------------------+
| Frontend Component               |
+----------------------------------+
                ↓
+----------------------------------+
| API Gateway Layer                |
|----------------------------------|
| → apiClient (Axios instance)     |
| → Request Interceptors           |
| → Response Interceptors          |
| → Session Management             |
| → Error Handling                 |
+----------------------------------+
                ↓
+----------------------------------+
| API Endpoints                    |
+----------------------------------+
```

### Key Components

1. **API Client**
   - Configured Axios instance with default settings
   - Consistent timeout handling (30s default)
   - Standard content-type headers
   - Base URL configuration by environment

2. **Request Interceptors**
   - Automatic session ID injection via X-Session-ID header
   - Request logging and debugging
   - Request cancellation support
   - Test mode detection

3. **Response Interceptors**
   - Standardized error handling and formatting
   - Test mode fallbacks for 404/500 responses
   - Mock data generation for development/testing
   - Error classification and normalization

4. **Session Management**
   - Two-tier architecture:
     - `sessionService`: Basic API interactions
     - `sessionManager`: Advanced session lifecycle
   - Automatic session creation, validation, and refresh
   - Event-based notification system for session state
   - Graceful fallbacks for development environments

5. **Error Handling**
   - Consistent error format across all endpoints
   - Detailed error categorization and coding
   - Proper HTTP status code mapping
   - Validation error specialization

## API Endpoint Registration Pattern

### Consolidated Single-Registration Architecture with Path Rewriting

The application implements a single-registration architecture with path rewriting middleware:

1. **Primary Endpoints** - Registered with `/api/v1/` prefix:
   - Chart-related endpoints follow the pattern: `/api/v1/chart/...`
   - Other services follow the pattern: `/api/v1/geocode`, `/api/v1/health`, etc.

2. **Legacy Support** - Through path rewriting middleware:
   - Requests to legacy endpoints (e.g., `/chart/...`, `/geocode`, etc.) are automatically rewritten to the standardized endpoints
   - Backward compatibility is maintained without code duplication
   - Deprecation warnings are included in response headers

This architecture follows modern API design principles with proper versioning while maintaining backward compatibility through middleware rather than duplicate registrations.

## Implementation Details

### Registration in FastAPI Application

The endpoint registration is implemented in `ai_service/unified_main.py` with a single registration pattern:

```python
# Create the v1 API router with proper prefix
v1_router = APIRouter(prefix="/api/v1")

# Register all routers with the v1 API router
v1_router.include_router(health_router, tags=["Health"])
v1_router.include_router(session_router, prefix="/session", tags=["Session"])
v1_router.include_router(geocode_router, prefix="/geocode", tags=["Geocoding"])
v1_router.include_router(consolidated_chart_router, prefix="/chart", tags=["Chart"])
v1_router.include_router(questionnaire_router, prefix="/questionnaire", tags=["Questionnaire"])
v1_router.include_router(ai_integration_test_router, prefix="/ai", tags=["AI Integration"])
v1_router.include_router(ai_status_router, prefix="/ai", tags=["AI Status"])

# Include the v1 router in the app
app.include_router(v1_router)

# Add path rewriter middleware for legacy route support
app.add_middleware(PathRewriterMiddleware)
```

The `PathRewriterMiddleware` handles backward compatibility by transparently rewriting legacy paths:

```python
class PathRewriterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to rewrite legacy API paths to standardized v1 API paths.
    This allows backward compatibility without duplicate router registration.
    """

    def __init__(self, app, add_deprecation_warnings: bool = True):
        super().__init__(app)
        self.add_deprecation_warnings = add_deprecation_warnings

        # Define path mapping rules - from legacy paths to standardized v1 paths
        self.path_mappings = [
            # Root level legacy routes
            (r"^/health$", "/api/v1/health"),
            (r"^/geocode$", "/api/v1/geocode"),
            (r"^/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),

            # Unversioned /api/ routes
            (r"^/api/health$", "/api/v1/health"),
            (r"^/api/geocode$", "/api/v1/geocode"),
            (r"^/api/chart/(.*)$", r"/api/v1/chart/\1"),
            (r"^/api/questionnaire/(.*)$", r"/api/v1/questionnaire/\1"),
        ]
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

## OpenAI Service Integration

The application uses the OpenAI service for chart verification and birth time rectification, ensuring accuracy according to Indian Vedic Astrological standards.

### Chart Verification Process

The chart verification process follows these steps:

1. The frontend sends a chart generation request with `verify_with_openai: true`
2. The API Gateway forwards this to the backend Chart Service
3. The Chart Service first calculates the initial chart using traditional algorithms
4. The initial chart is then sent to the OpenAI Service for verification
5. The OpenAI Service applies Indian Vedic Astrological standards to verify calculations
6. If corrections are needed, they are applied to the chart
7. The verified chart with confidence score is returned
8. The results are stored in the database for future reference

```
Frontend → API Gateway → Chart Service → Initial Calculation → OpenAI Verification → Apply Corrections → Return Verified Chart
```

### Dynamic Model Selection

The OpenAI Service uses dynamic model selection based on task type:

```python
# From ai_service/api/services/openai/model_selection.py
def select_model(task_type: str) -> str:
    """
    Select the appropriate model based on task type.
    Uses environment variables for model selection to allow flexible configuration.
    """
    # Determine the task category
    task_category = get_task_category(task_type)

    # Get models from environment variables with defaults
    model_env_vars = {
        "rectification": os.environ.get("OPENAI_MODEL_RECTIFICATION", "o1-preview"),
        "calculation": os.environ.get("OPENAI_MODEL_CALCULATION", "o1-preview"),
        "visualization": os.environ.get("OPENAI_MODEL_VISUALIZATION", "gpt-4-turbo"),
        "questionnaire": os.environ.get("OPENAI_MODEL_QUESTIONNAIRE", "gpt-4-turbo"),
        "explanation": os.environ.get("OPENAI_MODEL_EXPLANATION", "gpt-4-turbo"),
        "auxiliary": os.environ.get("OPENAI_MODEL_AUXILIARY", "gpt-4o-mini")
    }

    return model_env_vars.get(task_category, model_env_vars["auxiliary"])
```

### Fallback Mechanism

The system includes a fallback mechanism in case the OpenAI service is unavailable:

```python
# In ai_service/api/routers/chart.py
try:
    # First try to use the enhanced calculator with OpenAI verification
    chart_data = await calculate_verified_chart(...)
    logging.info("Using OpenAI-verified chart")
except Exception as e:
    # If OpenAI verification fails, fall back to basic calculation
    logging.warning(f"OpenAI chart verification failed, using basic calculation: {e}")
    chart_data = calculate_chart(...)
```

## Standard Endpoint Mapping

| Frontend Component | Primary API Endpoint | Alternative Endpoint | Backend Service | Verification |
|--------------------|---------------------|----------------------|-----------------|--------------|
| Birth Details Form | `/api/chart/validate` | `/chart/validate` | Validation Service | N/A |
| Birth Details Form | `/api/geocode` | `/geocode` | Geocoding Service | N/A |
| Initial Chart Gen | `/api/chart/generate` | `/chart/generate` | Chart Calculation Service | OpenAI Vedic Verification |
| Chart Visualization | `/api/chart/{id}` | `/chart/{id}` | Chart Retrieval Service | N/A |
| Questionnaire | `/api/questionnaire` | `/questionnaire` | Dynamic Questionnaire Service | N/A |
| Results | `/api/chart/rectify` | `/chart/rectify` | Birth Time Rectification Service | OpenAI Analysis |
| Export/Share | `/api/chart/export` | `/chart/export` | Export Service | N/A |
| Health Check | `/api/health` | `/health` | Health Monitoring | N/A |

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

## Benefits of Single Registration with Path Rewriting

1. **Reduced Code Duplication**: Each endpoint is registered only once
2. **Simplified Maintenance**: Changes made in one place apply consistently
3. **Backward Compatibility**: Legacy endpoints continue to work through path rewriting
4. **Consistent Error Handling**: Standardized error format across all endpoints
5. **Better Developer Experience**: Clear versioning strategy and organization
6. **Deprecation Notices**: Legacy routes include proper deprecation warnings

## Recommendations for Development

1. **Use Versioned Endpoints**: Always use the `/api/v1/...` endpoints in new code
2. **Plan for Future Versioning**: Design endpoints with future versions in mind
3. **Follow Path Rewriting Patterns**: When adding new endpoints, update the path rewriting middleware
4. **Include Consistent Error Handling**: Follow standardized error format for all new endpoints
5. **Document Thoroughly**: Include full endpoint documentation with examples
6. **Monitor Deprecation**: Track usage of legacy endpoints via deprecation headers

## Testing Considerations

The test suite in `consolidated-app-flow-test.sh` is configured to check and validate both the new versioned endpoints and legacy endpoints, ensuring that the path rewriting middleware functions correctly.

The test suite uses the centralized endpoint definitions from `tests/e2e/constants.js` to ensure consistency across all tests. With the new single-registration architecture, errors and responses are consistent regardless of which endpoint pattern is used.

### Recommended Test Strategy

1. **Test Primary Versioned Endpoints**: Focus main tests on the primary `/api/v1/` endpoints
2. **Verify Legacy Endpoints**: Include regression tests for legacy paths to ensure the middleware works correctly
3. **Check Error Formats**: Ensure all endpoints return standardized error responses
4. **Validate Deprecation Headers**: Verify that legacy routes return proper deprecation warnings
5. **Test Path Parameters**: Ensure path parameters are correctly passed through the middleware
6. **Test Middleware Order**: Ensure the path rewriting middleware is applied before other middleware
