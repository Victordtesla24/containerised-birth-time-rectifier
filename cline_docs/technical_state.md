# Technical State Documentation

## Core Components

### Frontend
1. Form Implementation
   - Complete BirthDetailsForm with timezone support
   - Comprehensive form validation with proper event handling
   - Real-time error handling and state management
   - Timezone selection and validation
   - Geocoding integration with debounce
   - Additional factors management (life events, health history)
   - Correct BirthDetails structure with nested coordinates

2. Time Utilities
   - Timezone list and selection
   - Timezone offset calculation
   - Time format validation
   - UTC conversion helpers
   - String/Date type handling

3. Chart Components
   - BirthChart component with interactive controls
   - ChartRenderer with WebGL support
   - CelestialBackground with progressive loading
   - Complete ChartData typing with aspects support
   - Proper handling of ascendant (number or object)

### Backend
1. API Endpoints (Dual-Registration Pattern)
   - Primary endpoints with `/api/` prefix:
     - `/api/health` (Operational)
     - `/api/chart/rectify` (Complete with timezone support)
     - `/api/chart/validate` (Form validation)
     - `/api/geocode` (Location geocoding)
     - `/api/chart/generate` (Chart generation)
     - `/api/chart/{id}` (Chart retrieval)
     - `/api/questionnaire` (Dynamic questionnaire)
     - `/api/chart/export` (Chart export)

   - Alternative endpoints without `/api/` prefix (for backward compatibility):
     - `/health` (Operational)
     - `/chart/rectify` (Complete with timezone support)
     - `/chart/validate` (Form validation)
     - `/geocode` (Location geocoding)
     - `/chart/generate` (Chart generation)
     - `/chart/{id}` (Chart retrieval)
     - `/questionnaire` (Dynamic questionnaire)
     - `/chart/export` (Chart export)

   - All endpoints include proper error handling and validation
   - Comprehensive documentation in `api_architecture_docs.md`

2. Time Processing
   - UTC conversion utilities
   - Timezone validation
   - Time format standardization
   - Offset calculations

3. Model Integration
   - GPU memory management
   - Model loading and optimization
   - Tokenizer integration
   - Prediction pipeline

### Testing Infrastructure
1. Consolidated Testing Framework
   - Single unified test script (consolidated-app-flow-test.sh)
   - Support for all application flows
   - Menu-driven interface for interactive testing
   - CLI options for CI/CD integration
   - Comprehensive service management
   - Enhanced error handling and reporting
   - Flexible worker configuration

2. Test Constants Management
   - Centralized API endpoint definitions
   - Test data sets for different scenarios
   - Utility functions for common operations
   - Organized by test pattern needs

3. Test Pattern Implementation
   - Complete application flow testing (A→B→C→D→E→F→G→H→I→K→L→M)
   - Validation failure path testing (A→B→C→B)
   - Low confidence path testing (G→H→J→G)
   - Boundary cases testing with extreme coordinates
   - API endpoint validation testing
   - Health check verification

## Implementation Details

### Frontend Components
1. BirthDetailsForm
   ```typescript
   - Form state management with validation
   - Timezone selection from standardized list
   - Real-time validation feedback
   - Additional factors management
   - Proper BirthDetails structure handling with nested coordinates
   - String/Date type handling for dates
   ```

2. Time Utilities
   ```typescript
   - Timezone definitions and mapping
   - Offset calculations
   - Format validation
   - String/Date conversion helpers
   ```

3. Chart Components
   ```typescript
   - Interactive chart controls
   - WebGL rendering with Three.js
   - Complete ChartData type handling
   - Conditional rendering with type guards
   - Aspects visualization
   ```

### Testing Components
1. Consolidated Test Script
   ```bash
   - Menu-driven and CLI interfaces
   - Service management (start, check, stop)
   - API endpoint validation
   - Test pattern selection
   - Worker configuration
   - Verbose mode for debugging
   - Docker integration
   - CI mode for automation
   ```

2. Test Constants Management
   ```javascript
   - API_ENDPOINTS object for centralized endpoint definitions
   - TEST_DATA object with test case variations
   - Utility functions for common operations
   - Boundary case definitions
   ```

3. Test Patterns
   ```javascript
   - Complete flow: Landing → Export/Share
   - Validation failure: Form validation handling
   - Low confidence: Additional question handling
   - Boundary cases: Extreme coordinate handling
   - API validation: Endpoint consistency
   ```

### Backend Services
1. Rectification Endpoint
   ```python
   - Time conversion to/from UTC
   - Timezone handling
   - Model prediction integration
   - Error handling
   ```

2. Time Utilities
   ```python
   - UTC conversion functions
   - Timezone validation
   - Offset calculations
   ```

## Current Technical Priorities
1. Test Consolidation and Consistency
   - Unified testing approach
   - Consistent API endpoint usage
   - Comprehensive flow testing
   - Enhanced error reporting
   - Improved test data management

