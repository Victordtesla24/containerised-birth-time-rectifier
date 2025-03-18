#!/bin/bash

# Update Package Lock Script
# This script updates the package-lock.json file to fix dependency issues

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  PACKAGE LOCK UPDATER  ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"

# Get project directory
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PACKAGE_LOCK="$PROJECT_DIR/package-lock.json"

# Check if package-lock.json exists
if [ -f "$PACKAGE_LOCK" ]; then
    echo -e "${YELLOW}Backing up existing package-lock.json...${NC}"
    cp "$PACKAGE_LOCK" "$PACKAGE_LOCK.backup"
    echo -e "${GREEN}✓ Backup created at $PACKAGE_LOCK.backup${NC}"
else
    echo -e "${YELLOW}⚠ No package-lock.json found, will create a new one${NC}"
fi

# Remove node_modules and package-lock.json
echo -e "\n${BLUE}Removing node_modules and package-lock.json...${NC}"
rm -rf "$PROJECT_DIR/node_modules"
rm -f "$PACKAGE_LOCK"
echo -e "${GREEN}✓ Removed node_modules and package-lock.json${NC}"

# Clean npm cache
echo -e "\n${BLUE}Cleaning npm cache...${NC}"
npm cache clean --force
echo -e "${GREEN}✓ Cleaned npm cache${NC}"

# Install dependencies
echo -e "\n${BLUE}Installing dependencies and generating new package-lock.json...${NC}"
cd "$PROJECT_DIR" && npm install

# Check if installation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ Successfully updated package-lock.json and installed dependencies${NC}"
else
    echo -e "${RED}${BOLD}✗ Failed to update package-lock.json${NC}"

    # Restore backup if available
    if [ -f "$PACKAGE_LOCK.backup" ]; then
        echo -e "${YELLOW}Restoring package-lock.json from backup...${NC}"
        cp "$PACKAGE_LOCK.backup" "$PACKAGE_LOCK"
        echo -e "${GREEN}✓ Restored package-lock.json from backup${NC}"
    fi
fi

echo -e "\n${YELLOW}Note: If you still encounter issues, try running the fix-npm-permissions.sh script first.${NC}"
