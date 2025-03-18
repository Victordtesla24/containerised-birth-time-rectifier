# Sequence Diagram Implementation Guide

## Complete Application Sequence Flow

```
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
| User           | --> | Frontend       | --> | API Layer      | --> | Backend        | --> | OpenAI        |
|                |     |                |     |                |     | Services       |     | Service       |
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |                      |
        |                     |                      |                     |                      |
        v                     v                      v                     v                      v
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
| Page Visit     | --> | Session Init   | --> | GET /api/      | --> | Create Session |     | Model         |
| Initial Load   |     | API Request    |     | session/init   |     | In Redis       |     | Selection     |
|                |     |                |     | ✅ Implemented |     |                |     |                |
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |                      |
        v                     v                      v                     v                      v
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
| Location Entry | --> | Geocode Request| --> | POST /api/     | --> | Location DB    |     | Vedic          |
| Birth City     |     | API Call       |     | geocode        |     | Coordinates    |     | Standards      |
|                |     |                |     |                |     | Timezone       |     | Verification   |
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |                      |
        v                     v                      v                     v                      v
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
| Birth Details  | --> | Validate Data  | --> | POST /api/     | --> | Format Check   |     | Birth Time     |
| Date & Time    |     | Form Submit    |     | chart/validate |     | Date/Time      |     | Rectification  |
| Input          |     |                |     |                |     | Verification   |     | Analysis       |
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |                      |
        v                     v                      v                     v                      v
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
| Generate Chart | --> | Submit Form    | --> | POST /api/     | --> | Calculate      | --> | Verify Chart   |
| Request        |     | API Call       |     | chart/generate |     | Initial Chart  |     | Against Vedic  |
|                |     | {verify: true} |     |                |     |                |     | Standards      |
+----------------+     +----------------+     +----------------+     +----------------+     +----------------+
                                                                                                    |
                                                                                                    v
                                                                     +----------------+     +----------------+
                                                                     | Store in DB    | <-- | Apply          |
                                                                     | Return Chart   |     | Corrections    |
                                                                     |                |     | if needed      |
                                                                     +----------------+     +----------------+
        |                     |                      |                     |
        v                     v                      v                     v
+----------------+     +----------------+     +----------------+     +----------------+
| View Chart     | --> | Render Chart   | --> | GET /api/chart | --> | Query DB       |
| Visualization  |     | API Call       |     | /{chart_id}    |     | Return Chart   |
|                |     |                |     | ✅ Fixed: 500  |     | Data           |
+----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |
        v                     v                      v                     v
+----------------+     +----------------+     +----------------+     +----------------+
| Answer         | --> | Submit Answers | --> | POST /api/     | --> | Process        |
| Questionnaire  |     | Series of Calls|     | questionnaire/ |     | Answers        |
| Questions      |     |                |     | ✅ Fixed: 500  |     | Store in DB    |
+----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |
        v                     v                      v                     v
+----------------+     +----------------+     +----------------+     +----------------+
| Birth Time     | --> | Request        | --> | POST /api/     | --> | AI Analysis    |
| Rectification  |     | Rectification  |     | chart/rectify  |     | Algorithm      |
| Process        |     |                |     |                |     | Calculate Time |
+----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |
        v                     v                      v                     v
+----------------+     +----------------+     +----------------+     +----------------+
| Comparison     | --> | Compare Charts | --> | GET /api/chart | --> | Analyze        |
| & Interpretation|    | GET Insight    |     | /compare       |     | Differences    |
|                |     |                |     |                |     |                |
+----------------+     +----------------+     +----------------+     +----------------+
        |                     |                      |                     |
        v                     v                      v                     v
+----------------+     +----------------+     +----------------+     +----------------+
| Export Chart   | --> | Request Export | --> | POST /api/     | --> | Generate PDF   |
| & Download     |     | & Download     |     | chart/export   |     | Download File  |
|                |     |                |     | ✅ Fixed: 500  |     |                |
+----------------+     +----------------+     +----------------+     +----------------+
```

## Enhanced Error Handling Sequence

