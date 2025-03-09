# Birth Time Rectifier - Vercel Deployment

## Overview

This project is configured for deployment on Vercel, with the frontend Next.js application being deployed directly. The AI service backend is designed to be deployed separately, and the frontend is configured to work both with and without the backend service.

## Deployment Instructions

### Prerequisites

1. Create a Vercel account at [vercel.com](https://vercel.com) if you don't have one already
2. Install the Vercel CLI: `npm install -g vercel`
3. Login to Vercel: `vercel login`

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

- `vercel.json`: Vercel-specific configuration
- `next.config.js`: Next.js configuration with Vercel optimizations
- `.github/workflows/vercel-deploy.yml`: GitHub CI/CD for Vercel deployment

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
```bash
vercel dev
```

## Support

For additional help, please refer to the Vercel documentation at [vercel.com/docs](https://vercel.com/docs) or create an issue in the GitHub repository.
