#!/bin/bash

# ============================================
# Birth Time Rectifier - Unified Start Script
# ============================================
# - Starts Redis, AI service, and Frontend
# - Includes Docker container support and auto-recovery
# - Manages port conflicts and ensures services are running

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service ports
REDIS_PORT=6379
AI_SERVICE_PORT=8000
FRONTEND_PORT=3000

# Project root directory (where this script is located)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOGS_DIR="$PROJECT_ROOT/logs"

# Create logs directory if it doesn't exist
mkdir -p "$LOGS_DIR"

# Configuration
USE_DOCKER=${USE_DOCKER:-false}
LOG_LEVEL=${LOG_LEVEL:-"INFO"}
AUTO_RESTART=${AUTO_RESTART:-true}
MAX_RETRIES=3

# Function to print status messages
print_status() {
  local emoji="$1"
  local message="$2"
  local color="$3"
  echo -e "${color}${emoji} ${message}${NC}"
}

# Function to print informational messages
print_info() {
  print_status "ℹ" "$1" "${BLUE}"
}

# Function to print success messages
print_success() {
  print_status "✓" "$1" "${GREEN}"
}

# Function to print warning messages
print_warning() {
  print_status "⚠" "$1" "${YELLOW}"
}

# Function to print error messages
print_error() {
  print_status "✗" "$1" "${RED}"
}

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to check if a port is in use
is_port_in_use() {
  local port="$1"
  if command_exists lsof; then
    lsof -i:"$port" >/dev/null 2>&1
    return $?
  else
    # Fallback to netstat if lsof is not available
    netstat -an | grep "LISTEN" | grep ":$port " >/dev/null 2>&1
    return $?
  fi
}

# Function to kill a process using a specific port
kill_process_on_port() {
  local port="$1"
  local force="$2"

  if is_port_in_use "$port"; then
    print_warning "Port $port is already in use. Attempting to free it..."

    if command_exists lsof; then
      local pid=$(lsof -t -i:"$port")
      if [ -n "$pid" ]; then
        if [ "$force" = "true" ]; then
          print_info "Force killing process $pid using port $port..."
          kill -9 "$pid" 2>/dev/null
        else
          print_info "Gracefully stopping process $pid using port $port..."
          kill "$pid" 2>/dev/null
        fi
        sleep 1
      fi
    else
      print_warning "lsof not found, unable to identify and kill process on port $port"
    fi
  fi
}

# Function to check Python dependencies
check_python_dependencies() {
  print_info "Checking Python dependencies..."

  # Check for Python 3
  if ! command_exists python3; then
    print_error "Python 3 is not installed. Please install it and try again."
    return 1
  fi

  # Check if virtual environment exists and activate it
  if [ -d ".venv" ]; then
    if [ -f ".venv/bin/activate" ]; then
      source .venv/bin/activate
      print_success "Virtual environment activated"
    else
      print_error "Virtual environment found but activation script is missing"
      return 1
    fi
  else
    print_warning "No virtual environment found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    print_success "Virtual environment created and activated"
  fi

  # Check for required packages
  if ! python3 -c "import pyswisseph" 2>/dev/null; then
    print_warning "Swiss Ephemeris (pyswisseph) not found. Installing..."
    pip install pyswisseph
  else
    print_success "Swiss Ephemeris (pyswisseph) is available"
  fi

  # Check other dependencies
  if [ -f "requirements.txt" ]; then
    print_info "Installing required Python packages..."
    # First attempt normal installation
    if pip install -r requirements.txt 2> "$LOGS_DIR/pip_errors.log"; then
      print_success "Successfully installed all required packages"
    else
      # Check for the flatlib & pyswisseph conflict specifically
      if grep -q "Cannot install.*flatlib.*pyswisseph" "$LOGS_DIR/pip_errors.log"; then
        print_warning "Detected conflict between flatlib and pyswisseph"
        print_info "Attempting to fix package conflicts..."

        # Try a more targeted installation approach
        # First install the older pyswisseph that flatlib needs
        if pip install "pyswisseph==2.08.00-1"; then
          print_success "Installed compatible pyswisseph version"

          # Then install everything except pyswisseph
          grep -v "pyswisseph" requirements.txt > "$LOGS_DIR/requirements_fixed.txt"
          if pip install -r "$LOGS_DIR/requirements_fixed.txt"; then
            print_success "Successfully installed packages with conflict resolution"
          else
            print_error "Failed to install packages even after resolving conflicts"
            cat "$LOGS_DIR/pip_errors.log"
            return 1
          fi
        else
          print_error "Could not install compatible pyswisseph version"
          cat "$LOGS_DIR/pip_errors.log"
          return 1
        fi
      else
        print_error "Failed to install required packages"
        cat "$LOGS_DIR/pip_errors.log"
        return 1
      fi
    fi
  fi

  return 0
}

# Function to start Redis
start_redis() {
  print_info "Starting Redis on port $REDIS_PORT..."

  # Kill any existing Redis process
  kill_process_on_port "$REDIS_PORT" "true"

  if [ "$USE_DOCKER" = "true" ]; then
    # Check if Docker is installed
    if ! command_exists docker; then
      print_error "Docker is not installed. Please install Docker and try again."
      return 1
    fi

    # Run Redis in Docker container
    docker rm -f birth-time-redis >/dev/null 2>&1
    docker run --name birth-time-redis -p $REDIS_PORT:6379 -d redis:alpine >/dev/null 2>&1

    if [ $? -eq 0 ]; then
      print_success "Redis started successfully in Docker container"
    else
      print_error "Failed to start Redis in Docker container"
      return 1
    fi
  else
    # Check if Redis server is installed
    if ! command_exists redis-server; then
      print_error "Redis server is not installed. Please install Redis or set USE_DOCKER=true."
      return 1
    fi

    # Start Redis server
    redis-server --port $REDIS_PORT --daemonize yes

    if [ $? -eq 0 ]; then
      print_success "Redis started successfully on port $REDIS_PORT"
    else
      print_error "Failed to start Redis server"
      return 1
    fi
  fi

  # Verify Redis is running
  sleep 1
  if command_exists redis-cli; then
    if redis-cli -p $REDIS_PORT PING | grep -q "PONG"; then
      print_success "Redis is responding to PING"
    else
      print_error "Redis is not responding to PING"
      return 1
    fi
  fi

  return 0
}