2. Type Safety Enhancements
   - Review remaining components for potential type issues
   - Consider stricter TypeScript configuration
   - Add runtime type checking for critical paths
   - Document type definitions and interfaces

3. API Endpoint Standardization
   - Consistent /api/ prefix usage
   - Proper error handling
   - Response format standardization
   - Documentation improvements

4. Test Coverage
   - All application flows covered
   - Edge cases handled
   - API consistency checked
   - Performance testing

5. CI/CD Integration
   - Test script automation
   - Report generation
   - Result visualization
   - Alert configuration

## Technical Debt
1. Test Coverage
   - Frontend component tests (all passing)
   - Type safety in test mocks improved
   - Selector specificity enhanced
   - Event handling optimization
   - Integration tests consolidated

2. Documentation
   - API documentation
   - Component documentation
   - Test script documentation
   - Type definition documentation
   - Setup guides

3. Optimization
   - Form performance
   - API response time
   - Memory management
   - Error handling
   - Type checking overhead

## Dependencies
1. Frontend
   - React/Next.js
   - TypeScript (with esModuleInterop)
   - TailwindCSS
   - Date/Time libraries

2. Backend
   - FastAPI
   - PyTorch
   - CUDA support
   - Time zone libraries

3. Testing
   - Playwright for browser testing
   - Jest for component testing
   - Docker for containerized testing
   - Shell scripting for test automation

4. Infrastructure
   - Docker
   - Redis
   - GPU support
   - Monitoring tools (pending)

## System Architecture
1. Frontend Service (Next.js)
   - Port: 3000
   - Status: Operational
   - Health Check: Passing
   - Dependencies: React, TypeScript, ChartJS
   - Type Safety: Enhanced with proper interface definitions

2. AI Service (FastAPI)
   - Port: 8000
   - Status: Operational (CPU Mode)
   - Health Check: Passing
   - Dependencies: PyTorch, FastAPI, transformers

3. Testing Service
   - Type: Consolidated shell script
   - Status: Operational
   - Features: Menu-driven, CLI options, Docker integration
   - Supported Flows: All application flows from implementation plan

4. Redis Service
   - Port: 6379
   - Status: Operational
   - Health Check: Passing
   - Role: Caching and data persistence

## Container Configuration
1. Development Environment
   - Docker Compose version: 3.8
   - Multi-stage builds implemented
   - CPU-only mode configured
   - Health checks implemented for all services
   - Volume mounts configured for development
   - Hot-reload enabled for frontend and AI service

2. Testing Environment
   - Playwright in Docker
   - Shared network with services
   - Volume mounting for test files
   - Memory configuration for browser testing
   - Improved worker configuration

## Testing Infrastructure
1. Test File Organization
   - Consolidated script at project root
   - Constants in tests/e2e/constants.js
   - Test specifications in tests/e2e/chart.spec.js
   - Helpers and utilities in tests/e2e/helpers
   - Configuration in playwright.config.js

2. Test Features
   - Menu-driven interface
   - CLI option support
   - Service management
   - API validation
   - Test pattern selection
   - Result reporting
   - Error handling

3. Test Patterns
   - Complete application flow: A→B→C→D→E→F→G→H→I→K→L→M
   - Validation failure path: A→B→C→B
   - Low confidence path: G→H→J→G
   - Boundary cases with extreme coordinates
   - API endpoint validation

## Current Technical Status
1. Development Environment
   - All services operational
   - Container builds successful
   - CPU mode functioning correctly
   - Inter-service communication verified
   - Testing infrastructure complete
   - TypeScript linter errors resolved

2. Test Infrastructure
   - Consolidated script operational
   - All patterns testable
   - API endpoints centralized
   - Test data organized
   - Service management improved
   - Error handling enhanced

3. Performance
   - Service startup times within acceptable range
   - CPU resource usage optimized
   - Memory management configured
   - Response times meeting requirements
   - Type checking overhead minimized

4. Monitoring
   - Basic health checks operational
   - Container logs accessible
   - Service status monitoring ready
   - Resource usage tracking prepared

## API Endpoint Architecture

The application implements a dual-registration pattern for API endpoints to ensure backward compatibility while following modern API design principles:

1. **Primary Endpoints** - Using `/api/` prefix:
   - Chart-related endpoints follow nested routing: `/api/chart/[endpoint]`
   - Other service endpoints follow flat routing: `/api/[endpoint]`

2. **Alternative Endpoints** - Without `/api/` prefix:
   - Chart-related endpoints: `/chart/[endpoint]`
   - Other service endpoints: `/[endpoint]`

This architecture is implemented in `ai_service/main.py` with explicit router registration for both patterns:

