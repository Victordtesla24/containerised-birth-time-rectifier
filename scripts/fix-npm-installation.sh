#!/bin/bash
# Comprehensive npm installation fix script
# This script addresses common npm installation issues

set -e  # Exit on error

echo "===== Birth Time Rectifier: NPM Installation Fix ====="
echo "Starting comprehensive npm installation fix..."

# Step 1: Fix ownership of the .npm directory
echo "Step 1: Fixing ownership of ~/.npm directory..."
sudo chown -R $(whoami):$(id -g) "/Users/vicd/.npm"

# Step 2: Clear npm cache safely
echo "Step 2: Clearing npm cache..."
npm cache clean --force || echo "Cache clean failed, continuing with other fixes..."

# Step 3: Fix permissions for the project directory
echo "Step 3: Fixing permissions for the project directory..."
sudo chown -R $(whoami):$(id -g) .

# Step 4: Update npm to latest version
echo "Step 4: Updating npm to latest version..."
sudo npm install --global npm@latest

# Step 5: Ensure node_modules has correct permissions
echo "Step 5: Ensuring node_modules has correct permissions..."
if [ -d "node_modules" ]; then
  sudo chown -R $(whoami):$(id -g) node_modules
  echo "Fixed node_modules permissions"
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

echo "Installing dependencies..."
npm install

echo "===== NPM Installation Fix Completed ====="
echo "If you encounter any issues, you can restore the backup package-lock.json with:"
echo "cp package-lock.json.backup package-lock.json"