# Function to start AI service
start_ai_service() {
  print_info "Starting AI service on port $AI_SERVICE_PORT..."

  # Kill any existing service on the AI service port
  kill_process_on_port "$AI_SERVICE_PORT" "true"

  # Set environment variables
  export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
  export LOG_LEVEL="$LOG_LEVEL"
  export REDIS_URL="redis://localhost:$REDIS_PORT"

  # Build command to start AI service
  local ai_cmd="uvicorn ai_service.api.main:app --host 0.0.0.0 --port $AI_SERVICE_PORT"

  print_info "Running AI service with: $ai_cmd"

  # Start the AI service
  cd "$PROJECT_ROOT" && $ai_cmd >>"$LOGS_DIR/ai_service.log" 2>&1 &
  local AI_PID=$!

  # Check if the process started
  if kill -0 $AI_PID >/dev/null 2>&1; then
    print_success "AI service started successfully on port $AI_SERVICE_PORT (PID: $AI_PID)"
    echo $AI_PID > "$LOGS_DIR/ai_service.pid"

    # Wait for the service to start responding
    print_info "Waiting for AI service to initialize..."
    local max_wait=30
    local wait_count=0
    local is_ready=false

    while [ $wait_count -lt $max_wait ]; do
      if curl -s "http://localhost:$AI_SERVICE_PORT/health" >/dev/null 2>&1; then
        is_ready=true
        break
      fi
      sleep 1
      wait_count=$((wait_count + 1))
    done

    if [ "$is_ready" = "true" ]; then
      print_success "AI service is responding to HTTP requests"
    else
      print_warning "AI service started but not responding after $max_wait seconds"
    fi
  else
    print_error "Failed to start AI service"
    return 1
  fi

  return 0
}

# Function to start Frontend
start_frontend() {
  print_info "Starting Frontend on port $FRONTEND_PORT..."

  # Kill any existing service on the frontend port
  kill_process_on_port "$FRONTEND_PORT" "true"

  # Set environment variables
  export NEXT_PUBLIC_API_URL="http://localhost:$AI_SERVICE_PORT"

  # Build command to start frontend
  local frontend_cmd="npm run dev"

  print_info "Running Frontend with: $frontend_cmd"

  # Start the frontend
  cd "$PROJECT_ROOT" && $frontend_cmd >>"$LOGS_DIR/frontend.log" 2>&1 &
  local FRONTEND_PID=$!

  # Check if the process started
  if kill -0 $FRONTEND_PID >/dev/null 2>&1; then
    print_success "Frontend started successfully on port $FRONTEND_PORT (PID: $FRONTEND_PID)"
    echo $FRONTEND_PID > "$LOGS_DIR/frontend.pid"
  else
    print_error "Failed to start Frontend"
    return 1
  fi

  return 0
}

# Function to verify all services are running
check_service_status() {
  local all_running=true

  print_info "Checking service status..."

  # Check Redis
  if command_exists redis-cli && redis-cli -p $REDIS_PORT PING | grep -q "PONG"; then
    print_success "Redis is running on port $REDIS_PORT"
  else
    print_error "Redis is not running on port $REDIS_PORT"
    all_running=false
  fi

  # Check AI Service
  if curl -s "http://localhost:$AI_SERVICE_PORT/health" >/dev/null 2>&1; then
    print_success "AI Service is running on port $AI_SERVICE_PORT"
  else
    print_error "AI Service is not running on port $AI_SERVICE_PORT"
    all_running=false
  fi

  # Check Frontend
  if curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 || curl -s -I "http://localhost:$FRONTEND_PORT" 2>&1 | grep -q "HTTP/"; then
    print_success "Frontend is running on port $FRONTEND_PORT"
  else
    # Additional check with a longer timeout as Next.js dev server can be slow to respond sometimes
    if timeout 5 curl -s "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1; then
      print_success "Frontend is running on port $FRONTEND_PORT (delayed response)"
    else
      # Check process is still alive
      if [ -f "$LOGS_DIR/frontend.pid" ] && kill -0 "$(cat "$LOGS_DIR/frontend.pid")" >/dev/null 2>&1; then
        print_warning "Frontend process is running but not responding to HTTP requests yet. It may still be initializing."
        print_info "Check logs at $LOGS_DIR/frontend.log for any errors."
        # Mark as running since process is alive
        frontend_running=true
      else
        print_error "Frontend is not running on port $FRONTEND_PORT"
        all_running=false
      fi
    fi
  fi

  # Print summary
  echo
  print_info "Service Status Summary:"
  if [ "$all_running" = "true" ]; then
    print_success "All services are running!"
    print_info "Access the application at: http://localhost:$FRONTEND_PORT"
  else
    print_error "Some services are not running. Check the logs for details."
  fi

  return $([ "$all_running" = "true" ])
}

# Main function to start all services
main() {
  print_info "Starting Birth Time Rectifier services..."

  # Check Python dependencies
  check_python_dependencies || return 1

  # Start Redis
  start_redis || return 1

  # Start AI service
  start_ai_service || return 1

  # Start Frontend
  start_frontend || return 1

  # Check service status
  check_service_status

  return $?
}

# Run the main function
main
exit $?
