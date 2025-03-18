#!/bin/bash
# CI-friendly npm installation fix script
# This script addresses common npm installation issues in CI environments
# without requiring sudo privileges

set -e  # Exit on error

echo "===== Birth Time Rectifier: NPM Installation Fix (CI) ====="
echo "Starting CI-friendly npm installation fix..."

# Step 1: Fix ownership of the .npm directory if possible
echo "Step 1: Attempting to fix ownership of ~/.npm directory..."
if [ -d "$HOME/.npm" ]; then
  chmod -R 777 "$HOME/.npm" || echo "Could not change permissions on ~/.npm, continuing..."
fi

# Step 2: Clear npm cache safely
echo "Step 2: Clearing npm cache..."
npm cache clean --force || echo "Cache clean failed, continuing with other fixes..."

# Step 3: Fix permissions for the project directory if possible
echo "Step 3: Attempting to fix permissions for the project directory..."
chmod -R 777 . || echo "Could not change permissions on project directory, continuing..."

# Step 4: Update npm to latest version (without sudo)
echo "Step 4: Updating npm to latest version..."
npm install --global npm@latest || echo "Global npm update failed, continuing with local installation..."

# Step 5: Ensure node_modules has correct permissions
echo "Step 5: Ensuring node_modules has correct permissions..."
if [ -d "node_modules" ]; then
  chmod -R 777 node_modules || echo "Could not change permissions on node_modules, continuing..."
  echo "Attempted to fix node_modules permissions"
else
  echo "node_modules directory not found, will be created during installation"
fi

# Step 6: Backup package-lock.json
echo "Step 6: Backing up package-lock.json..."
if [ -f "package-lock.json" ]; then
  cp package-lock.json package-lock.json.backup
  echo "Backed up package-lock.json to package-lock.json.backup"
fi

# Step 7: Clean installation
echo "Step 7: Performing clean installation..."
echo "Clearing npm cache again to ensure clean state..."
npm cache clean --force || echo "Cache clean failed, continuing with installation..."

# Step 8: Install with --no-optional to reduce potential issues
echo "Step 8: Installing dependencies with reduced options..."
npm install --no-optional || npm install --no-package-lock || npm install --force

echo "===== NPM Installation Fix (CI) Completed ====="
echo "If you encounter any issues, you can restore the backup package-lock.json with:"
echo "cp package-lock.json.backup package-lock.json"
