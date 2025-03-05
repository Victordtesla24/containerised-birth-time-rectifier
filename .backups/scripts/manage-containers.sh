#!/bin/bash

# Docker Container Management Script
# This script provides a unified interface for Docker container operations

# Set colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Default mode
MODE="dev"

# Show header
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}    BIRTH TIME RECTIFIER CONTAINER MANAGER  ${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "Run Date: $(date)"
echo -e "Project Root: ${PROJECT_ROOT}"
echo -e "${BLUE}--------------------------------------------${NC}\n"

# Show usage information
usage() {
  echo -e "Usage: $0 [OPTION]"
  echo -e "Options:"
  echo -e "  --run [dev|prod]     Build and run containers (dev mode by default)"
  echo -e "  --test [dev|prod]    Test containers (dev mode by default)"
  echo -e "  --stop               Stop running containers"
  echo -e "  --clean              Stop and remove containers, volumes, and images"
  echo -e "  --help               Show this help message"
  echo -e "\nExamples:"
  echo -e "  $0 --run             # Run containers in dev mode"
  echo -e "  $0 --run prod        # Run containers in prod mode"
  echo -e "  $0 --test            # Test containers in dev mode"
  echo -e "  $0 --stop            # Stop containers"
}

# Function to run containers
run_containers() {
  local container_mode="$1"

  echo -e "${BLUE}Building and running containers in ${container_mode} mode...${NC}"

  if ! "${PROJECT_ROOT}/scripts/run_containers.sh" "$container_mode"; then
    echo -e "\n${RED}Failed to build and run containers.${NC}"
    exit 1
  fi

  echo -e "\n${GREEN}Containers are running in ${container_mode} mode.${NC}"
}

# Function to test containers
test_containers() {
  local container_mode="$1"

  echo -e "${BLUE}Testing containers in ${container_mode} mode...${NC}"

  if ! "${PROJECT_ROOT}/scripts/test_containers.sh" "$container_mode"; then
    echo -e "\n${RED}Container tests failed.${NC}"
    exit 1
  fi

  echo -e "\n${GREEN}Container tests passed successfully.${NC}"
}

# Function to stop containers
stop_containers() {
  echo -e "${BLUE}Stopping containers...${NC}"

  if ! docker compose down; then
    echo -e "\n${RED}Failed to stop containers.${NC}"
    exit 1
  fi

  echo -e "\n${GREEN}Containers stopped successfully.${NC}"
}

# Function to clean containers and images
clean_containers() {
  echo -e "${YELLOW}This will stop and remove all containers, volumes, and images related to the project.${NC}"
  echo -e "${YELLOW}Are you sure you want to proceed? (y/n)${NC}"

  read -r answer
  if [[ ! $answer =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Operation cancelled.${NC}"
    exit 0
  fi

  echo -e "${BLUE}Stopping and removing containers, volumes, and images...${NC}"

  # Stop and remove containers and volumes
  docker compose down --volumes

  # Remove dangling images
  docker image prune -f

  echo -e "\n${GREEN}Cleanup completed successfully.${NC}"
}

# Process command-line arguments
if [ $# -eq 0 ]; then
  usage
  exit 1
fi

ACTION=""
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --run)
      ACTION="run"
      shift
      if [[ "$1" == "dev" || "$1" == "prod" ]]; then
        MODE="$1"
        shift
      fi
      ;;
    --test)
      ACTION="test"
      shift
      if [[ "$1" == "dev" || "$1" == "prod" ]]; then
        MODE="$1"
        shift
      fi
      ;;
    --stop)
      ACTION="stop"
      shift
      ;;
    --clean)
      ACTION="clean"
      shift
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
done

# Execute the requested action
case $ACTION in
  "run")
    run_containers "$MODE"
    ;;
  "test")
    test_containers "$MODE"
    ;;
  "stop")
    stop_containers
    ;;
  "clean")
    clean_containers
    ;;
  *)
    echo -e "${RED}Error: No action specified.${NC}\n"
    usage
    exit 1
    ;;
esac

exit 0
