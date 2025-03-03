# Birth Time Rectifier - Application Flow

## Overview

The Birth Time Rectifier is a comprehensive web application that uses AI and Vedic astrological principles to determine a person's accurate birth time. This document outlines the application flow, key components, and testing procedures.

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

### 2. Questionnaire
- System initializes a personalized questionnaire based on birth details
- User answers questions about life events, personality traits, etc.
- Each response refines the birth time calculation
- Confidence score increases with each answer

### 3. Analysis
- When confidence reaches a threshold, final analysis is performed
- Rectified birth time is calculated based on questionnaire responses
- Astrological chart is generated using the rectified time
- Interpretations are provided for key chart elements

## Testing the Application

### Automated Tests
1. Install test dependencies:
   ```
   cd tests
   npm install
   ```

2. Run the tests:
   ```
   npm test
   ```

### Manual Testing
1. Start all services:
   ```
   ./start.sh
   ```

2. Test full flow:
   - Open the frontend URL (typically http://localhost:3004)
   - Complete the birth details form with test data
     - Example: "Jan 1, 1990, 12:00 PM, London, UK"
   - Navigate through the questionnaire
   - Verify the analysis results

## Error Handling & Fallbacks

The application implements several fallback mechanisms:

1. **API Communication**
   - Retries with alternate endpoints if primary endpoint fails
   - Multiple backoff attempts for transient failures

2. **Geocoding Service**
   - Local fallbacks for common locations
   - Graceful degradation with approximate coordinates

3. **Chart Generation**
   - Simple chart placeholder if full chart cannot be generated
   - Text-based interpretations as backup

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