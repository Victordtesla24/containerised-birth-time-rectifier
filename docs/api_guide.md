# Birth Time Rectifier API Guide

## Introduction

The Birth Time Rectifier API allows developers to integrate astrological chart generation and birth time rectification capabilities into their own applications. This document provides detailed information about available endpoints, authentication, request/response formats, and examples.

## Base URL

All API endpoints are available at:

```
https://api.birthtimerectifier.com
```

## Authentication

API requests require authentication using an API key or OAuth2 token.

### API Key Authentication

Include your API key in the `X-API-Key` header:

```
X-API-Key: your_api_key_here
```

### OAuth2 Authentication

For authenticated user actions, use Bearer token authentication:

```
Authorization: Bearer your_access_token_here
```

To obtain an access token:

1. Make a POST request to `/api/auth/login`
2. Include the user's credentials
3. Store the returned access token

## Rate Limits

Free API accounts are limited to:
- 100 requests per day
- 10 requests per minute

Premium API accounts have higher limits:
- 1000 requests per day
- 60 requests per minute

Rate limit headers are included in all responses:
- `X-Rate-Limit-Limit`: Total allowed requests in period
- `X-Rate-Limit-Remaining`: Requests remaining in period
- `X-Rate-Limit-Reset`: Time in seconds until the rate limit resets

## API Endpoints

### Authentication

#### Login

```
POST /api/auth/login
```

Request body:
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_at": "2023-12-31T23:59:59Z",
  "user_id": "user123"
}
```

### Charts

#### Generate Chart

```
POST /api/charts
```

Request body:
```json
{
  "birthDate": "1990-01-01",
  "birthTime": "12:00",
  "birthPlace": "New York, NY",
  "name": "John Doe",
  "notes": "Example chart"
}
```

Response:
```json
{
  "id": "chart123",
  "birthDate": "1990-01-01",
  "birthTime": "12:00",
  "birthPlace": "New York, NY",
  "name": "John Doe",
  "notes": "Example chart",
  "ascendant": {
    "sign": "Taurus",
    "degree": 15.5
  },
  "planets": [
    {
      "planet": "Sun",
      "sign": "Capricorn",
      "degree": "10.5",
      "house": 9
    },
    // Additional planets...
  ],
  "houses": [
    {
      "number": 1,
      "sign": "Taurus",
      "startDegree": 15.5,
      "endDegree": 45.5
    },
    // Additional houses...
  ],
  "aspects": [
    {
      "planet1": "Sun",
      "planet2": "Moon",
      "aspectType": "trine",
      "orb": 2.3,
      "influence": "positive"
    },
    // Additional aspects...
  ]
}
```

#### Get Chart

```
GET /api/charts/{chart_id}
```

Response: Same as the Generate Chart response.

#### Update Chart

```
PUT /api/charts/{chart_id}
```

Request body:
```json
{
  "notes": "Updated notes",
  "tags": ["personal", "example"]
}
```

Response: Updated chart object.

#### Delete Chart

```
DELETE /api/charts/{chart_id}
```

Response:
```json
{
  "success": true
}
```

### Geocoding

#### Geocode Location

```
GET /api/geocoding/geocode?query={location_name}
```

Response:
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "timezone": "America/New_York"
}
```

### Questionnaire

#### Initialize Questionnaire

```
POST /api/questionnaire/initialize
```

Request body:
```json
{
  "birthDate": "1990-01-01",
  "birthTime": "12:00",
  "birthPlace": "New York, NY",
  "latitude": 40.7128,
  "longitude": -74.0060
}
```

Response:
```json
{
  "sessionId": "session123",
  "question": {
    "id": "q1",
    "text": "Do you know approximately what time of day you were born?",
    "type": "multiple_choice",
    "options": [
      {"id": "morning", "text": "Morning (6am-12pm)"},
      {"id": "afternoon", "text": "Afternoon (12pm-6pm)"},
      {"id": "evening", "text": "Evening (6pm-12am)"},
      {"id": "night", "text": "Night (12am-6am)"},
      {"id": "unknown", "text": "Unknown"}
    ]
  }
}
```

#### Submit Answer

```
POST /api/questionnaire/answer
```

