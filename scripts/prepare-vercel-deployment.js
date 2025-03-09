#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const ROOT_DIR = process.cwd();
const FRONTEND_DIR = path.join(ROOT_DIR, 'src');
const SERVICE_MANAGER_DIR = path.join(ROOT_DIR, 'service-manager');
const SERVICE_MANAGER_FRONTEND_DIR = path.join(SERVICE_MANAGER_DIR, 'frontend');
const AI_SERVICE_DIR = path.join(ROOT_DIR, 'ai_service');

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

console.log(`${colors.cyan}=== Birth Time Rectifier - Vercel Deployment Preparation ===${colors.reset}`);

// Check duplicates between service-manager/frontend and src directories
function findDuplicateFiles() {
  console.log(`\n${colors.yellow}Checking for duplicate files...${colors.reset}`);

  if (!fs.existsSync(SERVICE_MANAGER_FRONTEND_DIR)) {
    console.log(`${colors.blue}No service-manager/frontend directory found.${colors.reset}`);
    return;
  }

  try {
    // List all files in service-manager/frontend recursively
    const frontendFiles = execSync(`find ${SERVICE_MANAGER_FRONTEND_DIR} -type f | sort`).toString().split('\n').filter(Boolean);

    // Check if any of these files exist in src with the same relative path
    let duplicatesFound = false;

    for (const file of frontendFiles) {
      const relativePath = path.relative(SERVICE_MANAGER_FRONTEND_DIR, file);
      const srcPath = path.join(FRONTEND_DIR, relativePath);

      if (fs.existsSync(srcPath)) {
        duplicatesFound = true;
        console.log(`${colors.yellow}Duplicate file found:${colors.reset}`);
        console.log(`  ${colors.magenta}Original:${colors.reset} ${srcPath}`);
        console.log(`  ${colors.magenta}Duplicate:${colors.reset} ${file}`);

        // Compare files
        const originalContent = fs.readFileSync(srcPath, 'utf8');
        const duplicateContent = fs.readFileSync(file, 'utf8');

        if (originalContent === duplicateContent) {
          console.log(`  ${colors.green}Files are identical${colors.reset}`);
        } else {
          console.log(`  ${colors.red}Files differ${colors.reset}`);
          console.log(`  Please manually review and merge if needed.`);
        }
      }
    }

    if (!duplicatesFound) {
      console.log(`${colors.green}No duplicate files found.${colors.reset}`);
    }
  } catch (error) {
    console.error(`${colors.red}Error checking duplicate files:${colors.reset}`, error.message);
  }
}

// Ensure Next.js API routes have fallbacks for when AI service is unavailable
function updateApiRoutes() {
  console.log(`\n${colors.yellow}Updating API routes for Vercel compatibility...${colors.reset}`);

  const API_ROUTES_DIR = path.join(FRONTEND_DIR, 'pages', 'api');

  if (!fs.existsSync(API_ROUTES_DIR)) {
    console.error(`${colors.red}API routes directory not found:${colors.reset} ${API_ROUTES_DIR}`);
    return;
  }

  // Add helper function to API routes to detect if running on Vercel
  const API_UTILS_DIR = path.join(FRONTEND_DIR, 'utils');

  if (!fs.existsSync(API_UTILS_DIR)) {
    fs.mkdirSync(API_UTILS_DIR, { recursive: true });
  }

  // Write vercel-helpers.js
  const vercelHelpersPath = path.join(API_UTILS_DIR, 'vercel-helpers.js');

  const vercelHelpersContent = `/**
 * Utilities for Vercel deployment
 */

// Check if we're running on Vercel
export const isVercel = process.env.VERCEL === '1';

// Get the API URL
export const getApiUrl = () => {
  if (isVercel) {
    return process.env.NEXT_PUBLIC_API_URL || 'https://birth-time-rectifier.vercel.app/api';
  }

  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3000/api';
};

// Check if AI service is available
export async function isAiServiceAvailable() {
  try {
    const response = await fetch(\`\${getApiUrl()}/health\`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 2000, // 2 second timeout
    });

    return response.ok;
  } catch (error) {
    console.error('Error checking AI service:', error);
    return false;
  }
}

// Helper for handling API requests in Vercel
export async function handleApiRequest(handler, fallback, req, res) {
  try {
    return await handler(req, res);
  } catch (error) {
    console.error('API error:', error);

    if (fallback) {
      return fallback(req, res);
    }

    res.status(500).json({
      error: 'An error occurred processing your request',
      message: error.message,
    });
  }
}
`;

  fs.writeFileSync(vercelHelpersPath, vercelHelpersContent);
  console.log(`${colors.green}Created${colors.reset} ${vercelHelpersPath}`);
}