```
Frontend            Unified API Client       Next.js API Gateway      Python Backend
    |                      |                         |                      |
    | Request              |                         |                      |
    |--------------------->|                         |                      |
    |                      | Add Headers &           |                      |
    |                      | Prepare Request         |                      |
    |                      |------------------------>|                      |
    |                      |                         | Forward Request      |
    |                      |                         |--------------------->|
    |                      |                         |                      | Process
    |                      |                         |                      |------+
    |                      |                         |                      |      |
    |                      |                         |                      |<-----+
    |                      |                         |                      |
    |                      |                         |                      | Error Occurs!
    |                      |                         |                      |------+
    |                      |                         |                      |      |
    |                      |                         |                      |<-----+
    |                      |                         | Error Response (500) |
    |                      |                         |<---------------------|
    |                      |                         |                      |
    |                      |                         | Format Error &       |
    |                      |                         | Add Metadata         |
    |                      |                         |------+               |
    |                      |                         |      |               |
    |                      |                         |<-----+               |
    |                      | Standardized Error      |                      |
    |                      |<------------------------|                      |
    |                      |                         |                      |
    |                      | Retry Logic             |                      |
    |                      |------+                  |                      |
    |                      |      | (Try alternate   |                      |
    |                      |<-----+ endpoint)        |                      |
    |                      |                         |                      |
    |                      | Retry Request           |                      |
    |                      |------------------------>|                      |
    |                      |                         | Forward to           |
    |                      |                         | Alternative Endpoint |
    |                      |                         |--------------------->|
    |                      |                         |                      | Process
    |                      |                         |                      |------+
    |                      |                         |                      |      |
    |                      |                         |                      |<-----+
    |                      |                         | Success Response     |
    |                      |                         |<---------------------|
    |                      | Formatted Response      |                      |
    |                      |<------------------------|                      |
    | Rendered Result      |                         |                      |
    |<---------------------|                         |                      |
    |                      |                         |                      |
```

## Consolidated API Questionnaire Flow

```
User          Frontend            Unified API Client       Next.js Gateway          Python Backend
 |                |                       |                      |                        |
 | Start Quest.   |                       |                      |                        |
 |--------------->|                       |                      |                        |
 |                | Get Initial Question  |                      |                        |
 |                |---------------------->|                      |                        |
 |                |                       | Request              |                        |
 |                |                       |--------------------->|                        |
 |                |                       |                      | Forward                |
 |                |                       |                      |----------------------->|
 |                |                       |                      |                        | Generate Q
 |                |                       |                      |                        |----------+
 |                |                       |                      |                        |          |
 |                |                       |                      |                        |<---------+
 |                |                       |                      | Response               |
 |                |                       |                      |<-----------------------|
 |                |                       | Formatted Response   |                        |
 |                |                       |<---------------------|                        |
 |                | Display Question      |                      |                        |
 |                |<----------------------|                      |                        |
 | Answer Question|                       |                      |                        |
 |--------------->|                       |                      |                        |
 |                | Submit Answer         |                      |                        |
 |                |---------------------->|                      |                        |
 |                |                       | Cache Answer Locally |                        |
 |                |                       |------------+         |                        |
 |                |                       |            |         |                        |
 |                |                       |<-----------+         |                        |
 |                |                       | POST Answer          |                        |
 |                |                       |--------------------->|                        |
 |                |                       |                      | Forward                |
 |                |                       |                      |----------------------->|
 |                |                       |                      |                        | Process
 |                |                       |                      |                        |----------+
 |                |                       |                      |                        |          |
 |                |                       |                      |                        |<---------+
 |                |                       |                      | Next Question          |
 |                |                       |                      |<-----------------------|
 |                |                       | Format & Return      |                        |
 |                |                       |<---------------------|                        |
 |                | Display Next Question |                      |                        |
 |                |<----------------------|                      |                        |
 |                |                       |                      |                        |
```

## Original Sequence Diagram - Full Implementation

