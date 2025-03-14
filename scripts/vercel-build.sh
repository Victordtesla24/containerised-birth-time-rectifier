#!/bin/bash

# Custom build script for Vercel deployment
# This script uses a simplified configuration to avoid build errors

echo "=== Starting custom Vercel build ==="

# Save original configuration files
echo "Backing up original configuration files..."
cp package.json package.json.original
cp next.config.js next.config.js.original
cp src/components/ChartVisualization.js src/components/ChartVisualization.js.original
cp src/styles/globals.css src/styles/globals.css.original
cp src/styles/celestial.css src/styles/celestial.css.original

# Replace with simplified versions
echo "Using simplified configurations for Vercel deployment..."
cp package-vercel.json package.json
cp next.config.vercel.js next.config.js
cp src/components/ChartVisualization.simple.js src/components/ChartVisualization.js
cp src/styles/globals.simple.css src/styles/globals.css
cp src/styles/celestial.simple.css src/styles/celestial.css

# Ensure mocks directory exists
mkdir -p src/mocks

# Install dependencies
echo "Installing dependencies..."
npm install

# Explicitly install tailwindcss to fix build errors
echo "Ensuring tailwindcss is installed..."
npm install tailwindcss@3.3.5 postcss autoprefixer --no-save

# Build with Next.js
echo "Building with Next.js..."
NODE_ENV=production DISABLE_ESLINT_PLUGIN=true SKIP_TAILWIND=true next build

# Restore original configuration files
echo "Restoring original configuration files..."
mv package.json.original package.json
mv next.config.js.original next.config.js
mv src/components/ChartVisualization.js.original src/components/ChartVisualization.js
mv src/styles/globals.css.original src/styles/globals.css
mv src/styles/celestial.css.original src/styles/celestial.css

echo "=== Build completed ==="
