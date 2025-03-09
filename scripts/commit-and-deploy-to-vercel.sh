#!/bin/bash

# Script to commit changes and push to GitHub to trigger Vercel deployment
# This script will commit all the changes made for Vercel deployment
# and push them to the specified branch (defaults to main)

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
BRANCH="main"
COMMIT_MSG="Setup Vercel deployment with incremental migration"
PUSH=false
REMOTE="origin"

# Display help information
show_help() {
  echo -e "${BLUE}Birth Time Rectifier - Commit and Deploy to Vercel${NC}"
  echo ""
  echo "Usage: ./scripts/commit-and-deploy-to-vercel.sh [options]"
  echo ""
  echo "Options:"
  echo "  -h, --help            Show this help message"
  echo "  -b, --branch BRANCH   Specify the branch to push to (default: main)"
  echo "  -m, --message MSG     Specify the commit message (default: Setup Vercel deployment with incremental migration)"
  echo "  -p, --push            Push the changes to GitHub after committing"
  echo "  -r, --remote REMOTE   Specify the remote to push to (default: origin)"
  echo ""
  echo "Example:"
  echo "  ./scripts/commit-and-deploy-to-vercel.sh -p -b main -m 'Deploy to Vercel'"
  echo ""
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_help
      exit 0
      ;;
    -b|--branch)
      BRANCH="$2"
      shift 2
      ;;
    -m|--message)
      COMMIT_MSG="$2"
      shift 2
      ;;
    -p|--push)
      PUSH=true
      shift
      ;;
    -r|--remote)
      REMOTE="$2"
      shift 2
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_help
      exit 1
      ;;
  esac
done

echo -e "${CYAN}=== Birth Time Rectifier - Commit and Deploy to Vercel ===${NC}\n"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
  echo -e "${RED}Error: Not a git repository. Please run this script from the root of your git repository.${NC}"
  exit 1
fi

# List all Vercel deployment files
echo -e "${YELLOW}Files that will be committed:${NC}"
echo -e "${BLUE}Vercel Configuration Files:${NC}"
git ls-files --others --exclude-standard | grep -E '(vercel\.json|\.vercel)'
git ls-files --modified | grep -E '(vercel\.json|\.vercel)'

echo -e "${BLUE}GitHub Workflow Files:${NC}"
git ls-files --others --exclude-standard | grep -E '\.github/workflows'
git ls-files --modified | grep -E '\.github/workflows'

echo -e "${BLUE}Deployment Scripts:${NC}"
git ls-files --others --exclude-standard | grep -E 'scripts/.*vercel.*'
git ls-files --modified | grep -E 'scripts/.*vercel.*'

echo -e "${BLUE}Documentation Files:${NC}"
git ls-files --others --exclude-standard | grep -E 'docs/.*vercel.*|VERCEL_.*\.md'
git ls-files --modified | grep -E 'docs/.*vercel.*|VERCEL_.*\.md'

echo -e "${BLUE}Other Modified Files:${NC}"
git ls-files --modified | grep -E 'README\.md|\.nvmrc|next\.config\.js'

# Confirm with the user
echo ""
echo -e "${YELLOW}Do you want to commit these files with the message:${NC}"
echo -e "${CYAN}\"$COMMIT_MSG\"${NC}"
echo -e "${YELLOW}to the branch ${CYAN}$BRANCH${NC}?"
if [ "$PUSH" = true ]; then
  echo -e "${YELLOW}The changes will also be pushed to ${CYAN}$REMOTE/$BRANCH${NC}."
fi

read -p "Continue? (y/n): " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
  echo -e "${RED}Aborted.${NC}"
  exit 1
fi

# Stage all Vercel-related files
echo -e "\n${YELLOW}Staging Vercel configuration files...${NC}"
git add vercel.json .vercel 2>/dev/null || true

echo -e "${YELLOW}Staging GitHub workflow files...${NC}"
git add .github/workflows/vercel-deploy.yml .github/workflows/vercel-preview-comments.yml 2>/dev/null || true

echo -e "${YELLOW}Staging deployment scripts...${NC}"
git add scripts/*vercel* 2>/dev/null || true

echo -e "${YELLOW}Staging documentation files...${NC}"
git add docs/*vercel* VERCEL_*.md 2>/dev/null || true

echo -e "${YELLOW}Staging other modified files...${NC}"
git add README.md .nvmrc next.config.js src/middleware.ts src/utils/feature-flags.ts 2>/dev/null || true

# Check if there are any staged changes
if git diff --staged --quiet; then
  echo -e "${RED}No files were staged. Nothing to commit.${NC}"
  exit 1
fi

# Commit the changes
echo -e "\n${YELLOW}Committing changes...${NC}"
git commit -m "$COMMIT_MSG"

echo -e "${GREEN}Successfully committed changes with message:${NC}"
echo -e "${CYAN}\"$COMMIT_MSG\"${NC}"

# Push the changes if requested
if [ "$PUSH" = true ]; then
  echo -e "\n${YELLOW}Pushing changes to $REMOTE/$BRANCH...${NC}"
  git push "$REMOTE" "$BRANCH"
  echo -e "${GREEN}Successfully pushed changes to $REMOTE/$BRANCH.${NC}"
  echo -e "${BLUE}Check your Vercel dashboard to monitor the deployment:${NC}"
  echo -e "${CYAN}https://vercel.com/dashboard${NC}"
else
  echo -e "\n${YELLOW}Skipping push to GitHub. To push the changes manually, run:${NC}"
  echo -e "${CYAN}git push $REMOTE $BRANCH${NC}"
  echo -e "${YELLOW}Or run this script with the -p flag:${NC}"
  echo -e "${CYAN}./scripts/commit-and-deploy-to-vercel.sh -p${NC}"
fi

echo -e "\n${GREEN}=== Complete ===${NC}"
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. If you haven't pushed the changes yet, push them to GitHub to trigger the Vercel deployment."
echo -e "2. Check the GitHub Actions tab to monitor the CI/CD pipeline execution."
echo -e "3. Visit the Vercel dashboard to see your deployed application."
echo -e "4. Run the incremental migration script to set up feature flags:${NC}"
echo -e "${CYAN}   node scripts/setup-incremental-migration.js${NC}"
