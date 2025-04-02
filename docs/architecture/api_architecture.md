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
|  • Request Pipeline: Auth, Serialization, Retry      |
|  • Response Pipeline: Error handling, Caching        |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                NEXT.JS API GATEWAY                   |
|                                                      |
|  • Primary Routes: /api/v1/...                       |
|  • Session Manager                                   |
|  • Error Formatter                                   |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                PYTHON FASTAPI BACKEND                |
|                                                      |
|  • Services, Routers, Middleware                     |
|  • Models, Utils, External APIs                      |
+------------------------------------------------------+
                          |
                          v
+------------------------------------------------------+
|                   DATA STORAGE                       |
|                                                      |
|  • Redis, DB, File Storage                           |
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
|   |   NEXT.JS ROUTES    |         |   PYTHON ROUTES     |   |
|   |                     |         |                     |   |
|   |  • /api/v1/* Gateway|<------->|  • Versioned       |   |
|   |  • Session Mgmt     |         |    Endpoints       |   |
|   |  • Error Formatting |         |  • Routers         |   |
|   |                     |         |  • Controllers     |   |
|   +---------------------+         +---------------------+   |
|                |                             |              |
|                v                             v              |
|   +---------------------+         +---------------------+   |
|   |  SERVICES ACCESSED  |         |  IMPLEMENTATION     |   |
|   |                     |         |                     |   |
|   |  • Geocoding        |         |  • Chart Service    |   |
|   |  • Chart Generation |         |  • Geocoding Service|   |
|   |  • Questionnaire    |         |  • Rectification    |   |
|   |  • Rectification    |         |  • OpenAI Service   |   |
|   |  • Export           |         |  • Export Service   |   |
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

This document details the API endpoint architecture for the Astrological Chart Application. The application uses a single registration pattern with versioned API endpoints for consistency and maintainability.

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

### Consolidated Single-Registration Architecture

The application implements a single-registration architecture with versioned API endpoints:

1. **Primary Endpoints** - Registered with `/api/v1/` prefix:
   - Chart-related endpoints follow the pattern: `/api/v1/chart/...`
   - Other services follow the pattern: `/api/v1/geocode`, `/api/v1/health`, etc.

2. **Non-v1 API Paths** - Return 404 responses:
   - Requests to non-v1 API paths (e.g., `/chart/...`, `/geocode`, `/api/chart/...`) return 404 Not Found responses
   - Clear error messages direct users to use the appropriate `/api/v1/` endpoints

This architecture follows modern API design principles with proper versioning for better maintainability and future extensibility.

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
```

The API Gateway includes middleware that enforces the use of v1 API paths and returns appropriate 404 responses for non-v1 paths:

```python
@app.middleware("http")
async def enforce_v1_api_paths(request: Request, call_next):
    """
    Middleware to enforce v1 API paths.
    This ensures only standardized /api/v1/ endpoints are accessible.
    """
    path = request.url.path

    # Skip v1 API paths, they should be handled normally
    if path.startswith("/api/v1/"):
        return await call_next(request)

    # Skip root, websocket and documentation paths
    if path == "/" or path == "/health" or path.startswith("/ws") or path in ["/docs", "/redoc", "/openapi.json", "/swagger"]:
        return await call_next(request)

    # Return 404 for any other API path that starts with /api/
    if path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "code": "ENDPOINT_NOT_FOUND",
                    "message": "Endpoint not found. All API paths must use the /api/v1/ prefix.",
                    "timestamp": datetime.now().isoformat()
                }
            }
        )

    # For all other paths, continue normal processing
    return await call_next(request)
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
- `/api/v1/chart/generate`

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

| Frontend Component | API Endpoint | Backend Service | Verification |
|--------------------|--------------|--------------------|--------------|
| Birth Details Form | `/api/v1/chart/validate` | Validation Service | N/A |
| Birth Details Form | `/api/v1/geocode` | Geocoding Service | N/A |
| Initial Chart Gen | `/api/v1/chart/generate` | Chart Calculation Service | OpenAI Vedic Verification |
| Chart Visualization | `/api/v1/chart/{id}` | Chart Retrieval Service | N/A |
| Questionnaire | `/api/v1/questionnaire` | Dynamic Questionnaire Service | N/A |
| Results | `/api/v1/chart/rectify` | Birth Time Rectification Service | OpenAI Analysis |
| Export/Share | `/api/v1/chart/export` | Export Service | N/A |
| Health Check | `/api/v1/health` | Health Monitoring | N/A |

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
    // API endpoints with /api/v1/ prefix
    validate: '/api/v1/chart/validate',
    geocode: '/api/v1/geocode',
    chartGenerate: '/api/v1/chart/generate',
    chartGet: '/api/v1/chart/',
    questionnaire: '/api/v1/questionnaire',
    rectify: '/api/v1/chart/rectify',
    export: '/api/v1/chart/export',
    health: '/api/v1/health'
}
```

## Benefits of Single Registration Architecture

1. **Reduced Code Duplication**: Each endpoint is registered only once
2. **Simplified Maintenance**: Changes made in one place apply consistently
3. **Consistent Error Handling**: Standardized error format across all endpoints
4. **Better Developer Experience**: Clear versioning strategy and organization
5. **Future Extensibility**: Easy to add new API versions when needed

## Recommendations for Development

1. **Use Versioned Endpoints**: Always use the `/api/v1/...` endpoints in code
2. **Plan for Future Versioning**: Design endpoints with future versions in mind
3. **Include Consistent Error Handling**: Follow standardized error format for all endpoints
4. **Document Thoroughly**: Include full endpoint documentation with examples
5. **Enforce API Versioning**: Return appropriate error responses for non-v1 API paths

## Testing Considerations

The test suite in `api-test.sh` is configured to validate the versioned endpoints.

The test suite uses the centralized endpoint definitions from `tests/e2e/constants.js` to ensure consistency across all tests.

### Recommended Test Strategy

1. **Test Primary Versioned Endpoints**: Focus tests on the primary `/api/v1/` endpoints
2. **Verify Error Responses**: Ensure non-v1 paths return appropriate 404 responses
3. **Check Error Formats**: Ensure all endpoints return standardized error responses
4. **Test Path Parameters**: Ensure path parameters are correctly handled
5. **Test Middleware Order**: Ensure the API path validation middleware is applied in the correct order
