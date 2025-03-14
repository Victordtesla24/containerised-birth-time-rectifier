/**
 * Simple Test Case for Birth Time Rectifier
 *
 * This file contains a basic test case that checks the API health
 * Run with: node test_case.js
 */

const fetch = require('node-fetch');

// Test configuration
const config = {
  apiUrl: 'http://localhost:8000',
  timeoutMs: 5000
};

// Simple test runner
async function runTest() {
  console.log('=== Birth Time Rectifier Simple Test ===\n');

  try {
    console.log('Testing API Health...');
    const healthResponse = await fetch(`${config.apiUrl}/health`, {
      method: 'GET',
      timeout: config.timeoutMs
    });

    if (healthResponse.ok) {
      const healthData = await healthResponse.json();
      console.log(`✅ API Health Check Passed: ${JSON.stringify(healthData)}`);
    } else {
      console.log(`❌ API Health Check Failed: Status ${healthResponse.status}`);
      process.exit(1);
    }

    console.log('\nTesting Geocoding API...');
    const geocodeResponse = await fetch(`${config.apiUrl}/api/v1/geocode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: 'London, UK' }),
      timeout: config.timeoutMs
    });

    if (geocodeResponse.ok) {
      const geocodeData = await geocodeResponse.json();
      console.log(`✅ Geocoding API Test Passed: ${JSON.stringify(geocodeData)}`);
    } else {
      console.log(`❌ Geocoding API Test Failed: Status ${geocodeResponse.status}`);
      process.exit(1);
    }

    console.log('\n=== All Tests Passed ===');
    process.exit(0);
  } catch (error) {
    console.error('Test Error:', error.message);
    process.exit(1);
  }
}

// Run the test
runTest();