```python
# Register all routers with the /api prefix (primary endpoints)
app.include_router(health_router, prefix=API_PREFIX)
app.include_router(validate_router, prefix=f"{API_PREFIX}/chart")
app.include_router(geocode_router, prefix=API_PREFIX)
app.include_router(chart_router, prefix=f"{API_PREFIX}/chart")
app.include_router(questionnaire_router, prefix=f"{API_PREFIX}/questionnaire")
app.include_router(rectify_router, prefix=f"{API_PREFIX}/chart")
app.include_router(export_router, prefix=f"{API_PREFIX}/chart")

# Also register routers at root level (alternative endpoints)
app.include_router(health_router)
app.include_router(validate_router, prefix="/chart")
app.include_router(geocode_router)
app.include_router(chart_router, prefix="/chart")
app.include_router(questionnaire_router, prefix="/questionnaire")
app.include_router(rectify_router, prefix="/chart")
app.include_router(export_router, prefix="/chart")
```

### Implementation Details

1. **Router Organization**:
   - Each functionality has its own router file (chart.py, validate.py, geocode.py, etc.)
   - Routers are organized by domain area in the `ai_service/api/routers/` directory
   - All redundant and backup files have been removed for clarity

2. **Standardized Response Structure**:
   - Consistent JSON format across all endpoints
   - Appropriate HTTP status codes for different scenarios
   - Detailed error messages with error codes
   - Proper validation error handling

3. **Documentation**:
   - Comprehensive API documentation in `api_architecture_docs.md`
   - Endpoint details in `implementation_plan.md`
   - Centralized endpoint definitions in `tests/e2e/constants.js`

### Endpoint Status

#### Primary Endpoints (with /api/ prefix)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/api/chart/validate` | POST | Operational | Form validation |
| `/api/geocode` | GET/POST | Operational | Location geocoding |
| `/api/chart/generate` | POST | Operational | Chart generation |
| `/api/chart/{id}` | GET | Operational | Chart retrieval |
| `/api/questionnaire` | GET | Operational | Questionnaire retrieval |
| `/api/chart/rectify` | POST | Operational | Birth time rectification |
| `/api/chart/export` | POST | Operational | Chart export |
| `/api/health` | GET | Operational | Health check |

#### Alternative Endpoints (without /api/ prefix)
| Endpoint | Method | Status | Description |
|----------|--------|--------|-------------|
| `/chart/validate` | POST | Operational | Form validation |
| `/geocode` | GET/POST | Operational | Location geocoding |
| `/chart/generate` | POST | Operational | Chart generation |
| `/chart/{id}` | GET | Operational | Chart retrieval |
| `/questionnaire` | GET | Operational | Questionnaire retrieval |
| `/chart/rectify` | POST | Operational | Birth time rectification |
| `/chart/export` | POST | Operational | Chart export |
| `/health` | GET | Operational | Health check |

Both endpoint patterns are maintained for backward compatibility, with the `/api/` prefixed versions recommended for new development.

### Testing and Frontend Implementation

The frontend and test suite use a centralized constants file (`tests/e2e/constants.js`) that defines both primary and alternative endpoints:

```javascript
export const API_ENDPOINTS = {
    // Primary endpoints (with /api/ prefix)
    validate: '/api/chart/validate',
    geocode: '/api/geocode',
    chartGenerate: '/api/chart/generate',
    // ...

    // Alternative endpoints without /api/ prefix (for backward compatibility)
    validateAlt: '/chart/validate',
    geocodeAlt: '/geocode',
    chartGenerateAlt: '/chart/generate',
    // ...
}
```

This approach ensures consistent endpoint usage across the application and tests.

## Test Pattern Status
| Test Pattern | Status | Coverage |
|--------------|--------|----------|
| Complete Flow | Implemented | 8 steps (A→M) |
| Validation Failure | Implemented | Form validation (A→B→C→B) |
| Low Confidence | Implemented | Additional questions (G→H→J→G) |
| Boundary Cases | Implemented | 3 geographic extremes |
| API Validation | Implemented | 7 core endpoints |

## Current Challenges
1. Technical
   - Maintaining API endpoint consistency
   - Ensuring comprehensive test coverage
   - Handling edge cases in test data
   - Optimizing test performance

2. Implementation
   - Documenting test approach
   - Integrating with CI/CD pipeline
   - Enhancing error reporting
   - Improving test data management

## Recent Test Improvements
1. Script Consolidation
   - Merged duplicate scripts
   - Enhanced functionality
   - Improved interface
   - Better error handling

2. Test Data Management
   - Centralized test data
   - Organized by test pattern
   - Enhanced utility functions
   - Improved boundary case handling

3. API Endpoint Management
   - Centralized endpoint definitions
   - Consistent usage across tests
   - Alternative path support
   - Enhanced validation

4. Test Flow Implementation
   - All implementation flows covered
   - Complete application flow testing
   - Edge case handling
   - Error case testing
