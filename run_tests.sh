#!/bin/bash

# Script to run tests with proper environment variables

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please create a .env file with OPENAI_API_KEY=your-api-key"
    exit 1
fi

# Source the .env file to load variables
set -a
source .env
set +a

# Run the specified tests or all tests if none specified
if [ $# -eq 0 ]; then
    echo "Running all tests..."
    python -m pytest
else
    echo "Running specified tests..."
    python -m pytest "$@"
fi

# Run the specified tests or all tests if none specified
if [ $# -eq 0 ]; then
    echo "Running all tests..."
    python3 -m pytest
else
    echo "Running specified tests..."
    python3 -m pytest "$@"
fi
