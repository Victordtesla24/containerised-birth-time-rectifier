#!/bin/bash
set -e

echo "======================================================================"
echo "       Rebuilding Birth Time Rectifier Application Containers         "
echo "======================================================================"

# Define colors for output
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
NC="\033[0m" # No Color

# Wrapper function for the timeout command with fallback
run_with_timeout() {
  local cmd="$1"
  local timeout="$2"
  local output_file="$3"

  # Check if timeout command is available
  if command -v timeout &> /dev/null; then
    # Use timeout command
    timeout $timeout bash -c "$cmd" > "$output_file" 2>&1
    return $?
  elif command -v perl &> /dev/null; then
    # Use perl as fallback
    perl -e 'alarm shift @ARGV; exec @ARGV' "$timeout" bash -c "$cmd" > "$output_file" 2>&1
    local exit_code=$?
    if [ $exit_code -eq 255 ]; then
      # Timeout occurred
      return 124  # Standard timeout exit code
    fi
    return $exit_code
  else
    # No timeout available, run without timeout
    log_warning "No timeout command available. Running command without timeout."
    bash -c "$cmd" > "$output_file" 2>&1
    return $?
  fi
}

# Function to log messages
log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

# Spinner function for background tasks
spinner() {
  local pid=$1
  local delay=0.1
  local spinstr='|/-\'
  local start_time=$(date +%s)
  local elapsed=0
  local timeout=${3:-300}  # Default timeout of 5 minutes

  echo -n " "
  while kill -0 $pid 2>/dev/null; do
    local temp=${spinstr#?}
    printf "\r ${CYAN}[%c]${NC} %s (elapsed: %ds)" "$spinstr" "$2" "$elapsed"
    local spinstr=$temp${spinstr%"$temp"}
    sleep $delay
    elapsed=$(( $(date +%s) - start_time ))

    # Add timeout functionality
    if [ $timeout -gt 0 ] && [ $elapsed -ge $timeout ]; then
      printf "\r ${YELLOW}[!]${NC} %s timed out after %ds. Killing process...         \n" "$2" "$timeout"
      kill -9 $pid 2>/dev/null || true
      return 1
    fi
  done

  wait $pid
  local result=$?

  if [ $result -eq 0 ]; then
    printf "\r ${GREEN}[✓]${NC} %s (completed in %ds)                          \n" "$2" "$elapsed"
    return 0
  else
    printf "\r ${RED}[✗]${NC} %s failed with exit code %d (after %ds)          \n" "$2" "$result" "$elapsed"
    return $result
  fi
}

# Progress bar function for long operations
progress_bar() {
  local pid=$1
  local message=$2
  local width=50
  local refresh_rate=1
  local start_time=$(date +%s)
  local elapsed=0
  local timeout=${3:-1800}  # Default timeout of 30 minutes for longer build processes

  while kill -0 $pid 2>/dev/null; do
    # Calculate elapsed time
    elapsed=$(( $(date +%s) - start_time ))

    # Generate a random percent for visual progress (since we can't measure real progress)
    # This will increase gradually to 95% max (to avoid showing 100% until truly complete)
    local percent=$(( elapsed < 120 ? (elapsed * 95 / 120) : 95 ))

    # Number of filled positions in the bar
    local filled=$(( width * percent / 100 ))
    local unfilled=$(( width - filled ))

    # Build the progress bar
    local bar="["
    for (( i=0; i<filled; i++ )); do bar+="="; done
    if [ $filled -lt $width ]; then bar+=">"; fi
    for (( i=0; i<unfilled-1; i++ )); do bar+=" "; done
    bar+="]"

    # Display the progress bar
    printf "\r ${CYAN}%s${NC} %3d%% %s (elapsed: %ds)" "$message" "$percent" "$bar" "$elapsed"

    # Add timeout functionality
    if [ $timeout -gt 0 ] && [ $elapsed -ge $timeout ]; then
      printf "\r ${YELLOW}[!]${NC} %s timed out after %ds. Killing process...         \n" "$message" "$timeout"
      kill -9 $pid 2>/dev/null || true
      return 1
    fi

    sleep $refresh_rate
  done

  wait $pid
  local result=$?

  if [ $result -eq 0 ]; then
    # Show 100% when done
    printf "\r ${GREEN}%s${NC} 100%% [" "$message"
    for (( i=0; i<width; i++ )); do printf "="; done
    printf "] (completed in %ds) \n" "$elapsed"
    return 0
  else
    printf "\r ${RED}%s FAILED${NC} (exit code: %d, elapsed: %ds) \n" "$message" "$result" "$elapsed"
    return $result
  fi
}

# Display countdown timer
countdown() {
  local seconds=$1
  local message=$2

  for (( i=seconds; i>0; i-- )); do
    printf "\r ${BLUE}[WAIT]${NC} %s: %2ds remaining..." "$message" "$i"
    sleep 1
  done
  printf "\r ${GREEN}[DONE]${NC} %s completed                        \n" "$message"
}

# Function to check if requirements verification passes
verify_requirements() {
  log_info "Verifying requirements and dependencies..."

  # Set a timeout (in seconds) for the verification process
  local TIMEOUT=30
  local start_time=$(date +%s)
  local spinstr='|/-\'
  local tmpfile=$(mktemp)

  # Run verification script with timeout
  run_with_timeout "./scripts/setup/verify_fixes.sh" $TIMEOUT "$tmpfile" &
  local pid=$!

  # More reliable process checking with timeout
  while kill -0 $pid 2>/dev/null; do
    local elapsed=$(( $(date +%s) - start_time ))
    local spinchar=${spinstr:$(( elapsed % ${#spinstr} )):1}
    printf "\r ${CYAN}[%c]${NC} %s (elapsed: %ds)" "$spinchar" "Verifying dependencies" "$elapsed"

    # Check if we've exceeded our timeout
    if [ $elapsed -ge $(($TIMEOUT + 5)) ]; then
      kill -9 $pid 2>/dev/null || true
      printf "\r ${YELLOW}[!]${NC} Verification timed out after %ds. Continuing anyway.               \n" "$elapsed"
      rm -f "$tmpfile"
      return 0
    fi

    sleep 0.1
  done

  # Check if verification was successful
  wait $pid
  local result=$?

  if [ $result -eq 0 ]; then
    printf "\r ${GREEN}[✓]${NC} Verification completed successfully.                              \n"
    rm -f "$tmpfile"
    return 0
  elif [ $result -eq 124 ] || [ $result -eq 137 ]; then
    # 124 is timeout's exit code, 137 is for SIGKILL (128+9)
    printf "\r ${YELLOW}[!]${NC} Verification timed out. Continuing anyway.                       \n"
    rm -f "$tmpfile"
    return 0
  else
    printf "\r ${RED}[✗]${NC} Verification failed. Running again with output.                   \n"
    cat "$tmpfile"
    rm -f "$tmpfile"

    # Run again directly for user to see output
    ./scripts/setup/verify_fixes.sh

    # Ask the user if they want to continue anyway
    echo -n -e "\n${YELLOW}[CONFIRM]${NC} Continue despite verification failures? (y/n): "
    read -r answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
      log_warning "Continuing despite verification failures"
      return 0
    else
      log_error "Aborted due to verification failures"
      return 1
    fi
  fi
}

# Check if Docker is running
check_docker() {
  log_info "Checking Docker status..."

  (docker info > /dev/null 2>&1) &
  local pid=$!
  spinner $pid "Checking Docker daemon"
  wait $pid

  if [ $? -ne 0 ]; then
    log_error "Docker is not running or not accessible. Please start Docker."
    return 1
  else
    log_success "Docker is running"
    return 0
  fi
}

# Stop existing containers
stop_containers() {
  log_info "Stopping any existing containers..."

  (docker-compose down 2>/dev/null) &
  local pid=$!
  spinner $pid "Stopping containers"
  wait $pid || true

  # Check if there are any remaining containers
  if [ $(docker ps -a --filter "name=birth-rectifier" -q | wc -l) -gt 0 ]; then
    log_success "Existing containers stopped successfully"
  else
    log_warning "No running containers or error stopping containers"
  fi
}

# Validate docker-compose configuration
validate_compose() {
  log_info "Validating docker-compose configuration..."

  (docker-compose config > /dev/null 2>&1) &
  local pid=$!
  spinner $pid "Validating docker-compose.yml"
  wait $pid

  if [ $? -eq 0 ]; then
    log_success "Docker Compose configuration is valid"
    return 0
  else
    log_error "Docker Compose configuration is invalid:"
    docker-compose config
    return 1
  fi
}

# Ensure dependencies are properly set
ensure_dependencies() {
  log_info "Ensuring all dependencies are properly set..."

  # Check for pydantic version in requirements.txt
  if grep -q "pydantic==1.10.12" requirements.txt; then
    log_success "Pydantic version is set correctly in requirements.txt"
  else
    log_error "Pydantic version is not set correctly in requirements.txt"
    return 1
  fi

  # Check for React versions in frontend.Dockerfile
  if grep -q "react@18.2.0" frontend.Dockerfile && grep -q "react-dom@18.2.0" frontend.Dockerfile; then
    log_success "React versions are set correctly in frontend.Dockerfile"
  else
    log_error "React versions are not set correctly in frontend.Dockerfile"
    return 1
  fi

  # Check for SwissEph import in chart_calculator.py
  if grep -q "import pyswisseph as swe" "ai_service/core/rectification/chart_calculator.py"; then
    log_success "SwissEph import is set correctly in chart_calculator.py"
  else
    log_error "SwissEph import is not set correctly in chart_calculator.py"
    return 1
  fi

  # Ensure all required environment variables are set in docker-compose.yml
  required_env_vars=("SWISSEPH_PATH" "JWT_SECRET" "JWT_ALGORITHM")
  for var in "${required_env_vars[@]}"; do
    if grep -q "$var" docker-compose.yml; then
      log_success "$var is set in docker-compose.yml"
    else
      log_error "$var is not set in docker-compose.yml"
      return 1
    fi
  done

  return 0
}

# Build containers with updated configurations
rebuild_containers() {
  log_info "Rebuilding containers with no cache..."

  echo -e "\n${BLUE}[BUILDING]${NC} Building services in the following order:"
  echo -e " - redis (database cache)"
  echo -e " - postgres (database)"
  echo -e " - ai_service (core engine)"
  echo -e " - api_gateway (API)"
  echo -e " - frontend (web interface)"
  echo -e "\nThis process may take several minutes. Please be patient.\n"

  (docker-compose build --no-cache) &
  local pid=$!
  progress_bar $pid "Building containers"
  wait $pid

  if [ $? -eq 0 ]; then
    log_success "Containers rebuilt successfully!"
    return 0
  else
    log_error "Failed to rebuild containers"
    return 1
  fi
}

# Start containers and verify services
start_and_verify() {
  log_info "Starting containers..."

  (docker-compose up -d) &
  local pid=$!
  spinner $pid "Starting all services"
  wait $pid

  if [ $? -eq 0 ]; then
    log_success "Containers started successfully"

    log_info "Waiting for services to initialize..."

    # Start countdown for initialization
    countdown 30 "Waiting for services to initialize"

    # Check if each service is healthy
    services=("redis" "postgres" "ai_service" "api_gateway" "frontend")
    all_healthy=true

    echo -e "\n${BLUE}[VERIFYING]${NC} Checking service health status:"

    for service in "${services[@]}"; do
      echo -n -e " - ${service}: "

      # Try several times with a short delay
      for i in {1..5}; do
        if docker-compose ps | grep -q "$service.*healthy"; then
          echo -e "${GREEN}healthy${NC}"
          break
        elif [ $i -eq 5 ]; then
          echo -e "${RED}not healthy${NC}"
          all_healthy=false
        else
          echo -n "."
          sleep 2
        fi
      done
    done

    if [ "$all_healthy" = true ]; then
      log_success "All services are healthy and running"
      return 0
    else
      log_error "Not all services are healthy. Check logs with 'docker-compose logs'"
      return 1
    fi
  else
    log_error "Failed to start containers"
    return 1
  fi
}

# Check logs for common errors
check_logs() {
  log_info "Checking for common errors in logs..."

  (docker-compose logs > /tmp/docker_logs.txt 2>&1) &
  local pid=$!
  spinner $pid "Collecting logs for analysis"
  wait $pid

  echo -e "\n${BLUE}[SCANNING]${NC} Analyzing logs for common issues:"

  # Check for pydantic/dependency errors
  if grep -q "pydantic.*cannot install" /tmp/docker_logs.txt; then
    log_error "Found pydantic dependency errors in logs"
    return 1
  else
    echo -e " - ${GREEN}No pydantic dependency errors${NC}"
  fi

  # Check for SwissEph errors
  if grep -q "Error.*Swiss Ephemeris" /tmp/docker_logs.txt; then
    log_error "Found Swiss Ephemeris errors in logs"
    return 1
  else
    echo -e " - ${GREEN}No Swiss Ephemeris errors${NC}"
  fi

  # Check for React/Next.js errors
  if grep -q "Error: Cannot find module 'react'" /tmp/docker_logs.txt; then
    log_error "Found React module errors in logs"
    return 1
  else
    echo -e " - ${GREEN}No React module errors${NC}"
  fi

  # Clean up
  rm -f /tmp/docker_logs.txt

  log_success "No common errors found in logs"
  return 0
}

# Get status of all containers with pretty formatting
get_status() {
  log_info "Current container status:"

  echo -e "\n${CYAN}========= Container Status ==========${NC}"
  docker-compose ps --format "table {{.Name}}\t{{.Command}}\t{{.State}}\t{{.Health}}\t{{.Ports}}"
  echo -e "${CYAN}===================================${NC}\n"
}

# Main execution flow
main() {
  log_info "Starting rebuild process..."

  # First check if Docker is running
  if ! check_docker; then
    exit 1
  fi

  # Verify requirements
  if ! verify_requirements; then
    log_error "Please fix the requirements issues before proceeding"
    exit 1
  fi

  # Ensure dependencies are properly set
  if ! ensure_dependencies; then
    log_error "Please fix the dependency issues before proceeding"
    exit 1
  fi

  # Validate docker-compose configuration
  if ! validate_compose; then
    log_error "Please fix the docker-compose configuration before proceeding"
    exit 1
  fi

  # Stop existing containers
  stop_containers

  # Rebuild containers
  if ! rebuild_containers; then
    log_error "Container rebuild failed"
    exit 1
  fi

  # Start containers and verify services
  if ! start_and_verify; then
    log_error "Service verification failed"
    exit 1
  fi

  # Check logs for common errors
  if ! check_logs; then
    log_warning "Found potential issues in logs, but continuing"
  fi

  # Display final status
  get_status

  log_success "Application rebuild completed successfully!"
  echo
  echo "======================================================================"
  echo "  The Birth Time Rectifier application is now running successfully:   "
  echo "  - Frontend:   http://localhost:3000                                 "
  echo "  - API:        http://localhost:9000                                 "
  echo "  - WebSocket:  ws://localhost:9001/ws                                "
  echo "======================================================================"
}

# Run the main function
main
