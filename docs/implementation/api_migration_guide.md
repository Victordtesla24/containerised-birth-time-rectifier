# API Migration Guide

## Overview

We are standardizing our API Gateway to use a single registration pattern with
versioned endpoints. This document provides guidance for migrating from legacy
routes to the standardized API.

## Migration Timeline

- **Current Phase**: Legacy routes accepted with deprecation warnings
- **Phase 2** (3 months): Legacy routes return 301 redirects
- **Phase 3** (6 months): Legacy routes return 410 Gone status

## Path Mapping Reference

| Legacy Path | New Standardized Path |
|-------------|----------------------|
| `/health` | `/api/v1/health` |
| `/geocode` | `/api/v1/geocode` |
| `/chart/validate` | `/api/v1/chart/validate` |
| `/chart/generate` | `/api/v1/chart/generate` |
| `/chart/{id}` | `/api/v1/chart/{id}` |
| `/chart/rectify` | `/api/v1/chart/rectify` |
| `/chart/export` | `/api/v1/chart/export` |
| `/questionnaire` | `/api/v1/questionnaire` |
| `/api/health` | `/api/v1/health` |
| `/api/geocode` | `/api/v1/geocode` |
| `/api/chart/validate` | `/api/v1/chart/validate` |
| `/api/chart/generate` | `/api/v1/chart/generate` |
| `/api/chart/{id}` | `/api/v1/chart/{id}` |
| `/api/chart/rectify` | `/api/v1/chart/rectify` |
| `/api/chart/export` | `/api/v1/chart/export` |
| `/api/questionnaire` | `/api/v1/questionnaire` |

## Upgrading Your API Client

### Basic Update

Simply update your API base URL to include the `/api/v1` prefix:

```javascript
// Old
const API_BASE = 'https://your-api-domain.com';

// New
const API_BASE = 'https://your-api-domain.com/api/v1';
```

### Monitoring Deprecation Warnings

The API will return an `X-Deprecation-Warning` header when using legacy routes.
Monitor these warnings to identify endpoints that need migration.

## Testing Your Migration

Use our test endpoint to verify your client is using the correct paths:

```
GET /api/v1/health
```

You should receive a response with the correct version information.

## Breaking Changes

There are no breaking changes in the response format or request parameters.
Only the URLs are changing to follow a consistent pattern.

## Client Library Updates

If you are using our client libraries, please update to the latest versions:

- JavaScript SDK: version 2.0.0+
- Python SDK: version 1.5.0+
- Mobile SDKs: version 3.0.0+

These versions automatically use the new endpoint structure.

## Questions and Support

If you have any questions about the migration process, please contact our support team.
We're committed to making this transition as smooth as possible for all users.
