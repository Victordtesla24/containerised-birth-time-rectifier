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
        return { success: false, error: data, status: response.status };
      }
    } catch (error) {
      console.log(`❌ ${name}: Error! ${error.message}`);
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
        return { success: false, status: response.status };
      }
    } catch (error) {
      console.log(`❌ ${name}: Error! ${error.message}`);
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
    `${config.apiBaseUrl}/api/geocoding`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ place: 'London, UK' })
    }
  );

  // 3. Test Initialize Questionnaire API
  const initResult = await testUtils.testEndpoint(
    'Initialize Questionnaire API',
    `${config.apiBaseUrl}/api/questionnaire/initialize`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        birthDate: '1990-01-01',
        birthTime: '12:00',
        birthPlace: 'London, UK',
        latitude: 51.5074,
        longitude: -0.1278,
        timezone: 'Europe/London'
      })
    }
  );

  let sessionId;
  if (initResult.success && initResult.data && initResult.data.sessionId) {
    sessionId = initResult.data.sessionId;
    console.log(`Session ID: ${sessionId}`);

    // 4. Test Next Question API (only if we have a session ID)
    await testUtils.testEndpoint(
      'Next Question API',
      `${config.apiBaseUrl}/api/questionnaire/next-question`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          sessionId: sessionId,
          response: {
            questionId: "initial", // Use a placeholder ID for the first question
            answer: "yes"          // Provide a default answer
          }
        })
      }
    );

    // 5. Test Analysis API
    await testUtils.testEndpoint(
      'Analysis API',
      `${config.apiBaseUrl}/api/charts/analysis?sessionId=${sessionId}`
    );
  }

  // 6. Test Chart API
  await testUtils.testEndpoint(
    'Chart API',
    `${config.apiBaseUrl}/api/charts`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        birthDate: '1990-01-01',
        birthTime: '12:00',
        latitude: 51.5074,
        longitude: -0.1278,
        timezone: 'Europe/London',
        chartType: 'd1'
      })
    }
  );

  // 7. Test Frontend Pages
  await testUtils.testFrontendPage('Home Page', config.frontendBaseUrl);
  await testUtils.testFrontendPage('Birth Details Page', `${config.frontendBaseUrl}/birth-details`);
  await testUtils.testFrontendPage('Questionnaire Page', `${config.frontendBaseUrl}/questionnaire`);

  console.log('\n=== Tests Completed ===');
}

// Run tests
runTests();
