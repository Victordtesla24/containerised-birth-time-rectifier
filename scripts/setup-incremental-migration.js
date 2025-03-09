#!/usr/bin/env node

/**
 * Incremental Migration Setup Script
 *
 * This script sets up the necessary configuration and utilities for
 * implementing an incremental migration strategy to Vercel based on
 * https://vercel.com/docs/incremental-migration
 *
 * It follows a vertical migration approach, where we migrate feature by feature
 * while keeping both systems running in parallel.
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const ROOT_DIR = process.cwd();
const SRC_DIR = path.join(ROOT_DIR, 'src');

// Console colors
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
};

console.log(`${colors.cyan}=== Birth Time Rectifier - Incremental Migration Setup ===${colors.reset}\n`);

// Helper functions
function ensureDirectoryExists(directory) {
  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }
}

// 1. Update vercel.json to support incremental deployment
function updateVercelConfig() {
  console.log(`${colors.yellow}Updating Vercel configuration for incremental migration...${colors.reset}`);

  const vercelConfigPath = path.join(ROOT_DIR, 'vercel.json');

  if (!fs.existsSync(vercelConfigPath)) {
    console.error(`${colors.red}vercel.json not found. Please run prepare-vercel-deployment.js first.${colors.reset}`);
    return false;
  }

  try {
    const vercelConfig = JSON.parse(fs.readFileSync(vercelConfigPath, 'utf8'));

    // Add or update rewrites for incremental migration
    // This will allow the new Vercel deployment to proxy requests to the legacy system
    // for features that haven't been migrated yet
    vercelConfig.rewrites = [
      // Keep existing rewrites if any
      ...(vercelConfig.rewrites || []),

      // Add fallback to legacy system if needed
      // Uncomment and modify when ready to implement
      // {
      //   "source": "/(.*)",
      //   "destination": "https://legacy-system.example.com/$1",
      //   "has": [
      //     {
      //       "type": "cookie",
      //       "key": "use_legacy_system",
      //       "value": "true"
      //     }
      //   ]
      // }
    ];

    // Ensure we have proper headers for both systems
    vercelConfig.headers = [
      // Keep existing headers
      ...(vercelConfig.headers || []),

      // Add any missing headers needed for incremental migration
      {
        "source": "/(.*)",
        "headers": [
          { "key": "X-Incremental-Migration", "value": "enabled" }
        ]
      }
    ];

    fs.writeFileSync(vercelConfigPath, JSON.stringify(vercelConfig, null, 2));
    console.log(`${colors.green}Updated${colors.reset} ${vercelConfigPath}`);
    return true;
  } catch (error) {
    console.error(`${colors.red}Error updating vercel.json:${colors.reset}`, error.message);
    return false;
  }
}

// 2. Create feature flag utilities
function createFeatureFlagUtilities() {
  console.log(`${colors.yellow}Creating feature flag utilities...${colors.reset}`);

  const utilsDir = path.join(SRC_DIR, 'utils');
  ensureDirectoryExists(utilsDir);

  const featureFlagsPath = path.join(utilsDir, 'feature-flags.ts');

  const featureFlagsContent = `/**
 * Feature Flags for Incremental Migration
 *
 * This utility helps manage feature flags for the incremental migration
 * to Vercel. It allows us to toggle features on and off based on
 * environment variables, cookies, or URL parameters.
 */

// Feature flag types
export type FeatureFlag =
  | 'USE_NEW_CHART_VISUALIZATION'
  | 'USE_NEW_FORM_HANDLING'
  | 'USE_NEW_QUESTIONNAIRE'
  | 'USE_NEW_AI_RECTIFICATION';

// Default state of features
const defaultFeatures: Record<FeatureFlag, boolean> = {
  USE_NEW_CHART_VISUALIZATION: false,
  USE_NEW_FORM_HANDLING: false,
  USE_NEW_QUESTIONNAIRE: false,
  USE_NEW_AI_RECTIFICATION: false,
};

// Detect if we're running on Vercel
export const isVercel = process.env.VERCEL === '1';

