/**
 * Simple Health Check for Birth Time Rectifier
 */

const fetch = require('node-fetch');

// Services to check
const services = [
  { name: 'Backend API', url: 'http://localhost:8000/health', method: 'GET' },
  { name: 'Frontend', url: 'http://localhost:3000', method: 'GET' },
  { name: 'Geocoding API', url: 'http://localhost:8000/api/geocode', method: 'POST', 
    body: JSON.stringify({ place: 'London, UK' }) },
  { name: 'Initialize Questionnaire API', url: 'http://localhost:8000/api/initialize-questionnaire', method: 'POST',
    body: JSON.stringify({
      birthDate: '1990-01-01',
      birthTime: '12:00',
      birthPlace: 'London, UK',
      latitude: 51.5074,
      longitude: -0.1278,
      timezone: 'Europe/London'
    })
  }
];

async function checkHealth() {
  console.log('=== Birth Time Rectifier Health Check ===');
  console.log(`Time: ${new Date().toISOString()}\n`);
  
  let allHealthy = true;
  
  for (const service of services) {
    try {
      const options = { 
        method: service.method,
        headers: { 'Content-Type': 'application/json' }
      };
      
      if (service.body) {
        options.body = service.body;
      }
      
      const startTime = Date.now();
      const response = await fetch(service.url, options);
      const responseTime = Date.now() - startTime;
      
      const healthy = response.status >= 200 && response.status < 300;
      if (!healthy) allHealthy = false;
      
      console.log(`${service.name} (${service.url}):`);
      console.log(`  Status: ${response.status} ${response.statusText}`);
      console.log(`  Healthy: ${healthy ? '✅ YES' : '❌ NO'}`);
      console.log(`  Response Time: ${responseTime}ms`);
      
      if (response.headers.get('content-type')?.includes('application/json')) {
        const data = await response.json();
        console.log(`  Response: ${JSON.stringify(data).substring(0, 100)}${JSON.stringify(data).length > 100 ? '...' : ''}`);
      }
      
      console.log('');
    } catch (error) {
      allHealthy = false;
      console.log(`${service.name} (${service.url}):`);
      console.log(`  Status: ERROR`);
      console.log(`  Healthy: ❌ NO`);
      console.log(`  Error: ${error.message}`);
      console.log('');
    }
  }
  
  console.log(`Overall Health: ${allHealthy ? '✅ HEALTHY' : '❌ ISSUES DETECTED'}`);
  return allHealthy;
}

// Run the health check and log the output
console.log("Starting health check...");
checkHealth()
  .then(healthy => {
    console.log(`Health check complete. System is ${healthy ? 'healthy' : 'unhealthy'}.`);
    process.exit(healthy ? 0 : 1);
  })
  .catch(error => {
    console.error('Error running health check:', error);
    process.exit(1);
  }); 