```
User          Frontend            API Layer           Backend             OpenAI             Database
 |                |                   |                  |                   |                   |
 |                |                   |                  |                   |                   |
 | Visit App      |                   |                  |                   |                   |
 |--------------->|                   |                  |                   |                   |
 |                | GET /session/init |                  |                   |                   |
 |                |------------------>|                  |                   |                   |
 |                |                   | Create Session   |                   |                   |
 |                |                   |----------------->|                   |                   |
 |                |                   |                  | Store Session     |                   |
 |                |                   |                  |-------------------------------------->|
 |                |                   |                  |                   |                   |
 |                |                   |                  |     Session ID    |                   |
 |                |                   |                  |<--------------------------------------|
 |                |                   |   Session Data   |                   |                   |
 |                |                   |<-----------------|                   |                   |
 |                |    Session Token  |                  |                   |                   |
 |                |<------------------|                  |                   |                   |
 |                |                   |                  |                   |                   |
 | Enter Location |                   |                  |                   |                   |
 |--------------->|                   |                  |                   |                   |
 |                | POST /geocode     |                  |                   |                   |
 |                | {query: "NYC"}    |                  |                   |                   |
 |                |------------------>|                  |                   |                   |
 |                |                   | Process Location |                   |                   |
 |                |                   |----------------->|                   |                   |
 |                |                   |                  | Query Location DB |                   |
 |                |                   |                  |-------------------------------------->|
 |                |                   |                  |                   |                   |
 |                |                   |                  |    Coordinates    |                   |
 |                |                   |                  |<--------------------------------------|
 |                |                   | Location Data    |                   |                   |
 |                |                   |<-----------------|                   |                   |
 |                | {results: [{...}]}|                  |                   |                   |
 |                |<------------------|                  |                   |                   |
 |                |                   |                  |                   |                   |
 | Enter Date/Time|                   |                  |                   |                   |
 |--------------->|                   |                  |                   |                   |
 |                | POST /chart/validate                 |                   |                   |
 |                |------------------>|                  |                   |                   |
 |                |                   | Validate Details |                   |                   |
 |                |                   |----------------->|                   |                   |
 |                |                   | Validation Result|                   |                   |
 |                |                   |<-----------------|                   |                   |
 |                | {valid: true}     |                  |                   |                   |
 |                |<------------------|                  |                   |                   |
 |                |                   |                  |                   |                   |
 | Request Chart  |                   |                  |                   |                   |
 |--------------->|                   |                  |                   |                   |
 |                | POST /chart/generate                 |                   |                   |
 |                | {verify_with_openai: true}           |                   |                   |
 |                |------------------>|                  |                   |                   |
 |                |                   | Calculate Chart  |                   |                   |
 |                |                   |----------------->|                   |                   |
 |                |                   |                  | Initial Chart     |                   |
 |                |                   |                  | Calculation       |                   |
 |                |                   |                  |-------------------|                   |
 |                |                   |                  |                   |                   |
 |                |                   |                  | Verify Chart      |                   |
 |                |                   |                  |------------------>|                   |
 |                |                   |                  |                   | Multi-technique   |
 |                |                   |                  |                   | Vedic Analysis    |
 |                |                   |                  |                   |-------------------|
 |                |                   |                  |                   |                   |
 |                |                   |                  |                   | Verification      |
 |                |                   |                  |                   | Result            |
 |                |                   |                  |<------------------|                   |
 |                |                   |                  |                   |                   |
 |                |                   |                  | Apply Corrections |                   |
 |                |                   |                  | (if needed)       |                   |
 |                |                   |                  |-------------------|                   |
 |                |                   |                  |                   |                   |
 |                |                   |                  | Store Chart       |                   |
 |                |                   |                  |-------------------------------------->|
 |                |                   |                  |                   |                   |
 |                |                   |                  |     Chart ID      |                   |
 |                |                   |                  |<--------------------------------------|
 |                |                   |   Verified       |                   |                   |
 |                |                   |   Chart Data     |                   |                   |
 |                |                   |<-----------------|                   |                   |
 |                | {chart_id: "...", |                  |                   |                   |
 |                |  verification: {  |                  |                   |                   |
 |                |    confidence: 87,|                  |                   |                   |
 |                |    verified: true,|                  |                   |                   |
 |                |  }}               |                  |                   |                   |
 |                |<------------------|                  |                   |                   |
 |                |                   |                  |                   |
 |                | GET /chart/{id}   |                  |                   |
 |                |------------------>|                  |                   |
 |                |                   | Retrieve Chart   |                   |
 |                |                   |----------------->|                   |
 |                |                   |                  | Query Chart Data  |
 |                |                   |                  |------------------>|
 |                |                   |                  |                   |
 |                |                   |                  |   Chart Details   |
 |                |                   |                  |<------------------|
 |                |                   | Complete Data    |                   |
 |                |                   |<-----------------|                   |
 |                | Chart with Aspects|                  |                   |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 | To Questionnaire                   |                  |                   |
 |--------------->|                   |                  |                   |
 |                | GET /questionnaire|                  |                   |
 |                |------------------>|                  |                   |
 |                |                   | Generate Questions                   |
 |                |                   |----------------->|                   |
 |                |                   | Question Data    |                   |
 |                |                   |<-----------------|                   |
 |                | {questions: [...]}|                  |                   |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 | Answer: Yes    |                   |                  |                   |
 |--------------->|                   |                  |                   |
 |                | POST /questionnaire/{id}/answer      |                   |
 |                |------------------>|                  |                   |
 |                |                   | Process Answer   |                   |
 |                |                   |----------------->|                   |
 |                |                   |                  | Store Answer      |
 |                |                   |                  |------------------>|
 |                |                   |                  |                   |
 |                |                   | Next Question    |                   |
 |                |                   |<-----------------|                   |
 |                | {next_question}   |                  |                   |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 | Complete Quest.|                   |                  |                   |
 |--------------->|                   |                  |                   |
 |                | POST /questionnaire/complete         |                   |
 |                |------------------>|                  |                   |
 |                |                   | Finalize Quest.  |                   |
 |                |                   |----------------->|                   |
 |                |                   | Completion Status|                   |
 |                |                   |<-----------------|                   |
 |                | {status: "processing"}               |                   |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 |                | POST /chart/rectify                  |                   |
 |                |------------------>|                  |                   |
 |                |                   | Rectify Process  |                   |
 |                |                   |----------------->|                   |
 |                |                   |                  | Process Data      |
 |                |                   |                  |------------------>|
 |                |                   |                  |                   |
 |                |                   |     AI Analysis  |                   |
 |                |                   |     Determines   |                   |
 |                |                   |    Birth Time    |                   |
 |                |                   |                  |                   |
 |                |                   |                  | Analysis Results  |
 |                |                   |                  |<------------------|
 |                |                   | Rectification    |                   |
 |                |                   |<-----------------|                   |
 |                | {rectified_time: "15:12:00", confidence: 87.5%}          |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 |                | GET /chart/compare?chart1=X&chart2=Y |                   |
 |                |------------------>|                  |                   |
 |                |                   | Compare Charts   |                   |
 |                |                   |----------------->|                   |
 |                |                   |                  | Retrieve Charts   |
 |                |                   |                  |------------------>|
 |                |                   |                  |                   |
 |                |                   |                  | Charts Data       |
 |                |                   |                  |<------------------|
 |                |                   | Comparison Data  |                   |
 |                |                   |<-----------------|                   |
 |                | {differences: [...]}                 |                   |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 | Request Export |                   |                  |                   |
 |--------------->|                   |                  |                   |
 |                | POST /chart/export|                  |                   |
 |                |------------------>|                  |                   |
 |                |                   | Generate Export  |                   |
 |                |                   |----------------->|                   |
 |                |                   |                  | Get Chart Data    |
 |                |                   |                  |------------------>|
 |                |                   |                  |                   |
 |                |                   |                  | Chart Details     |
 |                |                   |                  |<------------------|
 |                |                   | Export Data      |                   |
 |                |                   |<-----------------|                   |
 |                | {download_url: "/api/export/..."}    |                   |
 |                |<------------------|                  |                   |
 |                |                   |                  |                   |
 |                | GET /export/{id}/download            |                   |
 |                |------------------>|                  |                   |
 |                |                   | Retrieve File    |                   |
 |                |                   |----------------->|                   |
 |                |                   | PDF File         |                   |
 |                |                   |<-----------------|                   |
 |                | Binary PDF Data   |                  |                   |
 |                |<------------------|                  |                   |
 | View Result    |                   |                  |                   |
 |<---------------|                   |                  |                   |
 |                |                   |                  |                   |
```