// Update next.config.js to properly handle environment variables in Vercel
function updateNextConfig() {
  console.log(`\n${colors.yellow}Updating Next.js configuration...${colors.reset}`);

  const nextConfigPath = path.join(ROOT_DIR, 'next.config.js');

  if (!fs.existsSync(nextConfigPath)) {
    console.error(`${colors.red}next.config.js not found${colors.reset}`);
    return;
  }

  try {
    let nextConfig = fs.readFileSync(nextConfigPath, 'utf8');

    // Check if the config already has Vercel-specific settings
    if (nextConfig.includes('process.env.VERCEL')) {
      console.log(`${colors.blue}Next.js config already has Vercel settings${colors.reset}`);
      return;
    }

    // Add Vercel-specific configurations
    nextConfig = nextConfig.replace(
      'module.exports = nextConfig;',
      `// Vercel-specific configurations
if (process.env.VERCEL) {
  nextConfig.env = {
    ...nextConfig.env,
    NEXT_PUBLIC_API_URL: process.env.VERCEL_URL ? \`https://\${process.env.VERCEL_URL}/api\` : 'https://birth-time-rectifier.vercel.app/api',
    IS_VERCEL: 'true',
  };
}

module.exports = nextConfig;`
    );

    fs.writeFileSync(nextConfigPath, nextConfig);
    console.log(`${colors.green}Updated${colors.reset} ${nextConfigPath}`);
  } catch (error) {
    console.error(`${colors.red}Error updating next.config.js:${colors.reset}`, error.message);
  }
}

// Add README with Vercel deployment instructions
function createVercelReadme() {
  console.log(`\n${colors.yellow}Creating Vercel deployment README...${colors.reset}`);

  const readmePath = path.join(ROOT_DIR, 'VERCEL_DEPLOYMENT.md');

  const readmeContent = `# Birth Time Rectifier - Vercel Deployment

## Overview

This project is configured for deployment on Vercel, with the frontend Next.js application being deployed directly. The AI service backend is designed to be deployed separately, and the frontend is configured to work both with and without the backend service.

## Deployment Instructions

### Prerequisites

1. Create a Vercel account at [vercel.com](https://vercel.com) if you don't have one already
2. Install the Vercel CLI: \`npm install -g vercel\`
3. Login to Vercel: \`vercel login\`

### Frontend Deployment

1. Connect your GitHub repository to Vercel:
   - Go to [vercel.com/new](https://vercel.com/new)
   - Import your GitHub repository
   - Configure the project with the following settings:
     - Framework Preset: Next.js
     - Root Directory: ./
     - Build Command: npm run build
     - Output Directory: .next

2. Set up environment variables:
   - NEXT_PUBLIC_API_URL: URL of your API (if deploying the backend separately)

3. Deploy with GitHub Integration (CI/CD):
   - Make sure to add the following secrets to your GitHub repository:
     - VERCEL_TOKEN: Your Vercel API token
     - VERCEL_ORG_ID: Your Vercel organization ID
     - VERCEL_PROJECT_ID: Your Vercel project ID

### Backend Deployment (AI Service)

The AI service requires a separate deployment. Options include:

1. **Serverless Platform** (Recommended for production):
   - Deploy to AWS Lambda or similar serverless platform
   - Configure the NEXT_PUBLIC_API_URL in the frontend to point to this deployment

2. **Dedicated Server**:
   - Deploy the AI service to a VPS, EC2 instance, or similar
   - Ensure proper CORS configuration
   - Update the frontend's API URL to point to this server

3. **Local Development**:
   - For testing, you can run the AI service locally
   - The frontend is configured to work without the backend by providing fallbacks

## Configuration

- \`vercel.json\`: Vercel-specific configuration
- \`next.config.js\`: Next.js configuration with Vercel optimizations
- \`.github/workflows/vercel-deploy.yml\`: GitHub CI/CD for Vercel deployment

## Important Notes

1. **API Routes Fallbacks**: The frontend includes fallbacks for when the AI service is unavailable.
2. **Environment Variables**: Make sure to configure all necessary environment variables in your Vercel project.
3. **Project Structure**: This project has been optimized for Vercel deployment by consolidating duplicated files and ensuring proper path configurations.

## Troubleshooting

If you encounter issues during deployment:

1. Check Vercel build logs for detailed error information
2. Ensure all required environment variables are properly set
3. Verify that your GitHub CI/CD configuration is correct if using GitHub integration

For local testing of the Vercel deployment configuration:
\`\`\`bash
vercel dev
\`\`\`

## Support

For additional help, please refer to the Vercel documentation at [vercel.com/docs](https://vercel.com/docs) or create an issue in the GitHub repository.
`;

  fs.writeFileSync(readmePath, readmeContent);
  console.log(`${colors.green}Created${colors.reset} ${readmePath}`);
}

// Main function
function main() {
  findDuplicateFiles();
  updateApiRoutes();
  updateNextConfig();
  createVercelReadme();

  console.log(`\n${colors.green}=== Preparation complete! ===${colors.reset}`);
  console.log(`${colors.cyan}Next steps:${colors.reset}`);
  console.log(`1. Review and commit the changes`);
  console.log(`2. Push to GitHub repository`);
  console.log(`3. Set up Vercel deployment as outlined in VERCEL_DEPLOYMENT.md`);
  console.log(`4. Add the required secrets to your GitHub repository for CI/CD`);
}

// Run the script
main();