/**
 * Check if a feature is enabled
 * @param feature The feature flag to check
 * @returns Whether the feature is enabled
 */
export function isFeatureEnabled(feature: FeatureFlag): boolean {
  // Server-side only code
  if (typeof window === 'undefined') {
    // Check environment variables first
    if (process.env[feature] === 'true') return true;
    if (process.env[feature] === 'false') return false;

    // Fall back to default
    return defaultFeatures[feature];
  }

  // Client-side code
  try {
    // Check URL parameters
    const url = new URL(window.location.href);
    const param = url.searchParams.get(feature.toLowerCase());
    if (param === 'true') return true;
    if (param === 'false') return false;

    // Check cookies
    const cookieValue = getCookie(feature.toLowerCase());
    if (cookieValue === 'true') return true;
    if (cookieValue === 'false') return false;

    // Check environment variables (client-side)
    if (window.__ENV__ && window.__ENV__[feature] === 'true') return true;
    if (window.__ENV__ && window.__ENV__[feature] === 'false') return false;

    // Fall back to default
    return defaultFeatures[feature];
  } catch (error) {
    // In case of any errors, fall back to default
    return defaultFeatures[feature];
  }
}

/**
 * Helper to get a cookie value
 */
function getCookie(name: string): string | null {
  if (typeof document === 'undefined') return null;

  const value = \`; \${document.cookie}\`;
  const parts = value.split(\`; \${name}=\`);
  if (parts.length === 2) return parts.pop()?.split(';').shift() || null;
  return null;
}

// Add TypeScript global declaration for client-side environment variables
declare global {
  interface Window {
    __ENV__?: Record<string, string>;
  }
}
`;

  fs.writeFileSync(featureFlagsPath, featureFlagsContent);
  console.log(`${colors.green}Created${colors.reset} ${featureFlagsPath}`);

  // Create global declaration file for the environment variables
  const envDeclarationPath = path.join(SRC_DIR, '@types', 'env.d.ts');
  ensureDirectoryExists(path.join(SRC_DIR, '@types'));

  const envDeclarationContent = `/**
 * Global Environment Variable Declarations
 */

declare global {
  namespace NodeJS {
    interface ProcessEnv {
      // Feature flags for incremental migration
      USE_NEW_CHART_VISUALIZATION?: string;
      USE_NEW_FORM_HANDLING?: string;
      USE_NEW_QUESTIONNAIRE?: string;
      USE_NEW_AI_RECTIFICATION?: string;

      // Vercel-specific environment variables
      VERCEL?: string;
      VERCEL_URL?: string;
      VERCEL_ENV?: 'production' | 'preview' | 'development';

      // Project environment variables
      NEXT_PUBLIC_API_URL?: string;
    }
  }
}

export {};
`;

  fs.writeFileSync(envDeclarationPath, envDeclarationContent);
  console.log(`${colors.green}Created${colors.reset} ${envDeclarationPath}`);

  return true;
}

