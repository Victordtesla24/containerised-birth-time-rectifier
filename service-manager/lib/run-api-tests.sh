#!/bin/bash

# ===========================================
# Run API Tests Script
# ===========================================
# This script kills any processes on ports 8000, 3000, and 9000,
# starts the API service in the background, and runs the API sequence flow tests

# ANSI color codes for status messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[1;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored status messages
print_status() {
  local status=$1
  local message=$2
  case $status in
    "INFO") echo -e "${BLUE}ℹ${NC} $message" ;;
    "SUCCESS") echo -e "${GREEN}✅${NC} $message" ;;
    "WARNING") echo -e "${YELLOW}⚠️${NC} $message" ;;
    "ERROR") echo -e "${RED}❌${NC} $message" ;;
    "START") echo -e "${MAGENTA}🧪${NC} $message" ;;
    "KILL") echo -e "${RED}🛑${NC} $message" ;;
    "RESTART") echo -e "${CYAN}🔄${NC} $message" ;;
    "SERVER") echo -e "${GREEN}🚀${NC} $message" ;;
    "ENDPOINTS") echo -e "${CYAN}📡${NC} $message" ;;
    "WAIT") echo -e "${YELLOW}⏳${NC} $message" ;;
    *) echo -e "${NC}$message" ;;
  esac
}

print_status "START" "Starting API Test setup..."

# Kill processes on service ports first
print_status "KILL" "Killing processes on service ports..."
./kill-service-ports.sh --auto-confirm > /dev/null 2>&1

# Start the debug API service
print_status "SERVER" "Starting debug API service on port 8001 in the background..."
python debug_chart_api.py &
DEBUG_SERVER_PID=$!

# Give the server time to start
sleep 3

# Start the API service
print_status "SERVER" "Starting API service on port 9000 in the background..."
API_PORT=9000 python -m ai_service.api.main > /dev/null 2>&1 &
API_PID=$!

# Wait for service to initialize
print_status "WAIT" "Waiting for API service to initialize..."
sleep 5

# Get API endpoints
print_status "ENDPOINTS" "Retrieving API endpoints..."
./view-api-endpoints.sh --fallback > /dev/null

# Get WebSocket API Gateway details
print_status "ENDPOINTS" "Retrieving WebSocket API Gateway details..."
./view-websocket-endpoints.sh --fallback > /dev/null

# Run tests
print_status "START" "Running API sequence flow tests..."
python -m pytest tests/integration/test_api_sequence_flow.py -v

# Cleanup
print_status "KILL" "Shutting down API service..."
kill $API_PID $DEBUG_SERVER_PID > /dev/null 2>&1

print_status "SUCCESS" "API tests completed"
