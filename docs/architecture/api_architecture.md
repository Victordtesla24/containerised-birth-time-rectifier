# API Endpoint Architecture Documentation

## API Integration Flow

```mermaid
flowchart TD
    %% UI/UX Components
    subgraph "Frontend UI/UX Components"
        A[Landing Page] --> B[Birth Details Form]
        B --> C{Valid Details?}
        C -->|Yes| D[Initial Chart Generation]
        C -->|No| B
        D --> E[Chart Visualization]
        E --> F[Questionnaire]
        F --> G[AI Analysis Processing]
        G --> H{Confidence > 80%?}
        H -->|Yes| I[Chart with Rectified Birth Time]
        H -->|No| J[Additional Questions]
        J --> G
        I --> K[Results Dashboard]
        K --> L[Export/Share]
    end

    %% API Integration Layer with Input/Output Structures
    B -.->|POST {query: "Location"}\nResponse: {latitude, longitude, timezone}| API3["/api/geocode\n/geocode"]
    B -.->|POST {birth_date, birth_time, latitude, longitude, timezone}\nResponse: {valid: true/false, errors: [...]}| API2["/api/chart/validate\n/chart/validate"]
    D -.->|POST {birth_date, birth_time, latitude, longitude, timezone, options}\nResponse: {chart_id, ascendant, planets, houses}| API4["/api/chart/generate\n/chart/generate"]
    E -.->|GET chart_id\nResponse: {chart_id, ascendant, planets, houses, aspects}| API5["/api/chart/{id}\n/chart/{id}"]
    F -.->|GET\nResponse: {questions: [...]}| API6["/api/questionnaire\n/questionnaire"]
    F -.->|POST {question_id, answer}\nResponse: {status, next_question_url}| API7["/api/questionnaire/{id}/answer\n/questionnaire/{id}/answer"]
    G -.->|POST {chart_id, answers, birth_time_range}\nResponse: {confidence_score, rectified_time, rectified_chart_id}| API8["/api/chart/rectify\n/chart/rectify"]
    I -.->|GET {chart1_id, chart2_id}\nResponse: {differences: [...]}| API9["/api/chart/compare\n/chart/compare"]
    K -.->|GET chart_id\nResponse: {insights: [...]}| API10["/api/interpretation\n/interpretation"]
    L -.->|POST {chart_id, format, options}\nResponse: {export_url or binary_data}| API11["/api/chart/export\n/chart/export"]

    %% Backend Services
    subgraph "Backend Services"
        API2 --> BS1[Validation Service]
        API3 --> BS2[Geocoding Service]
        API4 --> BS3[Chart Calculation Service]
        API5 --> BS4[Chart Retrieval Service]
        API6 --> BS5[Dynamic Questionnaire Service]
        API7 --> BS5
        API8 --> BS6[Birth Time Rectification Service]
        API9 --> BS7[Chart Comparison Service]
        API10 --> BS8[Interpretation Service]
        API11 --> BS9[Export Service]
    end

    %% Identified Gaps
    subgraph "Identified API Gaps"
        GAP1["❌ API Router Issue: /api prefix workaround\nAll endpoints registered twice"]
        GAP2["❌ Chart Comparison Service: Incomplete implementation\nData structures not fully defined"]
        GAP3["❌ Missing: Session Management\nEndpoint /api/session/init not implemented"]
        GAP4["❌ Interpretation Service: Incomplete implementation\nEndpoint exists but not documented properly"]
        GAP5["❌ Authentication/Authorization: Not implemented\nNo JWT/token validation in place"]
    end

    %% Connecting Gaps to Components
    API9 -.-> GAP2
    API10 -.-> GAP4

    %% Missing Components (should exist)
    A -.->|"❌ Missing Endpoint\nPOST {user data}\nResponse: {session_token}"| MISSING1["/api/session/init\n/session/init"]
    MISSING1 -.-> GAP3

    %% Style Definitions
    classDef page fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef api fill:#dff5ff,stroke:#0078d7,stroke-width:1px;
    classDef service fill:#e1ffe1,stroke:#107c10,stroke-width:1px;
    classDef gap fill:#ffeeee,stroke:#d13438,stroke-width:1px;
    classDef missing fill:#ffe6cc,stroke:#ff8c00,stroke-width:1px;

    class A,B,C,D,E,F,G,H,I,J,K,L page;
    class API2,API3,API4,API5,API6,API7,API8,API9,API10,API11 api;
    class BS1,BS2,BS3,BS4,BS5,BS6,BS7,BS8,BS9 service;
    class GAP1,GAP2,GAP3,GAP4,GAP5 gap;
    class MISSING1 missing;
```

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