// 3. Create middleware for client-side feature flag detection
function createMiddleware() {
  console.log(`${colors.yellow}Creating middleware for feature flags...${colors.reset}`);

  const middlewarePath = path.join(SRC_DIR, 'middleware.ts');

  const middlewareContent = `/**
 * Next.js Middleware for Incremental Migration
 *
 * This middleware handles:
 * 1. Feature flag detection via cookies, headers, or URL parameters
 * 2. A/B testing between legacy and new implementations
 * 3. Cookie-based feature persistence
 */

import { NextRequest, NextResponse } from 'next/server';

// Feature flag constants
const FEATURE_FLAGS = [
  'USE_NEW_CHART_VISUALIZATION',
  'USE_NEW_FORM_HANDLING',
  'USE_NEW_QUESTIONNAIRE',
  'USE_NEW_AI_RECTIFICATION',
];

export function middleware(request: NextRequest) {
  const url = request.nextUrl.clone();

  // Get the path
  const { pathname } = url;

  // Create a response object to modify
  const response = NextResponse.next();

  // Check for override params in the URL to enable/disable features
  FEATURE_FLAGS.forEach(flag => {
    const paramValue = url.searchParams.get(flag.toLowerCase());

    if (paramValue === 'true' || paramValue === 'false') {
      // Set a cookie to persist the feature flag
      response.cookies.set(flag.toLowerCase(), paramValue, {
        maxAge: 60 * 60 * 24 * 30, // 30 days
        path: '/',
      });
    }
  });

  // Handle vertical migration paths
  if (pathname.startsWith('/chart') || pathname === '/chart') {
    // Check if we should use the new chart visualization
    const useNewChart = request.cookies.get('use_new_chart_visualization');

    if (useNewChart?.value !== 'true') {
      // Optionally redirect to legacy system for this feature
      // Uncomment when ready to implement
      // return NextResponse.rewrite(new URL(\`\${process.env.LEGACY_SYSTEM_URL}\${pathname}\`));
    }
  }

  // Add the X-Incremental-Migration header to indicate we're using the incremental approach
  response.headers.set('X-Incremental-Migration', 'enabled');

  return response;
}

// Only run middleware on the paths we need for incremental migration
export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
`;

  fs.writeFileSync(middlewarePath, middlewareContent);
  console.log(`${colors.green}Created/Updated${colors.reset} ${middlewarePath}`);

  return true;
}

// 4. Create a migration documentation file
function createMigrationDocumentation() {
  console.log(`${colors.yellow}Creating incremental migration documentation...${colors.reset}`);

  const docsDir = path.join(ROOT_DIR, 'docs');
  ensureDirectoryExists(docsDir);

  const migrationDocPath = path.join(docsDir, 'incremental-migration.md');

  const migrationDocContent = `# Birth Time Rectifier - Incremental Migration to Vercel

This document outlines the incremental migration strategy for moving the Birth Time Rectifier application to Vercel.

## Migration Strategy

We're following a **Vertical Migration** approach as recommended by Vercel's documentation (https://vercel.com/docs/incremental-migration). This means we'll migrate feature by feature while keeping both systems running in parallel.

## Migration Phases

### Phase 1: Core Frontend
- **Basic UI Components** ✅
- **Form Handling** ⏳
- **Chart Visualization (Basic)** ⏳
- **Routing and Navigation** ✅

### Phase 2: API Integration
- **Backend API Connection** ⏳
- **Feature Flags Implementation** ✅
- **Environment Variable Setup** ✅

### Phase 3: Advanced Features
- **AI-Powered Birth Time Rectification** 🔜
- **Comprehensive Questionnaire System** 🔜
- **Advanced Chart Comparisons** 🔜

## Feature Flag Usage

We've implemented feature flags to toggle between legacy and new implementations. This allows us to:

1. **Conduct A/B Testing** - Compare performance between implementations
2. **Roll Back Quickly** - If issues arise, we can disable new features instantly
3. **Progressive Rollout** - Enable new features for specific user groups

### How to Use Feature Flags

**Environment Variables:**
- Set these in the Vercel dashboard or .env file
- Example: \`USE_NEW_CHART_VISUALIZATION=true\`

**URL Parameters:**
- Add to any URL to override the default setting
- Example: \`?use_new_chart_visualization=true\`

**Cookies:**
- Persistent storage of feature preferences
- Set automatically when URL parameters are used

## Testing Strategy

For each migrated feature:

1. **Parallel Running** - Both implementations available simultaneously
2. **Monitoring** - Compare performance metrics between implementations
3. **Gradual Rollout** - Start with internal users, then expand to all users

## Rollback Procedure

If issues arise with a new implementation:

1. Disable the feature flag in Vercel's environment variables
2. Traffic will automatically route to the legacy implementation
3. Fix issues and re-enable when ready

## Migration Checklist

For each feature to be migrated:

- [ ] Implement the feature in the new system
- [ ] Add appropriate feature flags
- [ ] Test both implementations side by side
- [ ] Monitor performance after release
- [ ] Once stable, remove legacy implementation

## Technical Details

See the following files for implementation details:

- \`src/utils/feature-flags.ts\` - Feature flag utility
- \`src/middleware.ts\` - Request handling for feature detection
- \`vercel.json\` - Vercel-specific configuration
`;

  fs.writeFileSync(migrationDocPath, migrationDocContent);
  console.log(`${colors.green}Created${colors.reset} ${migrationDocPath}`);

  return true;
}

