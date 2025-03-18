# Birth Time Rectifier Scripts

This directory contains utility scripts for the Birth Time Rectifier project.

## NPM Installation Fix Scripts

These scripts help fix common npm installation issues, particularly permission problems that can occur on macOS and Linux systems.

### fix-npm-permissions.sh

This script fixes permission issues with the npm cache directory and project node_modules directory.

```bash
./fix-npm-permissions.sh
```

### update-package-lock.sh

This script updates the package-lock.json file to fix dependency issues.

```bash
./update-package-lock.sh
```

### fix-npm-installation.sh

This is a comprehensive script that fixes common npm installation issues by addressing permissions, cleaning caches, and updating package-lock.json. It provides an interactive experience with clear prompts and feedback.

```bash
./fix-npm-installation.sh
```

### fix-npm-installation-ci.sh

This is a non-interactive version of the fix-npm-installation.sh script, designed for CI/CD environments or automated scripts. It accepts command-line arguments to control its behavior.

```bash
# Basic usage
./fix-npm-installation-ci.sh

# Update package-lock.json
./fix-npm-installation-ci.sh --update-package-lock

# Skip npm update
./fix-npm-installation-ci.sh --skip-npm-update

# Skip permission fixes (for environments without sudo)
./fix-npm-installation-ci.sh --skip-permissions

# Show help
./fix-npm-installation-ci.sh --help
```

## Common NPM Issues and Solutions

### Permission Errors

If you encounter permission errors when running npm commands, such as:

```
npm error code EACCES
npm error syscall unlink
npm error path /Users/username/.npm/_cacache/...
npm error errno -13
```

Run the fix-npm-permissions.sh script to fix the permissions:

```bash
./scripts/fix-npm-permissions.sh
```

### Package Lock Issues

If you encounter issues with package-lock.json, such as:

```
npm ERR! Invalid dependency type requested: alias
```

Run the update-package-lock.sh script to regenerate the package-lock.json file:

```bash
./scripts/update-package-lock.sh
```

### Comprehensive Fix

If you're experiencing multiple npm issues, run the comprehensive fix script:

```bash
./scripts/fix-npm-installation.sh
```

## Test Scripts

### run_integrated_api_test.sh

This script runs the integrated API tests for the Birth Time Rectifier project. It tests the complete flow from session initialization to chart export.

```bash
# Basic usage
./run_integrated_api_test.sh

# Use random birth data
./run_integrated_api_test.sh --random-data

# Validate against sequence diagram
./run_integrated_api_test.sh --validate-sequence

# Set confidence threshold
./run_integrated_api_test.sh --confidence-threshold 0.9

# Skip frontend tests
./run_integrated_api_test.sh --skip-frontend

# Skip backend tests
./run_integrated_api_test.sh --skip-backend

# Use custom birth data file
./run_integrated_api_test.sh --birth-data /path/to/birth_data.json

# Show help
./run_integrated_api_test.sh --help
```
