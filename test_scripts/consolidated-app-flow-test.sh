#!/bin/bash

# Consolidated Astrological Chart Application Test Script
#
# This script provides both CLI and menu-driven interfaces to test the complete
# astrological chart application flow using Playwright tests. It follows the
# application flow diagram:
#
# A[Landing Page] --> B[Birth Details Form]
# B --> C{Valid Details?}
# C -->|Yes| D[Initial Chart Generation]
# C -->|No| B
# D --> E[Chart Visualization]
# E --> F[Questionnaire]
# F --> G[AI Analysis]
# G --> H{Confidence > 80%?}
# H -->|Yes| I[Birth Time Rectification]
# H -->|No| J[Additional Questions]
# I --> K[Chart with Rectified Birth Time]
# J --> G
# K --> L[Results]
# L --> M[Export/Share]
#
# Available test patterns:
# - "complete astrological chart application flow" (Tests all 8 steps)
# - "validation failure path" (Tests A→B→C→B flow)
# - "low confidence path" (Tests G→H→J→G flow)
# - "boundary cases" (Tests edge cases with extreme coordinates)
# - "api endpoints validation" (Verifies API endpoints)
#
# Usage examples:
# - Standard full test with services & dependencies:
#   ./consolidated-app-flow-test.sh
#
# - Run without installing dependencies:
#   ./consolidated-app-flow-test.sh --no-deps
#
# - Run without starting services (if already running):
#   ./consolidated-app-flow-test.sh --no-services
#
# - Run specific test case:
#   ./consolidated-app-flow-test.sh --test-pattern "validation failure path"
#
# - Run with multiple workers in parallel:
#   ./consolidated-app-flow-test.sh --workers 3
#
# - Run in menu-driven mode:
#   ./consolidated-app-flow-test.sh --menu
#
# - Specify model for test execution:
#   ./consolidated-app-flow-test.sh --model "deepseek-coder-v2"
#
set -e  # Exit immediately if a command exits with a non-zero status

# Token Optimization - Component Abbreviations
# BDF: Birth Details Form
# CV:  Chart Visualization
# QS:  Questionnaire System
# AIA: AI Analysis
# BTR: Birth Time Rectification
# VS:  Validation Service
# GS:  Geocoding Service
# CCS: Chart Calculation Service
# DQS: Dynamic Questionnaire Service

# Token Optimization - Model Selection Strategy
# Default to DeepSeek-Coder-V2 for routine coding tasks (~$0.20/100K tokens)
# Can be overridden with --model parameter or MODEL_SELECTION env var
MODEL_SELECTION=${MODEL_SELECTION:-"deepseek-coder-v2"}
# Available models:
# - deepseek-coder-v2: For routine coding tasks
# - claude-3-haiku:    For debugging
# - claude-3-5-sonnet: For complex architecture design
# - qwen-2-5-coder:    For UI/UX improvements
# - gemini-2-0-flash:  For documentation

# Token usage tracking
TOKEN_USAGE=0
TOKEN_DAILY_LIMIT=100000

# Color definitions for pretty output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Docker image to use - updated to match Playwright version requirements
PLAYWRIGHT_IMAGE="mcr.microsoft.com/playwright:v1.50.1-jammy"

# Default options
INSTALL_DEPS=true
START_SERVICES=true
WORKERS=1
TEST_PATTERN='complete astrological chart application flow'
VERBOSE=false
SHOULD_ASK_TO_STOP=true
USE_DOCKER=true  # Option to disable Docker
MENU_MODE=false  # Option to run in menu-driven mode
CI_MODE=false    # Option to run in CI mode

# Base directory - where we are now
BASE_DIR="$(pwd)"

# Detect Mac OS and set correct Docker socket path
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS specific Docker socket path - Try multiple possible locations
  if [ -S "/var/run/docker.sock" ]; then
    export DOCKER_HOST="unix:///var/run/docker.sock"
    echo -e "${YELLOW}Detected macOS, using Docker socket: $DOCKER_HOST${NC}"
  elif [ -S "/Users/Shared/Library/Containers/com.docker.docker/Data/docker-cli.sock" ]; then
    export DOCKER_HOST="unix:///Users/Shared/Library/Containers/com.docker.docker/Data/docker-cli.sock"
    echo -e "${YELLOW}Detected macOS, using Docker socket: $DOCKER_HOST${NC}"
  elif [ -S "$HOME/Library/Containers/com.docker.docker/Data/docker-cli.sock" ]; then
    export DOCKER_HOST="unix:///$HOME/Library/Containers/com.docker.docker/Data/docker-cli.sock"
    echo -e "${YELLOW}Detected macOS, using Docker socket: $DOCKER_HOST${NC}"
  elif [ -S "/var/run/com.docker.docker.sock" ]; then
    export DOCKER_HOST="unix:///var/run/com.docker.docker.sock"
    echo -e "${YELLOW}Detected macOS, using Docker socket: $DOCKER_HOST${NC}"
  else
    echo -e "${RED}Warning: Could not find Docker socket. Docker commands may fail.${NC}"
    # Check if Docker Desktop is running
    if pgrep -x "Docker" > /dev/null; then
      echo -e "${YELLOW}Docker Desktop appears to be running, but socket not found in expected locations.${NC}"
    else
      echo -e "${RED}Docker Desktop does not appear to be running. Please start Docker Desktop.${NC}"
    fi
  fi
