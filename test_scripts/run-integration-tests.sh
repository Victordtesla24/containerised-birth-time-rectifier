#!/bin/bash

# Colors for pretty output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if services are running
check_services() {
  echo -e "${BLUE}Checking if services are running...${NC}"
  
  # Check if frontend is running
  if curl -s http://localhost:3001/api/health > /dev/null; then
    echo -e "${GREEN}✓ Frontend service is running${NC}"
    frontend_running=true
  else
    echo -e "${RED}✗ Frontend service is not running${NC}"
    frontend_running=false
  fi
  
  # Check if AI service is running
  if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ AI service is running${NC}"
    ai_running=true
  else
    echo -e "${RED}✗ AI service is not running${NC}"
    ai_running=false
  fi
  
  # Return true if both services are running
  if [ "$frontend_running" = true ] && [ "$ai_running" = true ]; then
    return 0
  else
    return 1
  fi
}

# Main script

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   Birth Time Rectifier Integration Tests   ${NC}"
echo -e "${BLUE}============================================${NC}"
echo

# Check if services are running
if ! check_services; then
  echo -e "${YELLOW}Would you like to start the services? (y/n)${NC}"
  read -r answer
  if [[ $answer =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}Starting services...${NC}"
    ./start_services.sh &
    
    # Wait for services to be ready
    echo -e "${BLUE}Waiting for services to start...${NC}"
    max_attempts=10
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
      if check_services; then
        echo -e "${GREEN}All services are running!${NC}"
        break
      fi
      
      if [ $attempt -eq $max_attempts ]; then
        echo -e "${RED}Timeout waiting for services to start. Please start them manually.${NC}"
        exit 1
      fi
      
      echo -e "${YELLOW}Waiting for services... (Attempt $attempt/$max_attempts)${NC}"
      attempt=$((attempt + 1))
      sleep 5
    done
  else
    echo -e "${RED}Services must be running to execute integration tests. Exiting.${NC}"
    exit 1
  fi
fi

echo
echo -e "${BLUE}Running static tests first...${NC}"
npm test -- --testPathIgnorePatterns=integration

if [ $? -ne 0 ]; then
  echo -e "${RED}Static tests failed. Please fix them before running integration tests.${NC}"
  exit 1
fi

echo
echo -e "${BLUE}Running integration tests...${NC}"
npm test -- --testMatch=**/__tests__/integration/**/*test.{ts,tsx}

test_result=$?

echo
if [ $test_result -eq 0 ]; then
  echo -e "${GREEN}All integration tests passed successfully!${NC}"
else
  echo -e "${RED}Some integration tests failed. Please check the output for details.${NC}"
fi

exit $test_result 