## Simplified Sequence Diagram - User Testing Iteration 2

```
User          Frontend            Mock Services
 |                |                     |
 | Visit App      |                     |
 |--------------->|                     |
 |                |     Create Mock     |
 |                |     Session Locally |
 |                |-------------------->|
 |                |                     |
 | Enter Location |                     |
 |--------------->|                     |
 |                | Validate Format     |
 |                | Locally             |
 |                |-------------------->|
 |                |                     |
 |                | Mock Geocode Request|
 |                |-------------------->|
 |                |                     |
 |                | Mock Location Data  |
 |                |<--------------------|
 |                |                     |
 | Enter Date/Time|                     |
 |--------------->|                     |
 |                | Validate Date/Time  |
 |                | Locally             |
 |                |-------------------->|
 |                | Show Validation     |
 |                | Status              |
 |                |-------------------->|
 |                |                     |
 | Submit Form    |                     |
 |--------------->|                     |
 |                | Validate All Fields |
 |                | Locally             |
 |                |-------------------->|
 |                |                     |
 |                | Generate Chart ID   |
 |                | Using Timestamp     |
 |                |-------------------->|
 |                |                     |
 |                | Navigate to Chart   |
 |                | Display Page        |
 |                |-------------------->|
 |                |                     |
 |                | Mock Chart Request  |
 |                |-------------------->|
 |                |                     |
 |                | Mock Chart Data     |
 |                |<--------------------|
 |                |                     |
 |                | Render Visualization|
 |                |-------------------->|
 |                |                     |
 |                | Show Results        |
 |                |-------------------->|
 |                |                     |
 | View Results   |                     |
 |<---------------|                     |
 |                |                     |
 | Export Chart   |                     |
 |--------------->|                     |
 |                | "Feature Coming     |
 |                |  Soon" Message      |
 |<---------------|                     |
 |                |                     |
```

