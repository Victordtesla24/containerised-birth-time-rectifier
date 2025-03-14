/**
 * API Integration Tests for Birth Time Rectifier
 *
 * This file contains test functions to validate API endpoints and functionality.
 * Run with Node.js: node tests/api_tests.js
 */

const fetch = require('node-fetch');

// Configuration
const config = {
  apiBaseUrl: 'http://localhost:8000',
  frontendBaseUrl: 'http://localhost:3000',
  testTimeout: 5000, // 5 seconds
};

// Track test failures
let testFailures = 0;

// Test utilities
const testUtils = {
  async testEndpoint(name, url, options = {}) {
    console.log(`Testing ${name}...`);
    try {
      const response = await fetch(url, options);
      const data = await response.json();

      if (response.ok) {
        console.log(`✅ ${name}: Success! Status: ${response.status}`);
        return { success: true, data };
      } else {
        console.log(`❌ ${name}: Failed! Status: ${response.status}, Message: ${data.detail || JSON.stringify(data)}`);
        testFailures++;
        return { success: false, error: data, status: response.status };
      }
    } catch (error) {
      console.log(`❌ ${name}: Error! ${error.message}`);
      testFailures++;
      return { success: false, error: error.message };
    }
  },

  async testFrontendPage(name, url) {
    console.log(`Testing frontend page ${name}...`);
    try {
      const response = await fetch(url);
      const html = await response.text();

      if (response.ok && html.includes('</html>')) {
        console.log(`✅ ${name}: Page loaded successfully! Status: ${response.status}`);
        return { success: true };
      } else {
        console.log(`❌ ${name}: Page failed to load! Status: ${response.status}`);
        testFailures++;
        return { success: false, status: response.status };
      }
    } catch (error) {
      console.log(`❌ ${name}: Error! ${error.message}`);
      testFailures++;
      return { success: false, error: error.message };
    }
  }
};

// Test Cases
async function runTests() {
  console.log('=== Birth Time Rectifier API Tests ===\n');

  // 1. Test API Health
  await testUtils.testEndpoint(
    'API Health Check',
    `${config.apiBaseUrl}/health`
  );

  // 2. Test Geocoding API
  await testUtils.testEndpoint(
    'Geocoding API',
    `${config.apiBaseUrl}/api/v1/geocode`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'London, UK' })
    }
  );

  // 3. Test Initialize Questionnaire API
  const initResult = await testUtils.testEndpoint(
    'Initialize Questionnaire API',
    `${config.apiBaseUrl}/api/v1/questionnaire/initialize`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        birth_details: {
          date: '1990-01-01',
          time: '12:00',
          location: 'London, UK',
          latitude: 51.5074,
          longitude: -0.1278,
          timezone: 'Europe/London'
        }
      })
    }
  );

  let sessionId;
  if (initResult.success && initResult.data && initResult.data.session_id) {
    sessionId = initResult.data.session_id;
    console.log(`Session ID: ${sessionId}`);

    // 4. Test Answer Question API (only if we have a session ID)
    await testUtils.testEndpoint(
      'Next Question API',
      `${config.apiBaseUrl}/api/v1/questionnaire/answer`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          birth_details: {
            date: '1990-01-01',
            time: '12:00',
            location: 'London, UK',
            latitude: 51.5074,
            longitude: -0.1278,
            timezone: 'Europe/London'
          },
          previous_answers: [],
          answer: {
            question_id: "q_001",
            text: "yes"
          }
        })
      }
    );

    // 5. Test Analysis API
    await testUtils.testEndpoint(
      'Analysis API',
      `${config.apiBaseUrl}/api/v1/questionnaire/analyze?session_id=${sessionId}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId
        })
      }
    );
  }

  // 6. Test Chart API
  await testUtils.testEndpoint(
    'Chart API',
    `${config.apiBaseUrl}/api/v1/chart/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        birth_details: {
          date: '1990-01-01',
          time: '12:00',
          location: 'London, UK',
          latitude: 51.5074,
          longitude: -0.1278,
          timezone: 'Europe/London'
        }
      })
    }
  );

  // 7. Test Frontend Pages
  await testUtils.testFrontendPage('Home Page', config.frontendBaseUrl);
  await testUtils.testFrontendPage('Birth Details Page', `${config.frontendBaseUrl}/birth-details`);
  await testUtils.testFrontendPage('Questionnaire Page', `${config.frontendBaseUrl}/questionnaire`);

  console.log('\n=== Tests Completed ===');

  // Report overall test status
  if (testFailures > 0) {
    console.log(`\n❌ TESTS FAILED: ${testFailures} test(s) reported failures`);
    process.exit(1); // Exit with error code
  } else {
    console.log('\n✅ ALL TESTS PASSED');
    process.exit(0); // Exit with success code
  }
}

// Run tests
runTests();
