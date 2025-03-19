# Environment Variables Guide

This document explains how to set up and use environment variables with the `.env` file for the Birth Time Rectifier application.

## Overview

The application uses a `.env` file to manage environment variables, which provides several benefits:

- Keeps sensitive information like API keys secure and out of version control
- Simplifies configuration across different environments
- Makes testing with different configurations easier

## Required Environment Variables

The following environment variables are required for the application to function properly:

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key for AI integration | `sk-abcdef123456789...` |
| `DEBUG` | Enable or disable debug mode | `True` or `False` |
| `SECRET_KEY` | Secret key for authentication | Any secure string |
| `GPU_MEMORY_FRACTION` | Amount of GPU memory to use (0-1) | `0.7` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per minute | `60` |

## Setting Up Your Environment

1. Create a `.env` file in the root directory of the project
2. Add your environment variables to the file using the format:

```
VARIABLE_NAME=value
```

3. Make sure your `.env` file is in the `.gitignore` to avoid committing sensitive information

### Example `.env` File

```
# Environment variables for Birth Time Rectifier
# API Keys
OPENAI_API_KEY=sk-your-api-key-here

# Application settings
DEBUG=True
SECRET_KEY=your-secret-key-here

# GPU Settings
GPU_MEMORY_FRACTION=0.7

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
```

## Running Tests with Environment Variables

To run tests with the correct environment variables, use the provided `run_tests.sh` script:

```bash
./run_tests.sh [test path]
```

For example:

```bash
# Run all tests
./run_tests.sh

# Run a specific test file
./run_tests.sh tests/unit/test_chart_verification.py

# Run a specific test
./run_tests.sh tests/unit/test_chart_verification.py::test_chart_verification_flow
```

The script automatically loads the variables from your `.env` file before running the tests.

## Verifying Your Environment

You can verify that your environment variables are correctly loaded by running:

```bash
python test_env.py
```

This script will check if the required environment variables are set and display their values.

## Troubleshooting

If you encounter errors related to missing environment variables:

1. Ensure your `.env` file exists in the root directory
2. Verify that the variable names match exactly (they are case-sensitive)
3. Make sure you're using the correct format (`VARIABLE_NAME=value` without quotes)
4. Check that python-dotenv is installed (`pip install python-dotenv`)

For OpenAI API issues, verify that your API key is valid and has not expired.
