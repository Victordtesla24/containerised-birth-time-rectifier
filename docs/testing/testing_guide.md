# Comprehensive Testing Guide

This guide provides a comprehensive approach to testing the Birth Time Rectification application, covering UI/UX components, API integration, and system verification.

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [UI/UX Testing](#uiux-testing)
3. [API Integration Testing](#api-integration-testing)
4. [Setting Up Test Environment](#setting-up-test-environment)
5. [Running Tests](#running-tests)
6. [Interpreting Results](#interpreting-results)
7. [Troubleshooting](#troubleshooting)
8. [Implementation Verification Checklist](#implementation-verification-checklist)

## Testing Strategy

Our testing approach aims to verify and showcase the following aspects:

1. **Visual Quality**: Ensure all UI components render correctly with high visual fidelity
2. **Performance**: Verify smooth animations and efficient rendering
3. **Compatibility**: Ensure the application works across browsers and devices
4. **Interactivity**: Validate user interactions function correctly
5. **Accessibility**: Ensure the application is accessible to all users
6. **API Integration**: Verify that frontend-backend integration functions correctly
7. **Data Accuracy**: Ensure astrological calculations and rectifications are accurate

## UI/UX Testing

### Visual Regression Testing

These tests capture screenshots of key UI components and compare them against baseline images to detect unintended visual changes.

**Key aspects tested:**
- Correct rendering of celestial bodies
- Proper display of space effects (nebulas, stars)
- Responsive design across different screen sizes
- Consistent visual appearance

### Performance Testing

These tests measure the application's performance metrics to ensure smooth and efficient rendering.

**Key metrics measured:**
- Frame rates during animations (target: 30+ FPS)
- Initial load times (target: under 5 seconds)
- 3D scene initialization time (target: under 3 seconds)
- Memory usage stability during animations

### Compatibility Testing

These tests ensure the application works correctly across different browsers and devices.

**Key aspects tested:**
- Cross-browser functionality (Chrome, Firefox, Safari)
- Responsive design across different screen sizes
- WebGL capabilities and fallbacks
- Touch interactions on mobile devices

### Interaction Testing

These tests verify that user interactions work correctly.

**Key aspects tested:**
- Camera controls (rotation, zoom)
- Animation controls (play, pause)
- Form interactions (input validation, submission)
- Keyboard accessibility
- Color contrast for accessibility

### Visual Quality Testing

These tests verify the quality of shaders, materials, and visual effects.

**Key aspects tested:**
- Sun shader effects (corona, prominences, flares)
- Planet material quality (normal maps, specular highlights)
- Nebula particle effects
- Lighting and shadow quality
- Post-processing effects

## API Integration Testing

### API Router and Path Handling

**Key aspects tested:**
- Access endpoints with and without `/api` prefix
- Verify versioned endpoints (`/api/v1/...`)
- Confirm consistent behavior between equivalent endpoints
- Check router registration and OpenAPI documentation

### Session Management

**Key aspects tested:**
- Session initialization and retrieval
- Session persistence across requests
- Session data storage and update
- Session timeout and expiration
- Redis integration and fallback behavior

### Chart Comparison Service

**Key aspects tested:**
- Comparison of identical and different charts
- Detection of ascendant shifts and planetary house transitions
- Aspect formation and dissolution
- Significance scoring of differences
- Different comparison types and options

### Error Handling

**Key aspects tested:**
- Validation errors and appropriate responses
- HTTP exceptions and standardized error format
- Custom error responses with domain-specific error codes
- Error detail inclusion and security considerations

### End-to-End Workflows

**Key aspects tested:**
- Complete user flows from session creation to chart comparison
- Rectification process and results
- Performance under load
- Backward compatibility with existing clients

## Setting Up Test Environment

To set up the testing environment:

1. Run the setup script:

```bash
./setup-test-dependencies.sh
```

This script will:
- Install necessary dependencies
- Create test directories
- Set up test pages for component testing
- Update package.json scripts
- Install Playwright browsers

2. Make sure your development server is running:

```bash
npm run dev
```

3. Configure environment variables for API testing:

```bash
cp .env.test.example .env.test
# Edit .env.test with appropriate values
```

## Running Tests

You can run individual test categories or all tests at once:

### UI/UX Tests

```bash
# Run all UI/UX tests and generate a comprehensive report
npm run test:ui:all

# Run individual test categories
npm run test:ui:visual       # Visual regression tests
npm run test:ui:performance  # Performance tests
npm run test:ui:interaction  # Interaction tests
npm run test:ui:compatibility # Compatibility tests
npm run test:ui:quality      # Visual quality tests
```

### API Tests

```bash
# Run all API tests
npm run test:api:all

# Run individual API test categories
npm run test:api:router      # API router tests
npm run test:api:session     # Session management tests
npm run test:api:chart       # Chart generation and comparison tests
npm run test:api:errors      # Error handling tests
npm run test:api:e2e         # End-to-end workflow tests
```

### System Tests

```bash
# Run complete system tests
npm run test:system
```

## Interpreting Results

After running the tests, a comprehensive HTML report will be generated at `test-results/report.html`. You can open it with:

```bash
npm run test:report
```

The report includes:
- Overall test results summary
- Detailed results for each test category
- Visual evidence (screenshots and videos)
- Performance metrics
- API response validation

### Key Metrics to Look For

- **Visual Regression**: All screenshots should match baseline images
- **Performance**:
  - Frame rates should be above 30 FPS
  - Load times should be under 5 seconds
  - API response times should be within acceptable limits
- **Interaction**: All user interactions should work correctly
- **Compatibility**: Application should work in all tested browsers and devices
- **Visual Quality**: All visual effects should render at high quality
- **API Integration**: All API endpoints should return correct responses

## Troubleshooting

### Common Issues

1. **Tests fail due to visual differences**
   - Check if the differences are intentional (due to UI improvements)
   - If intentional, update the baseline images with `npx playwright test --update-snapshots`

2. **Performance tests fail**
   - Check if hardware acceleration is enabled in your browser
   - Close other resource-intensive applications
   - Try running tests on a more powerful machine

3. **WebGL-related failures**
   - Ensure your graphics drivers are up to date
   - Check if WebGL is enabled in your browser
   - Try a different browser

4. **API tests fail**
   - Check if the API server is running
   - Verify environment variables are set correctly
   - Check for network connectivity issues
   - Review server logs for errors

### Debugging Tests

To debug tests:

```bash
# Run UI tests in debug mode
npx playwright test --debug

# Run UI tests with UI mode
npx playwright test --ui

# Debug API tests
npm run test:api:debug
```

## Implementation Verification Checklist

Use this checklist to verify the implementation of key features.

### API Router and Path Handling

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Access endpoint without `/api` prefix | Request should be handled correctly | ⬜ |
| Access versioned endpoint | Request should return the same response as above | ⬜ |
| Access custom endpoint with parameters | Both prefixed and non-prefixed should return identical responses | ⬜ |
| Check router registration | All routers should be registered once in the log | ⬜ |
| Verify endpoint discovery | All endpoints should be properly documented with prefixes | ⬜ |

### Session Management

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Initialize new session | Response should include `session_id` and metadata | ⬜ |
| Check session status | Response should include session details and expiration | ⬜ |
| Update session data | Session data should be updated and reflected in status | ⬜ |
| Verify session cookie | Response should set a session cookie with appropriate parameters | ⬜ |
| Test session persistence | Server should recognize the existing session | ⬜ |
| Test session timeout | Session should expire and return not found | ⬜ |
| Check Redis storage | Session data should be stored in Redis with TTL | ⬜ |
| Test fallback behavior | Server should log fallback to in-memory store | ⬜ |

### Chart Comparison

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Compare identical charts | Response should indicate no significant differences | ⬜ |
| Compare different charts | Response should list differences between charts | ⬜ |
| Detect ascendant shifts | Response should include ascendant shift with significance | ⬜ |
| Detect house transitions | Response should include planet house transitions | ⬜ |
| Test aspect detection | Response should include aspects that formed or dissolved | ⬜ |
| Test different comparison types | Results should match the requested comparison type | ⬜ |
| Test POST endpoint | Both should return equivalent results | ⬜ |
| Test significance scoring | Differences should include significance scores | ⬜ |

### Error Handling

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Missing required field | Should return 422 with standardized error format | ⬜ |
| Invalid data type | Should return 422 with descriptive error | ⬜ |
| Multiple validation errors | Should return all validation errors in details array | ⬜ |
| Resource not found | Should return 404 with standardized error format | ⬜ |
| Unauthorized access | Should return 401 with standardized format | ⬜ |
| Server error | Should return 500 with generic error message | ⬜ |
| API-specific error | Should return appropriate status code with domain-specific error | ⬜ |
| Error with details | Error should include details field with additional information | ⬜ |

### Integration Testing

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| Session and chart generation | Complete flow should work without errors | ⬜ |
| Rectification and comparison | Flow should complete with meaningful comparison | ⬜ |
| Response time | Response times should be within acceptable limits | ⬜ |
| Concurrent requests | All requests should be handled without errors | ⬜ |
| Legacy client simulation | Old request patterns should still work correctly | ⬜ |
| Data format compatibility | Responses should maintain compatibility with existing clients | ⬜ |

### Documentation Verification

| Test Case | Expected Result | Status |
|-----------|-----------------|--------|
| OpenAPI documentation | All endpoints should be properly documented | ⬜ |
| API examples | Examples should work as documented | ⬜ |
| Error documentation | Error format should match documentation | ⬜ |

## Requirements for Sign-off

- All critical tests (API Router, Session Management, Chart Comparison) must pass
- At least 90% of all tests must pass
- Any failed tests must have documented workarounds or mitigation plans
- Performance tests must show acceptable response times under load