## Vedic Chart Verification Flow - OpenAI Integration

```
User          Frontend            API Gateway          Chart Calculator    OpenAI Service
 |                |                   |                      |                     |
 |                |                   |                      |                     |
 | Submit Birth   |                   |                      |                     |
 | Details        |                   |                      |                     |
 |--------------->|                   |                      |                     |
 |                | POST /api/chart/generate                 |                     |
 |                | {verify_with_openai: true}               |                     |
 |                |------------------>|                      |                     |
 |                |                   | Calculate Initial    |                     |
 |                |                   | Chart                |                     |
 |                |                   |--------------------->|                     |
 |                |                   |                      |                     |
 |                |                   |                      | Initial Chart Data  |
 |                |                   |<---------------------|                     |
 |                |                   |                      |                     |
 |                |                   | Verify Chart         |                     |
 |                |                   | Against Indian       |                     |
 |                |                   | Vedic Standards      |                     |
 |                |                   |--------------------->|                     |
 |                |                   |                      | Verification        |
 |                |                   |                      | Request             |
 |                |                   |                      |-------------------->|
 |                |                   |                      |                     |
 |                |                   |                      |                     | Multi-technique
 |                |                   |                      |                     | Vedic Analysis
 |                |                   |                      |                     |----------------
 |                |                   |                      |                     |
 |                |                   |                      | Verification        |
 |                |                   |                      | Result              |
 |                |                   |                      |<--------------------|
 |                |                   |                      |                     |
 |                |                   |                      | Apply               |
 |                |                   |                      | Corrections         |
 |                |                   |                      | (if needed)         |
 |                |                   |                      |----------------     |
 |                |                   |                      |                     |
 |                |                   | Verified/Corrected   |                     |
 |                |                   | Chart Data           |                     |
 |                |                   |<---------------------|                     |
 |                | {chart_id: "...",                        |                     |
 |                |  verification: {  |                      |                     |
 |                |    verified: true,|                      |                     |
 |                |    confidence: 87,|                      |                     |
 |                |    corrections_applied: true|            |                     |
 |                |  }}               |                      |                     |
 |                |<------------------|                      |                     |
 |                |                   |                      |                     |
 | Display Chart  |                   |                      |                     |
 |<---------------|                   |                      |                     |
 |                |                   |                      |                     |
```

