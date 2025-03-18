#!/bin/bash
# Fix npm permissions script
# This script addresses common npm permission issues

echo "Starting npm permission fix..."

# Step 1: Fix ownership of the .npm directory
echo "Fixing ownership of ~/.npm directory..."
sudo chown -R $(whoami):$(id -g) ~/.npm

# Step 2: Clear npm cache safely
echo "Clearing npm cache..."
npm cache clean --force

# Step 3: Fix permissions for the project directory
echo "Fixing permissions for the project directory..."
sudo chown -R $(whoami):$(id -g) .

# Step 4: Ensure node_modules has correct permissions
echo "Ensuring node_modules has correct permissions..."
if [ -d "node_modules" ]; then
  sudo chown -R $(whoami):$(id -g) node_modules
fi

echo "Permission fix completed!"
echo "You can now run 'npm install' to install dependencies."
