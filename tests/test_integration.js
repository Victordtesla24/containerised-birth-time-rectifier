/**
 * Birth Time Rectifier Integration Test
 * 
 * This script tests the integration between the frontend and backend
 * using the test data: DOB: 24/10/1985, Time: 02:30 PM, Place: Pune, India
 */

const axios = require('axios');

// Test data
const testData = {
  birthDate: "1985-10-24T00:00:00",
  birthTime: "14:30", // 2:30 PM in 24h format
  birthPlace: "Pune, India",
  latitude: 18.5204,
  longitude: 73.8567,
  timezone: "Asia/Kolkata"
};

// API base URL
const API_URL = 'http://localhost:8000/api';

async function runTests() {
  console.log('🧪 Running Birth Time Rectifier Integration Tests 🧪');
  console.log('Test Data:', JSON.stringify(testData, null, 2));
  console.log('---------------------------------------------------');
  
  try {
    // Test 1: Geocoding API
    console.log('✅ Testing Geocoding API...');
    const geocodeResponse = await axios.post(`${API_URL}/geocode`, {
      place: testData.birthPlace
    });
    console.log('  Geocoding Response:', JSON.stringify(geocodeResponse.data, null, 2));
    
    // Test 2: Charts API
    console.log('✅ Testing Charts API...');
    const chartsResponse = await axios.post(`${API_URL}/charts`, {
      birthDate: testData.birthDate,
      birthTime: testData.birthTime,
      latitude: testData.latitude,
      longitude: testData.longitude,
      timezone: testData.timezone,
      chartType: 'ALL'
    });
    console.log('  Charts API Success! Response includes:');
    console.log(`  - D1 Chart: ${chartsResponse.data.d1Chart ? 'Present' : 'Missing'}`);
    console.log(`  - D9 Chart: ${chartsResponse.data.d9Chart ? 'Present' : 'Missing'}`);
    
    // Test 3: Questionnaire API
    console.log('✅ Testing Questionnaire Initialization API...');
    const initResponse = await axios.post(`${API_URL}/initialize-questionnaire`, {
      birthDate: testData.birthDate,
      birthTime: testData.birthTime,
      birthPlace: testData.birthPlace,
      latitude: testData.latitude,
      longitude: testData.longitude,
      timezone: testData.timezone
    });
    console.log('  Questionnaire Initialized!');
    console.log(`  - Session ID: ${initResponse.data.sessionId}`);
    console.log(`  - Initial Confidence: ${initResponse.data.confidence}%`);
    
    // Overall result
    console.log('---------------------------------------------------');
    console.log('🎉 All Integration Tests Passed! 🎉');
    
  } catch (error) {
    console.error('❌ Test Failed!');
    console.error('Error:', error.message);
    
    if (error.response) {
      console.error('Response Status:', error.response.status);
      console.error('Response Data:', JSON.stringify(error.response.data, null, 2));
    }
  }
}

// Run the tests
runTests(); 