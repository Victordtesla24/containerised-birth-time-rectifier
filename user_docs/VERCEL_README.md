# Vercel Deployment Instructions

This document provides instructions for deploying the Birth Time Rectifier application to Vercel.

## Prerequisites

- GitHub account connected to Vercel
- Vercel account with access to deploy
- Vercel CLI installed (`npm i -g vercel`)

## Setup Instructions

### 1. Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Victordtesla24/containerised-birth-time-rectifier.git
   cd containerised-birth-time-rectifier
   ```

2. Login to Vercel:
   ```bash
   vercel login
   ```

3. Link your project to Vercel:
   ```bash
   vercel link
   ```

### 2. Environment Variables

Set up the following environment variables in your Vercel project dashboard:

- `NODE_ENV`: `production`
- `NEXT_PUBLIC_API_URL`: Your API URL (e.g., `https://your-project.vercel.app/api`)

### 3. Deploy

1. Manual deployment:
   ```bash
   vercel --prod
   ```

2. Or use the GitHub integration for automatic deployments on push to main branch.

## GitHub CI/CD Integration

We've set up GitHub Actions to automatically deploy to Vercel when pushing to the main branch. The workflow is defined in `.github/workflows/vercel-deploy.yml`.

To enable this workflow, you need to add a repository secret:

1. Go to your GitHub repository settings
2. Navigate to "Secrets and variables" → "Actions"
3. Add a new repository secret with the name `VERCEL_TOKEN` and your Vercel token as the value

## Project Structure

The project has been optimized for Vercel deployment:

- Custom build script: `vercel-build.sh`
- Simplified package configuration: `package-vercel.json`
- Optimized Next.js configuration: `next.config.vercel.js`

## Incremental Migration

For an incremental migration approach:

1. Deploy the initial version
2. Use feature flags to gradually roll out new features
3. Configure both systems to run in parallel during transition
4. Monitor and validate each feature before full rollout

## Troubleshooting

If you encounter build errors:

1. Check Vercel build logs
2. Ensure all dependencies are correctly specified in `package-vercel.json`
3. Verify that `next.config.vercel.js` is correctly configured
4. Check if the build is failing due to TypeScript errors (we've disabled TS checks in the build process)

## Performance Monitoring

Once deployed, monitor your application performance using Vercel Analytics.
