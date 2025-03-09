#!/usr/bin/env node

/**
 * Setup script for GitHub to Vercel deployment pipeline
 *
 * This script helps configure the GitHub repository and prepare it for
 * CI/CD with Vercel, including:
 *
 * 1. Setting up Git configuration
 * 2. Creating a README with deployment info
 * 3. Creating PR template for Vercel previews
 * 4. Instructions for setting up Vercel integration
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const readline = require('readline');

// Configuration
const ROOT_DIR = process.cwd();

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

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

// Prompt helper
const prompt = (question) => {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
};

console.log(`${colors.cyan}=== Birth Time Rectifier - GitHub to Vercel Setup ===${colors.reset}\n`);

// 1. Create GitHub README section
async function createGitHubReadmeSection() {
  console.log(`${colors.yellow}Creating GitHub README section...${colors.reset}`);

  const readmePath = path.join(ROOT_DIR, 'README.md');

  if (!fs.existsSync(readmePath)) {
    console.log(`${colors.red}README.md not found. Creating new README...${colors.reset}`);
    fs.writeFileSync(readmePath, '# Birth Time Rectifier\n\n');
  }

  let readme = fs.readFileSync(readmePath, 'utf8');

  // Check if Vercel deployment section already exists
  if (readme.includes('## Vercel Deployment')) {
    console.log(`${colors.yellow}Vercel deployment section already exists in README.${colors.reset}`);
    return;
  }

  // Add Vercel deployment section
  const deploymentSection = `
## Vercel Deployment

This project is configured for deployment on Vercel. For detailed instructions, see [Vercel Deployment Guide](docs/vercel-deployment-guide.md).

### Deployment Status

[![Vercel Production Deployment](https://github.com/Victordtesla24/containerised-birth-time-rectifier/actions/workflows/vercel-deploy.yml/badge.svg)](https://github.com/Victordtesla24/containerised-birth-time-rectifier/actions/workflows/vercel-deploy.yml)

### Quick Start

1. **Prerequisites**
   - Vercel account
   - GitHub account
   - Required environment variables (see .env.example)

2. **Setup**
   - Fork/clone this repository
   - Link it to your Vercel account
   - Set up the required environment variables

3. **Deployment**
   - Push to main branch for production deployment
   - Create pull requests for preview deployments

For more details on the deployment process and architecture, see [docs/vercel-deployment-guide.md](docs/vercel-deployment-guide.md).
`;

  readme += deploymentSection;
  fs.writeFileSync(readmePath, readme);
  console.log(`${colors.green}Added Vercel deployment section to README.md${colors.reset}`);
}

// 2. Create PR template for Vercel preview deployments
function createPRTemplate() {
  console.log(`${colors.yellow}Creating PR template for Vercel preview deployments...${colors.reset}`);

  const githubDir = path.join(ROOT_DIR, '.github');
  const prTemplateDir = path.join(githubDir, 'PULL_REQUEST_TEMPLATE');

  // Create directories if they don't exist
  if (!fs.existsSync(githubDir)) {
    fs.mkdirSync(githubDir);
  }

  if (!fs.existsSync(prTemplateDir)) {
    fs.mkdirSync(prTemplateDir);
  }

  // Create PR template
  const prTemplatePath = path.join(prTemplateDir, 'vercel-preview.md');
  const prTemplateContent = `# Pull Request

## Description
<!-- Describe your changes in detail -->

## Related Issue
<!-- If fixing a bug, add "Fixes #issue_number" to automatically close the issue when this PR is merged -->
<!-- If implementing a feature, add "Implements #issue_number" -->

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to change)
- [ ] Documentation update

## Screenshots (if appropriate)
<!-- Add screenshots or examples of your changes -->

## How Has This Been Tested?
<!-- Please describe the tests you've run to verify your changes -->

## Vercel Preview
<!-- This section will be automatically filled by the Vercel GitHub integration -->
<!-- VERCEL_PREVIEW_DEPLOYMENT_URL -->

## Checklist:
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes
`;

  fs.writeFileSync(prTemplatePath, prTemplateContent);
  console.log(`${colors.green}Created PR template at ${prTemplatePath}${colors.reset}`);
}

// 3. Create GitHub Actions workflow for Vercel preview comments
function createPreviewCommentsWorkflow() {
  console.log(`${colors.yellow}Creating GitHub Actions workflow for Vercel preview comments...${colors.reset}`);

  const workflowsDir = path.join(ROOT_DIR, '.github', 'workflows');

  if (!fs.existsSync(workflowsDir)) {
    fs.mkdirSync(workflowsDir, { recursive: true });
  }

  // Check if the workflow already exists
  const workflowPath = path.join(workflowsDir, 'vercel-preview-comments.yml');

  if (fs.existsSync(workflowPath)) {
    console.log(`${colors.yellow}Vercel preview comments workflow already exists.${colors.reset}`);
    return;
  }

  // Create the workflow file
  const workflowContent = `name: Vercel Preview URL Comments

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  comment-preview-url:
    runs-on: ubuntu-latest
    steps:
      - name: Wait for Vercel preview deployment
        uses: patrickedqvist/wait-for-vercel-preview@v1.3.1
        id: waitForPreview
        with:
          token: \${{ secrets.GITHUB_TOKEN }}
          max_timeout: 300
          check_interval: 10

      - name: Add or update PR comment with preview URL
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          header: vercel-preview-url
          message: |
            🚀 **Preview Deployment**

            This change has been deployed to: \${{ steps.waitForPreview.outputs.url }}

            Compare changes with [production environment](\${{ secrets.VERCEL_PROD_URL || 'https://your-project-name.vercel.app' }})
`;

  fs.writeFileSync(workflowPath, workflowContent);
  console.log(`${colors.green}Created Vercel preview comments workflow at ${workflowPath}${colors.reset}`);
}

// 4. Gather GitHub repository information
async function gatherGitHubInfo() {
  console.log(`${colors.yellow}Gathering GitHub repository information...${colors.reset}`);

  // Try to detect current GitHub remote
  let gitRemote = '';
  try {
    gitRemote = execSync('git config --get remote.origin.url').toString().trim();
  } catch (error) {
    // Git remote not found, that's okay
  }

  let gitHubRepo = '';
  if (gitRemote) {
    // Extract username/repo from git remote URL
    const match = gitRemote.match(/github\.com[:/]([^/]+)\/([^/.]+)/);
    if (match) {
      gitHubRepo = `${match[1]}/${match[2]}`;
    }
  }

  let repoInfo = {
    owner: '',
    repo: '',
    githubUrl: ''
  };

  if (gitHubRepo) {
    const [owner, repo] = gitHubRepo.split('/');
    repoInfo.owner = owner;
    repoInfo.repo = repo;
    repoInfo.githubUrl = `https://github.com/${owner}/${repo}`;

    console.log(`${colors.green}Detected GitHub repository: ${repoInfo.githubUrl}${colors.reset}`);
  } else {
    console.log(`${colors.yellow}Could not detect GitHub repository.${colors.reset}`);

    repoInfo.owner = await prompt(`${colors.blue}Enter GitHub username or organization: ${colors.reset}`);
    repoInfo.repo = await prompt(`${colors.blue}Enter repository name: ${colors.reset}`);
    repoInfo.githubUrl = `https://github.com/${repoInfo.owner}/${repoInfo.repo}`;
  }

  return repoInfo;
}

// 5. Update vercel.json with GitHub repository info
async function updateVercelConfig(repoInfo) {
  console.log(`${colors.yellow}Updating vercel.json with GitHub repository info...${colors.reset}`);

  const vercelConfigPath = path.join(ROOT_DIR, 'vercel.json');

  if (!fs.existsSync(vercelConfigPath)) {
    console.log(`${colors.red}vercel.json not found. Please run prepare-vercel-deployment.js first.${colors.reset}`);
    return;
  }

  try {
    const vercelConfig = JSON.parse(fs.readFileSync(vercelConfigPath, 'utf8'));

    // Add GitHub repository information
    vercelConfig.github = {
      ...vercelConfig.github,
      enabled: true,
      silent: false
    };

    fs.writeFileSync(vercelConfigPath, JSON.stringify(vercelConfig, null, 2));
    console.log(`${colors.green}Updated vercel.json with GitHub integration settings${colors.reset}`);
  } catch (error) {
    console.error(`${colors.red}Error updating vercel.json:${colors.reset}`, error.message);
  }
}

// 6. Generate a secrets setup guide
async function generateSecretsGuide(repoInfo) {
  console.log(`${colors.yellow}Generating secrets setup guide...${colors.reset}`);

  const guidePath = path.join(ROOT_DIR, 'GITHUB_SECRETS_SETUP.md');

  const guideContent = `# GitHub Secrets Setup for Vercel Deployment

To enable automated deployments to Vercel from GitHub Actions, you need to set up the following secrets in your GitHub repository.

## Required Secrets

### 1. VERCEL_TOKEN

This is your Vercel API token, which allows GitHub Actions to deploy to Vercel on your behalf.

**Steps to get your Vercel token:**

1. Log in to your Vercel account
2. Go to Settings -> Tokens
3. Create a new token with a meaningful name like "GitHub CI/CD"
4. Copy the token

**Add to GitHub:**

1. Go to ${repoInfo.githubUrl}/settings/secrets/actions
2. Click "New repository secret"
3. Name: \`VERCEL_TOKEN\`
4. Value: Paste your Vercel token
5. Click "Add secret"

### 2. VERCEL_ORG_ID

This is your Vercel organization ID.

**Steps to get your organization ID:**

1. Go to your Vercel dashboard
2. Run this command in your browser console: \`copy(JSON.parse(localStorage.getItem('client:teams')).teams[0].id || JSON.parse(localStorage.getItem('vercel:metadata')).user.uid)\`
3. The ID will be copied to your clipboard

**Add to GitHub:**

1. Go to ${repoInfo.githubUrl}/settings/secrets/actions
2. Click "New repository secret"
3. Name: \`VERCEL_ORG_ID\`
4. Value: Paste your organization ID
5. Click "Add secret"

### 3. VERCEL_PROJECT_ID

This is the ID of your Vercel project.

**Steps to get your project ID:**

1. Go to your Vercel dashboard
2. Select your project
3. Go to Settings -> General
4. Copy the "Project ID"

**Add to GitHub:**

1. Go to ${repoInfo.githubUrl}/settings/secrets/actions
2. Click "New repository secret"
3. Name: \`VERCEL_PROJECT_ID\`
4. Value: Paste your project ID
5. Click "Add secret"

### 4. VERCEL_PROD_URL (Optional)

This is the URL of your production deployment, used in PR preview comments.

**Add to GitHub:**

1. Go to ${repoInfo.githubUrl}/settings/secrets/actions
2. Click "New repository secret"
3. Name: \`VERCEL_PROD_URL\`
4. Value: Your production URL (e.g., \`https://your-project.vercel.app\`)
5. Click "Add secret"

## Verification

Once you've added these secrets, your GitHub Actions workflows will be able to deploy to Vercel automatically:

- Pushes to the main branch will be deployed to production
- Pull requests will create preview deployments

For more information, see [docs/vercel-deployment-guide.md](docs/vercel-deployment-guide.md).
`;

  fs.writeFileSync(guidePath, guideContent);
  console.log(`${colors.green}Created GitHub secrets setup guide at ${guidePath}${colors.reset}`);
}

// Main function
async function main() {
  try {
    // 1. Create GitHub README section
    await createGitHubReadmeSection();

    // 2. Create PR template
    createPRTemplate();

    // 3. Create preview comments workflow
    createPreviewCommentsWorkflow();

    // 4. Gather GitHub info
    const repoInfo = await gatherGitHubInfo();

    // 5. Update vercel.json
    await updateVercelConfig(repoInfo);

    // 6. Generate secrets guide
    await generateSecretsGuide(repoInfo);

    console.log(`\n${colors.green}=== GitHub to Vercel setup complete! ===${colors.reset}`);
    console.log(`${colors.cyan}Next steps:${colors.reset}`);
    console.log(`1. Review the changes and commit them to your repository`);
    console.log(`2. Follow the instructions in GITHUB_SECRETS_SETUP.md to set up your GitHub secrets`);
    console.log(`3. Connect your repository to Vercel using the Vercel dashboard or CLI`);
    console.log(`4. Push your changes to trigger the first deployment`);
  } catch (error) {
    console.error(`${colors.red}Setup failed:${colors.reset}`, error.message);
  } finally {
    rl.close();
  }
}

// Run the script
main();
