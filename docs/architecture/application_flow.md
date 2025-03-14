# Birth Time Rectifier - Application Flow

## Complete System, OpenAI Integration & User Interaction Architecture

```
+---------------+      +---------------+      +---------------+      +---------------+      +---------------+
| User          |<---->| Frontend UI   |<---->| API Gateway   |<---->| Backend       |<---->| OpenAI        |
| (Browser)     |      | (Next.js)     |      | Layer         |      | Services      |      | Verification  |
+---------------+      +---------------+      +---------------+      +---------------+      +---------------+
       |                      |                     |                      |                       |
       v                      v                     v                      v                       v
+---------------+      +---------------+      +---------------+      +---------------+      +---------------+
| User Journey  |      | React         |      | API Client    |      | Service       |      | AI-Based      |
| Experience    |      | Components    |      | & Middleware  |      | Architecture  |      | Verification  |
+---------------+      +---------------+      +---------------+      +---------------+      +---------------+
```

## Consolidated User Journey Diagram

```
+----------------------------------------------------------+
|                                                          |
|                     USER JOURNEY                         |
|                                                          |
+----------------------------------------------------------+
                           |
        +------------------v-------------------+
        |                                      |
        |      1. BIRTH DETAILS ENTRY          |
        |                                      |
        |  • Enter Birth Date                  |
        |  • Enter Approximate Time            |
        |  • Enter Birth Location              |
        |                                      |
        |  Key APIs:                           |
        |  - /api/geocode                      |
        |  - /api/chart/validate               |
        |                                      |
        +------------------+-------------------+
                           |
        +------------------v-------------------+
        |                                      |
        |     2. INITIAL CHART GENERATION      |
        |                                      |
        |  • Initial Chart Calculation         |
        |  • OpenAI Verification               |
        |  • Vedic Standards Check             |
        |  • 3D Visualization                  |
        |                                      |
        |  Key APIs:                           |
        |  - /api/chart/generate               |
        |  - /api/chart/{id}                   |
        |                                      |
        +------------------+-------------------+
                           |
        +------------------v-------------------+
        |                                      |
        |     3. DYNAMIC QUESTIONNAIRE         |
        |                                      |
        |  • Personalized Questions            |
        |  • Answer Processing                 |
        |  • Confidence Score Calculation      |
        |  • Adaptive Question Selection       |
        |                                      |
        |  Key APIs:                           |
        |  - /api/questionnaire                |
        |  - /api/questionnaire/{id}/answer    |
        |                                      |
        +------------------+-------------------+
                           |
        +------------------v-------------------+
        |                                      |
        |     4. BIRTH TIME RECTIFICATION      |
        |                                      |
        |  • AI Analysis of Answers            |
        |  • Time Adjustment Calculation       |
        |  • Confidence Scoring                |
        |  • Final Chart Generation            |
        |                                      |
        |  Key APIs:                           |
        |  - /api/chart/rectify                |
        |  - /api/chart/compare                |
        |                                      |
        +------------------+-------------------+
                           |
        +------------------v-------------------+
        |                                      |
        |     5. RESULTS & EXPORT              |
        |                                      |
        |  • View Rectified Chart              |
        |  • Compare Original vs Rectified     |
        |  • Export PDF Report                 |
        |  • Share Results                     |
        |                                      |
        |  Key APIs:                           |
        |  - /api/chart/export                 |
        |  - /api/export/{id}/download         |
        |                                      |
        +--------------------------------------+
```

## Detailed User-System Interaction Flow

