/**
 * API Endpoint Validator
 *
 * This script verifies the API endpoints for the Birth Time Rectifier application
 * according to the dual-registration pattern. It checks both primary (with /api/ prefix)
 * and alternative (without prefix) endpoints.
 *
 * Usage:
 *   node endpoint-validator.js [options]
 *
 * Options:
 *   --host, -h  Host to test (default: "http://localhost:3000")
 *   --verbose   Show detailed output
 *
 * Example:
 *   node endpoint-validator.js --host http://localhost:3000 --verbose
 */

const http = require('http');
const https = require('https');

// CLI arguments
const args = process.argv.slice(2);
let host = 'http://localhost:3000';
let verbose = false;

// Parse arguments
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--host' || args[i] === '-h') {
    host = args[i + 1];
    i++;
  } else if (args[i] === '--verbose') {
    verbose = true;
  }
}

// Remove trailing slash if present
if (host.endsWith('/')) {
  host = host.slice(0, -1);
}

console.log(`\nAPI Endpoint Validator`);
console.log(`Testing host: ${host}`);
console.log('Verifying dual-registration pattern...\n');

// Endpoints to test based on the dual-registration pattern
const endpointsToTest = [
  // Primary endpoints (with /api/ prefix)
  { method: 'GET', path: '/api/health', isPrimary: true },
  { method: 'POST', path: '/api/chart/validate', isPrimary: true },
  { method: 'GET', path: '/api/geocode', isPrimary: true },
  { method: 'POST', path: '/api/chart/generate', isPrimary: true },
  { method: 'GET', path: '/api/chart/dummy-id', isPrimary: true },
  { method: 'GET', path: '/api/questionnaire', isPrimary: true },
  { method: 'POST', path: '/api/chart/rectify', isPrimary: true },
  { method: 'POST', path: '/api/chart/export', isPrimary: true },

  // Alternative endpoints (without /api/ prefix)
  { method: 'GET', path: '/health', isPrimary: false },
  { method: 'POST', path: '/chart/validate', isPrimary: false },
  { method: 'GET', path: '/geocode', isPrimary: false },
  { method: 'POST', path: '/chart/generate', isPrimary: false },
  { method: 'GET', path: '/chart/dummy-id', isPrimary: false },
  { method: 'GET', path: '/questionnaire', isPrimary: false },
  { method: 'POST', path: '/chart/rectify', isPrimary: false },
  { method: 'POST', path: '/chart/export', isPrimary: false }
];

// Track results
const results = {};
let totalTested = 0;
let totalSuccessful = 0;
let primarySuccessful = 0;
let alternativeSuccessful = 0;

// Test a single endpoint
async function testEndpoint(endpoint) {
  return new Promise((resolve) => {
    const url = new URL(host + endpoint.path);
    const client = url.protocol === 'https:' ? https : http;

    const options = {
      method: endpoint.method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      }
    };

    // Add minimal payload for POST requests
    let postData = null;
    if (endpoint.method === 'POST') {
      postData = JSON.stringify({});
      options.headers['Content-Length'] = Buffer.byteLength(postData);
    }

    if (verbose) {
      console.log(`Testing ${endpoint.method} ${endpoint.path}...`);
    }

    // Make the request
    const req = client.request(url, options, (res) => {
      let data = '';

      res.on('data', (chunk) => {
        data += chunk;
      });

      res.on('end', () => {
        const status = res.statusCode;
        // Consider 200, 400, 401, 403, 404, 422 as "available" endpoints
        const isAvailable = [200, 400, 401, 403, 404, 422].includes(status);

        const result = {
          status,
          isAvailable,
          isPrimary: endpoint.isPrimary
        };

        // Extract key name from path
        let keyName = endpoint.path;
        if (keyName.includes('/api/')) {
          keyName = keyName.replace('/api/', '');
        } else if (keyName.startsWith('/')) {
          keyName = keyName.substring(1);
        }
        // Replace dummy-id with {id}
        keyName = keyName.replace('dummy-id', '{id}');

        // Store result
        results[keyName] = {
          ...(results[keyName] || {}),
          [endpoint.isPrimary ? 'primary' : 'alternative']: result
        };

        if (isAvailable) {
          totalSuccessful++;
          if (endpoint.isPrimary) {
            primarySuccessful++;
          } else {
            alternativeSuccessful++;
          }
        }

        if (verbose) {
          console.log(`  ${isAvailable ? '✓' : '✗'} ${status} ${endpoint.isPrimary ? 'Primary' : 'Alternative'} ${endpoint.path}`);
        }

        resolve(result);
      });
    });

    req.on('error', (error) => {
      if (verbose) {
        console.log(`  ✗ Error: ${error.message}`);
      }

      // Extract key name from path
      let keyName = endpoint.path;
      if (keyName.includes('/api/')) {
        keyName = keyName.replace('/api/', '');
      } else if (keyName.startsWith('/')) {
        keyName = keyName.substring(1);
      }
      // Replace dummy-id with {id}
      keyName = keyName.replace('dummy-id', '{id}');

      // Store result
      results[keyName] = {
        ...(results[keyName] || {}),
        [endpoint.isPrimary ? 'primary' : 'alternative']: {
          status: 0,
          isAvailable: false,
          isPrimary: endpoint.isPrimary
        }
      };

      resolve({ status: 0, isAvailable: false });
    });

    // Send POST data if needed
    if (postData) {
      req.write(postData);
    }

    req.end();
  });
}

// Test all endpoints
async function testAllEndpoints() {
  for (const endpoint of endpointsToTest) {
    await testEndpoint(endpoint);
    totalTested++;
  }

  // Output results
  console.log('\nEndpoint Test Results:');
  console.log(`Total endpoints tested: ${totalTested}`);
  console.log(`Total successful: ${totalSuccessful}/${totalTested}`);
  console.log(`Primary endpoints: ${primarySuccessful}/${totalTested/2}`);
  console.log(`Alternative endpoints: ${alternativeSuccessful}/${totalTested/2}`);

  // Determine if the dual-registration pattern is supported
  const dualRegistrationSupported = primarySuccessful > 0 && alternativeSuccessful > 0;
  console.log(`\nDual-registration pattern: ${dualRegistrationSupported ? 'Supported ✓' : 'Not fully supported ✗'}`);

  // Detailed results
  if (verbose) {
    console.log('\nDetailed Results:');
    Object.entries(results).forEach(([path, result]) => {
      const primaryStatus = result.primary?.status || 'N/A';
      const alternativeStatus = result.alternative?.status || 'N/A';
      console.log(`${path}: Primary: ${primaryStatus}, Alternative: ${alternativeStatus}`);
    });
  }

  // Generate recommended constants.js configuration
  console.log('\nRecommended constants.js Configuration:');
  console.log(`
export const API_ENDPOINTS = {
    // Primary endpoints (with /api/ prefix)${Object.entries(results)
    .filter(([_, result]) => result.primary?.isAvailable)
    .map(([path, _]) => {
      const camelCaseName = path.replace(/\//g, '_').replace(/[{}]/g, '').replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      const apiPath = path.includes('chart/') ? `/api/${path}` : `/api/${path}`;
      return `\n    ${camelCaseName}: '${apiPath}',`;
    }).join('')}

    // Alternative endpoints without /api/ prefix (for backward compatibility)${Object.entries(results)
    .filter(([_, result]) => result.alternative?.isAvailable)
    .map(([path, _]) => {
      const camelCaseName = path.replace(/\//g, '_').replace(/[{}]/g, '').replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
      return `\n    ${camelCaseName}Alt: '/${path}',`;
    }).join('')}
};
  `);
}

testAllEndpoints();