// 5. Update next.config.js to support feature flags
function updateNextConfig() {
  console.log(`${colors.yellow}Updating Next.js configuration for feature flags...${colors.reset}`);

  const nextConfigPath = path.join(ROOT_DIR, 'next.config.js');

  if (!fs.existsSync(nextConfigPath)) {
    console.error(`${colors.red}next.config.js not found.${colors.reset}`);
    return false;
  }

  try {
    let nextConfig = fs.readFileSync(nextConfigPath, 'utf8');

    // Check if the config already has feature flag settings
    if (nextConfig.includes('FEATURE_FLAGS')) {
      console.log(`${colors.blue}Next.js config already has feature flag settings.${colors.reset}`);
      return true;
    }

    // Add feature flag environment variables
    if (nextConfig.includes('module.exports = nextConfig;')) {
      nextConfig = nextConfig.replace(
        'module.exports = nextConfig;',
        `// Feature flags for incremental migration
const FEATURE_FLAGS = [
  'USE_NEW_CHART_VISUALIZATION',
  'USE_NEW_FORM_HANDLING',
  'USE_NEW_QUESTIONNAIRE',
  'USE_NEW_AI_RECTIFICATION',
];

// Add feature flags to env
if (!nextConfig.env) nextConfig.env = {};
FEATURE_FLAGS.forEach(flag => {
  nextConfig.env[flag] = process.env[flag] || 'false';
});

module.exports = nextConfig;`
      );
    } else {
      console.error(`${colors.red}Could not update next.config.js: Module exports line not found.${colors.reset}`);
      return false;
    }

    fs.writeFileSync(nextConfigPath, nextConfig);
    console.log(`${colors.green}Updated${colors.reset} ${nextConfigPath}`);

    return true;
  } catch (error) {
    console.error(`${colors.red}Error updating next.config.js:${colors.reset}`, error.message);
    return false;
  }
}