```
+---------------+      +---------------+      +---------------+      +---------------+
| USER          |      | FRONTEND      |      | API GATEWAY   |      | BACKEND       |
+---------------+      +---------------+      +---------------+      +---------------+
       |                      |                     |                      |
       | Visit Application    |                     |                      |
       |--------------------->|                     |                      |
       |                      | Initialize Session  |                      |
       |                      |-------------------->|                      |
       |                      |                     | Create Session       |
       |                      |                     |--------------------->|
       |                      |                     |                      |
       |                      |                     |     Session Token    |
       |                      |<-------------------------------------------|
       |                      |                     |                      |
       | Enter Birth Details  |                     |                      |
       |--------------------->|                     |                      |
       |                      | Validate Locally    |                      |
       |                      |--------------------+|                      |
       |                      |                     |                      |
       |                      |<-------------------+|                      |
       |                      | Geocode Location    |                      |
       |                      |-------------------->|                      |
       |                      |                     | Process Location     |
       |                      |                     |--------------------->|
       |                      |                     |                      |
       |                      |                     |    Location Data     |
       |                      |<-------------------------------------------|
       |                      |                     |                      |
       | Submit Form          |                     |                      |
       |--------------------->|                     |                      |
       |                      | Generate Chart      |                      |
       |                      |-------------------->|                      |
       |                      |                     | Calculate Chart      |
       |                      |                     |--------------------->|
       |                      |                     |                      |
       |                      |                     |      Chart Data      |
       |                      |<-------------------------------------------|
       |                      |                     |                      |
       |     Display Chart    |                     |                      |
       |<---------------------|                     |                      |
       |                      |                     |                      |
```

## Consolidated Data Flow Diagram

```
+---------------------------------------------------------------+
|                     CONSOLIDATED DATA FLOW                     |
+---------------------------------------------------------------+
|                                                               |
|  +---------------+     +---------------+    +---------------+ |
|  |               |     |               |    |               | |
|  | FRONTEND DATA |---->| API GATEWAY   |--->| BACKEND DATA  | |
|  | MANAGEMENT    |     | PROCESSING    |    | SERVICES      | |
|  |               |<----|               |<---|               | |
|  +---------------+     +---------------+    +---------------+ |
|                                                               |
|  +---------+  +---------+  +---------+  +---------+  +-----+  |
|  | User    |  | Form    |  | Session |  | API     |  | DB  |  |
|  | Input   |->| State   |->| Token   |->| Request |->| Op  |  |
|  +---------+  +---------+  +---------+  +---------+  +-----+  |
|                                                               |
|  +---------------+     +---------------+    +---------------+ |
|  | Birth Details |---->| Location      |--->| Coordinates   | |
|  | Form          |     | Validation    |    | & Timezone    | |
|  +---------------+     +---------------+    +---------------+ |
|                                                               |
|  +---------------+     +---------------+    +---------------+ |
|  | Chart Request |---->| Data          |--->| Planet        | |
|  | Parameters    |     | Transformation|    | Positions     | |
|  +---------------+     +---------------+    +---------------+ |
|                                                               |
|  +---------------+     +---------------+    +---------------+ |
|  | Questionnaire |---->| AI Selection  |--->| Question      | |
|  | Answers       |     | Logic         |    | Generation    | |
|  +---------------+     +---------------+    +---------------+ |
|                                                               |
|  +---------------+     +---------------+    +---------------+ |
|  | Rectification |---->| Birth Time    |--->| Result        | |
|  | Request       |     | Adjustment    |    | Application   | |
|  +---------------+     +---------------+    +---------------+ |
|                                                               |
+---------------------------------------------------------------+
```

## Comprehensive System Component Architecture

