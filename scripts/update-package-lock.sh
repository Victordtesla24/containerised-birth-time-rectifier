#!/bin/bash

# Script to regenerate package-lock.json file

set -e

echo "Updating package-lock.json file..."

# Remove existing package-lock.json
if [ -f package-lock.json ]; then
  echo "Removing existing package-lock.json..."
  rm package-lock.json
fi

# Remove node_modules directory
if [ -d node_modules ]; then
  echo "Removing node_modules directory..."
  rm -rf node_modules
fi

# Install dependencies and generate a new package-lock.json
echo "Installing dependencies and generating new package-lock.json..."
npm install --legacy-peer-deps

echo "Package-lock.json has been updated successfully!"
echo "You can now build your Docker containers with the updated package-lock.json file."
