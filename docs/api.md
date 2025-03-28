# Birth Time Rectifier API Documentation

## Base URL
```
http://localhost:8000/api
```

## Authentication
Currently, no authentication is required for API access.

## Endpoints

### Questionnaire

#### Initialize Questionnaire
```
POST /questionnaire/initialize
```

Initializes a new questionnaire session for birth time rectification.

**Request Body:**
```json
{
  "birthDetails": {
    "birth_date": "1990-01-01",
    "birth_time": "12:00:00",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timezone": "America/New_York"
  },
  "chart_id": "chart_05fa8e00"
}
```

**Response:**
```json
{
  "session_id": "b5335e68-da6b-4504-ae0d-82b4238a52f9",
  "first_question": {
    "id": "q_birth_time_general",
    "text": "Do you know your approximate birth time?",
    "type": "multiple_choice",
    "options": [
      {"id": "opt_exact", "text": "Yes, I have an exact time"},
      {"id": "opt_approximate", "text": "I have an approximate time"},
      {"id": "opt_window", "text": "I know a time window (e.g., morning, afternoon)"},
      {"id": "opt_unknown", "text": "I don't know my birth time"}
    ]
  }
}
```

#### Submit Answer
```
POST /questionnaire/{session_id}/answer
```

Submits an answer to a questionnaire question.

**Request Body:**
```json
{
  "question_id": "q_birth_time_general",
  "answer": "opt_exact"
}
```

**Response:**
```json
{
  "success": true,
  "next_question": {
    "id": "q_major_life_events",
    "text": "Please list any major life events with their dates",
    "type": "text"
  }
}
```

#### Complete Questionnaire
```
POST /questionnaire/complete
```

Completes a questionnaire session and prepares for birth time rectification.

**Request Body:**
```json
{
  "session_id": "b5335e68-da6b-4504-ae0d-82b4238a52f9",
  "chart_id": "chart_05fa8e00"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "b5335e68-da6b-4504-ae0d-82b4238a52f9",
  "chart_id": "chart_05fa8e00",
  "completed": true,
  "questions_answered": 5,
  "rectification_ready": true
}
```

### Chart

#### Rectify Birth Time
```
POST /chart/rectify
```

Rectifies birth time based on questionnaire answers.

**Request Body:**
```json
{
  "chart_id": "chart_05fa8e00",
  "session_id": "b5335e68-da6b-4504-ae0d-82b4238a52f9",
  "confidence_threshold": 0.7
}
```

**Response:**
```json
{
  "success": true,
  "chart_id": "chart_05fa8e00",
  "original_birth_time": "12:00:00",
  "rectified_birth_time": "12:15:00",
  "adjustment_minutes": 15,
  "confidence_score": 85,
  "analysis": "Based on the questionnaire answers, the birth time has been adjusted..."
}
```

#### Get Chart
```
GET /chart/{chart_id}
```

Retrieves chart data by ID.

**Response:**
```json
{
  "chart_id": "chart_05fa8e00",
  "birth_details": {
    "birth_date": "1990-01-01",
    "birth_time": "12:00:00",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "timezone": "America/New_York"
  },
  "chart_data": {
    "planets": [...],
    "houses": [...],
    "aspects": [...]
  }
}
```

#### Compare Charts
```
GET /chart/compare?chart1={chart1_id}&chart2={chart2_id}
```

Compares two charts and returns key differences.

**Response:**
```json
{
  "chart1_id": "chart_05fa8e00",
  "chart2_id": "chart_05fa8e01",
  "differences": {
    "planets": [...],
    "houses": [...],
    "aspects": [...]
  },
  "analysis": "The main differences between these charts are..."
}
```

#### Export Chart
```
POST /chart/export
```

Exports a chart in the specified format.

**Request Body:**
```json
{
  "chart_id": "chart_05fa8e00",
  "format": "pdf"
}
```

**Response:**
Binary file data or a URL to download the exported file.

### Geocoding

#### Search Locations
```
GET /geocode?query={search_term}&limit={limit}&include_timezone={bool}
```

Searches for locations and returns coordinates and timezone information.

**Response:**
```json
{
  "results": [
    {
      "name": "New York, NY, USA",
      "latitude": 40.7128,
      "longitude": -74.0060,
      "timezone": "America/New_York",
      "country": "United States",
      "state": "New York"
    }
  ]
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "An unexpected error occurred"
}
```