```
+--------------------------------------------------------------+
|                   USER INTERFACE LAYER                       |
+--------------------------------------------------------------+
| +-----------------+  +-----------------+  +-----------------+|
| | Birth Details   |  | Chart           |  | Questionnaire   ||
| | Form Components |  | Visualization   |  | Components      ||
| |                 |  | Components      |  |                 ||
| | ┌-------------┐ |  | ┌-------------┐ |  | ┌-------------┐ ||
| | | Input Fields| |  | | WebGL Chart | |  | | Form Wizard | ||
| | +-------------+ |  | +-------------+ |  | +-------------+ ||
| | | Validation  | |  | | Planet View | |  | | Stepper UI  | ||
| | +-------------+ |  | +-------------+ |  | +-------------+ ||
| | | GeoLocation | |  | | Interaction | |  | | Progress Bar| ||
| | +-------------+ |  | +-------------+ |  | +-------------+ ||
| +-----------------+  +-----------------+  +-----------------+|
+-----------------------------||-------------------------------+
                              ||
+-----------------------------||--------------------------------+
|                       API GATEWAY LAYER                       |
+-----------------------------||--------------------------------+
| +-----------------+  +-----------------+  +-----------------+ |
| | Request/Response|  | Session/Auth    |  | Error Handling  | |
| | Processing      |  | Management      |  | & Interceptors  | |
| |                 |  |                 |  |                 | |
| | ┌-------------┐ |  | ┌-------------┐ |  | ┌-------------┐ | |
| | | API Client  | |  | | Token Mgmt  | |  | | Error Format| | |
| | +-------------+ |  | +-------------+ |  | +-------------+ | |
| | | Data Trans. | |  | | Session Val.| |  | | Retry Logic | | |
| | +-------------+ |  | +-------------+ |  | +-------------+ | |
| | | Content-Type| |  | | Expiry Hndl | |  | | Status Codes| | |
| | +-------------+ |  | +-------------+ |  | +-------------+ | |
| +-----------------+  +-----------------+  +-----------------+ |
+-----------------------------||---------------------------------+
                              ||
+-----------------------------||--------------------------------+
|                    BACKEND SERVICES LAYER                     |
+-----------------------------||--------------------------------+
| +-----------------+  +-----------------+  +-----------------+ |
| | Chart Services  |  | Geocoding       |  | Rectification   | |
| |                 |  | Services        |  | & AI Services   | |
| |                 |  |                 |  |                 | |
| | ┌-------------┐ |  | ┌-------------┐ |  | ┌-------------┐ | |
| | | Calculation | |  | | Location DB | |  | | AI Analysis | | |
| | +-------------+ |  | +-------------+ |  | +-------------+ | |
| | | Planet Pos. | |  | | Coordinates | |  | | Time Adjust | | |
| | +-------------+ |  | +-------------+ |  | +-------------+ | |
| | | Aspects     | |  | | Timezone    | |  | | Confidence  | | |
| | +-------------+ |  | +-------------+ |  | +-------------+ | |
| +-----------------+  +-----------------+  +-----------------+ |
+-----------------------------||---------------------------------+
                              ||
+-----------------------------||--------------------------------+
|                      DATA STORAGE LAYER                       |
+-----------------------------||--------------------------------+
| +-----------------+  +-----------------+  +-----------------+ |
| | Session Storage |  | Chart Data      |  | User Data       | |
| | (Redis)         |  | Storage         |  | Storage         | |
| +-----------------+  +-----------------+  +-----------------+ |
+---------------------------------------------------------------+
```

## Application Lifecycle States

```
+---------------------+     +---------------------+     +---------------------+
| INITIALIZATION      |     | DATA PROCESSING     |     | RESULTS DELIVERY    |
+---------------------+     +---------------------+     +---------------------+
| • Session Creation  |     | • Form Validation   |     | • Chart Rendering   |
| • Environment Check |     | • Geocoding         |     | • Display Results   |
| • Config Loading    |---->| • Chart Generation  |---->| • Export Options    |
| • UI Initialization |     | • AI Analysis       |     | • PDF Generation    |
| • API Client Setup  |     | • Rectification     |     | • Interpretation    |
+---------------------+     +---------------------+     +---------------------+
```

## Error Recovery & Fallback Flow

```
+------------------------------------------------------------+
|            ERROR RECOVERY FLOW                             |
+------------------------------------------------------------+
|                                                            |
|  API Request                                               |
|     |                                                      |
|     v                                                      |
|  +------------------+                                      |
|  | Primary Endpoint |                                      |
|  +------------------+                                      |
|     |                                                      |
|     v                                                      |
|  +------------------+   No    +-------------+              |
|  | Success?         |-------->| Error Type? |              |
|  +------------------+         +-------------+              |
|     | Yes                        |         |               |
|     v                            v         v               |
|  +------------------+     +-------------+  +-------------+ |
|  | Return Response  |     | 4xx Error?  |  | 5xx Error?  | |
|  +------------------+     +-------------+  +-------------+ |
|                             |                    |         |
|                             v                    v         |
|                        +-------------+     +-------------+ |
|                        | Client-side |     | Server-side | |
|                        | Handling    |     | Fallback    | |
|                        +-------------+     +-------------+ |
|                             |                    |         |
|                             v                    v         |
|                        +-------------+     +-------------+ |
|                        | User Error  |     | Try Alt     | |
|                        | Message     |     | Endpoint    | |
|                        +-------------+     +-------------+ |
|                                                 |          |
|                                                 v          |
|                                            +-------------+ |
|                                            | Success?    | |
|                                            +-------------+ |
|                                                 |    |     |
|                                                 v    v     |
|                                             Yes      No    |
|                                              |      |      |
|                                              v      v      |
|                                         +------+ +------+  |
|                                         |Return| |Display| |
|                                         |Data  | |Fallback |
|                                         +------+ |UI     | |
|                                                  +------+  |
+------------------------------------------------------------+
```

