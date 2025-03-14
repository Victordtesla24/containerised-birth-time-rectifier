#!/bin/bash
set -e

echo "Running Next.js entrypoint script..."

# Create the necessary directories and files
mkdir -p .next
touch .next/fallback-build-manifest.json

# Ensure proper permissions
chmod -R 755 .next

# Install missing babel dependencies if needed
if ! node -e "try { require('@babel/plugin-transform-runtime'); console.log('Babel plugin found'); } catch(e) { console.error('Babel plugin missing'); process.exit(1); }"; then
  echo "Installing missing Babel plugin..."
  npm install --save-dev @babel/plugin-transform-runtime @babel/core
fi

echo "Next.js directories and files prepared"

# Check NODE_ENV and ensure the right setup
if [ "$NODE_ENV" = "development" ]; then
    echo "Starting Next.js in development mode..."

    # Ensure the fallback file is properly created with content
    echo "{}" > .next/fallback-build-manifest.json

    # Run the dev server
    exec npm run dev
else
    echo "Building Next.js for production..."

    # Clean any previous builds and ensure folders exist
    rm -rf .next
    mkdir -p .next
    echo "{}" > .next/fallback-build-manifest.json

    # Build the application with retries
    echo "Running Next.js build..."
    max_retries=3
    retry_count=0

    until npm run build; do
        retry_count=$((retry_count+1))
        echo "Build attempt $retry_count of $max_retries"

        if [ $retry_count -ge $max_retries ]; then
            echo "Failed to build after $max_retries attempts. Starting in dev mode as fallback."
            echo "{}" > .next/fallback-build-manifest.json
            exec npm run dev
            break
        fi

        echo "Build failed. Retrying... ($retry_count/$max_retries)"
        # Re-create the fallback file before each retry
        echo "{}" > .next/fallback-build-manifest.json
        sleep 2
    done

    echo "Starting Next.js in production mode..."
    exec npm start
fi