## Sequence Overview and Component Interactions

The sequence diagrams illustrate the complete flow of the Birth Time Rectifier application, showing both:

1. **Full Implementation** - The intended end-to-end flow with backend integration
2. **Simplified Flow** - The current implementation with mock services for testing
3. **Vedic Chart Verification Flow** - The specific OpenAI integration for chart verification

### Key Integration Points for OpenAI Verification

1. **Chart Calculator to OpenAI Service**:
   - After initial chart calculation, the Chart Calculator sends chart data to OpenAI Service
   - OpenAI validates the chart against Indian Vedic Astrological standards
   - Corrections are applied if needed and verification metadata is added to the chart

2. **Verification Data Structure**:
   - `verified`: Boolean indicating successful verification
   - `confidence_score`: Numeric score (0-100) indicating confidence level
   - `corrections_applied`: Boolean indicating whether corrections were applied
   - `message`: Human-readable message explaining verification results

3. **API Parameters**:
   - `verify_with_openai`: Boolean flag to control verification (defaults to true)
   - Allows for bypassing verification in development/testing scenarios

### Implementation Priorities

Based on the simplified sequence, the implementation priorities are:

1. **Client-Side Validation**: Robust validation for all form inputs with immediate feedback.

2. **Mock Data Services**: Simple data providers that simulate API responses without dependencies.

3. **Navigation Flow**: Ensure smooth transitions between form submission and results display.

4. **Error Boundaries**: Add proper error handling at key points to prevent blank screens.

5. **Fallback Content**: Provide graceful degradation when WebGL or other features fail.

This approach allows for testing the core user journey without requiring the full backend implementation, addressing the critical issues identified in User Testing Iteration 1.

## Component Interaction Map

The sequence diagram involves the following components, with their responsibilities and interactions:

### Frontend (FE)
- Initiates session on application load
- Collects user input for birth details
- Sends API requests for geocoding, validation, chart generation, and rectification
- Establishes WebSocket connection for real-time updates
- Renders chart and rectification results

### API Layer (API)
- Routes requests to appropriate backend services
- Validates session and authentication
- Returns formatted responses
- Establishes WebSocket connections

### Backend Services (BE)
- **Auth Service**: Creates and manages user sessions, validates authentication tokens
- **Chart Service**: Processes geocoding requests, validates birth details, generates charts
- **Rectification Service**: Processes birth time rectification, sends progress updates
- **Interpretation Service**: Generates chart interpretations and insights

### OpenAI Service
- Verifies charts against Indian Vedic Astrological standards
- Applies corrections to chart data when necessary
- Provides confidence scoring for verification
- Generates explanation of verification results

### Database (DB)
- Stores session data
- Persists user information
- Stores chart and rectification data
- Manages location data

## Detailed Implementation Steps

To implement this sequence diagram correctly, follow these detailed steps:

### 1. Session Initialization

1. **Create Session Service**
   - Implement `SessionService` in `ai_service/services/session_service.py`
   - Add Redis integration for session storage
   - Implement session creation, retrieval, and validation methods

2. **Add Session Initialization Endpoint**
   - Create `/api/session/init` endpoint in `ai_service/api/routers/session.py`
   - Generate unique session ID
   - Store initial session data in Redis
   - Return session token to frontend

3. **Frontend Session Integration**
   - Add session initialization on application load
   - Store session token in frontend state
   - Include session token in all subsequent API requests

### 2. Geocoding Implementation

1. **Create Geocoding Service**
   - Implement `GeocodingService` in `ai_service/services/geocoding_service.py`
   - Add integration with geocoding provider (e.g., Google Maps, OpenStreetMap)
   - Implement location search and retrieval methods

2. **Add Geocoding Endpoint**
   - Create `/api/geocode` endpoint in `ai_service/api/routers/geocoding.py`
   - Accept location query parameter
   - Return coordinates, timezone, and location details

3. **Frontend Geocoding Integration**
   - Implement location search in birth details form
   - Display location suggestions as user types
   - Store selected location data for chart generation

### 3. Chart Validation