// 6. Create example components with feature flags
function createExampleComponents() {
  console.log(`${colors.yellow}Creating example components with feature flags...${colors.reset}`);

  const componentsDir = path.join(SRC_DIR, 'components', 'chart');
  ensureDirectoryExists(componentsDir);

  // Create legacy chart component
  const legacyChartPath = path.join(componentsDir, 'LegacyChartVisualization.tsx');
  const legacyChartContent = `/**
 * Legacy Chart Visualization Component
 * Used when the feature flag is disabled
 */
import React from 'react';

interface ChartProps {
  birthData: {
    date: string;
    time: string;
    latitude: number;
    longitude: number;
  };
}

const LegacyChartVisualization: React.FC<ChartProps> = ({ birthData }) => {
  return (
    <div className="legacy-chart">
      <div className="legacy-chart-header">
        <h3>Birth Chart (Legacy Visualization)</h3>
        <p>Birth Date: {birthData.date}</p>
        <p>Birth Time: {birthData.time}</p>
        <p>Location: {birthData.latitude}, {birthData.longitude}</p>
      </div>

      <div className="legacy-chart-content">
        {/* Legacy chart implementation */}
        <div className="chart-placeholder">
          [Legacy Chart Visualization]
        </div>
      </div>
    </div>
  );
};

export default LegacyChartVisualization;
`;

  fs.writeFileSync(legacyChartPath, legacyChartContent);
  console.log(`${colors.green}Created${colors.reset} ${legacyChartPath}`);

  // Create new chart component
  const newChartPath = path.join(componentsDir, 'NewChartVisualization.tsx');
  const newChartContent = `/**
 * New Chart Visualization Component
 * Used when the feature flag is enabled
 */
import React from 'react';

interface ChartProps {
  birthData: {
    date: string;
    time: string;
    latitude: number;
    longitude: number;
  };
}

const NewChartVisualization: React.FC<ChartProps> = ({ birthData }) => {
  return (
    <div className="new-chart">
      <div className="new-chart-header">
        <h3>Birth Chart (New Visualization)</h3>
        <p>Birth Date: {birthData.date}</p>
        <p>Birth Time: {birthData.time}</p>
        <p>Location: {birthData.latitude}, {birthData.longitude}</p>
      </div>

      <div className="new-chart-content">
        {/* New chart implementation */}
        <div className="chart-placeholder">
          [New Chart Visualization]
        </div>
      </div>
    </div>
  );
};

export default NewChartVisualization;
`;

  fs.writeFileSync(newChartPath, newChartContent);
  console.log(`${colors.green}Created${colors.reset} ${newChartPath}`);

  // Create feature flagged component
  const featureFlaggedChartPath = path.join(componentsDir, 'ChartVisualization.tsx');
  const featureFlaggedChartContent = `/**
 * Feature-Flagged Chart Visualization Component
 *
 * This component uses the feature flag utility to determine
 * whether to render the legacy or new chart visualization.
 */
import React from 'react';
import { isFeatureEnabled } from '../../utils/feature-flags';

// Import both implementations
import LegacyChartVisualization from './LegacyChartVisualization';
import NewChartVisualization from './NewChartVisualization';

interface ChartProps {
  birthData: {
    date: string;
    time: string;
    latitude: number;
    longitude: number;
  };
}

const ChartVisualization: React.FC<ChartProps> = (props) => {
  // Check if the new chart visualization is enabled
  const useNewChart = isFeatureEnabled('USE_NEW_CHART_VISUALIZATION');

  return (
    <div className="chart-visualization-wrapper">
      {/* Display a banner for easy identification during testing */}
      <div className="feature-flag-banner" style={{
        background: useNewChart ? '#e6f7ff' : '#fff7e6',
        padding: '10px',
        textAlign: 'center',
        marginBottom: '10px'
      }}>
        Using {useNewChart ? 'NEW' : 'LEGACY'} Chart Visualization
      </div>

      {/* Render the appropriate component based on the feature flag */}
      {useNewChart ? (
        <NewChartVisualization {...props} />
      ) : (
        <LegacyChartVisualization {...props} />
      )}
    </div>
  );
};

export default ChartVisualization;
`;

  fs.writeFileSync(featureFlaggedChartPath, featureFlaggedChartContent);
  console.log(`${colors.green}Created${colors.reset} ${featureFlaggedChartPath}`);

  return true;
}

// Main function
function main() {
  try {
    const results = {
      vercelConfig: updateVercelConfig(),
      featureFlags: createFeatureFlagUtilities(),
      middleware: createMiddleware(),
      documentation: createMigrationDocumentation(),
      nextConfig: updateNextConfig(),
      exampleComponents: createExampleComponents(),
    };

    const allSucceeded = Object.values(results).every(Boolean);

    if (allSucceeded) {
      console.log(`\n${colors.green}=== Incremental migration setup complete! ===${colors.reset}`);
      console.log(`${colors.cyan}Next steps:${colors.reset}`);
      console.log(`1. Review the generated files and configurations`);
      console.log(`2. Implement feature flags in your components where needed`);
      console.log(`3. Follow the migration phases as outlined in the documentation`);
      console.log(`4. Run the appropriate deployment script to deploy to Vercel`);
      console.log(`\nSee ${colors.cyan}docs/incremental-migration.md${colors.reset} for detailed instructions.`);
    } else {
      console.log(`\n${colors.yellow}=== Incremental migration setup completed with warnings ===${colors.reset}`);
      console.log(`${colors.yellow}Some steps failed or were skipped. Please review the logs above.${colors.reset}`);

      if (!results.vercelConfig) {
        console.log(`${colors.red}- vercel.json couldn't be updated${colors.reset}`);
      }
      if (!results.nextConfig) {
        console.log(`${colors.red}- next.config.js couldn't be updated${colors.reset}`);
      }
    }
  } catch (error) {
    console.error(`${colors.red}An error occurred during setup:${colors.reset}`, error.message);
  }
}

// Run the script
main();
