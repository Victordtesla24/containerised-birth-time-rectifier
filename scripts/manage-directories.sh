#!/bin/bash

# Directory Management Consolidation Script
# This script provides a unified interface for directory management operations

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Show header
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}    BIRTH TIME RECTIFIER DIRECTORY MANAGER  ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Run Date: $(date)"
echo -e "Project Root: ${PROJECT_ROOT}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Show usage information
usage() {
  echo -e "Usage: $0 [OPTION]"
  echo -e "Options:"
  echo -e "  --cleanup        Clean up temporary files only (safe)"
  echo -e "  --consolidate    Run directory consolidation (use with caution!)"
  echo -e "  --finalize       Finalize consolidation (use with caution!)"
  echo -e "  --help           Show this help message"
  echo -e "\nExamples:"
  echo -e "  $0 --cleanup     # Run temp file cleanup"
  echo -e "  $0 --help        # Show help"
}

# Function to confirm dangerous actions
confirm_action() {
  local action="$1"

  echo -e "${YELLOW}WARNING: ${action} is potentially dangerous and may modify your project structure.${NC}"
  echo -e "${YELLOW}Are you sure you want to proceed? (y/n)${NC}"

  read -r answer
  if [[ ! $answer =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Operation cancelled.${NC}"
    exit 0
  fi
}

# Run temp file cleanup
run_cleanup() {
  echo -e "${BLUE}Running temporary file cleanup...${NC}"
  node "${PROJECT_ROOT}/scripts/cleanup-temp-files.js"

  if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Temporary file cleanup completed successfully.${NC}"
  else
    echo -e "\n${RED}Temporary file cleanup encountered errors.${NC}"
    exit 1
  fi
}

# Run directory consolidation
run_consolidation() {
  echo -e "${BLUE}Running directory consolidation...${NC}"
  confirm_action "Directory consolidation"

  node "${PROJECT_ROOT}/scripts/consolidate-directories.js"

  if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Directory consolidation completed successfully.${NC}"
    echo -e "${YELLOW}To finalize the consolidation, run this script with --finalize${NC}"
  else
    echo -e "\n${RED}Directory consolidation encountered errors.${NC}"
    exit 1
  fi
}

# Finalize consolidation
finalize_consolidation() {
  echo -e "${BLUE}Finalizing directory consolidation...${NC}"
  confirm_action "Finalizing consolidation"

  node "${PROJECT_ROOT}/scripts/cleanup-consolidation.js"

  if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}Consolidation finalization completed successfully.${NC}"
  else
    echo -e "\n${RED}Consolidation finalization encountered errors.${NC}"
    exit 1
  fi
}

# Process command-line arguments
if [ $# -eq 0 ]; then
  usage
  exit 1
fi

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --cleanup)
      run_cleanup
      ;;
    --consolidate)
      run_consolidation
      ;;
    --finalize)
      finalize_consolidation
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      echo -e "${RED}Error: Unknown option: $1${NC}\n"
      usage
      exit 1
      ;;
  esac
  shift
done

echo -e "\n${BLUE}Directory management operations completed.${NC}"
exit 0