1. **Create Validation Service**
   - Implement validation logic in `ai_service/services/chart_service.py`
   - Add methods to validate birth date, time, and location

2. **Add Validation Endpoint**
   - Create `/api/chart/validate` endpoint in `ai_service/api/routers/chart.py`
   - Accept birth details parameters
   - Return validation result with any errors

3. **Frontend Validation Integration**
   - Add client-side validation with API validation
   - Display validation errors to user
   - Enable chart generation only for valid details

### 4. Chart Generation with OpenAI Verification

1. **Enhance Chart Service**
   - Implement chart calculation logic in `ai_service/services/chart_service.py`
   - Add methods to calculate planetary positions, house cusps, and aspects
   - Create data models for chart components

2. **Implement OpenAI Verification**
   - Create `EnhancedChartCalculator` class with verification capabilities
   - Implement connection to OpenAI service
   - Add correction application logic for chart data
   - Add verification metadata to chart response

3. **Add Chart Generation Endpoint**
   - Create `/api/chart/generate` endpoint in `ai_service/api/routers/chart.py`
   - Accept birth details and options parameters including `verify_with_openai`
   - Validate session and user authentication
   - Return complete chart data with verification information

4. **Frontend Chart Integration**
   - Implement chart visualization component
   - Display planetary positions, houses, and aspects
   - Add visual indicators for verified/corrected chart elements
   - Add interactive elements for chart exploration

### 5. Rectification Process

1. **Create Rectification Service**
   - Implement `RectificationService` in `ai_service/services/rectification_service.py`
   - Add birth time rectification algorithms
   - Implement progress tracking and event handling

2. **Add Rectification Endpoint**
   - Create `/api/chart/rectify` endpoint in `ai_service/api/routers/chart.py`
   - Accept chart ID and options parameters
   - Validate session and user authentication
   - Return rectification result with confidence score

3. **Add WebSocket Support**
   - Implement WebSocket endpoint in `ai_service/api/websockets.py`
   - Create connection manager for client sessions
   - Add progress notification system

4. **Frontend Rectification Integration**
   - Implement rectification request UI
   - Establish WebSocket connection for progress updates
   - Display progress indicators during processing
   - Show rectified chart with confidence score

### 6. Chart Comparison

1. **Create Comparison Service**
   - Implement chart comparison logic in `ai_service/services/chart_service.py`
   - Add methods to detect differences between charts
   - Create data models for comparison results

2. **Add Comparison Endpoint**
   - Create `/api/chart/compare` endpoint in `ai_service/api/routers/chart.py`
   - Accept chart IDs for comparison
   - Return detailed comparison results

3. **Frontend Comparison Integration**
   - Implement comparison visualization
   - Highlight differences between original and rectified charts
   - Add toggle options for different comparison views

### 7. Interpretation Service

1. **Create Interpretation Service**
   - Implement `InterpretationService` in `ai_service/services/interpretation_service.py`
   - Add interpretation logic for planetary positions, aspects, and houses
   - Create synthesis engine for personalized interpretations

2. **Add Interpretation Endpoint**
   - Create `/api/interpretation` endpoint in `ai_service/api/routers/interpretation.py`
   - Accept chart ID parameter
   - Return detailed interpretation data

3. **Frontend Interpretation Integration**
   - Implement interpretation display component
   - Show personalized interpretations for chart elements
   - Add expandable sections for detailed information

## Testing Implementation

Testing this sequence flow follows a systematic approach:

1. **Unit Tests**
   - Test individual components like OpenAI service, chart calculator
   - Verify error handling and fallback mechanisms
   - Test dynamic model selection based on task type

2. **Integration Tests**
   - Test chart generation with and without OpenAI verification
   - Verify verification data structure in responses
   - Test correction application logic

3. **End-to-End Tests**
   - Test complete user flow from birth details to verification
   - Test the sequence via Playwright tests in `vedic-verification-flow.spec.js`
   - Use test script in `test_scripts/run-vedic-verification-test.sh`

4. **Visualization Tests**
   - Test rendering of verification indicators
   - Test display of correction information in the UI

This comprehensive testing approach ensures the OpenAI integration for Vedic chart verification works as expected throughout the application flow.
