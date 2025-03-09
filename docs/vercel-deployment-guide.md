# Vercel Deployment Guide

This guide provides detailed instructions for deploying and maintaining the Birth Time Rectifier application on Vercel.

## Prerequisites

- GitHub account linked to Vercel
- Vercel account with appropriate permissions
- Vercel CLI installed locally (`npm i -g vercel`)

## Initial Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Victordtesla24/containerised-birth-time-rectifier.git
cd containerised-birth-time-rectifier
```

### 2. Vercel Login and Project Setup

```bash
# Login to Vercel CLI
vercel login

# Link your local project to Vercel
vercel link
```

### 3. Deploy the Project

```bash
# Deploy to production
vercel --prod
```

## Project Structure for Vercel

The project has been specifically optimized for Vercel deployment:

- **Custom Build Script**: `vercel-build.sh` - Handles the build process with special configurations to avoid common deployment issues.
- **Simplified Configurations**:
  - `package-vercel.json` - Optimized dependencies for Vercel deployment
  - `next.config.vercel.js` - Next.js configuration tuned for Vercel
  - Simplified CSS and component files for compatibility

## Continuous Deployment with GitHub

The project is configured to automatically deploy to Vercel when changes are pushed to the main branch. This is managed through:

1. GitHub Actions workflow in `.github/workflows/vercel-deploy.yml`
2. Vercel's GitHub integration

### Setting Up GitHub Actions

To enable the GitHub Actions workflow:

1. Add a repository secret named `VERCEL_TOKEN` with your Vercel API token
2. Push changes to the main branch to trigger deployment

## Incremental Migration Strategy

For migrating features gradually:

1. Deploy the basic application structure
2. Enable feature flags for new components
3. Roll out features incrementally
4. Monitor performance and user feedback
5. Gradually replace legacy components

## Environment Variables

Set the following environment variables in your Vercel project settings:

- `NODE_ENV`: `production`
- `NEXT_PUBLIC_API_URL`: Your API URL

## Troubleshooting

### Common Issues

- **Build Failures**: Check that all required dependencies are in `package-vercel.json`
- **CSS Issues**: Ensure CSS is properly imported in the simplified component files
- **API Connection Problems**: Verify environment variables are correctly set

### Vercel Logs

To view deployment logs:

```bash
vercel logs <deployment-url>
```

## Performance Monitoring

Monitor your application's performance using:

1. Vercel Analytics dashboard
2. Real User Monitoring (RUM)
3. Lighthouse scores for Core Web Vitals

## Security Considerations

- Keep your Vercel token secure
- Regularly rotate deployment tokens
- Do not commit sensitive environment variables to the repository
- Use Vercel's environment variable encryption for sensitive data

## Rollback Procedure

If a deployment causes issues:

```bash
# List deployments
vercel list

# Rollback to a previous deployment
vercel alias set <previous-deployment-url> <your-domain>
```

## Contact

For deployment issues or questions, please contact the team administrator.
