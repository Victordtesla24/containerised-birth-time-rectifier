#!/bin/bash
#
# API Gateway Implementation Script
#
# This script automates the implementation of the Unified API Gateway architecture.
#

set -e  # Exit on error

echo "=== API Gateway Implementation Script ==="
echo ""

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT=$(pwd)
BACKUP_DIR="$PROJECT_ROOT/backup-$(date +%Y%m%d-%H%M%S)"

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo -e "${YELLOW}Created backup directory: $BACKUP_DIR${NC}"

# Function to backup a file
backup_file() {
  local file=$1
  if [ -f "$file" ]; then
    cp "$file" "$BACKUP_DIR/$(basename "$file")"
    echo -e "${GREEN}Backed up: $file${NC}"
  else
    echo -e "${YELLOW}Warning: $file does not exist, skipping backup${NC}"
  fi
}

# Backup files
echo ""
echo "Backing up files..."
backup_file "ai_service/main.py"
backup_file "ai_service/api/middleware/legacy_support.py"

# Install required dependencies
echo ""
echo "Installing required dependencies..."
npm install --save http-proxy-middleware next-connect
echo -e "${GREEN}Dependencies installed successfully${NC}"

# Verify required files
echo ""
echo "Verifying required files..."
required_files=(
  "src/utils/unifiedApiClient.js"
  "src/utils/apiTransitionHelper.js"
  "src/pages/api/[[...path]].js"
  "src/config/apiGateway.js"
)

missing_files=false
for file in "${required_files[@]}"; do
  if [ ! -f "$file" ]; then
    echo -e "${RED}Error: Required file $file is missing${NC}"
    missing_files=true
  else
    echo -e "${GREEN}✓ $file exists${NC}"
  fi
done

if [ "$missing_files" = true ]; then
  echo -e "${RED}Error: Some required files are missing. Please create them before running this script.${NC}"
  exit 1
fi

# Update legacy files to use the transition helper
echo ""
echo "Updating legacy imports to use transition helper..."

# Create transition import line
transition_import="// Updated to use transition helper\nimport pythonBackendClient, { generateChart, rectifyBirthTime, generateQuestionnaire, submitQuestionnaireAnswers, validateBirthDetails, isPythonBackendAvailable } from '../utils/apiTransitionHelper';"

# Find files that import pythonBackendClient and update them
echo "Finding files that import pythonBackendClient..."
import_files=$(grep -l "import.*pythonBackendClient" --include="*.js" --include="*.jsx" --include="*.ts" --include="*.tsx" -r src/)

for file in $import_files; do
  echo "Updating imports in $file..."
  # Create a backup of the file
  backup_file "$file"

  # Replace the import statement with our transition import
  sed -i'.bak' -E 's/import.*pythonBackendClient.*from.*$/'"$transition_import"'/' "$file"

  # Remove the backup file created by sed
  rm "${file}.bak"

  echo -e "${GREEN}Updated imports in $file${NC}"
done

# Test API gateway
echo ""
echo "Testing API gateway..."
if [ -f "test_scripts/test-api-gateway.sh" ]; then
  chmod +x test_scripts/test-api-gateway.sh

  if [ "$1" == "test" ] || [ "$2" == "test" ]; then
    ./test_scripts/test-api-gateway.sh
  else
    echo -e "${YELLOW}Skipped running tests (use './scripts/implement-api-gateway.sh test' to run tests)${NC}"
  fi
else
  echo -e "${YELLOW}Warning: test-api-gateway.sh not found, skipping tests${NC}"
fi

echo ""
echo -e "${GREEN}API Gateway implementation completed!${NC}"
echo ""
echo "Next steps:"
echo "1. Run the application with 'npm run dev'"
echo "2. Test the API gateway with './test_scripts/test-api-gateway.sh'"
echo "3. Apply the changes with './scripts/implement-api-gateway.sh apply'"
echo ""
