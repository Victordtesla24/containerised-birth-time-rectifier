# API Gateway Implementation Plan

This document outlines a structured approach to build an advanced, scalable API Gateway for a Node.js project (using Cursor AI Editor on MacBook Air M3). It adheres to CI/CD best practices, industry standards, and integrates with Vercel deployment via GitHub. Key areas include architecture design, CI/CD pipeline, containerization, automation scripts, testing, environment/secrets management, and UI/UX considerations.

## How to Use This Document

This plan is structured to be implementable by both human developers and AI models. Each section follows a consistent format:

1. **Concept Overview**: Explains what the component is and why it's important
2. **Implementation Tasks**: Explicit, numbered tasks with specific steps
3. **Decision Points**: Clear options with selection criteria when implementation choices exist
4. **Verification Steps**: How to confirm successful implementation

## Implementation Progress Tracker

- [ ] Phase 1: API Gateway Architecture
  - [ ] Task 1.1: Select and Configure Web Framework
  - [ ] Task 1.2: Implement Authentication & Authorization Middleware
  - [ ] Task 1.3: Implement Rate Limiting
  - [ ] Task 1.4: Implement Logging
  - [ ] Task 1.5: Implement Caching Strategy
  - [ ] Task 1.6: Implement Load Balancing & Scalability
  - [ ] Task 1.7: Implement Security Measures
  - [ ] Task 1.8: Implement Monitoring & Resilience
- [ ] Phase 2: CI/CD Pipeline Setup
- [ ] Phase 3: Docker & Containerization
- [ ] Phase 4: Shell Scripts for Automation
- [ ] Phase 5: Testing & Best Practices
- [ ] Phase 6: Environment & Secrets Management
- [ ] Phase 7: UI/UX Considerations
- [ ] Phase 8: Environment Maintenance Scripts

## Table of Contents