## Session Management Architecture

```
+---------------------+      +---------------------+      +---------------------+
| SESSION CREATION    |      | SESSION MONITORING  |      | SESSION STORAGE     |
+---------------------+      +---------------------+      +---------------------+
| • On App Load       |      | • Status Checks     |      | • Redis (Prod)      |
| • Session Token Gen |      | • Auto-refresh      |      | • LocalStorage      |
| • Unique ID Assign  |----->| • Expiry Tracking   |----->| • Fallback Modes    |
| • Headers Setup     |      | • Event Callbacks   |      | • Persistence       |
+---------------------+      +---------------------+      +---------------------+
```

## Overview

The Birth Time Rectifier is a comprehensive web application that uses AI and astrological principles to determine a person's accurate birth time. This document outlines the application flow, key components, and interactions.

## Application Components

1. **Frontend** (Next.js)
   - User interface for entering birth details
   - Questionnaire for gathering information
   - Results display with rectified birth time and chart visualization

2. **Backend API** (FastAPI)
   - Geocoding service for birth locations
   - Questionnaire generation and analysis
   - Chart generation and interpretation

3. **Services**
   - Redis for session storage and caching
   - AI service for birth time rectification

## Complete Application Flow

### 1. Birth Details Entry
- User enters their birth date, approximate time, and place
- Application geocodes the birthplace to get coordinates and timezone
- Birth details are saved in session storage for persistence

### 2. Chart Generation with OpenAI Verification
- Chart calculator generates initial planetary positions and house cusps
- Initial chart data is sent to OpenAI service for verification against Indian Vedic standards
- OpenAI applies multi-technique verification (including Tattva, Nadi, and KP methods)
- Any necessary corrections are applied to ensure chart accuracy
- Verification metadata (including confidence score) is included in the response
- The verified chart is displayed to the user with any applicable corrections highlighted

### 3. Questionnaire
- System initializes a personalized questionnaire based on birth details
- User answers questions about life events, personality traits, etc.
- Each response refines the birth time calculation
- Confidence score increases with each answer

### 4. Analysis
- When confidence reaches a threshold, final analysis is performed
- Rectified birth time is calculated based on questionnaire responses
- Astrological chart is generated using the rectified time
- Interpretations are provided for key chart elements

## Session Management Architecture

1. **Two-Tier Architecture**
   - **SessionService**: Handles API communication with session endpoints
   - **SessionManager**: Manages session lifecycle, monitoring, and events

2. **Automatic Session Handling**
   - Session creation on application load
   - Periodic health checks (every 5 minutes)
   - Automatic refresh before expiration
   - Graceful recovery from session expiration

3. **Environment-Based Behavior**
   - Production: Full Redis-backed sessions
   - Development: Local fallback sessions
   - Test: Mock session data

## Error Handling & Fallbacks

The application implements several fallback mechanisms:

1. **API Communication**
   - Standardized error format across all endpoints
   - Automatic session header injection
   - Retries with alternate endpoints if primary endpoint fails
   - Multiple backoff attempts for transient failures

2. **Geocoding Service**
   - Local fallbacks for common locations
   - Graceful degradation with approximate coordinates

3. **Chart Generation**
   - Simple chart placeholder if full chart cannot be generated
   - Text-based interpretations as backup

4. **Request Interceptors**
   - Test mode detection for development/testing
   - Mock API responses for offline development
   - Detailed error classification

## Performance Considerations

- Session storage minimizes data transfer between pages
- Asynchronous API calls prevent UI blocking
- Progressive loading indicators for long-running operations

## Future Enhancements

1. **Enhanced Error Reporting**
   - Detailed client-side error logging
   - Centralized error dashboard

2. **Additional Chart Types**
   - Support for South Indian style charts
   - Divisional charts (D9, D10, etc.)

3. **Extended Automation**
   - End-to-end UI testing with Cypress
   - Load testing for API endpoints