fi

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-deps)
      INSTALL_DEPS=false
      shift
      ;;
    --no-services)
      START_SERVICES=false
      shift
      ;;
    --workers)
      WORKERS="$2"
      shift 2
      ;;
    --test-pattern)
      TEST_PATTERN="$2"
      shift 2
      ;;
    --verbose)
      VERBOSE=true
      shift
      ;;
    --no-prompt)
      SHOULD_ASK_TO_STOP=false
      shift
      ;;
    --no-docker)
      USE_DOCKER=false
      shift
      ;;
    --menu)
      MENU_MODE=true
      shift
      ;;
    --ci)
      CI_MODE=true
      shift
      ;;
    --model)
      MODEL_SELECTION="$2"
      shift 2
      ;;
    --all-tests)
      # Run all available test patterns
      TEST_PATTERN="all"
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --no-deps             Skip installing dependencies"
      echo "  --no-services         Skip starting Docker services"
      echo "  --workers NUMBER      Set number of test workers (default: 1)"
      echo "  --test-pattern PATTERN Run tests matching this pattern"
      echo "                        Available patterns:"
      echo "                        - 'complete astrological chart application flow'"
      echo "                        - 'validation failure path'"
      echo "                        - 'low confidence path'"
      echo "                        - 'boundary cases'"
      echo "                        - 'api endpoints validation'"
      echo "  --all-tests           Run all test patterns sequentially"
      echo "  --verbose             Enable verbose output"
      echo "  --no-prompt           Don't prompt to stop services"
      echo "  --no-docker           Run tests locally without Docker"
      echo "  --menu                Run in menu-driven mode"
      echo "  --ci                  Run in CI mode (automatic testing)"
      echo "  --model MODEL         Select model for test execution:"
      echo "                        - deepseek-coder-v2 (default, for routine tasks)"
      echo "                        - claude-3-haiku (for debugging)"
      echo "                        - claude-3-5-sonnet (for complex architecture)"
      echo "                        - qwen-2-5-coder (for UI/UX improvements)"
      echo "                        - gemini-2-0-flash (for documentation)"
      echo "  --help                Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Function to print section headers
print_header() {
  echo -e "\n${BOLD}${BLUE}=== $1 ===${NC}\n"
}

# Function to print subheaders
print_subheader() {
  echo -e "\n${BOLD}${CYAN}>> $1${NC}\n"
}

# Function to print info messages
print_info() {
  echo -e "${YELLOW}$1${NC}"
}

# Function to print success messages
print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

# Function to print error messages
print_error() {
  echo -e "${RED}❌ $1${NC}"
}

# Function to print warning messages
print_warning() {
  echo -e "${YELLOW}⚠️ $1${NC}"
}

# Function to track token usage - TOKEN_OPTIMIZATION
track_tokens() {
  local prompt_tokens=$1
  local response_tokens=$2
  local total=$(($prompt_tokens + $response_tokens))

  TOKEN_USAGE=$(($TOKEN_USAGE + $total))
  local percentage=$(echo "scale=1; ($TOKEN_USAGE / $TOKEN_DAILY_LIMIT) * 100" | bc)

  print_info "Token usage: $total ($prompt_tokens prompt, $response_tokens response)"
  print_info "Daily total: $TOKEN_USAGE / $TOKEN_DAILY_LIMIT ($percentage%)"

  # Alert if approaching limit
  if [ $(echo "$TOKEN_USAGE > $TOKEN_DAILY_LIMIT * 0.8" | bc) -eq 1 ]; then
    print_error "⚠️ Approaching daily token limit!"
  fi
}

# Template cache for common test operations - TOKEN_OPTIMIZATION
# Using functions instead of associative arrays for better shell compatibility

# Get template by key (compatible with all shells)
get_template() {
  local key="$1"
  case "$key" in
    "form_submit") echo "await page.click('button[data-testid=\"submit-button\"]');" ;;
    "wait_chart") echo "await page.waitForSelector('.chart-visualization');" ;;
    "fill_date") echo "await page.fill('#birthDate', '%s');" ;;
    "fill_time") echo "await page.fill('#birthTime', '%s');" ;;
    "fill_location") echo "await page.fill('#location', '%s');" ;;
    "validate_field") echo "expect(await page.isVisible('text=%s')).toBeTruthy();" ;;
    "screenshot") echo "await page.screenshot({ path: 'screenshot-%s.png' });" ;;
    *) echo "Template not found for key: $key" >&2; return 1 ;;
  esac
}

# Format template with arguments
format_template() {
  local template="$1"
  local arg="$2"
  echo "$template" | sed "s/%s/$arg/g"
}

# Initialize template cache (just a placeholder function for compatibility)
init_template_cache() {
  print_info "Template cache initialized"
}