- [Phase 1: API Gateway Architecture](#phase-1-api-gateway-architecture)
- [Phase 2: CI/CD Pipeline Setup](#phase-2-cicd-pipeline-setup)
- [Phase 3: Docker & Containerization](#phase-3-docker--containerization)
- [Phase 4: Shell Scripts for Automation](#phase-4-shell-scripts-for-automation)
- [Phase 5: Testing & Best Practices](#phase-5-testing--best-practices)
- [Phase 6: Environment & Secrets Management](#phase-6-environment--secrets-management)
- [Phase 7: UI/UX Considerations](#phase-7-uiux-considerations)
- [Phase 8: Environment Maintenance Scripts](#phase-8-environment-maintenance-scripts)

## Phase 1: API Gateway Architecture

### Concept Overview

The API Gateway serves as the single entry point for all clients, enforcing centralized security (authentication/authorization) and handling intelligent routing to backend services. It must be designed to be stateless and easily scalable horizontally.

Key architectural principles include:
- Leveraging Node.js's event-driven model for non-blocking I/O
- Offloading heavy work to worker threads or microservices
- Running multiple instances behind a load balancer for high traffic

### Task 1.1: Select and Configure Web Framework

**Purpose**: Establish the foundation for building the API Gateway.

**Dependencies**:
- Node.js (v16+ recommended)
- npm or yarn package manager

**Decision Point**: Choose a Node.js web framework

**Options**:
1. **Express.js**
   - Pros: Widely used, extensive middleware ecosystem, mature documentation
   - Cons: Slightly lower performance than newer alternatives
   - Recommended when: Familiarity and middleware availability are priorities

2. **Fastify**
   - Pros: Higher performance, built-in validation, more modern design
   - Cons: Smaller ecosystem than Express
   - Recommended when: Raw performance is critical

**Implementation Steps**:

1. Initialize project and install dependencies:
   ```bash
   mkdir -p api-gateway/src
   cd api-gateway
   npm init -y
   # For Express option
   npm install express helmet compression cors
   # For Fastify option
   # npm install fastify @fastify/helmet @fastify/compress @fastify/cors
   ```

2. Create the base server file:

   **File**: `src/server.js` (Express implementation)
   ```javascript
   const express = require('express');
   const helmet = require('helmet');
   const compression = require('compression');
   const cors = require('cors');

   // Initialize app
   const app = express();
   const PORT = process.env.PORT || 3000;

   // Apply essential middleware
   app.use(helmet()); // Security headers
   app.use(compression()); // Response compression
   app.use(cors()); // Enable CORS
   app.use(express.json({ limit: '1mb' })); // Parse JSON with size limit

   // Basic health check
   app.get('/healthz', (req, res) => {
     res.status(200).json({ status: 'ok' });
   });

   // Start server
   const server = app.listen(PORT, () => {
     console.log(`API Gateway running on port ${PORT}`);
   });

   // Graceful shutdown
   process.on('SIGTERM', () => {
     console.log('SIGTERM signal received: closing HTTP server');
     server.close(() => {
       console.log('HTTP server closed');
     });
   });

   module.exports = { app, server };
   ```

**Verification Steps**:
1. Run the server: `node src/server.js`
2. Test health endpoint: `curl http://localhost:3000/healthz`
3. Verify response contains: `{"status":"ok"}`
4. Confirm server logs show: `API Gateway running on port 3000`

### Task 1.2: Implement Authentication & Authorization Middleware

**Purpose**: Secure the API Gateway by validating user identity and permissions.

**Dependencies**:
- Selected web framework from Task 1.1
- jsonwebtoken package

**Implementation Steps**:

1. Install JWT library:
   ```bash
   npm install jsonwebtoken
   ```

2. Create authentication middleware:

   **File**: `src/middleware/auth.js`
   ```javascript
   const jwt = require('jsonwebtoken');

   const verifyToken = (req, res, next) => {
     // Get token from Authorization header
     const authHeader = req.headers.authorization;
     const token = authHeader && authHeader.split(' ')[1];

     if (!token) {
       return res.status(401).json({ message: 'No token provided' });
     }

     try {
       // Verify the token
       const decoded = jwt.verify(token, process.env.JWT_SECRET);
       req.user = decoded;
       next();
     } catch (error) {
       return res.status(401).json({ message: 'Invalid token' });
     }
   };

   module.exports = { verifyToken };
   ```

3. Apply authentication to routes:

   **File**: `src/routes/index.js`
   ```javascript
   const express = require('express');
   const router = express.Router();
   const { verifyToken } = require('../middleware/auth');

   // Public routes
   router.get('/public', (req, res) => {
     res.json({ message: 'Public endpoint' });
   });

   // Protected routes
   router.get('/protected', verifyToken, (req, res) => {
     res.json({ message: 'Protected endpoint', user: req.user });
   });

   module.exports = router;
   ```

4. Add role-based access control (optional):

   **Decision Point**: Role-based authorization implementation

   **Options**:
   1. **Simple approach**: Add role check to existing middleware
   2. **Advanced approach**: Implement dedicated RBAC system with role hierarchies

   **Simple implementation**:
   ```javascript
   // Add to auth.js
   const checkRole = (role) => {
     return (req, res, next) => {
       if (!req.user) {
         return res.status(401).json({ message: 'Authentication required' });
       }

       if (req.user.role !== role) {
         return res.status(403).json({ message: 'Insufficient permissions' });
       }

       next();
     };
   };

   module.exports = { verifyToken, checkRole };
   ```

**Verification Steps**:
1. Generate a test JWT token with a role claim
   ```javascript
   // Example token generation (for testing only)
   const token = jwt.sign({ id: 1, role: 'admin' }, process.env.JWT_SECRET, { expiresIn: '1h' });
   console.log(token);
   ```
2. Send request to protected endpoint without token
   - Expected: 401 Unauthorized
3. Send request with valid token
   - Expected: 200 OK with user data
4. If using role check, send request with incorrect role
   - Expected: 403 Forbidden

### Task 1.3: Implement Rate Limiting

**Purpose**: Prevent abuse and DDoS attacks by limiting request frequency.

**Dependencies**:
- express-rate-limit package (for Express)
- Redis (optional, for distributed rate limiting)

**Implementation Steps**:

1. Install rate limiting package:
   ```bash
   npm install express-rate-limit
   # For Redis store (optional)
   # npm install rate-limit-redis redis
   ```

2. Configure rate limiting middleware:

   **File**: `src/middleware/rate-limit.js`
   ```javascript
   const rateLimit = require('express-rate-limit');

   const apiLimiter = rateLimit({
     windowMs: 15 * 60 * 1000, // 15 minutes
     max: 100, // limit each IP to 100 requests per windowMs
     standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
     legacyHeaders: false, // Disable the `X-RateLimit-*` headers
     message: {
       status: 429,
       message: 'Too many requests, please try again later.'
     }
   });

   const authLimiter = rateLimit({
     windowMs: 60 * 60 * 1000, // 1 hour
     max: 5, // 5 failed attempts per hour
     skipSuccessfulRequests: true, // only count failed requests
     message: {
       status: 429,
       message: 'Too many failed login attempts, please try again later'
     }
   });

   module.exports = { apiLimiter, authLimiter };
   ```

3. Apply rate limiting to routes:

   **File**: `src/app.js`
   ```javascript
   const { apiLimiter, authLimiter } = require('./middleware/rate-limit');

   // Apply general rate limiting to all routes
   app.use(apiLimiter);

   // Apply stricter limits to auth endpoints
   app.use('/api/auth/login', authLimiter);
   ```

**Verification Steps**:
1. Send multiple requests exceeding the limit (can use a script)
   ```bash
   # Example script to send multiple requests
   for i in {1..110}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/api/v1/public; done
   ```
2. Verify response contains status code 429 after limit is reached
3. Check response headers contain rate limit information:
   ```
   RateLimit-Limit: 100
   RateLimit-Remaining: 0
   RateLimit-Reset: 1234567890
   ```

### Task 1.4: Implement Logging

**Purpose**: Enable robust request logging for monitoring and debugging.

**Dependencies**:
- morgan package (for request logging)
- winston package (for structured logging)

**Implementation Steps**:

1. Install logging packages:
   ```bash
   npm install morgan winston
   ```

2. Create logger configuration:

   **File**: `src/middleware/logger.js`
   ```javascript
   const morgan = require('morgan');
   const winston = require('winston');

   // Create Winston logger
   const logger = winston.createLogger({
     level: process.env.LOG_LEVEL || 'info',
     format: winston.format.combine(
       winston.format.timestamp(),
       winston.format.json()
     ),
     defaultMeta: { service: 'api-gateway' },
     transports: [
       new winston.transports.Console(),
       new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
       new winston.transports.File({ filename: 'logs/combined.log' })
     ]
   });

   // Create Morgan middleware that writes to Winston
   const httpLogger = morgan('combined', {
     stream: {
       write: (message) => logger.http(message.trim())
     }
   });

   module.exports = { logger, httpLogger };
   ```

3. Apply logging to the application:

   **File**: `src/app.js`
   ```javascript
   const { httpLogger, logger } = require('./middleware/logger');

   // Use HTTP request logging
   app.use(httpLogger);

   // Add correlation ID to track requests
   app.use((req, res, next) => {
     req.correlationId = req.get('X-Correlation-ID') || uuid.v4();
     res.set('X-Correlation-ID', req.correlationId);
     next();
   });
   ```

**Verification Steps**:
1. Make requests to different endpoints
   ```bash
   curl http://localhost:3000/healthz
   curl http://localhost:3000/api/v1/public
   ```
2. Check log files contain structured entries:
   ```bash
   cat logs/combined.log | tail -n 5
   ```
3. Verify correlation IDs are propagated in responses:
   ```bash
   curl -v http://localhost:3000/healthz | grep 'X-Correlation-ID'
   ```

### Task 1.5: Implement Caching Strategy

**Purpose**: Improve response times and reduce backend load by caching frequent requests.

**Dependencies**:
- node-cache (for in-memory caching)
- redis (for distributed caching in multi-instance deployments)

**Decision Point**: Caching implementation approach

**Options**:
1. **In-memory cache**: Simpler, works for single instances
2. **Redis-based cache**: Works across multiple instances, more complex

**Implementation Steps**:

1. Install caching packages:
   ```bash
   npm install node-cache
   # For distributed option
   # npm install redis
   ```

2. Create cache middleware:

   **File**: `src/middleware/cache.js` (In-memory implementation)
   ```javascript
   const NodeCache = require('node-cache');

   // Create cache with 60 second TTL default
   const cache = new NodeCache({ stdTTL: 60 });

   // Cache middleware
   const cacheMiddleware = (req, res, next) => {
     // Only cache GET requests
     if (req.method !== 'GET') {
       return next();
     }

     const key = req.originalUrl;
     const cachedResponse = cache.get(key);

     if (cachedResponse) {
       return res.json(cachedResponse);
     }

     // Store original send method
     const originalSend = res.send;

     // Override send method to cache successful responses
     res.send = function(body) {
       if (res.statusCode >= 200 && res.statusCode < 300) {
         try {
           const parsedBody = JSON.parse(body);
           cache.set(key, parsedBody);
         } catch (error) {
           // If body is not JSON, don't cache
         }
       }
       originalSend.call(this, body);
     };

     next();
   };

   module.exports = { cacheMiddleware };
   ```

3. Apply cache middleware to routes:

   **File**: `src/routes/index.js`
   ```javascript
   const { cacheMiddleware } = require('../middleware/cache');

   // Apply caching to specific routes
   router.get('/api/products', cacheMiddleware, (req, res) => {
     // Handler for products endpoint
   });
   ```

4. Configure cache headers for client/CDN caching:

   ```javascript
   // Add to specific route handlers
   res.set('Cache-Control', 'public, max-age=60');
   res.set('ETag', resourceVersion);
   ```

**Verification Steps**:
1. Make repeated requests to cached endpoint
   ```bash
   time curl http://localhost:3000/api/products # First request
   time curl http://localhost:3000/api/products # Subsequent request should be faster
   ```
2. Measure response time improvement on subsequent requests
3. Verify cache is invalidated after TTL expires:
   ```bash
   # Wait for TTL to expire
   sleep 61
   time curl http://localhost:3000/api/products # Should be slower again
   ```

### Task 1.6: Implement Load Balancing & Scalability

**Purpose**: Ensure the gateway can scale horizontally to handle increased traffic.

**Implementation Steps**:

1. Make the application stateless:
   - Use JWT tokens instead of session cookies
   - Store any persistent data in external databases

2. Configure graceful shutdown handling:

   **File**: `src/server.js`
   ```javascript
   // Add to server initialization
   const server = app.listen(PORT, () => {
     console.log(`API Gateway running on port ${PORT}`);
   });

   // Graceful shutdown
   process.on('SIGTERM', () => {
     console.log('SIGTERM signal received: closing HTTP server');
     server.close(() => {
       console.log('HTTP server closed');
     });
   });
   ```

3. For multi-core environments, use Node.js Cluster:

   **File**: `src/cluster.js`
   ```javascript
   const cluster = require('cluster');
   const os = require('os');
   const { logger } = require('./middleware/logger');

   const numCPUs = os.cpus().length;

   if (cluster.isMaster) {
     logger.info(`Master ${process.pid} is running`);

     // Fork workers
     for (let i = 0; i < numCPUs; i++) {
       cluster.fork();
     }

     cluster.on('exit', (worker, code, signal) => {
       logger.warn(`Worker ${worker.process.pid} died with code: ${code}, signal: ${signal}`);
       logger.info('Starting a new worker');
       cluster.fork();
     });
   } else {
     // Workers can share any TCP connection
     require('./server');
     logger.info(`Worker ${process.pid} started`);
   }
   ```

4. In production environments (like Vercel), ensure compatibility with the platform's scaling mechanism.

**Verification Steps**:
1. Run the application in cluster mode
   ```bash
   node src/cluster.js
   ```
2. Verify multiple worker processes are created
   ```bash
   ps aux | grep node
   ```
3. Test graceful shutdown with SIGTERM signal
   ```bash
   # Find the process ID
   ps aux | grep node
   # Send SIGTERM
   kill -SIGTERM <process_id>
   ```
4. Ensure connections are properly closed by checking logs

### Task 1.7: Implement Security Measures

**Purpose**: Protect the API Gateway from common security threats.

**Implementation Steps**:

1. Ensure HTTPS is enforced:

   ```javascript
   // Redirect HTTP to HTTPS in production
   app.use((req, res, next) => {
     if (process.env.NODE_ENV === 'production' && !req.secure) {
       return res.redirect(`https://${req.headers.host}${req.url}`);
     }
     next();
   });
   ```

2. Implement input validation:

   ```bash
   npm install joi
   ```

   **File**: `src/middleware/validation.js`
   ```javascript
   const Joi = require('joi');

   const validate = (schema) => {
     return (req, res, next) => {
       const { error } = schema.validate(req.body);
       if (error) {
         return res.status(400).json({
           message: 'Validation error',
           details: error.details.map(detail => detail.message)
         });
       }
       next();
     };
   };

   // Example schema
   const userSchema = Joi.object({
     username: Joi.string().alphanum().min(3).max(30).required(),
     email: Joi.string().email().required(),
     password: Joi.string().pattern(new RegExp('^[a-zA-Z0-9]{8,30}$')).required()
   });

   module.exports = { validate, schemas: { user: userSchema } };
   ```

3. Add audit logging for security events:

   ```javascript
   // In authentication middleware
   if (!token) {
     logger.warn('Authentication failure: No token provided', {
       ip: req.ip,
       path: req.path,
       correlationId: req.correlationId
     });
     return res.status(401).json({ message: 'No token provided' });
   }
   ```

4. Implement optional IP allow/block lists:

   **File**: `src/middleware/ip-filter.js`
   ```javascript
   const ipFilter = (options = {}) => {
     const { whitelist = [], blacklist = [] } = options;

     return (req, res, next) => {
       const clientIp = req.ip;

       // Check blacklist
       if (blacklist.includes(clientIp)) {
         logger.warn(`Blocked request from blacklisted IP: ${clientIp}`);
         return res.status(403).json({ message: 'Access denied' });
       }

       // If whitelist exists and IP not in whitelist
       if (whitelist.length > 0 && !whitelist.includes(clientIp)) {
         logger.warn(`Blocked request from non-whitelisted IP: ${clientIp}`);
         return res.status(403).json({ message: 'Access denied' });
       }

       next();
     };
   };

   module.exports = { ipFilter };
   ```

**Verification Steps**:
1. Test input validation with invalid data
   ```bash
   curl -X POST -H "Content-Type: application/json" -d '{"username": "a"}' http://localhost:3000/api/users
   ```
   - Expected: 400 Bad Request with validation error
2. Verify security headers are set correctly
   ```bash
   curl -I http://localhost:3000/healthz
   ```
   - Check for headers like X-Content-Type-Options, X-XSS-Protection, etc.
3. Attempt access with blocked IP (if implemented)
4. Check audit logs for security events:
   ```bash
   grep "Authentication failure" logs/combined.log
   ```

### Task 1.8: Implement Monitoring & Resilience

**Purpose**: Ensure the API Gateway remains operational and performant.

**Implementation Steps**:

1. Create health check endpoint:

   ```javascript
   app.get('/healthz', (req, res) => {
     // Basic health check
     res.status(200).json({ status: 'ok' });
   });

   // Advanced health check with dependency status
   app.get('/healthz/detailed', async (req, res) => {
     try {
       const dbStatus = await checkDatabaseConnection();
       const redisStatus = await checkRedisConnection();

       const isHealthy = dbStatus && redisStatus;

       res.status(isHealthy ? 200 : 503).json({
         status: isHealthy ? 'ok' : 'degraded',
         database: dbStatus ? 'connected' : 'disconnected',
         cache: redisStatus ? 'connected' : 'disconnected'
       });
     } catch (error) {
       res.status(500).json({ status: 'error', message: error.message });
     }
   });
   ```

2. Implement circuit breaker pattern for downstream services:

   ```bash
   npm install opossum
   ```

   **File**: `src/utils/circuit-breaker.js`
   ```javascript
   const CircuitBreaker = require('opossum');

   const defaultOptions = {
     timeout: 3000, // If function takes longer than 3 seconds, trigger a failure
     errorThresholdPercentage: 50, // When 50% of requests fail, open the circuit
     resetTimeout: 30000 // After 30 seconds, try again
   };

   const createBreaker = (fn, options = {}) => {
     return new CircuitBreaker(fn, { ...defaultOptions, ...options });
   };

   module.exports = { createBreaker };
   ```

3. Use circuit breaker for service calls:

   ```javascript
   const { createBreaker } = require('../utils/circuit-breaker');

   // Function to call downstream service
   const getUserFromService = async (userId) => {
     const response = await fetch(`http://user-service/users/${userId}`);
     if (!response.ok) throw new Error('User service error');
     return response.json();
   };

   // Create circuit breaker
   const userServiceBreaker = createBreaker(getUserFromService);

   // In route handler
   router.get('/api/users/:id', async (req, res) => {
     try {
       const user = await userServiceBreaker.fire(req.params.id);
       res.json(user);
     } catch (error) {
       if (userServiceBreaker.status === 'open') {
         // Circuit is open, service is likely down
         logger.error('User service circuit open', { userId: req.params.id });
         return res.status(503).json({ message: 'Service temporarily unavailable' });
       }
       res.status(500).json({ message: 'Error fetching user data' });
     }
   });
   ```

**Verification Steps**:
1. Test health check endpoint returns 200 OK
   ```bash
   curl http://localhost:3000/healthz
   ```
2. Simulate downstream service failure
   ```javascript
   // Mock a failing service for testing
   const failingServiceBreaker = createBreaker(() => Promise.reject(new Error('Service error')));

   // Call it multiple times to open the circuit
   for (let i = 0; i < 10; i++) {
     failingServiceBreaker.fire().catch(err => console.error(err.message));
   }

   // Check the status
   console.log('Circuit status:', failingServiceBreaker.status);
   ```
3. Verify circuit breaker prevents cascading failures
4. Check metrics collection is working properly
   - Look for logs and metrics output

## Phase 2: CI/CD Pipeline Setup

### Concept Overview

The CI/CD pipeline automates testing, building, and deploying the API Gateway to ensure high-quality, reliable releases. GitHub Actions will be used for workflow automation, and Vercel for deployment, providing a seamless integration from code to production.

### Task 2.1: Set Up GitHub Actions Workflow

**Purpose**: Create automated workflows to validate code quality and prepare for deployment.

**Dependencies**:
- GitHub repository
- Node.js project with package.json
- Test and lint scripts configured

**Implementation Steps**:

1. Create GitHub Actions workflow directory:
   ```bash
   mkdir -p .github/workflows
   ```

2. Create CI workflow file:

   **File**: `.github/workflows/ci.yml`
   ```yaml
   name: Continuous Integration

   on:
     push:
       branches: [ main, develop ]
     pull_request:
       branches: [ main, develop ]

   jobs:
     test:
       runs-on: ubuntu-latest

       steps:
         - uses: actions/checkout@v3

         - name: Set up Node.js
           uses: actions/setup-node@v3
           with:
             node-version: '18'
             cache: 'npm'

         - name: Install dependencies
           run: npm ci

         - name: Lint code
           run: npm run lint

         - name: Run tests
           run: npm test
   ```

3. Configure test and lint scripts in package.json:

   **File**: `package.json`
   ```json
   {
     "scripts": {
       "lint": "eslint .",
       "test": "jest --coverage"
     }
   }
   ```

**Verification Steps**:
1. Push the workflow file to the repository
   ```bash
   git add .github/workflows/ci.yml
   git commit -m "Add CI workflow"
   git push origin main
   ```
2. Check GitHub Actions tab in the repository to verify workflow is triggered
   - Navigate to: https://github.com/[username]/[repo-name]/actions
   - Verify the workflow appears and runs successfully
3. Make a test commit with a failing test to ensure the CI correctly identifies failures
   ```bash
   # Create a failing test
   echo "test('should fail', () => { expect(1).toBe(2); });" > src/__tests__/fail.test.js
   git add src/__tests__/fail.test.js
   git commit -m "Add failing test to verify CI"
   git push origin develop
   ```
   - Confirm the workflow fails as expected in GitHub Actions

### Task 2.2: Configure Multi-Environment Deployment

**Purpose**: Set up separate deployments for staging and production environments.

**Dependencies**:
- GitHub repository with CI workflow
- Vercel account
- API Gateway project setup

**Decision Point**: Deployment approach

**Options**:
1. **Vercel GitHub Integration**: Automatic deploys via Vercel's GitHub integration
   - Pros: Simpler setup, automatic preview deployments for PRs
   - Cons: Less control over deployment process
   - Recommended when: Simplicity and quick setup are priorities

2. **GitHub Actions with Vercel CLI**: More control over deployment process
   - Pros: More customizable, can add pre/post-deployment steps
   - Cons: More complex configuration
   - Recommended when: Advanced deployment scenarios are needed

**Implementation Steps**:

1. Set up GitHub Secrets for Vercel:
   - VERCEL_TOKEN (personal/project deploy token)
   - VERCEL_ORG_ID
   - VERCEL_PROJECT_ID

   To obtain these from Vercel:
   ```bash
   # Install Vercel CLI
   npm install -g vercel

   # Login to Vercel
   vercel login

   # Link your project to get IDs
   vercel link
   ```

2. Create deployment workflow file:

   **File**: `.github/workflows/deploy.yml`
   ```yaml
   name: Deploy to Vercel

   on:
     push:
       branches: [main, develop]

   jobs:
     deploy:
       runs-on: ubuntu-latest

       steps:
         - uses: actions/checkout@v3

         - name: Set up Node.js
           uses: actions/setup-node@v3
           with:
             node-version: '18'
             cache: 'npm'

         - name: Install dependencies
           run: npm ci

         - name: Install Vercel CLI
           run: npm install -g vercel

         - name: Pull Vercel Environment Information
           run: vercel pull --yes --environment=${{ github.ref == 'refs/heads/main' && 'production' || 'preview' }} --token=${{ secrets.VERCEL_TOKEN }}

         - name: Build Project Artifacts
           run: vercel build --token=${{ secrets.VERCEL_TOKEN }}

         - name: Deploy Project Artifacts to Vercel
           run: |
             if [ ${{ github.ref }} == 'refs/heads/main' ]; then
               vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
             else
               vercel deploy --prebuilt --token=${{ secrets.VERCEL_TOKEN }}
             fi
   ```

3. Configure Vercel project settings:
   - Connect to GitHub repository through Vercel dashboard
   - Configure environment variables for each environment
   - Set up deployment domains for staging and production

**Verification Steps**:
1. Push to develop branch to trigger a preview deployment
   ```bash
   git checkout develop
   # Make a small change
   echo "// Test comment" >> src/server.js
   git add src/server.js
   git commit -m "Test preview deployment"
   git push origin develop
   ```
2. Check GitHub Actions tab to verify deployment workflow runs
   - Navigate to: https://github.com/[username]/[repo-name]/actions
3. Verify preview URL is generated and accessible
   - Look for the deployment URL in the workflow logs or Vercel dashboard
   - Access the URL and confirm the API Gateway is working
4. Create and merge a PR to main to trigger production deployment
   - Verify production URL is updated with the changes

### Task 2.3: Implement Deployment Safeguards

**Purpose**: Protect production environment from broken code or unauthorized changes.

**Implementation Steps**:

1. Configure branch protection for main branch:
   - Navigate to GitHub repository Settings > Branches
   - Add rule for main branch with the following settings:
     - ✓ Require a pull request before merging
     - ✓ Require approvals (at least 1)
     - ✓ Require status checks to pass before merging
     - ✓ Require branches to be up to date before merging
     - In the status checks section, select the CI workflow

2. Add conditional deployment workflow step:

   ```yaml
   # Add to deploy.yml workflow
   - name: Deploy to Production
     if: github.ref == 'refs/heads/main' && success()
     run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
   ```

3. Configure automatic PR review assignment:

   **File**: `.github/CODEOWNERS`
   ```
   # Require specific team review for all changes
   * @org-name/reviewers-team

   # More specific ownership
   /src/auth/ @org-name/security-team
   ```

**Verification Steps**:
1. Try pushing directly to main branch (should be blocked)
   ```bash
   git checkout main
   echo "// Direct change" >> src/server.js
   git add src/server.js
   git commit -m "Test branch protection"
   git push origin main
   ```
   - Verify you receive an error that the push was rejected

2. Create a PR without required approvals
   ```bash
   git checkout -b test-branch
   echo "// Test change" >> src/server.js
   git add src/server.js
   git commit -m "Test branch protection"
   git push origin test-branch
   ```
   - Create a PR on GitHub and try to merge it
   - Verify merge is blocked until all required checks pass

3. Create a PR with failing tests
   - Add a failing test to your branch
   - Create a PR and verify that merge is blocked due to failing checks

### Task 2.4: Set Up Notifications & Monitoring

**Purpose**: Ensure team is promptly notified of build or deployment issues.

**Dependencies**:
- GitHub repository with CI/CD workflows
- Notification channel (email or Slack)

**Implementation Steps**:

1. Add notification step to GitHub Actions:

   ```yaml
   # Add to workflow files
   - name: Notify on failure
     if: failure()
     uses: actions/github-script@v6
     with:
       github-token: ${{ secrets.GITHUB_TOKEN }}
       script: |
         const { repo, owner } = context.repo;
         const run_id = context.runId;
         const run_url = `https://github.com/${owner}/${repo}/actions/runs/${run_id}`;
         github.rest.issues.createComment({
           issue_number: context.issue.number,
           owner,
           repo,
           body: `❌ CI failed! [View run](${run_url})`
         });
   ```

2. Set up Slack notifications (optional):

   ```yaml
   # Add to workflow files
   - name: Slack Notification
     uses: rtCamp/action-slack-notify@v2
     env:
       SLACK_WEBHOOK: ${{ secrets.SLACK_WEBHOOK }}
       SLACK_CHANNEL: ci-cd-alerts
       SLACK_COLOR: ${{ job.status == 'success' && 'good' || 'danger' }}
       SLACK_TITLE: ${{ github.workflow }} workflow ${{ job.status }}
       SLACK_MESSAGE: '${{ github.repository }} - ${{ github.event_name }} - ${{ github.ref }}'
   ```

3. Configure post-deployment monitoring:
   - Set up Vercel Analytics for deployment monitoring
   - Configure Vercel logs to be accessible to the team
   - Set up alerts for production errors through Vercel integrations

**Verification Steps**:
1. Trigger a failed workflow and verify notification
   ```bash
   # Create a branch with something that will fail CI
   git checkout -b test-notification
   echo "const x = 'missing semicolon'" >> src/badcode.js
   git add src/badcode.js
   git commit -m "Test notifications on failure"
   git push origin test-notification
   ```
   - Create a PR and verify that the failure notification appears as a comment

2. Check Slack notifications (if configured)
   - Verify that the notification appears in the designated Slack channel

3. Confirm deployment logs are accessible
   - Navigate to the Vercel dashboard
   - Verify that logs and analytics for the project are accessible

## Phase 3: Docker & Containerization

### Concept Overview

Containerization provides consistency across environments and enables easy scalability for the API Gateway. Docker containers package the application with its dependencies, ensuring identical behavior in development, testing, and production environments.

### Task 3.1: Create Dockerfile for API Gateway

**Purpose**: Create a standardized, secure container image for the API Gateway.

**Dependencies**:
- Docker installed
- Node.js API Gateway project

**Implementation Steps**:

1. Create Dockerfile in project root:

   **File**: `Dockerfile`
   ```dockerfile
   # Base image - specify exact version for consistency
   FROM node:18-alpine

   # Set working directory
   WORKDIR /app

   # Copy package files first for better caching
   COPY package*.json ./

   # Install dependencies
   RUN npm ci --only=production

   # Copy application code
   COPY . .

   # Set production environment
   ENV NODE_ENV=production

   # Expose API port
   EXPOSE 3000

   # Use non-root user for security
   USER node

   # Start application
   CMD ["node", "src/server.js"]
   ```

2. Create .dockerignore file:

   **File**: `.dockerignore`
   ```
   node_modules
   npm-debug.log
   .git
   .github
   .vscode
   coverage
   tests
   *.md
   .env*
   ```

3. For multi-stage builds (optional for improved security and smaller images):

   **File**: `Dockerfile.multistage`
   ```dockerfile
   # Build stage
   FROM node:18-alpine AS build

   WORKDIR /app

   COPY package*.json ./
   RUN npm ci

   COPY . .

   # Run tests and linting in build stage
   RUN npm run lint
   RUN npm test

   # If using TypeScript or other build step
   RUN npm run build

   # Production stage
   FROM node:18-alpine

   WORKDIR /app

   # Copy only production dependencies
   COPY package*.json ./
   RUN npm ci --only=production

   # Copy built application from build stage
   COPY --from=build /app/dist ./dist

   ENV NODE_ENV=production

   EXPOSE 3000

   USER node

   CMD ["node", "dist/server.js"]
   ```

**Verification Steps**:
1. Build the Docker image
   ```bash
   # Build standard image
   docker build -t api-gateway .

   # Or build multi-stage image
   docker build -f Dockerfile.multistage -t api-gateway:multistage .
   ```

2. Run the container locally
   ```bash
   # Run container and map port 3000
   docker run -p 3000:3000 api-gateway
   ```

3. Access the API to verify it's working
   ```bash
   curl http://localhost:3000/healthz
   ```
   - Expected response: `{"status":"ok"}`

4. Check security aspects
   ```bash
   # Verify the container is running as non-root
   docker exec $(docker ps -q -f "ancestor=api-gateway") whoami
   # Should output: node

   # Scan image for vulnerabilities (if Docker Desktop or similar tool available)
   docker scan api-gateway
   ```

### Task 3.2: Create Docker Compose Configuration

**Purpose**: Define a multi-container setup for local development and testing.

**Dependencies**:
- Docker and Docker Compose installed
- Dockerfile from previous task

**Implementation Steps**:

1. Create Docker Compose file:

   **File**: `docker-compose.yml`
   ```yaml
   version: '3.8'

   services:
     api-gateway:
       build:
         context: .
         dockerfile: Dockerfile
       ports:
         - "3000:3000"
       environment:
         - NODE_ENV=development
         - PORT=3000
         - JWT_SECRET=dev_secret_change_in_production
       depends_on:
         - redis
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:3000/healthz"]
         interval: 30s
         timeout: 10s
         retries: 3

     redis:
       image: redis:alpine
       ports:
         - "6379:6379"
       volumes:
         - redis-data:/data
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "redis-cli", "ping"]
         interval: 30s
         timeout: 10s
         retries: 3

   volumes:
     redis-data:
   ```

2. Create development-specific configuration (optional):

   **File**: `docker-compose.dev.yml`
   ```yaml
   version: '3.8'

   services:
     api-gateway:
       build:
         context: .
         dockerfile: Dockerfile.dev
       volumes:
         - ./src:/app/src
         - ./tests:/app/tests
       command: npm run dev
   ```

3. Create production-specific configuration (optional):

   **File**: `docker-compose.prod.yml`
   ```yaml
   version: '3.8'

   services:
     api-gateway:
       image: ${DOCKER_REGISTRY}/api-gateway:${IMAGE_TAG}
       environment:
         - NODE_ENV=production
       restart: always
   ```

**Verification Steps**:
1. Start the containers with Docker Compose
   ```bash
   # Start standard environment
   docker-compose up -d

   # Or with development overrides
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   ```

2. Check container status
   ```bash
   docker-compose ps
   ```
   - Verify both api-gateway and redis containers are running

3. Verify Redis connection from API Gateway
   ```bash
   # Check logs for successful Redis connection
   docker-compose logs api-gateway | grep -i redis

   # Or connect to the container and check manually
   docker-compose exec api-gateway sh -c "nc -zv redis 6379"
   ```

4. Verify container logs
   ```bash
   docker-compose logs api-gateway
   ```
   - Look for successful startup messages

5. Test the API via the composed stack
   ```bash
   curl http://localhost:3000/healthz
   ```
   - Expected response: `{"status":"ok"}`

### Task 3.3: Optimize for Efficient Image Management

**Purpose**: Ensure Docker images are small, secure, and built efficiently.

**Implementation Steps**:

1. Layer optimization:
   - Order Dockerfile commands from least to most frequently changing
   - Group related RUN commands to reduce layers
   - Use .dockerignore to exclude unnecessary files

2. Implement image tagging strategy:
   ```bash
   # For local development
   docker build -t api-gateway:latest .

   # For versioned releases
   docker build -t api-gateway:1.0.0 .
   docker tag api-gateway:1.0.0 api-gateway:latest

   # For specific environments
   docker tag api-gateway:1.0.0 api-gateway:staging
   docker tag api-gateway:1.0.0 api-gateway:production
   ```

3. Set up automated cleanup:

   **File**: `scripts/docker-cleanup.sh`
   ```bash
   #!/bin/bash

   # Remove unused containers
   docker container prune -f

   # Remove dangling images
   docker image prune -f

   # Remove unused volumes (use with caution)
   # docker volume prune -f

   echo "Docker cleanup completed"
   ```

   Make the script executable:
   ```bash
   chmod +x scripts/docker-cleanup.sh
   ```

**Verification Steps**:
1. Build image and check size
   ```bash
   docker build -t api-gateway:test .
   docker images api-gateway:test
   ```
   - Note the size in MB

2. Run cleanup script and verify space reclaimed
   ```bash
   ./scripts/docker-cleanup.sh
   ```
   - Check output for containers and images removed

3. Verify build time is optimized through caching
   ```bash
   # First build
   time docker build -t api-gateway:cached .

   # Second build (should be faster due to caching)
   time docker build -t api-gateway:cached .
   ```
   - Second build should complete significantly faster if caching is working properly

### Task 3.4: Implement Container Security Measures

**Purpose**: Ensure containers are secure and follow best practices.

**Implementation Steps**:

1. Regularly scan for vulnerabilities:
   ```bash
   # Using Docker Scan (Snyk)
   docker scan api-gateway

   # Or using Trivy
   trivy image api-gateway
   ```

2. Create container security policy:

   **File**: `.github/workflows/container-security.yml`
   ```yaml
   name: Container Security Scan

   on:
     push:
       branches: [ main, develop ]
     pull_request:
       branches: [ main ]
     schedule:
       - cron: '0 2 * * 1'  # Weekly on Mondays at 2 AM

   jobs:
     scan:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3

         - name: Build image
           run: docker build -t api-gateway:${{ github.sha }} .

         - name: Run Trivy vulnerability scanner
           uses: aquasecurity/trivy-action@master
           with:
             image-ref: 'api-gateway:${{ github.sha }}'
             format: 'sarif'
             output: 'trivy-results.sarif'
             severity: 'CRITICAL,HIGH'

         - name: Upload Trivy scan results to GitHub Security tab
           uses: github/codeql-action/upload-sarif@v2
           with:
             sarif_file: 'trivy-results.sarif'
   ```

3. Implement secrets management:
   - Use environment variables for runtime secrets
   - Never bake secrets into the image
   - For Kubernetes, use secrets or HashiCorp Vault

**Verification Steps**:
1. Run security scan and review findings
   ```bash
   # Install trivy if not available
   # brew install trivy (for macOS)

   # Run scan
   trivy image api-gateway
   ```
   - Address any high-severity findings

2. Check that container runs as non-root user
   ```bash
   docker run --rm -it api-gateway whoami
   ```
   - Should output: `node`

3. Verify no secrets are stored in the image
   ```bash
   # Export the image to files
   docker save api-gateway | tar -xf - -C /tmp/image-extract

   # Search for sensitive terms
   grep -r "password\|token\|secret\|key" /tmp/image-extract

   # Clean up
   rm -rf /tmp/image-extract
   ```
   - Should not find any actual secrets (might find variable names but not values)

### Task 3.5: Multi-Architecture Support

**Purpose**: Ensure the Docker setup works across different CPU architectures (ARM/x86).

**Dependencies**:
- Docker with buildx extension

**Implementation Steps**:

1. Set up multi-architecture building:
   ```bash
   # Create and use a builder that supports multi-architecture builds
   docker buildx create --name multiarch-builder --use

   # Build and push for multiple platforms
   docker buildx build --platform linux/amd64,linux/arm64 -t username/api-gateway:latest --push .
   ```

2. Add ARM compatibility verification:

   **File**: `.github/workflows/multi-arch-test.yml`
   ```yaml
   name: Test Multi-Architecture Builds

   on:
     push:
       branches: [ main, develop ]

   jobs:
     build:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3

         - name: Set up QEMU
           uses: docker/setup-qemu-action@v2

         - name: Set up Docker Buildx
           uses: docker/setup-buildx-action@v2

         - name: Build for multiple architectures
           uses: docker/build-push-action@v3
           with:
             context: .
             platforms: linux/amd64,linux/arm64
             load: true
             tags: api-gateway:test
   ```

**Verification Steps**:
1. Build for multiple architectures
   ```bash
   # Ensure buildx is set up
   docker buildx ls

   # Build for multiple platforms
   docker buildx build --platform linux/amd64,linux/arm64 -t api-gateway:multiarch --load .
   ```

2. Verify architectures in the image manifest
   ```bash
   docker buildx imagetools inspect api-gateway:multiarch
   ```
   - Should show both amd64 and arm64 platforms

3. Test the image on different platforms (if available)
   ```bash
   # On ARM machine (like M1/M3 MacBook)
   docker run --rm api-gateway:multiarch uname -m
   # Should output: arm64

   # On x86 machine
   docker run --rm api-gateway:multiarch uname -m
   # Should output: x86_64
   ```

## Phase 4: Shell Scripts for Automation

### Concept Overview

Shell scripts automate common development tasks, streamline environment setup, and ensure consistency across development, testing, and production environments. These scripts make the project more maintainable and reduce manual error.

### Task 4.1: Create Project Setup Scripts

**Purpose**: Provide scripts to initialize or reset the project environment for new developers.

**Dependencies**:
- Bash shell
- Node.js and npm installed

**Implementation Steps**:

1. Create directory for scripts:
   ```bash
   mkdir -p scripts
   ```

2. Create setup script:

   **File**: `scripts/setup.sh`
   ```bash
   #!/bin/bash
   set -e

   # Print with color for better UX
   GREEN='\033[0;32m'
   RED='\033[0;31m'
   NC='\033[0m' # No Color

   echo -e "${GREEN}Setting up API Gateway development environment...${NC}"

   # Check prerequisites
   if ! [ -x "$(command -v node)" ]; then
     echo -e "${RED}Error: Node.js is not installed.${NC}" >&2
     exit 1
   fi

   if ! [ -x "$(command -v npm)" ]; then
     echo -e "${RED}Error: npm is not installed.${NC}" >&2
     exit 1
   fi

   # Install dependencies
   echo "Installing dependencies..."
   npm ci

   # Create necessary directories if they don't exist
   echo "Creating required directories..."
   mkdir -p logs
   mkdir -p src/controllers src/middleware src/routes src/utils
   mkdir -p tests/unit tests/integration

   # Set up environment file from example if it doesn't exist
   if [ ! -f .env ]; then
     echo "Creating .env file from template..."
     cp .env.example .env
     echo -e "${GREEN}Created .env file. Please update it with your local configuration.${NC}"
   fi

   echo -e "${GREEN}Setup complete! You can now start the development server with:${NC}"
   echo "npm run dev"
   ```

3. Create reset script:

   **File**: `scripts/reset.sh`
   ```bash
   #!/bin/bash
   set -e

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   NC='\033[0m' # No Color

   echo -e "${YELLOW}This will reset your development environment to a clean state.${NC}"
   echo -e "${YELLOW}It will remove node_modules, logs, and build artifacts.${NC}"

   # Ask for confirmation
   read -p "Are you sure you want to continue? (y/n) " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
     echo "Operation cancelled."
     exit 0
   fi

   # Clean up directories
   echo "Removing node_modules directory..."
   rm -rf node_modules

   echo "Removing logs..."
   rm -rf logs/*.log

   echo "Removing build artifacts..."
   rm -rf dist build .next coverage

   echo "Cleaning npm cache..."
   npm cache clean --force

   echo -e "${GREEN}Reset complete. Run 'npm ci' to reinstall dependencies.${NC}"
   ```

4. Make scripts executable:
   ```bash
   chmod +x scripts/setup.sh scripts/reset.sh
   ```

**Verification Steps**:
1. Run the setup script in a clean environment
   ```bash
   # Clone the repository (if needed)
   git clone https://github.com/your-org/api-gateway.git
   cd api-gateway

   # Run setup script
   ./scripts/setup.sh
   ```
   - Verify that it creates all necessary directories
   - Check that node_modules is populated
   - Confirm .env file is created from template

2. Test the reset script
   ```bash
   # Create some test files to be cleaned up
   touch logs/test.log
   mkdir -p dist && touch dist/test.js

   # Run reset script
   ./scripts/reset.sh
   ```
   - Enter 'y' when prompted
   - Verify that node_modules, logs, dist and other artifact directories are removed
   - Confirm the script completes without errors

3. Verify scripts work on both MacOS (M3) and Linux environments
   - If possible, test on both platforms to ensure compatibility
   - Check for any platform-specific commands that might need adjustment

### Task 4.2: Create Docker Management Scripts

**Purpose**: Wrap Docker and Docker Compose commands in convenient scripts with additional logic.

**Dependencies**:
- Docker and Docker Compose installed
- Bash shell

**Implementation Steps**:

1. Create start script:

   **File**: `scripts/start.sh`
   ```bash
   #!/bin/bash
   set -e

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   RED='\033[0;31m'
   NC='\033[0m' # No Color

   # Check if Docker is running
   if ! docker info > /dev/null 2>&1; then
     echo -e "${RED}Error: Docker is not running.${NC}"
     exit 1
   fi

   # Parse arguments
   ENV="development"

   while getopts "e:" opt; do
     case $opt in
       e) ENV=$OPTARG ;;
       *) echo "Usage: $0 [-e environment]" && exit 1 ;;
     esac
   done

   echo -e "${GREEN}Starting API Gateway in ${ENV} environment...${NC}"

   # Start containers based on environment
   if [ "$ENV" = "production" ]; then
     docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   elif [ "$ENV" = "testing" ]; then
     docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d
   else
     docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
   fi

   # Wait for containers to be healthy
   echo -e "${YELLOW}Waiting for containers to be ready...${NC}"
   sleep 5

   # Run database migrations if needed
   if [ "$ENV" != "production" ]; then
     echo "Running database migrations..."
     docker-compose exec api-gateway npm run db:migrate
   fi

   echo -e "${GREEN}API Gateway is now running!${NC}"
   echo "Access the API at: http://localhost:3000"
   echo "To view logs, run: ./scripts/logs.sh"
   echo "To stop the API, run: ./scripts/stop.sh"
   ```

2. Create stop script:

   **File**: `scripts/stop.sh`
   ```bash
   #!/bin/bash

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   NC='\033[0m' # No Color

   # Parse arguments
   REMOVE_VOLUMES=false

   while getopts "v" opt; do
     case $opt in
       v) REMOVE_VOLUMES=true ;;
       *) echo "Usage: $0 [-v]" && exit 1 ;;
     esac
   done

   if [ "$REMOVE_VOLUMES" = true ]; then
     echo -e "${YELLOW}Stopping containers and removing volumes...${NC}"
     docker-compose down -v
   else
     echo -e "${YELLOW}Stopping containers...${NC}"
     docker-compose down
   fi

   echo -e "${GREEN}API Gateway stopped successfully.${NC}"
   ```

3. Create logs script:

   **File**: `scripts/logs.sh`
   ```bash
   #!/bin/bash

   # Parse arguments
   SERVICE="api-gateway"
   FOLLOW=false

   while getopts "s:f" opt; do
     case $opt in
       s) SERVICE=$OPTARG ;;
       f) FOLLOW=true ;;
       *) echo "Usage: $0 [-s service] [-f]" && exit 1 ;;
     esac
   done

   if [ "$FOLLOW" = true ]; then
     docker-compose logs -f "$SERVICE" | grep --color=auto -E '^|ERROR|WARN'
   else
     docker-compose logs "$SERVICE" | grep --color=auto -E '^|ERROR|WARN'
   fi
   ```

4. Make scripts executable:
   ```bash
   chmod +x scripts/start.sh scripts/stop.sh scripts/logs.sh
   ```

**Verification Steps**:
1. Test the start script with different environments
   ```bash
   # Start in development mode
   ./scripts/start.sh

   # Start in production mode
   ./scripts/start.sh -e production

   # Start in testing mode
   ./scripts/start.sh -e testing
   ```
   - Verify that appropriate compose files are used based on environment
   - Confirm containers start successfully
   - Check that the correct environment variables are applied

2. Test the logs script with different options
   ```bash
   # View logs without following
   ./scripts/logs.sh

   # Follow logs
   ./scripts/logs.sh -f

   # View logs for a specific service
   ./scripts/logs.sh -s redis
   ```
   - Verify that logs are displayed with color highlighting
   - Confirm the follow option works correctly
   - Check that service selection works

3. Test the stop script with and without volume removal
   ```bash
   # Stop without removing volumes
   ./scripts/stop.sh

   # Stop and remove volumes
   ./scripts/stop.sh -v
   ```
   - Verify containers stop cleanly
   - Confirm volumes are removed only when the -v flag is used
   - Check that the script provides appropriate feedback

### Task 4.3: Create Directory Structure Management Scripts

**Purpose**: Ensure consistent project structure and reduce redundancy.

**Implementation Steps**:

1. Create directory structure verification script:

   **File**: `scripts/verify-structure.sh`
   ```bash
   #!/bin/bash

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   RED='\033[0;31m'
   NC='\033[0m' # No Color

   # Required directories
   REQUIRED_DIRS=(
     "src/controllers"
     "src/middleware"
     "src/routes"
     "src/utils"
     "tests/unit"
     "tests/integration"
     "logs"
     "scripts"
   )

   # Check and create missing directories
   MISSING=0
   for DIR in "${REQUIRED_DIRS[@]}"; do
     if [ ! -d "$DIR" ]; then
       echo -e "${YELLOW}Missing directory: $DIR${NC}"
       MISSING=$((MISSING+1))

       # Create the directory
       mkdir -p "$DIR"
       echo -e "${GREEN}Created directory: $DIR${NC}"
     fi
   done

   if [ $MISSING -eq 0 ]; then
     echo -e "${GREEN}All required directories exist.${NC}"
   else
     echo -e "${YELLOW}Created $MISSING missing directories.${NC}"
   fi

   # Check for stale build artifacts
   if [ -d "dist" ] && [ -d "src" ]; then
     SRC_TIMESTAMP=$(stat -c %Y src 2>/dev/null || stat -f %m src)
     DIST_TIMESTAMP=$(stat -c %Y dist 2>/dev/null || stat -f %m dist)

     if [ $SRC_TIMESTAMP -gt $DIST_TIMESTAMP ]; then
       echo -e "${YELLOW}Warning: dist directory may be out of date with src.${NC}"
       echo "Consider rebuilding the project."
     fi
   fi

   exit 0
   ```

2. Create cleanup script:

   **File**: `scripts/cleanup.sh`
   ```bash
   #!/bin/bash

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   NC='\033[0m' # No Color

   echo -e "${YELLOW}Cleaning up project...${NC}"

   # Remove log files older than 7 days
   echo "Removing old log files..."
   find logs -name "*.log" -type f -mtime +7 -delete

   # Remove test coverage reports
   echo "Removing test coverage reports..."
   rm -rf coverage

   # Clean up temporary files
   echo "Removing temporary files..."
   find . -name "*.tmp" -type f -delete
   find . -name ".DS_Store" -type f -delete

   # Removing empty directories
   echo "Removing empty directories..."
   find . -type d -empty -delete

   echo -e "${GREEN}Cleanup complete.${NC}"
   ```

3. Make scripts executable:
   ```bash
   chmod +x scripts/verify-structure.sh scripts/cleanup.sh
   ```

**Verification Steps**:
1. Test the verify-structure script
   ```bash
   # Remove a required directory to test creation
   rm -rf src/controllers

   # Run the script
   ./scripts/verify-structure.sh
   ```
   - Verify that it detects and creates the missing directory
   - Confirm the script reports correctly on what was created
   - Check that it detects stale build artifacts

2. Test the cleanup script
   ```bash
   # Create some test files to be cleaned up
   touch logs/old.log
   mkdir -p coverage && touch coverage/test.json
   touch .DS_Store
   mkdir -p empty/dir

   # Set the timestamp on the log file to be old (8 days)
   touch -t $(date -d "8 days ago" "+%Y%m%d%H%M.%S" 2>/dev/null || date -v-8d "+%Y%m%d%H%M.%S") logs/old.log

   # Run the script
   ./scripts/cleanup.sh
   ```
   - Verify that old log files are removed
   - Confirm coverage directory is removed
   - Check that .DS_Store files are deleted
   - Verify that empty directories are removed

### Task 4.4: Create Automation Scripts for Repetitive Tasks

**Purpose**: Automate manual, error-prone tasks to improve developer productivity.

**Implementation Steps**:

1. Create API documentation generation script:

   **File**: `scripts/generate-docs.sh`
   ```bash
   #!/bin/bash
   set -e

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   NC='\033[0m' # No Color

   echo -e "${YELLOW}Generating API Documentation...${NC}"

   # Check if swagger-jsdoc is installed
   if ! [ -x "$(command -v swagger-jsdoc)" ]; then
     echo "Installing swagger-jsdoc..."
     npm install -g swagger-jsdoc
   fi

   # Create docs directory if it doesn't exist
   mkdir -p docs

   # Generate OpenAPI spec from JSDoc comments
   swagger-jsdoc -d swagger.config.js -o docs/openapi.json

   # Generate HTML documentation
   npx redoc-cli bundle docs/openapi.json -o docs/index.html

   echo -e "${GREEN}Documentation generated successfully!${NC}"
   echo "API Spec: docs/openapi.json"
   echo "HTML Documentation: docs/index.html"
   ```

2. Create deployment script:

   **File**: `scripts/deploy.sh`
   ```bash
   #!/bin/bash
   set -e

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   RED='\033[0;31m'
   NC='\033[0m' # No Color

   # Parse arguments
   ENV="staging"

   while getopts "e:" opt; do
     case $opt in
       e) ENV=$OPTARG ;;
       *) echo "Usage: $0 [-e environment]" && exit 1 ;;
     esac
   done

   if [ "$ENV" != "staging" ] && [ "$ENV" != "production" ]; then
     echo -e "${RED}Invalid environment. Use 'staging' or 'production'.${NC}"
     exit 1
   fi

   echo -e "${YELLOW}Deploying to $ENV environment...${NC}"

   # Run tests first
   echo "Running tests..."
   npm test

   if [ $? -ne 0 ]; then
     echo -e "${RED}Tests failed. Deployment aborted.${NC}"
     exit 1
   fi

   # Build the project
   echo "Building project..."
   npm run build

   # Deploy with Vercel CLI
   echo "Deploying with Vercel..."
   if [ "$ENV" = "production" ]; then
     vercel --prod
   else
     vercel
   fi

   echo -e "${GREEN}Deployment to $ENV complete!${NC}"
   ```

3. Create status monitoring script:

   **File**: `scripts/monitor.sh`
   ```bash
   #!/bin/bash

   # Function to display API status with color
   show_status() {
     local endpoint=$1
     local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/$endpoint)

     if [ "$response" -eq 200 ]; then
       echo -e "\033[0;32m✓ $endpoint: OK ($response)\033[0m"
     else
       echo -e "\033[0;31m✗ $endpoint: FAIL ($response)\033[0m"
     fi
   }

   clear
   echo "======================================"
   echo "      API Gateway Status Monitor      "
   echo "======================================"

   # Show container stats
   echo
   echo "Container Stats:"
   docker stats --no-stream api-gateway

   # Show API endpoints status
   echo
   echo "API Endpoints:"
   show_status "healthz"
   show_status "api/v1/status"

   # Monitor logs in real-time
   echo
   echo "Recent Logs:"
   docker logs --tail 10 api-gateway

   echo
   echo "Press Ctrl+C to exit"

   # Run the script in a loop for continuous monitoring
   if [ "$1" = "--watch" ]; then
     sleep 5
     exec $0
   fi
   ```

4. Make scripts executable:
   ```bash
   chmod +x scripts/generate-docs.sh scripts/deploy.sh scripts/monitor.sh
   ```

**Verification Steps**:
1. Test the API documentation generation script
   ```bash
   # Create a basic swagger config first
   cat > swagger.config.js << 'EOF'
   module.exports = {
     swaggerDefinition: {
       openapi: '3.0.0',
       info: {
         title: 'API Gateway',
         version: '1.0.0',
         description: 'API Gateway Documentation',
       },
     },
     apis: ['./src/**/*.js'],
   };
   EOF

   # Add a sample JSDoc comment to a route file
   mkdir -p src/routes
   cat > src/routes/example.js << 'EOF'
   /**
    * @swagger
    * /healthz:
    *   get:
    *     summary: Health check endpoint
    *     responses:
    *       200:
    *         description: API is healthy
    */
   EOF

   # Run the script
   ./scripts/generate-docs.sh
   ```
   - Verify that docs directory is created
   - Confirm openapi.json is generated
   - Check that index.html is created and can be opened in a browser

2. Test the deployment script (with mock deployment)
   ```bash
   # Create a mock build and test script
   echo '#!/bin/bash\necho "Building project..."\nexit 0' > build-test.sh
   chmod +x build-test.sh

   # Temporarily modify package.json to use our mock script
   sed -i.bak 's/"test": ".*"/"test": ".\/build-test.sh"/' package.json
   sed -i.bak 's/"build": ".*"/"build": ".\/build-test.sh"/' package.json

   # Run the script with dry-run mode
   VERCEL_CLI="echo would run vercel" ./scripts/deploy.sh

   # Restore original package.json
   mv package.json.bak package.json
   ```
   - Verify the script executes the tests and build commands
   - Confirm it selects the right deployment command based on environment

3. Test the monitoring script
   ```bash
   # Ensure API container is running
   docker-compose up -d api-gateway

   # Run the script
   ./scripts/monitor.sh
   ```
   - Verify it shows container stats
   - Confirm it checks endpoint status with color-coding
   - Check that it displays recent logs

### Task 4.5: Create Console-Based Metrics and Visual Feedback

**Purpose**: Provide quick insights for development and debugging.

**Implementation Steps**:

1. Create a basic monitoring script:

   **File**: `scripts/monitor.sh`
   ```bash
   #!/bin/bash

   # Colors for better visibility
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   RED='\033[0;31m'
   BLUE='\033[0;34m'
   NC='\033[0m' # No Color

   # Default interval
   INTERVAL=5

   # Parse arguments
   while getopts "i:" opt; do
     case $opt in
       i) INTERVAL=$OPTARG ;;
       *) echo "Usage: $0 [-i interval_in_seconds]" && exit 1 ;;
     esac
   done

   # Function to clear the screen and show header
   show_header() {
     clear
     echo -e "${BLUE}====================================${NC}"
     echo -e "${BLUE}   API Gateway Monitoring Tool      ${NC}"
     echo -e "${BLUE}====================================${NC}"
     echo -e "Refreshing every ${INTERVAL} seconds. Press Ctrl+C to exit."
     echo
   }

   # Function to show Docker status
   show_docker_status() {
     echo -e "${YELLOW}CONTAINER STATUS:${NC}"
     docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep api-gateway
     echo

     echo -e "${YELLOW}RESOURCE USAGE:${NC}"
     docker stats --no-stream api-gateway
     echo
   }

   # Function to show API health
   show_api_health() {
     echo -e "${YELLOW}API HEALTH:${NC}"

     # Check API health endpoint
     HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/healthz)

     if [ "$HEALTH_STATUS" -eq 200 ]; then
       echo -e "${GREEN}Health Check: ✓ OK ($HEALTH_STATUS)${NC}"
     else
       echo -e "${RED}Health Check: ✗ FAIL ($HEALTH_STATUS)${NC}"
     fi

     echo
   }

   # Function to show recent logs
   show_recent_logs() {
     echo -e "${YELLOW}RECENT LOGS:${NC}"
     docker logs --tail 10 api-gateway
     echo
   }

   # Function to show ASCII chart of requests
   show_request_chart() {
     echo -e "${YELLOW}REQUEST RATE (last minute):${NC}"

     # This would normally parse from logs to get actual data
     # Here we're generating random data for demonstration
     for i in {1..10}; do
       COUNT=$((RANDOM % 20))
       BAR=$(printf '%*s' "$COUNT" | tr ' ' '█')
       echo -e "$(date -d "-$i min" "+%H:%M"): $BAR $COUNT req/s"
     done

     echo
   }

   # Main monitoring loop
   while true; do
     show_header
     show_docker_status
     show_api_health
     show_recent_logs
     show_request_chart

     sleep $INTERVAL
   done
   ```

2. Create a project structure visualization script:

   **File**: `scripts/visualize-structure.sh`
   ```bash
   #!/bin/bash

   # Check if tree command is available
   if ! [ -x "$(command -v tree)" ]; then
     echo "Error: tree command not found. Please install it first."
     echo "MacOS: brew install tree"
     echo "Linux: apt-get install tree"
     exit 1
   fi

   # Define colors
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   BLUE='\033[0;34m'
   NC='\033[0m' # No Color

   # Header
   echo -e "${BLUE}=====================================${NC}"
   echo -e "${BLUE}   API Gateway Project Structure     ${NC}"
   echo -e "${BLUE}=====================================${NC}"

   # Generate project tree, excluding node_modules and other non-essential directories
   echo -e "${GREEN}Source Code Structure:${NC}"
   tree -L 3 -I "node_modules|coverage|.git|dist|logs" ./src

   echo
   echo -e "${YELLOW}Configuration Files:${NC}"
   tree -L 1 -I "node_modules|coverage|.git|dist|logs|src|scripts|tests" .

   echo
   echo -e "${GREEN}Test Structure:${NC}"
   tree -L 3 -I "node_modules|coverage|.git|dist|logs" ./tests

   # Print summary
   echo
   echo -e "${BLUE}Summary:${NC}"
   echo -e "Total source files: $(find ./src -type f | wc -l)"
   echo -e "Total test files: $(find ./tests -type f | wc -l)"
   echo -e "Total script files: $(find ./scripts -type f | wc -l)"
   ```

3. Make scripts executable:
   ```bash
   chmod +x scripts/monitor.sh scripts/visualize-structure.sh
   ```

**Verification Steps**:
1. Test the monitoring script with different refresh intervals
   ```bash
   # Run with default interval
   ./scripts/monitor.sh

   # Run with custom interval
   ./scripts/monitor.sh -i 10
   ```
   - Verify that it shows Docker stats and health checks
   - Confirm that the ASCII charts render correctly
   - Check that it refreshes at the specified interval
   - Press Ctrl+C to exit and confirm it terminates cleanly

2. Test the project structure visualization script
   ```bash
   # Install tree if needed
   # macOS: brew install tree
   # Ubuntu: apt-get install tree

   # Run the script
   ./scripts/visualize-structure.sh
   ```
   - Verify it correctly displays the project structure
   - Confirm it excludes the specified directories
   - Check that the summary counts are accurate

## Phase 5: Testing & Best Practices

### Concept Overview

Ensure the project maintains high reliability and quality by enforcing testing, linting, and security best practices.

### Task 5.1: Robust Testing and Code Quality Practices

**Purpose**: Write comprehensive tests for the API Gateway using Jest, Supertest, and other testing frameworks.

**Dependencies**:
- Jest testing framework
- Supertest for HTTP testing
- Node.js API Gateway project

**Implementation Steps**:

1. Install testing dependencies:
   ```bash
   npm install --save-dev jest supertest @types/jest @types/supertest
   ```

2. Configure Jest in package.json:
   ```json
   {
     "scripts": {
       "test": "jest",
       "test:watch": "jest --watch",
       "test:coverage": "jest --coverage"
     },
     "jest": {
       "testEnvironment": "node",
       "coverageThreshold": {
         "global": {
           "branches": 80,
           "functions": 80,
           "lines": 80,
           "statements": 80
         }
       },
       "collectCoverageFrom": [
         "src/**/*.js",
         "!src/server.js"
       ]
     }
   }
   ```

3. Write unit tests for utility functions:

   **File**: `tests/unit/auth.test.js`
   ```javascript
   const { verifyToken, checkRole } = require('../../src/middleware/auth');
   const jwt = require('jsonwebtoken');

   // Mock environment variables and jwt functions
   process.env.JWT_SECRET = 'test_secret';
   jwt.verify = jest.fn();

   describe('Auth Middleware', () => {
     let req, res, next;

     beforeEach(() => {
       req = {
         headers: {
           authorization: 'Bearer valid_token'
         }
       };
       res = {
         status: jest.fn().mockReturnThis(),
         json: jest.fn()
       };
       next = jest.fn();
     });

     afterEach(() => {
       jest.clearAllMocks();
     });

     test('verifyToken passes valid tokens', () => {
       jwt.verify.mockReturnValue({ id: 1, role: 'user' });

       verifyToken(req, res, next);

       expect(jwt.verify).toHaveBeenCalledWith('valid_token', 'test_secret');
       expect(req.user).toEqual({ id: 1, role: 'user' });
       expect(next).toHaveBeenCalled();
       expect(res.status).not.toHaveBeenCalled();
     });

     test('verifyToken rejects requests without token', () => {
       req.headers.authorization = undefined;

       verifyToken(req, res, next);

       expect(jwt.verify).not.toHaveBeenCalled();
       expect(res.status).toHaveBeenCalledWith(401);
       expect(res.json).toHaveBeenCalledWith({ message: 'No token provided' });
       expect(next).not.toHaveBeenCalled();
     });
   });
   ```

4. Write integration tests with Supertest:

   **File**: `tests/integration/routes.test.js`
   ```javascript
   const request = require('supertest');
   const { app } = require('../../src/server');
   const jwt = require('jsonwebtoken');

   // Mock environment variables
   process.env.JWT_SECRET = 'test_secret';

   describe('API Routes', () => {
     test('Health endpoint returns 200', async () => {
       const response = await request(app).get('/healthz');
       expect(response.statusCode).toBe(200);
       expect(response.body).toHaveProperty('status', 'ok');
     });

     test('Protected route rejects unauthorized requests', async () => {
       const response = await request(app).get('/protected');
       expect(response.statusCode).toBe(401);
     });

     test('Protected route allows authorized requests', async () => {
       // Create a valid token
       const token = jwt.sign({ id: 1, role: 'user' }, process.env.JWT_SECRET);

       const response = await request(app)
         .get('/protected')
         .set('Authorization', `Bearer ${token}`);

       expect(response.statusCode).toBe(200);
       expect(response.body).toHaveProperty('message', 'Protected endpoint');
     });
   });
   ```

5. Set up test coverage reporting:
   ```bash
   mkdir -p coverage
   ```

**Verification Steps**:
1. Run the test suite
   ```bash
   npm test
   ```
   - Verify that all tests pass without errors

2. Check test coverage
   ```bash
   npm run test:coverage
   ```
   - Verify that coverage exceeds the defined thresholds
   - Review the coverage report (usually in coverage/lcov-report/index.html)
   - Identify any critical code paths that lack test coverage

3. Verify tests cover edge cases
   - Check that error conditions are tested
   - Verify that boundary cases are handled
   - Ensure authentication/authorization is thoroughly tested

### Task 5.2: Testing Best Practices

**Purpose**: Implement testing best practices to ensure reliable, maintainable tests.

**Implementation Steps**:

1. Structure tests with descriptive blocks:

   **File**: `tests/unit/rate-limit.test.js`
   ```javascript
   const { apiLimiter, authLimiter } = require('../../src/middleware/rate-limit');

   describe('Rate Limiting Middleware', () => {
     describe('API Rate Limiter', () => {
       test('has correct window size', () => {
         expect(apiLimiter.windowMs).toBe(15 * 60 * 1000); // 15 minutes
       });

       test('has correct request limit', () => {
         expect(apiLimiter.max).toBe(100);
       });
     });

     describe('Auth Rate Limiter', () => {
       test('has correct window size', () => {
         expect(authLimiter.windowMs).toBe(60 * 60 * 1000); // 1 hour
       });

       test('has correct attempt limit', () => {
         expect(authLimiter.max).toBe(5);
       });

       test('only counts failed requests', () => {
         expect(authLimiter.skipSuccessfulRequests).toBe(true);
       });
     });
   });
   ```

2. Create test fixtures and mock data:

   **File**: `tests/fixtures/users.js`
   ```javascript
   module.exports = {
     validUser: {
       id: 1,
       username: 'testuser',
       email: 'test@example.com',
       role: 'user'
     },
     adminUser: {
       id: 2,
       username: 'admin',
       email: 'admin@example.com',
       role: 'admin'
     },
     invalidUser: {
       username: 'test',
       // Missing required email
     }
   };
   ```

3. Implement test helpers for common operations:

   **File**: `tests/helpers/auth.js`
   ```javascript
   const jwt = require('jsonwebtoken');

   /**
    * Generate a test JWT token for a given user
    */
   function generateToken(user, secret = process.env.JWT_SECRET) {
     return jwt.sign(user, secret, { expiresIn: '1h' });
   }

   /**
    * Create an authorization header with Bearer token
    */
   function authHeader(user, secret) {
     const token = generateToken(user, secret);
     return { Authorization: `Bearer ${token}` };
   }

   module.exports = {
     generateToken,
     authHeader
   };
   ```

4. Set up test environment cleanup:

   **File**: `tests/setup.js`
   ```javascript
   // Global test setup and teardown

   // Mock environment variables
   process.env.NODE_ENV = 'test';
   process.env.JWT_SECRET = 'test_secret';
   process.env.PORT = '3001';

   // Global before all tests
   beforeAll(() => {
     // Setup test database or other resources
     console.log('Setting up test environment');
   });

   // Global after all tests
   afterAll(() => {
     // Cleanup resources
     console.log('Tearing down test environment');
   });
   ```

**Verification Steps**:
1. Run tests with watch mode during development
   ```bash
   npm run test:watch
   ```
   - Verify that tests rerun automatically when code changes
   - Confirm tests remain fast (under 10 seconds for the full suite)

2. Verify test organization
   - Check that tests use descriptive blocks and names
   - Confirm that fixtures and helpers are used consistently
   - Ensure test files are organized in a logical structure

3. Examine test output
   - Verify that test failures provide clear error messages
   - Confirm that test reports are easy to interpret

### Task 5.3: Code Linting and Formatting

**Purpose**: Maintain a consistent code style using ESLint and Prettier.

**Dependencies**:
- ESLint for code quality and style enforcement
- Prettier for code formatting

**Implementation Steps**:

1. Install linting and formatting dependencies:
   ```bash
   npm install --save-dev eslint prettier eslint-config-prettier eslint-plugin-prettier
   ```

2. Create ESLint configuration:

   **File**: `.eslintrc.js`
   ```javascript
   module.exports = {
     "env": {
       "node": true,
       "es6": true,
       "jest": true
     },
     "extends": [
       "eslint:recommended",
       "plugin:prettier/recommended"
     ],
     "parserOptions": {
       "ecmaVersion": 2020,
       "sourceType": "module"
     },
     "rules": {
       "no-console": "warn",
       "no-unused-vars": ["error", { "argsIgnorePattern": "^_" }],
       "prettier/prettier": "error"
     }
   };
   ```

3. Create Prettier configuration:

   **File**: `.prettierrc.js`
   ```javascript
   module.exports = {
     semi: true,
     trailingComma: 'none',
     singleQuote: true,
     printWidth: 100,
     tabWidth: 2
   };
   ```

4. Add lint and format scripts to package.json:
   ```json
   {
     "scripts": {
       "lint": "eslint .",
       "lint:fix": "eslint --fix .",
       "format": "prettier --write \"**/*.{js,json,md}\"",
       "format:check": "prettier --check \"**/*.{js,json,md}\""
     }
   }
   ```

5. Set up Git hooks (optional) with Husky:
   ```bash
   npm install --save-dev husky lint-staged
   ```

   Add to package.json:
   ```json
   {
     "husky": {
       "hooks": {
         "pre-commit": "lint-staged"
       }
     },
     "lint-staged": {
       "*.js": ["eslint --fix", "prettier --write"],
       "*.{json,md}": ["prettier --write"]
     }
   }
   ```

**Verification Steps**:
1. Run linter on the codebase
   ```bash
   npm run lint
   ```
   - Verify it identifies code style issues
   - Check that errors are clear and actionable

2. Test automatic fixing
   ```bash
   # Create a test file with style issues
   echo "const x = 'test' ; const y =   'test2'" > style-test.js

   # Run the fix command
   npm run lint:fix

   # Check the result
   cat style-test.js
   ```
   - Verify the file is properly formatted

3. Check CI integration
   - Ensure linting is part of the CI workflow
   - Verify that the build fails if linting fails

### Task 5.4: Security Best Practices in Code

**Purpose**: Incorporate security checks and tests as part of development.

**Dependencies**:
- Helmet for security headers
- Security testing tools

**Implementation Steps**:

1. Ensure Helmet is properly configured:

   **File**: `src/server.js` (update)
   ```javascript
   // Secure headers configuration
   app.use(helmet({
     contentSecurityPolicy: {
       directives: {
         defaultSrc: ["'self'"],
         scriptSrc: ["'self'"],
         styleSrc: ["'self'", "'unsafe-inline'"],
         imgSrc: ["'self'", "data:"]
       }
     },
     hsts: {
       maxAge: 31536000, // 1 year
       includeSubDomains: true,
       preload: true
     }
   }));
   ```

2. Create security tests for headers:

   **File**: `tests/security/headers.test.js`
   ```javascript
   const request = require('supertest');
   const { app } = require('../../src/server');

   describe('Security Headers', () => {
     test('Response includes security headers', async () => {
       const response = await request(app).get('/healthz');

       // Check for important security headers
       expect(response.headers).toHaveProperty('x-content-type-options', 'nosniff');
       expect(response.headers).toHaveProperty('x-xss-protection', '1; mode=block');
       expect(response.headers).toHaveProperty('x-frame-options', 'SAMEORIGIN');
       expect(response.headers).toHaveProperty('strict-transport-security');
       expect(response.headers).toHaveProperty('content-security-policy');
     });

     test('CORS headers are properly set', async () => {
       const response = await request(app)
         .get('/healthz')
         .set('Origin', 'https://example.com');

       expect(response.headers).toHaveProperty('access-control-allow-origin');
     });
   });
   ```

3. Install and configure dependency security scanning:
   ```bash
   npm install --save-dev npm-audit-resolver
   ```

   Add to package.json:
   ```json
   {
     "scripts": {
       "security:audit": "npm audit",
       "security:fix": "npm audit fix",
       "security:resolve": "resolve-audit"
     }
   }
   ```

4. Implement input validation tests:

   **File**: `tests/security/validation.test.js`
   ```javascript
   const request = require('supertest');
   const { app } = require('../../src/server');
   const { authHeader } = require('../helpers/auth');
   const { adminUser } = require('../fixtures/users');

   describe('Input Validation', () => {
     test('Rejects invalid data in request body', async () => {
       const response = await request(app)
         .post('/api/users')
         .set(authHeader(adminUser))
         .send({
           username: 'a', // Too short - should fail validation
           email: 'not-an-email',
           password: '12345' // Too short - should fail validation
         });

       expect(response.statusCode).toBe(400);
       expect(response.body).toHaveProperty('message', 'Validation error');
     });

     test('Sanitizes output to prevent XSS', async () => {
       // Create a user with potentially harmful content
       const user = {
         name: '<script>alert("XSS")</script>User'
       };

       // Mock user service to return this user
       // Implementation depends on your app structure

       const response = await request(app)
         .get('/api/users/profile')
         .set(authHeader(user));

       // Check that the script tag was escaped/sanitized
       expect(response.text).not.toContain('<script>');
     });
   });
   ```

**Verification Steps**:
1. Run security header tests
   ```bash
   npm test -- -t "Security Headers"
   ```
   - Verify all security headers are present
   - Confirm CORS is properly configured

2. Perform dependency security audit
   ```bash
   npm run security:audit
   ```
   - Check for vulnerable dependencies
   - Address any high-severity issues found

3. Test input validation
   ```bash
   npm test -- -t "Input Validation"
   ```
   - Verify invalid inputs are rejected
   - Confirm potential XSS attacks are mitigated

4. Review authentication tests
   ```bash
   npm test -- -t "Auth"
   ```
   - Ensure authentication flows are thoroughly tested
   - Verify token validation works correctly

### Task 5.5: Additional Best Practices

**Purpose**: Maintain clear API documentation, run load tests, and periodically review the project against a security checklist.

**Implementation Steps**:

1. Set up OpenAPI/Swagger documentation:
   ```bash
   npm install --save-dev swagger-jsdoc swagger-ui-express
   ```

   **File**: `src/docs/swagger.js`
   ```javascript
   const swaggerJSDoc = require('swagger-jsdoc');

   const options = {
     definition: {
       openapi: '3.0.0',
       info: {
         title: 'API Gateway',
         version: '1.0.0',
         description: 'Documentation for the API Gateway'
       },
       servers: [
         {
           url: 'http://localhost:3000',
           description: 'Development server'
         }
       ]
     },
     apis: ['./src/routes/*.js', './src/controllers/*.js']
   };

   module.exports = swaggerJSDoc(options);
   ```

2. Create a security checklist script:

   **File**: `scripts/security-checklist.sh`
   ```bash
   #!/bin/bash
   set -e

   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   RED='\033[0;31m'
   NC='\033[0m' # No Color

   echo -e "${YELLOW}Running API Gateway Security Checklist...${NC}"

   # Check for dependency vulnerabilities
   echo -e "\n${YELLOW}Checking dependencies for vulnerabilities...${NC}"
   npm audit --json | grep -c '"severity":"high"' > /dev/null && echo -e "${RED}High severity vulnerabilities found${NC}" || echo -e "${GREEN}No high severity vulnerabilities found${NC}"

   # Check for secrets in code
   echo -e "\n${YELLOW}Checking for secrets in code...${NC}"
   grep -r "password\|secret\|key\|token" --include="*.js" --include="*.json" --exclude-dir="node_modules" . | grep -v "process.env" > /dev/null && echo -e "${RED}Possible hardcoded secrets found${NC}" || echo -e "${GREEN}No hardcoded secrets found${NC}"

   # Check security headers (requires a running server)
   if curl -s http://localhost:3000/healthz > /dev/null; then
     echo -e "\n${YELLOW}Checking security headers...${NC}"
     curl -s -I http://localhost:3000/healthz | grep -i "x-content-type-options\|x-frame-options\|strict-transport-security" > /dev/null && echo -e "${GREEN}Security headers found${NC}" || echo -e "${RED}Security headers missing${NC}"
   else
     echo -e "${YELLOW}Server not running, skipping header checks${NC}"
   fi

   # Run ESLint security plugins if installed
   if npm list | grep eslint-plugin-security > /dev/null; then
     echo -e "\n${YELLOW}Running security linting...${NC}"
     npx eslint . --plugin security -c .eslintrc.js --quiet || echo -e "${RED}Security linting found issues${NC}"
   fi

   echo -e "\n${GREEN}Security checklist complete${NC}"
   ```

3. Create a load testing script:

   **File**: `scripts/load-test.js`
   ```javascript
   const autocannon = require('autocannon');

   const instance = autocannon({
     url: 'http://localhost:3000/healthz',
     connections: 10,
     pipelining: 1,
     duration: 10
   }, (err, results) => {
     if (err) {
       console.error(err);
       process.exit(1);
     }
     console.log(results);
   });

   // Track progress
   autocannon.track(instance);

   // Log results to console
   process.once('SIGINT', () => {
     instance.stop();
   });
   ```

4. Add as npm scripts:
   ```json
   {
     "scripts": {
       "docs": "node src/docs/generate.js",
       "security:check": "./scripts/security-checklist.sh",
       "load:test": "node scripts/load-test.js"
     }
   }
   ```

**Verification Steps**:
1. Generate and check API documentation
   ```bash
   npm run docs
   ```
   - Open the generated documentation in a browser
   - Verify all endpoints are documented
   - Confirm request/response schemas are accurate

2. Run the security checklist
   ```bash
   chmod +x scripts/security-checklist.sh
   npm run security:check
   ```
   - Address any issues identified
   - Verify all checks complete successfully

3. Perform a load test (on non-production environment)
   ```bash
   npm install --save-dev autocannon
   npm run load:test
   ```
   - Check response times under load
   - Verify the API can handle expected traffic
   - Identify any performance bottlenecks

## Phase 6: Environment & Secrets Management

### Concept Overview

Properly handle environment-specific settings (like API keys, database URLs, etc.) using environment variables and ensure secrets are not exposed.

### Task 6.1: dotenv for Local Development

**Purpose**: Use the dotenv package to load variables from a .env file into process.env.

**Implementation Steps**:

1. Use the dotenv package to load variables from a .env file into process.env
2. In development, maintain a .env file in the project root with entries like DB_PASSWORD=... and API_KEY=....
3. Call require('dotenv').config() in the app (e.g., in index.js before anything else)

**Verification**:
1. Run the app and verify that it loads environment variables correctly
2. Verify that the .env file is populated correctly

### Task 6.2: Never Commit Secrets

**Purpose**: Do not commit the actual .env file or any secrets to the repository.

**Implementation Steps**:

1. Add .env to .gitignore to ensure it's not tracked
2. Ensure that these values are provided through secure means in the CI/CD and production environment
3. Developers should avoid logging secrets or printing them in console

**Verification**:
1. Push to a branch and verify that .env is not committed
2. Verify that the CI/CD pipeline uses secure methods to inject env vars

### Task 6.3: Multiple Environments Configuration

**Purpose**: Manage separate configurations for development, staging, and production.

**Implementation Steps**:

1. Use multiple .env files (like .env.development, .env.staging, .env.production) and load the appropriate one based on an environment variable or Node environment
2. Alternatively, for a deployment on Vercel, set actual environment variables in the project settings
3. Vercel allows defining Environment Variables for Development (local/preview builds) and Production separately
4. Replicate staging by using Vercel's Preview environment

**Verification**:
1. Deploy to staging and verify that it uses the correct .env file
2. Deploy to production and verify that it uses the correct .env file

### Task 6.4: Secure Handling of Sensitive Variables

**Purpose**: Ensure that sensitive data (passwords, keys, tokens) are only present in secure storage.

**Implementation Steps**:

1. In development, .env is fine but treat that file carefully
2. In production, do not use a .env file on disk; instead use the platform's secret management
3. For Vercel, set the env vars in the Vercel dashboard or via vercel cli (vercel env add)
4. Rotate secrets if needed (change them periodically or if someone leaves the team)
5. Use least privilege principles: for example, if the API Gateway only needs read access to a database, use read-only credentials
6. Avoid printing env vars in logs
7. Provide default values in code where appropriate (for non-secret config)

**Verification**:
1. Deploy to production and verify that sensitive data is not exposed
2. Verify that the platform secret management is used correctly

### Task 6.5: Use of Secret Management Services

**Purpose**: For enterprise scenarios or added security, consider using a dedicated secrets manager.

**Implementation Steps**:

1. Consider using a dedicated secrets manager (like HashiCorp Vault, AWS Secrets Manager, etc.)
2. Instead of storing secrets directly in env vars, the app could fetch them from a secure store at runtime
3. Vercel's solution is usually sufficient for most cases (as it encrypts at rest and in transit to the build)
4. Rotate secrets if needed (change them periodically or if someone leaves the team)
5. Use least privilege principles: for example, if the API Gateway only needs read access to a database, use read-only credentials
6. Avoid printing env vars in logs
7. Provide default values in code where appropriate (for non-secret config)

**Verification**:
1. Deploy to production and verify that sensitive data is not exposed
2. Verify that the secrets manager is used correctly

### Task 6.6: Testing and CI with Env Vars

**Purpose**: When running tests, you might have a separate .env.test or simply supply necessary env vars in the test command.

**Implementation Steps**:

1. In package.json test script: ENV=test JWT_SECRET=testsecret npm test
2. In CI, define those in the workflow file or use GitHub Actions secrets for anything sensitive
3. The goal is to make tests and builds reproducible by explicitly providing needed env configuration

**Verification**:
1. Run the test suite and verify that it runs with the correct env vars
2. Verify that the test suite is reproducible

### Task 6.7: Preventing Leaks

**Purpose**: Double-check that no secret or env-specific config is accidentally hardcoded.

**Implementation Steps**:

1. Review any error reporting or bundling process to ensure secrets aren't included
2. Ensure that no code like if (dev) use API key XYZ in the code – always pull from env so that switching environments doesn't require code changes
3. Ensure that no config is sent to front-end if it's not safe

**Verification**:
1. Push to a branch and verify that no secrets are hardcoded
2. Verify that the code is secure and doesn't expose sensitive information

## Phase 7: UI/UX Considerations

### Concept Overview

Although the API Gateway is a backend component, its design greatly impacts the UI/UX of the client applications that consume it.

### Task 7.1: Front-End Experience (UI/UX) Alignment

**Purpose**: Ensure that any projects built on this environment can deliver advanced visualizations and animations smoothly.

**Implementation Steps**:

1. Optimize the API for performance and enable capabilities that modern rich UIs require
2. Ensure that the API Gateway responds quickly and enables HTTP compression
3. Enable Cross-Origin Resource Sharing (CORS) on the API Gateway
4. Consider supporting WebSockets or Server-Sent Events (SSE) in the API Gateway
5. Plan the API responses in a way that is convenient for the front-end
6. Include front-end performance considerations in the deployment pipeline
7. Ensure that adding new features to the gateway does not degrade response times beyond acceptable thresholds

**Verification**:
1. Deploy to staging and verify that the API responds quickly and enables HTTP compression
2. Verify that the API Gateway supports WebSockets or SSE
3. Verify that the API responses are convenient for the front-end
4. Verify that the API's performance does not degrade response times

### Task 7.2: UI Performance Testing

**Purpose**: Include front-end performance considerations in the deployment pipeline.

**Implementation Steps**:

1. If the project includes a front-end, use tools like Lighthouse CI to test performance budgets
2. Although this is more on the front-end side, the API's performance will indirectly factor into those scores
3. Ensure that adding new features to the gateway does not degrade response times beyond acceptable thresholds

**Verification**:
1. Deploy to staging and verify that the API's performance is considered in the deployment pipeline
2. Verify that the API's performance does not degrade response times

### Task 7.3: Animations and Data Loading

**Purpose**: For smooth animations, the UI might use techniques like lazy loading or incremental data loading.

**Implementation Steps**:

1. Ensure that the API supports pagination or partial data requests where applicable
2. For instance, if a chart can animate data in chunks, provide endpoints that allow fetching data ranges or subscribing to updates
3. Document these capabilities so front-end developers can utilize them to optimize user experience

**Verification**:
1. Deploy to staging and verify that the API supports pagination or partial data requests
2. Verify that the API's capabilities are documented

### Task 7.4: Static Asset Delivery

**Purpose**: If the API Gateway also serves as a host for any static content, ensure those are served with proper caching headers and from a CDN edge.

**Implementation Steps**:

1. Ensure that static assets are served with proper caching headers and from a CDN edge
2. Vercel automatically handles static assets via their CDN

**Verification**:
1. Deploy to staging and verify that static assets are served with proper caching headers and from a CDN edge
2. Verify that the API's static assets are served correctly

### Task 7.5: Testing UI/API Integration

**Purpose**: As part of QA, test the integrated system: run the front-end against the staging API to see that animations and visualizations work well with real response times and data sizes.

**Implementation Steps**:

1. Run the front-end against the staging API to see that animations and visualizations work well with real response times and data sizes
2. If any jank or delay is observed in the UI, consider whether the API can be adjusted to meet the UX needs

**Verification**:
1. Deploy to staging and verify that the API's performance is considered in the deployment pipeline
2. Verify that the API's performance does not degrade response times

### Task 7.6: UX Feedback Loop

**Purpose**: Implement monitoring on the client (like Real User Monitoring) that can report if certain API calls are slow for users.

**Implementation Steps**:

1. Implement monitoring on the client (like Real User Monitoring) that can report if certain API calls are slow for users
2. This will feed back into improving the gateway
3. Also, use the logging in the gateway to detect if any request patterns from the UI are inefficient
4. With that insight, you could tweak either the UI or provide a new API method that is more suited, thereby improving overall UX

**Verification**:
1. Deploy to staging and verify that the API's performance is considered in the deployment pipeline
2. Verify that the API's performance does not degrade response times

## Phase 8: Environment Maintenance Scripts

### Concept Overview

To maintain a high-performance development environment for the Node.js API Gateway, we introduce modular shell scripts that automate routine maintenance.

### Task 8.1: Menu-Based Orchestration Script

**Purpose**: A menu-driven orchestration script serves as a central entry point for maintenance tasks.

**Implementation Steps**:

1. Create a Bash script that presents a user-friendly menu to choose between tasks (cleanup, directory structuring, performance optimization, etc.)
2. The script can even handle scheduling for regular maintenance runs
3. The script acts as an orchestrator – it calls subordinate scripts or functions for each task

**Verification**:
1. Run the menu script and verify that it presents a user-friendly menu
2. Verify that the script can handle scheduling

### Task 8.2: Directory Management & Cleanup Tasks

**Purpose**: Enforce a clean project structure and remove unnecessary files.

**Implementation Steps**:

1. Ensure that the Node.js project follows industry-standard directory practices
2. Remove unnecessary files that are not needed for source control
3. Use targeted rm commands or patterns to delete such files
4. Use Git to clean the workspace
5. Clear out any logs or temp files that accumulate

**Verification**:
1. Run the directory management script and verify that it enforces the correct directory structure
2. Verify that the repository is free of clutter

### Task 8.3: Performance Optimization for Cursor AI Editor and VSCode

**Purpose**: Introduce script-driven tweaks to ensure these tools run smoothly with our Node.js API Gateway codebase.

**Implementation Steps**:

1. Manage VSCode settings that impact performance
2. Adjust the file explorer and search exclusions
3. Ensure that large generated folders are excluded from VSCode's indexing
4. Manage VSCode extensions and remove unused ones
5. Clear Cursor's cache or temporary data
6. Optimize Node.js language server settings

**Verification**:
1. Run the editor optimization script and verify that it improves editor responsiveness
2. Verify that the editor's intellisense and Cursor's analysis focus only on relevant code

### Task 8.4: System-Level Optimizations

**Purpose**: Ensure the underlying machine (developer's workstation or CI runner) runs efficiently.

**Implementation Steps**:

1. Monitor system memory and swap usage
2. Alert the user or take action if free memory is below a threshold
3. Identify memory-heavy processes and log them
4. Advise a reboot if the system has memory leaks
5. Monitor disk utilization and perform automated cleanup or optimizations
6. Integrate system monitoring with scheduling
7. Monitor CPU load and flag anomalies

**Verification**:
1. Run the system optimization script and verify that it improves system performance
2. Verify that the system remains healthy and responsive

### Task 8.5: CI/CD Pipeline Integration

**Purpose**: Integrate these maintenance scripts into the CI/CD pipeline to ensure they run consistently and benefit all team members.

**Implementation Steps**:

1. Pre-Build Cleanup Stage: Invoke the directory management & cleanup script before installing dependencies or building the project
2. Post-Build/Post-Deploy Maintenance: Run another job to perform cleanup after a successful build or deployment
3. Regular Scheduled Runs: Configure a scheduled pipeline to run the full maintenance suite
4. Integration in Developer Workflow: Run the maintenance script locally as needed
5. Continuous Monitoring in CI: Incorporate system-level monitoring into pipeline steps
6. Ensure No Impact on Production: Scope script execution to development or CI environments

**Verification**:
1. Run the CI/CD pipeline and verify that maintenance scripts run consistently
2. Verify that the pipeline remains clean and efficient

## Conclusion

This updated plan enhances the Node.js API Gateway project's environment maintenance by introducing robust, modular shell scripts. Through a menu-based orchestrator, developers can easily execute tasks on demand or schedule them. The scripts rigorously enforce project structure and cleanliness, remove waste files, and tune development tools for performance. System resource monitors guard against slowdowns due to low memory or disk space, automatically reclaiming space as needed. By integrating all these measures into the CI/CD pipeline, the project benefits from consistent housekeeping: every build and developer environment remains clean, efficient, and aligned with best practices. This not only speeds up the development cycle and editor responsiveness but also reduces the likelihood of build failures and environment-specific bugs. Ultimately, the combination of these scripting strategies contributes to a well-maintained, high-performance development environment for the API Gateway, allowing the team to focus on feature development and quality.






[SEQUENCE STEP 1]
User          Frontend            API Layer           Backend             OpenAI             Database
 |                |                   |                  |                   |                   |
 |                |                   |                  |                   |                   |
 | Visit App      |                   |                  |                   |                   |
 |--------------->|                   |                  |                   |                   |
 |                | GET /session/init |                  |                   |                   |
 |                |------------------>|                  |                   |                   |
 |                |                   | Create Session   |                   |                   |
 |                |                   |----------------->|                   |                   |
 |                |                   |                  | Store Session     |                   |
 |                |                   |                  |-------------------------------------->|
 |                |                   |                  |                   |                   |
 |                |                   |                  |     Session ID    |                   |
 |                |                   |                  |<--------------------------------------|
 |                |                   |   Session Data   |                   |                   |
 |                |                   |<-----------------|                   |                   |
 |                |    Session Token  |                  |                   |                   |
 |                |<------------------|                  |                   |                   |
 |                |                   |                  |                   |                   |


[SEQUENCE 1 CONSOLE DISPLAY]

| INPUT       |   OUTPUT         |
|-------------|------------------|
| USER RUNS   |  {SESSION TOKEN} |
| THE SCRIPT  |                  |
|-------------|------------------|

=================================================

[SEQUENCE STEP 2]
User          Frontend            API Layer           Backend             OpenAI             Database
 |                |                   |                  |                   |                   |
 |                |                   |                  |                   |                   |
 | Enter Location |                   |                  |                   |                   |
 |--------------->|                   |                  |                   |                   |
 |                | POST /geocode     |                  |                   |                   |
 |                | {query: "NYC"}    |                  |                   |                   |
 |                |------------------>|                  |                   |                   |
 |                |                   | Process Location |                   |                   |
 |                |                   |----------------->|                   |                   |
 |                |                   |                  | Query Location DB |                   |
 |                |                   |                  |-------------------------------------->|
 |                |                   |                  |                   |                   |
 |                |                   |                  |    Coordinates    |                   |
 |                |                   |                  |<--------------------------------------|
 |                |                   | Location Data    |                   |                   |
 |                |                   |<-----------------|                   |                   |
 |                | {results: [{...}]}|                  |                   |                   |
 |                |<------------------|                  |                   |                   |
 |                |                   |                  |                   |                   |
 |                |                   |                  |                   |                   |


[SEQUENCE 2 CONSOLE DISPLAY]

| INPUT       |   OUTPUT         |
|-------------|------------------|
| USER ENTERS |  {LOCATION       |
|  LOCATION   |   DATA}          |
|  ON THE     |                  |
| CONSOLE     |                  |
|-------------|------------------|

=================================================