Request body:
```json
{
  "sessionId": "session123",
  "questionId": "q1",
  "answer": "morning"
}
```

Response:
```json
{
  "nextQuestion": {
    "id": "q2",
    "text": "Have you experienced significant career changes around age 29-30?",
    "type": "yes_no"
  },
  "progress": 0.1,
  "remainingQuestions": 9
}
```

#### Analyze Questionnaire

```
POST /api/questionnaire/analyze
```

Request body:
```json
{
  "sessionId": "session123"
}
```

Response:
```json
{
  "rectifiedTime": "07:15",
  "confidence": 85.5,
  "reliability": "high",
  "alternativeTimes": [
    {
      "time": "08:30",
      "confidence": 75.2
    },
    {
      "time": "06:45",
      "confidence": 65.8
    }
  ],
  "details": {
    "ascendantSign": "Taurus",
    "ascendantDegree": 15.5,
    "technique": "AI-assisted analysis"
  }
}
```

## Error Handling

All API errors follow a standard format:

```json
{
  "detail": "Error message here",
  "code": "ERROR_CODE",
  "timestamp": "2023-01-01T12:00:00Z"
}
```

Common error codes:

- `AUTHENTICATION_ERROR`: Authentication failed
- `VALIDATION_ERROR`: Request validation failed
- `RATE_LIMIT_EXCEEDED`: Rate limit exceeded
- `RESOURCE_NOT_FOUND`: Requested resource not found
- `SERVER_ERROR`: Internal server error

## Webhooks

Premium API accounts can register webhooks to receive events for:

- Chart generation completion
- Rectification analysis completion
- User account events

To register a webhook:

```
POST /api/webhooks
```

Request body:
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["chart.created", "rectification.completed"],
  "secret": "your_webhook_secret"
}
```

## SDK Libraries

We provide official SDK libraries for:

- JavaScript/TypeScript: `npm install birthtimerectifier-js`
- Python: `pip install birthtimerectifier`
- PHP: `composer require birthtimerectifier/sdk`

## Example Code

### JavaScript Example

```javascript
const BirthTimeRectifier = require('birthtimerectifier-js');

const api = new BirthTimeRectifier('your_api_key');

// Generate a chart
async function generateChart() {
  try {
    const chart = await api.charts.create({
      birthDate: '1990-01-01',
      birthTime: '12:00',
      birthPlace: 'New York, NY',
      name: 'John Doe'
    });
    console.log(chart);
  } catch (error) {
    console.error('Error generating chart:', error);
  }
}

// Start a rectification process
async function startRectification() {
  try {
    const session = await api.questionnaire.initialize({
      birthDate: '1990-01-01',
      birthTime: '12:00',
      birthPlace: 'New York, NY'
    });

    console.log('First question:', session.question);

    // Answer the first question
    const nextQuestion = await api.questionnaire.answer({
      sessionId: session.sessionId,
      questionId: session.question.id,
      answer: 'morning'
    });

    console.log('Next question:', nextQuestion);

    // Continue with more questions...

  } catch (error) {
    console.error('Error in rectification process:', error);
  }
}
```

### Python Example

```python
from birthtimerectifier import BirthTimeRectifier

api = BirthTimeRectifier('your_api_key')

# Generate a chart
try:
    chart = api.charts.create(
        birth_date='1990-01-01',
        birth_time='12:00',
        birth_place='New York, NY',
        name='John Doe'
    )
    print(chart)
except Exception as e:
    print(f"Error generating chart: {e}")

# Geocode a location
try:
    location = api.geocoding.geocode('New York')
    print(f"Latitude: {location.latitude}, Longitude: {location.longitude}")
except Exception as e:
    print(f"Error geocoding: {e}")
```

## Support

If you encounter any issues or have questions about the API:

- Check the [Developer Documentation](https://developers.birthtimerectifier.com)
- Join our [Developer Community](https://community.birthtimerectifier.com)
- Email us at [api-support@birthtimerectifier.com](mailto:api-support@birthtimerectifier.com)

## Changelog

### v1.0.0 (2023-01-01)

- Initial API release

### v1.1.0 (2023-02-15)

- Added webhook support
- Improved rate limiting
- Added new chart customization options