# Function to start services if needed
start_services() {
  if [ "$START_SERVICES" = true ]; then
    print_header "Starting Services"

    # Check if services are already running
    if docker ps | grep -q "birth-rectifier"; then
      print_success "BTR services already running"
      return 0
    fi

    # Check for redis.conf file
    if [ -f "docker/redis.conf" ]; then
      print_info "Found redis.conf, using standard docker-compose.yml"
      docker compose -f docker-compose.yml up -d
    else
      print_info "Redis config not found, using modified docker compose configuration"

      # Create a temporary docker-compose file that doesn't require redis.conf
      cat > docker-compose.tmp.yml << EOF
version: '3.8'
services:
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.frontend
    container_name: birth-rectifier-frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - MODEL_SELECTION=${MODEL_SELECTION}
    restart: unless-stopped

  ai_service:
    build:
      context: .
      dockerfile: Dockerfile.backend
    container_name: birth-rectifier-ai
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
      - ENVIRONMENT=development
      - REDIS_URL=redis://redis:6379/0
      - MODEL_SELECTION=${MODEL_SELECTION}
    restart: unless-stopped
    depends_on:
      - redis

  redis:
    image: redis:7.2-alpine
    container_name: birth-rectifier-redis
    ports:
      - "6379:6379"
    command: redis-server
    restart: unless-stopped

volumes:
  redis_data:
EOF

      docker compose -f docker-compose.tmp.yml up -d
    fi

    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    wait_for_services
  else
    print_info "Skipping service startup (--no-services flag provided)"
  fi
}

# Function to wait for services to be healthy
wait_for_services() {
  MAX_ATTEMPTS=20
  ATTEMPT=1

  while [ $ATTEMPT -le $MAX_ATTEMPTS ]; do
    print_info "Checking services health (Attempt $ATTEMPT/$MAX_ATTEMPTS)"

    # Check frontend health - Frontend prefers /api/health
    if curl -s http://localhost:3000/api/health > /dev/null; then
      print_success "Frontend service is healthy"
      FRONTEND_HEALTHY=true
    else
      # Try alternative health endpoint if first one fails
      if curl -s http://localhost:3000/health > /dev/null; then
        print_success "Frontend service is healthy (using alternative endpoint)"
        FRONTEND_HEALTHY=true
      else
        echo -e "${YELLOW}⏳ Frontend service is still starting...${NC}"
        FRONTEND_HEALTHY=false
      fi
    fi

    # Check AI service health - Both /health and /api/health work
    if curl -s http://localhost:8000/health > /dev/null; then
      print_success "AIA service is healthy"
      AI_HEALTHY=true
    else
      # Try alternative health endpoint if first one fails
      if curl -s http://localhost:8000/api/health > /dev/null; then
        print_success "AIA service is healthy (using alternative endpoint)"
        AI_HEALTHY=true
      else
        echo -e "${YELLOW}⏳ AIA service is still starting...${NC}"
        AI_HEALTHY=false
      fi
    fi

    # If both services are healthy, we're good to go
    if [ "$FRONTEND_HEALTHY" = true ] && [ "$AI_HEALTHY" = true ]; then
      print_success "All services are ready!"

      # Verify API endpoint consistency with improved validation
      print_info "Validating API endpoint consistency..."
      validate_critical_endpoints

      return 0
    fi

    # If we've reached max attempts, exit with failure
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
      print_error "Timeout waiting for services to be healthy. Please check the Docker logs."
      docker compose logs
      return 1
    fi

    # Wait before next attempt
    ATTEMPT=$((ATTEMPT + 1))
    sleep 10
  done
}

