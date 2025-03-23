#!/bin/bash
set -e

echo "Running Next.js entrypoint script..."

# Create the necessary directories and files
mkdir -p .next
touch .next/fallback-build-manifest.json
echo "{}" > .next/fallback-build-manifest.json

# Ensure proper permissions (allow write access for all)
chmod -R 777 .next
chmod -R 777 node_modules 2>/dev/null || true

# Install required babel plugins
echo "Installing required babel packages..."
npm install --save-dev @babel/core @babel/preset-env @babel/preset-react babel-plugin-transform-runtime next
chmod -R 777 node_modules

echo "Next.js directories and files prepared"

# Create a simplified babel config without references to next/babel
echo "module.exports = {
  presets: [
    ['@babel/preset-env', { targets: { node: 'current' } }],
    '@babel/preset-react'
  ],
  plugins: ['@babel/plugin-transform-runtime']
};" > babel.config.js

# Check NODE_ENV and ensure the right setup
if [ "$NODE_ENV" = "development" ]; then
    echo "Starting Next.js in development mode..."

    # Run the dev server with fallback in place
    echo "{}" > .next/fallback-build-manifest.json

    # Start Next.js
    exec npx next dev
else
    echo "Building Next.js for production..."

    # Clean any previous builds and ensure folders exist
    rm -rf .next
    mkdir -p .next
    echo "{}" > .next/fallback-build-manifest.json
    chmod -R 777 .next

    # Build the application with retries
    echo "Running Next.js build..."
    max_retries=3
    retry_count=0

    until npx next build; do
        retry_count=$((retry_count+1))
        echo "Build attempt $retry_count of $max_retries"

        if [ $retry_count -ge $max_retries ]; then
            echo "Failed to build after $max_retries attempts. Starting in dev mode as fallback."
            echo "{}" > .next/fallback-build-manifest.json
            chmod -R 777 .next

            # Try to start in dev mode as a last resort
            exec npx next dev
            break
        fi

        echo "Build failed. Retrying... ($retry_count/$max_retries)"
        # Re-create the fallback file before each retry
        echo "{}" > .next/fallback-build-manifest.json
        chmod -R 777 .next
        sleep 2
    done

    echo "Starting Next.js in production mode..."
    exec npx next start
fi