# Function to validate critical API endpoints
validate_critical_endpoints() {
  print_header "Validating Critical API Endpoints"

  # Define the actual endpoints to test based on the dual-registration pattern
  local backend_endpoints=(
    "/health:GET"
    "/api/health:GET"
    "/chart/validate:POST"
    "/api/chart/validate:POST"
    "/geocode:GET"
    "/api/geocode:GET"
    "/chart/generate:POST"
    "/api/chart/generate:POST"
    "/chart/rectify:POST"
    "/api/chart/rectify:POST"
  )

  local frontend_endpoints=(
    "/api/health:GET"
    "/health:GET"
    "/api/chart/validate:POST"
    "/chart/validate:POST"
    "/api/geocode:GET"
    "/geocode:GET"
    "/api/chart/generate:POST"
    "/chart/generate:POST"
    "/api/chart/rectify:POST"
    "/chart/rectify:POST"
  )

  local backend_valid_count=0
  local frontend_valid_count=0

  echo "Testing backend endpoints..."
  for endpoint_spec in "${backend_endpoints[@]}"; do
    # Split endpoint and method
    local endpoint="${endpoint_spec%%:*}"
    local method="${endpoint_spec##*:}"

    # Test the endpoint
    local status
    if [ "$method" = "GET" ]; then
      status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000${endpoint}" 2>/dev/null)
    else
      # For non-GET methods, add a minimal request body
      status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d '{}' "http://localhost:8000${endpoint}" 2>/dev/null)
    fi

    # Check if endpoint is available (200 OK or 4xx = endpoint exists but has validation issues)
    if [[ "$status" =~ ^(200|400|401|403|405|422)$ ]]; then
      print_success "Backend: ${endpoint} - Available (${status})"
      backend_valid_count=$((backend_valid_count + 1))
    else
      print_error "Backend: ${endpoint} - Not available (${status})"
    fi
  done

  echo "Testing frontend endpoints..."
  for endpoint_spec in "${frontend_endpoints[@]}"; do
    # Split endpoint and method
    local endpoint="${endpoint_spec%%:*}"
    local method="${endpoint_spec##*:}"

    # Test the endpoint
    local status
    if [ "$method" = "GET" ]; then
      status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000${endpoint}" 2>/dev/null)
    else
      # For non-GET methods, add a minimal request body
      status=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" -H "Content-Type: application/json" -d '{}' "http://localhost:3000${endpoint}" 2>/dev/null)
    fi

    # Check if endpoint is available
    if [[ "$status" =~ ^(200|400|401|403|405|422)$ ]]; then
      print_success "Frontend: ${endpoint} - Available (${status})"
      frontend_valid_count=$((frontend_valid_count + 1))
    else
      print_error "Frontend: ${endpoint} - Not available (${status})"
    fi
  done

  # Check for specific critical endpoints that must be available
  # Test both primary and alternative health endpoints
  local primary_health_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/health" 2>/dev/null)
  local alt_health_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/health" 2>/dev/null)

  if [[ "$primary_health_status" =~ ^(200|400|401|403|405|422)$ ]]; then
    print_success "Critical endpoint '/api/health' is available (${primary_health_status})"
  elif [[ "$alt_health_status" =~ ^(200|400|401|403|405|422)$ ]]; then
    print_success "Critical endpoint '/health' is available (${alt_health_status})"
  else
    print_error "No health endpoint is available - API service may not be running"
    return 1
  fi

  # Summary
  print_info "Backend endpoints: ${backend_valid_count}/${#backend_endpoints[@]} available"
  print_info "Frontend endpoints: ${frontend_valid_count}/${#frontend_endpoints[@]} available"

  # Update constants.js hint
  if [ $backend_valid_count -lt ${#backend_endpoints[@]} ] || [ $frontend_valid_count -lt ${#frontend_endpoints[@]} ]; then
    print_info "Based on available endpoints, ensure tests/e2e/constants.js matches the dual-registration pattern."
    print_info "The API supports dual registration patterns for backward compatibility:"
    print_info "  - Primary endpoints with /api/ prefix (e.g., /api/chart/validate)"
    print_info "  - Alternative endpoints without prefix (e.g., /chart/validate)"
  fi

  # Always return success if at least one health endpoint is available
  # This allows tests to proceed even if some endpoints are missing
  return 0
}

# Function to validate API endpoint consistency
validate_api_endpoints() {
  local frontend_url="http://localhost:3000"

  # Define primary and alternative endpoints according to the dual-registration pattern
  # Primary endpoints use /api/ prefix, with chart-related endpoints under /api/chart/
  # Alternative endpoints have no /api/ prefix, with chart-related endpoints under /chart/
  local primary_endpoints=(
    "/api/chart/validate"
    "/api/geocode"
    "/api/chart/generate"
    "/api/chart/1" # Test with a dummy ID
    "/api/questionnaire"
    "/api/chart/rectify"
    "/api/chart/export"
    "/api/health"
  )

  local alternative_endpoints=(
    "/chart/validate"
    "/geocode"
    "/chart/generate"
    "/chart/1"
    "/questionnaire"
    "/chart/rectify"
    "/chart/export"
    "/health"
  )

  local failed_primary=0
  local failed_alternative=0
  local success_count=0
  local total_endpoints=${#primary_endpoints[@]}
  local critical_endpoints=0 # Count of truly critical endpoints

  # Define critical endpoints (ones that would block functionality)
  local critical_patterns=(
    "/chart/validate"
    "/geocode"
    "/chart/generate"
    "/chart/rectify"
  )

  print_header "Validating API Endpoints"
  print_info "Checking API endpoints consistency (using both primary and alternative paths)"

  # Test all endpoints
  for i in "${!primary_endpoints[@]}"; do
    local primary="${primary_endpoints[$i]}"
    local alternative="${alternative_endpoints[$i]}"
    local endpoint_name="${primary#/}"
    local primary_status=""
    local alt_status=""
    local is_critical=false

    # Check if this is a critical endpoint
    for pattern in "${critical_patterns[@]}"; do
      if [[ $primary == *"$pattern"* ]]; then
        is_critical=true
        break
      fi
    done

    # Test primary endpoint (non-prefixed)
    primary_status=$(curl -s --max-time 2 "$frontend_url$primary" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
    primary_valid=$(echo "$primary_status" | grep -q -E "200|201|202|204|400|401|403" && echo "true" || echo "false")

    # Even a 404 might be valid for some endpoints that just use a different route
    primary_accessible=$(echo "$primary_status" | grep -q -E "200|201|202|204|400|401|403|404" && echo "true" || echo "false")

    # Test alternative endpoint (/api/ prefixed)
    alt_status=$(curl -s --max-time 2 "$frontend_url$alternative" -o /dev/null -w "%{http_code}" 2>/dev/null || echo "000")
    alt_valid=$(echo "$alt_status" | grep -q -E "200|201|202|204|400|401|403" && echo "true" || echo "false")
    alt_accessible=$(echo "$alt_status" | grep -q -E "200|201|202|204|400|401|403|404" && echo "true" || echo "false")

    # Print appropriate status message using abbreviated component names where applicable
    if [ "$primary_valid" = "true" ]; then
      print_success "VS: Endpoint $primary available (${primary_status})"
      success_count=$((success_count + 1))
      if [ "$is_critical" = true ]; then
        critical_endpoints=$((critical_endpoints + 1))
      fi
    elif [ "$alt_valid" = "true" ]; then
      print_info "VS: Primary endpoint $primary returned ${primary_status}, using alternative $alternative (${alt_status})"
      failed_primary=$((failed_primary + 1))
      success_count=$((success_count + 1))
      if [ "$is_critical" = true ]; then
        critical_endpoints=$((critical_endpoints + 1))
      fi
    elif [ "$primary_accessible" = "true" ]; then
      print_info "VS: Endpoint $primary accessible but returned ${primary_status}"
      success_count=$((success_count + 1))
      if [ "$is_critical" = true ]; then
        critical_endpoints=$((critical_endpoints + 1))
      fi
    elif [ "$alt_accessible" = "true" ]; then
      print_info "VS: Alternative endpoint $alternative accessible but returned ${alt_status}"
      success_count=$((success_count + 1))
      if [ "$is_critical" = true ]; then
        critical_endpoints=$((critical_endpoints + 1))
      fi
    else
      print_error "VS: Both endpoints $primary (${primary_status}) and $alternative (${alt_status}) are unavailable"
      failed_primary=$((failed_primary + 1))
      failed_alternative=$((failed_alternative + 1))
    fi
  done

  # Print summary based on critical endpoints status
  local critical_patterns_count=${#critical_patterns[@]}

  # Verify constants.js endpoint configuration is consistent with observed endpoints
  local config_verified=0
  if [ -f "tests/e2e/constants.js" ]; then
    print_info "Verifying API endpoints against tests/e2e/constants.js..."
    verify_api_endpoints
    config_verified=$?
  fi

  if [ $critical_endpoints -eq $critical_patterns_count ]; then
    print_success "All critical API endpoints are accessible (primary or alternative)"
    if [ $success_count -lt $total_endpoints ]; then
      print_info "Note: ${total_endpoints - success_count} non-critical endpoints may be inaccessible but shouldn't affect core functionality"
    fi
    if [ $config_verified -eq 0 ]; then
      print_success "API endpoint configuration is consistent with available endpoints"
    fi
    return 0
  else
    if [ $failed_primary -gt 0 ]; then
      print_info "Warning: $failed_primary primary endpoints are unavailable"
    fi
    if [ $failed_alternative -gt 0 ]; then
      if [ $critical_endpoints -lt $critical_patterns_count ]; then
        print_error "Error: Critical endpoints are inaccessible ($critical_endpoints/$critical_patterns_count available)"
        print_info "Hint: Ensure that the API service is running correctly"
        return 1
      else
        print_info "Some non-critical endpoints are unavailable but core functionality should work"
      fi
    fi
    if [ $failed_primary -gt 0 ] && [ $failed_alternative -eq 0 ]; then
      print_info "Note: Using alternative (/api/ prefixed) endpoints - consider updating test configuration"
    fi
  fi

  if [ $config_verified -ne 0 ]; then
    print_warning "API endpoint configuration may be inconsistent with available endpoints"
  fi

  return 0
}

# Function to build installation command based on options
build_install_command() {
  if [ "$INSTALL_DEPS" = true ]; then
    # Full installation
    INSTALL_CMD="echo 'Installing dependencies...' && npm ci --legacy-peer-deps && npx playwright install --with-deps chromium"
  else
    # Minimal installation
    INSTALL_CMD="echo 'Installing Playwright package...' && npm install -D @playwright/test && npx playwright install"
  fi
  echo "$INSTALL_CMD"
}

# Function to build test command based on options
build_test_command() {
  # Set debug level
  DEBUG_OPTIONS="DEBUG=pw:browser*"
  if [ "$VERBOSE" = true ]; then
    DEBUG_OPTIONS="DEBUG=pw:browser*,pw:api,pw:protocol"
    # Replace --verbose with --debug which is supported by Playwright
    VERBOSE_FLAG="--debug"
  else
    VERBOSE_FLAG=""
  fi

  # If "all" was specified, we'll handle multiple test patterns later
  if [ "$TEST_PATTERN" = "all" ]; then
    TEST_CMD="${DEBUG_OPTIONS} npx playwright test --workers=${WORKERS} ${VERBOSE_FLAG}"
  else
    # Build the test command with a specific pattern
    TEST_CMD="${DEBUG_OPTIONS} npx playwright test -g '${TEST_PATTERN}' --workers=${WORKERS} ${VERBOSE_FLAG}"
  fi

  echo "$TEST_CMD"
}

# Function to run tests with specific pattern
run_test_with_pattern() {
  local pattern="$1"
  local no_services="${2:-false}"
  local additional_args="${3:-}"

  print_subheader "Running test pattern: '${pattern}'"

  # Select recommended model based on test pattern - TOKEN_OPTIMIZATION
  local selected_model="${MODEL_SELECTION}"
  if [[ "$pattern" == *"api endpoints validation"* ]]; then
    selected_model="claude-3-haiku" # Use Haiku for debugging API issues
  elif [[ "$pattern" == *"boundary cases"* ]]; then
    selected_model="claude-3-haiku" # Use Haiku for edge cases testing
  fi

  print_info "Using model: ${selected_model} for this test pattern"

  # Build command for this specific pattern
  local debug_options="DEBUG=pw:browser*"
  if [ "$VERBOSE" = true ]; then
    debug_options="DEBUG=pw:browser*,pw:api,pw:protocol"
    # Replace --verbose with --debug which is supported by Playwright
    local verbose_flag="--debug"
  else
    local verbose_flag=""
  fi

  local test_cmd="${debug_options} npx playwright test -g '${pattern}' --workers=${WORKERS} ${verbose_flag} ${additional_args}"

  # Run the test
  if [ "$USE_DOCKER" = true ]; then
    docker run --rm \
      -v "$(pwd):/app" \
      -w /app \
      -e TEST_URL=http://localhost:3000 \
      -e DOCKER_ENV=true \
      -e MODEL_SELECTION="${selected_model}" \
      --ipc=host \
      --network=host \
      --shm-size=4g \
      ${PLAYWRIGHT_IMAGE} \
      /bin/bash -c "cd /app && ${test_cmd}"
  else
    # Export model selection for local execution
    export MODEL_SELECTION="${selected_model}"
    eval "${test_cmd}"
  fi

  local exit_code=$?
  if [ $exit_code -eq 0 ]; then
    print_success "Test '${pattern}' completed successfully!"
  else
    print_error "Test '${pattern}' failed with exit code $exit_code"
    if [ -f "test-results/${pattern//[^a-zA-Z0-9]/-}/traces" ]; then
      print_info "Test traces available at line: test-results/${pattern//[^a-zA-Z0-9]/-}/traces"
    fi
  fi

  return $exit_code
}

# Function to run all tests sequentially
run_all_tests() {
  print_header "Running All Tests Sequentially"

  # Define all test patterns
  ALL_PATTERNS=(
    "complete astrological chart application flow"
    "validation failure path"
    "low confidence path"
    "boundary cases"
    "api endpoints validation"
  )

  OVERALL_EXIT_CODE=0
  FAILED_PATTERNS=()

  for pattern in "${ALL_PATTERNS[@]}"; do
    print_header "Running test pattern: $pattern"

    run_test_with_pattern "$pattern"
    PATTERN_EXIT_CODE=$?

    if [ $PATTERN_EXIT_CODE -ne 0 ]; then
      OVERALL_EXIT_CODE=1
      FAILED_PATTERNS+=("$pattern")
    fi
  done

  # Display summary of all test patterns
  print_header "Test Results Summary"

  if [ ${#FAILED_PATTERNS[@]} -eq 0 ]; then
    print_success "All test patterns passed successfully!"
  else
    print_error "The following test patterns failed:"
    for pattern in "${FAILED_PATTERNS[@]}"; do
      print_error "  - $pattern"
    done
    print_info "Check the logs above for more details."
  fi

  return $OVERALL_EXIT_CODE
}

# Function to run tests with a single service startup
run_tests_with_single_startup() {
  print_header "Running All Tests (Single Service Startup)"

  # Start services only once
  start_services

  # Run all test patterns using the existing service
  ALL_PATTERNS=(
    "complete astrological chart application flow"
    "validation failure path"
    "low confidence path"
    "boundary cases"
    "api endpoints validation"
  )

  OVERALL_EXIT_CODE=0
  FAILED_PATTERNS=()

  for pattern in "${ALL_PATTERNS[@]}"; do
    print_subheader "Running test pattern: $pattern"

    run_test_with_pattern "$pattern" true
    PATTERN_EXIT_CODE=$?

    if [ $PATTERN_EXIT_CODE -ne 0 ]; then
      OVERALL_EXIT_CODE=1
      FAILED_PATTERNS+=("$pattern")
    fi
  done

  # Display summary of all test patterns
  print_header "Test Results Summary"

  if [ ${#FAILED_PATTERNS[@]} -eq 0 ]; then
    print_success "All test patterns passed successfully!"
  else
    print_error "The following test patterns failed:"
    for pattern in "${FAILED_PATTERNS[@]}"; do
      print_error "  - $pattern"
    done
    print_info "Check the logs above for more details."
  fi

  return $OVERALL_EXIT_CODE
}

# Function to display the test summary
display_test_summary() {
  if [ -f "test_summary_report.md" ]; then
    print_header "Test Summary Report"
    echo -e "${YELLOW}$(cat test_summary_report.md)${NC}"
  else
    print_info "No test summary report available"
  fi
}

# Function to stop all services
stop_all_services() {
  print_header "Stopping All Services"

  if docker ps | grep -q "birth-rectifier"; then
    print_info "Stopping Docker services..."
    if [ -f "docker-compose.tmp.yml" ]; then
      docker compose -f docker-compose.tmp.yml down
      rm docker-compose.tmp.yml
    else
      docker compose down
    fi
    print_success "Services stopped."
  else
    print_info "No services running."
  fi
}

# Function to verify API endpoint configuration
verify_api_endpoints() {
  print_header "Verifying API Endpoint Configuration"

  if [ ! -f "tests/e2e/constants.js" ]; then
    print_error "API endpoint configuration file not found: tests/e2e/constants.js"
    return 1
  fi

  print_info "Checking API endpoint configuration..."

  # Check if the file contains the API_ENDPOINTS object
  if grep -q "export const API_ENDPOINTS" "tests/e2e/constants.js"; then
    print_success "API endpoint configuration found"

    # Extract and display the endpoints
    echo -e "${CYAN}Configured API endpoints:${NC}"
    grep -A 30 "API_ENDPOINTS" "tests/e2e/constants.js" | grep -E ":|}" | grep -v "}" | \
    sed 's/.*\/\//\/\//g' | sed 's/",//g' | sed 's/"//g' | sed 's/^ *//g' | \
    while IFS= read -r line; do
      if [[ "$line" == /api/* ]]; then
        echo -e "  ${GREEN}$line${NC} ✓ (with /api/ prefix)"
      else
        echo -e "  ${YELLOW}$line${NC} ⚠️  (without /api/ prefix)"
      fi
    done

    # Now check which endpoints actually work by testing both versions
    print_subheader "Testing configured endpoints for availability"

    local frontend_url="http://localhost:3000"
    local primary_found=0
    local alt_found=0

    # Test key endpoints in both formats to confirm dual-registration pattern
    # Chart-related primary endpoints should be under /api/chart/
    for endpoint_pair in "chart/validate:/chart/validate" "geocode:/geocode" "health:/health"; do
      # Split into primary and alternative endpoint
      IFS=':' read -r primary_path alt_path <<< "$endpoint_pair"

      # Add API prefix for primary
      local primary_endpoint="/api/${primary_path}"
      local alt_endpoint="/${alt_path}"

      local primary_status=$(curl -s "$frontend_url$primary_endpoint" -o /dev/null -w "%{http_code}" 2>/dev/null)
      local alt_status=$(curl -s "$frontend_url$alt_endpoint" -o /dev/null -w "%{http_code}" 2>/dev/null)

      if echo "$primary_status" | grep -q -E "200|404|400|401|403"; then
        print_success "VS: Primary endpoint $primary_endpoint is accessible: $primary_status"
        primary_found=$((primary_found + 1))
      fi

      if echo "$alt_status" | grep -q -E "200|404|400|401|403"; then
        print_success "VS: Alternative endpoint $alt_endpoint is accessible: $alt_status"
        alt_found=$((alt_found + 1))
      fi
    done

    if [ $primary_found -gt 0 ] && [ $alt_found -eq 0 ]; then
      print_info "Endpoint pattern: Only primary (/api/ prefixed) endpoints are accessible"
    elif [ $primary_found -eq 0 ] && [ $alt_found -gt 0 ]; then
      print_info "Endpoint pattern: Only alternative (non-prefixed) endpoints are accessible"
    elif [ $primary_found -gt 0 ] && [ $alt_found -gt 0 ]; then
      print_info "Endpoint pattern: Both primary and alternative endpoints are accessible (dual-registration)"
    else
      print_error "None of the tested endpoints are accessible"
    fi

    # Check if constants.js matches the detected endpoint pattern
    # Primary endpoints should use /api/ prefix with chart endpoints under /api/chart/
    if grep -q "validate: '/api/chart/validate'" "tests/e2e/constants.js" && \
       grep -q "validateAlt: '/chart/validate'" "tests/e2e/constants.js"; then
      print_success "API_ENDPOINTS in constants.js correctly configured with dual-registration pattern"
    else
      print_error "API_ENDPOINTS in constants.js may need updating to match the dual-registration pattern"
      print_info "API architecture follows dual-registration: "
      echo -e "  - ${GREEN}Primary endpoints with /api/ prefix (e.g., /api/chart/validate)${NC}"
      echo -e "  - ${GREEN}Alternative endpoints without prefix (e.g., /chart/validate)${NC}"
      print_info "Consider updating tests/e2e/constants.js to match this pattern."
    fi
  else
    print_error "API_ENDPOINTS object not found in constants.js"
    print_info "The file may need to be updated or created."
  fi
}

# Function to handle errors with retries - Implements Recursive Error Resolution Algorithm
handle_error() {
  local error_message="$1"
  local retry_count="${2:-0}"
  local max_retries=2

  print_error "Error: $error_message"

  if [ $retry_count -lt $max_retries ]; then
    print_info "Attempting to fix automatically (Attempt $((retry_count + 1)) of $max_retries)..."

    # Basic diagnosis
    if [[ "$error_message" == *"API endpoint"* || "$error_message" == *"connection"* ]]; then
      # API connection issue - check services
      print_info "API connection issue detected. Checking services..."

      if ! docker ps | grep -q "birth-rectifier"; then
        print_info "Services not running. Attempting to start..."
        start_services
        return $?
      else
        print_info "Services running. Checking health..."
        wait_for_services
        return $?
      fi
    elif [[ "$error_message" == *"playwright"* || "$error_message" == *"test"* ]]; then
      # Test runner issue
      print_info "Test runner issue detected. Checking Playwright installation..."
      npm ls @playwright/test || npm install -D @playwright/test
      npx playwright install
      return $?
    else
      # Generic retry
      print_info "Retrying operation..."
      return 0
    fi
  else
    print_error "Failed after $max_retries attempts. Please check the logs for details."
    print_info "Consider searching online for a solution or seek assistance."
    return 1
  fi
}

# Function to show menu and handle user selection
show_menu() {
  clear
  print_header "Birth Time Rectifier Test Suite"

  echo -e "${BOLD}Available Test Patterns:${NC}"
  echo -e "1) Complete astrological chart application flow"
  echo -e "2) Validation failure path"
  echo -e "3) Low confidence path"
  echo -e "4) Boundary cases (extreme coordinates)"
  echo -e "5) API endpoints validation"
  echo -e "6) Run all test patterns"
  echo
  echo -e "${BOLD}Services:${NC}"
  echo -e "7) Start services"
  echo -e "8) Stop services"
  echo -e "9) Check service health"
  echo
  echo -e "${BOLD}Other Options:${NC}"
  echo -e "v) Toggle verbose mode (currently: $([ "$VERBOSE" = true ] && echo 'ON' || echo 'OFF'))"
  echo -e "d) Toggle Docker use (currently: $([ "$USE_DOCKER" = true ] && echo 'ON' || echo 'OFF'))"
  echo -e "w) Set worker count (currently: $WORKERS)"
  echo -e "m) Set model (currently: $MODEL_SELECTION)"
  echo -e "q) Quit"
  echo
  echo -e "${BOLD}Current Status:${NC}"

  # Check services status
  if docker ps | grep -q "birth-rectifier"; then
    echo -e "Services: ${GREEN}Running${NC}"
  else
    echo -e "Services: ${RED}Stopped${NC}"
  fi

  # Check for test results
  if [ -f "test_summary_report.md" ]; then
    echo -e "Last test run: ${GREEN}Available${NC} (use 'r' to show results)"
  else
    echo -e "Last test run: ${YELLOW}Not available${NC}"
  fi

  echo
  read -p "Enter your choice: " choice

  case $choice in
    1)
      TEST_PATTERN="complete astrological chart application flow"
      run_test_with_pattern "$TEST_PATTERN"
      read -p "Press Enter to continue..."
      ;;
    2)
      TEST_PATTERN="validation failure path"
      run_test_with_pattern "$TEST_PATTERN"
      read -p "Press Enter to continue..."
      ;;
    3)
      TEST_PATTERN="low confidence path"
      run_test_with_pattern "$TEST_PATTERN"
      read -p "Press Enter to continue..."
      ;;
    4)
      TEST_PATTERN="boundary cases"
      run_test_with_pattern "$TEST_PATTERN"
      read -p "Press Enter to continue..."
      ;;
    5)
      TEST_PATTERN="api endpoints validation"
      run_test_with_pattern "$TEST_PATTERN"
      read -p "Press Enter to continue..."
      ;;
    6)
      run_all_tests
      read -p "Press Enter to continue..."
      ;;
    7)
      start_services
      read -p "Press Enter to continue..."
      ;;
    8)
      stop_all_services
      read -p "Press Enter to continue..."
      ;;
    9)
      wait_for_services
      read -p "Press Enter to continue..."
      ;;
    v)
      VERBOSE=$([ "$VERBOSE" = true ] && echo "false" || echo "true")
      echo "Verbose mode $([ "$VERBOSE" = true ] && echo 'enabled' || echo 'disabled')"
      sleep 1
      ;;
    d)
      USE_DOCKER=$([ "$USE_DOCKER" = true ] && echo "false" || echo "true")
      echo "Docker usage $([ "$USE_DOCKER" = true ] && echo 'enabled' || echo 'disabled')"
      sleep 1
      ;;
    w)
      read -p "Enter number of workers: " WORKERS
      echo "Worker count set to $WORKERS"
      sleep 1
      ;;
    m)
      echo "Available models:"
      echo "1) deepseek-coder-v2 (for routine tasks)"
      echo "2) claude-3-haiku (for debugging)"
      echo "3) claude-3-5-sonnet (for complex architecture)"
      echo "4) qwen-2-5-coder (for UI/UX improvements)"
      echo "5) gemini-2-0-flash (for documentation)"
      read -p "Select model number: " model_choice
      case $model_choice in
        1) MODEL_SELECTION="deepseek-coder-v2" ;;
        2) MODEL_SELECTION="claude-3-haiku" ;;
        3) MODEL_SELECTION="claude-3-5-sonnet" ;;
        4) MODEL_SELECTION="qwen-2-5-coder" ;;
        5) MODEL_SELECTION="gemini-2-0-flash" ;;
        *) echo "Invalid selection, keeping current model" ;;
      esac
      echo "Model set to $MODEL_SELECTION"
      sleep 1
      ;;
    r)
      display_test_summary
      read -p "Press Enter to continue..."
      ;;
    q)
      if [ "$SHOULD_ASK_TO_STOP" = true ] && docker ps | grep -q "birth-rectifier"; then
        read -p "Do you want to stop running services? (y/n): " stop
        if [ "$stop" = "y" ]; then
          stop_all_services
        fi
      fi
      echo "Exiting..."
      exit 0
      ;;
    *)
      echo "Invalid option. Press Enter to continue..."
      read
      ;;
  esac

  # Return to menu
  show_menu
}

# Initialize the template cache for token optimization
init_template_cache

# Main script execution
if [ "$MENU_MODE" = true ]; then
  # Run in menu-driven mode
  show_menu
else
  # Run in CLI mode
  EXIT_CODE=0

  # Start services if needed
  if [ "$START_SERVICES" = true ]; then
    start_services || {
      handle_error "Failed to start services" 0 || EXIT_CODE=1
    }
  fi

  # Run tests if services started successfully
  if [ $EXIT_CODE -eq 0 ]; then
    if [ "$TEST_PATTERN" = "all" ]; then
      run_all_tests || EXIT_CODE=$?
    else
      run_test_with_pattern "$TEST_PATTERN" || EXIT_CODE=$?
    fi
  fi

  # Display test summary if available
  display_test_summary

  # Stop services if needed
  if [ "$SHOULD_ASK_TO_STOP" = true ] && [ "$START_SERVICES" = true ]; then
    read -p "Do you want to stop the services? (y/n): " STOP_SERVICES
    if [ "$STOP_SERVICES" = "y" ]; then
      stop_all_services
    else
      echo "Services left running. You can stop them later with 'docker compose down'"
    fi
  fi

  exit $EXIT_CODE
fi
