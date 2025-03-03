#!/bin/bash

# ===========================================
# Common Functions, Colors, and Constants
# ===========================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

# Modern progress bar and spinner characters
FILL_CHAR="█"
EMPTY_CHAR="░"
SPINNER_CHARS=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")

# Terminal width
TERMINAL_WIDTH=$(tput cols 2>/dev/null || echo 80)

# Default configuration
DEFAULT_REDIS_PORT=6379
DEFAULT_API_PORT=8000
DEFAULT_FRONTEND_PORT=3000
DEFAULT_VERBOSE=false
DEFAULT_LOG_LEVEL="info"
DEFAULT_ENV="development"

# Config file
CONFIG_FILE=".service_config.json"

# Paths for log files
LOG_DIR="logs"
FRONTEND_LOG="$LOG_DIR/frontend.log"
AI_SERVICE_LOG="$LOG_DIR/ai_service.log"
REDIS_LOG="$LOG_DIR/redis.log"
ERROR_LOG="$LOG_DIR/error.log"
DEBUG_LOG="$LOG_DIR/debug.log"

# Initialize global variables
DOCKER_AVAILABLE=false
DOCKER_COMPOSE_AVAILABLE=false

# Function to print status with appropriate color
print_status() {
    local color=$1
    local symbol=$2
    local message=$3
    echo -e "${color}${symbol} ${message}${NC}"
    echo "DEBUG: Status: ${symbol} ${message}" >> "$DEBUG_LOG" 2>&1
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
    local result=$?
    echo "DEBUG: Checking command $1: $result" >> "$DEBUG_LOG" 2>&1
    return $result
}

# Function to ensure log directory exists
ensure_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR" >/dev/null 2>&1
        echo "DEBUG: Created log directory $LOG_DIR" >> "$DEBUG_LOG" 2>&1
    fi
}

# Function to ensure log files exist and are initialized
ensure_log_files() {
    echo "DEBUG: Ensuring log files exist and are properly initialized" >> "$DEBUG_LOG" 2>/dev/null
    
    # Create logs directory if it doesn't exist
    ensure_log_dir
    
    # Initialize log files if they don't exist
    touch "$FRONTEND_LOG" 2>/dev/null
    touch "$AI_SERVICE_LOG" 2>/dev/null
    touch "$REDIS_LOG" 2>/dev/null
    touch "$ERROR_LOG" 2>/dev/null
    touch "$DEBUG_LOG" 2>/dev/null
    
    # Add headers to empty log files
    for log_file in "$FRONTEND_LOG" "$AI_SERVICE_LOG" "$REDIS_LOG" "$ERROR_LOG" "$DEBUG_LOG"; do
        if [ ! -s "$log_file" ]; then
            echo "# Log file initialized on $(date)" > "$log_file"
            echo "# --------------------------------" >> "$log_file"
            echo "DEBUG: Initialized log file: $log_file" >> "$DEBUG_LOG" 2>/dev/null
        fi
    done
}

# Function to update progress counter (for parallel processes)
update_progress() {
    echo "DEBUG: Updating progress to $1" >> "$DEBUG_LOG" 2>&1
    echo $1 > /tmp/progress_step
}

# Function to display dynamic spinner and progress in one line
show_spinner_progress() {
    local pid=$1
    local prefix=$2
    local total_steps=$3
    local current_step=0
    local max_width=$((TERMINAL_WIDTH - 30))
    local bar_width=$((max_width > 30 ? 30 : max_width))
    local spinstr=0
    local spin_index=0
    local max_wait_time=120  # Maximum wait time in seconds
    local start_time=$(date +%s)
    
    # Save cursor position
    tput sc 2>/dev/null
    
    # Check if process exists before entering loop
    if ! ps -p $pid > /dev/null 2>&1; then
        # Process already completed
        tput rc 2>/dev/null
        printf "${prefix} ✓ ["
        printf "%${bar_width}s" | tr ' ' "$FILL_CHAR"
        printf "] ${GREEN}%3d%%${NC}" 100
        tput el 2>/dev/null
        echo
        return
    fi
    
    while ps -p $pid > /dev/null 2>&1; do
        # Check if we've been waiting too long
        local current_time=$(date +%s)
        local elapsed_time=$((current_time - start_time))
        
        if [ $elapsed_time -gt $max_wait_time ]; then
            echo "DEBUG: Spinner timed out after $max_wait_time seconds" >> "$DEBUG_LOG" 2>&1
            kill -9 $pid >/dev/null 2>&1 || true
            break
        fi
        
        # Calculate percentage based on real-time progress
        spin_index=$(( (spin_index + 1) % 10 ))
        current_step=$(cat /tmp/progress_step 2>/dev/null || echo 0)
        percentage=$((current_step * 100 / total_steps))
        filled=$((bar_width * current_step / total_steps))
        empty=$((bar_width - filled))
        
        # Restore cursor position
        tput rc 2>/dev/null
        
        # Print combined spinner and progress bar
        printf "${prefix} ${SPINNER_CHARS[$spin_index]} ["
        printf "%${filled}s" | tr ' ' "$FILL_CHAR"
        printf "%${empty}s" | tr ' ' "$EMPTY_CHAR"
        printf "] ${GREEN}%3d%%${NC}" $percentage
        
        # Clear rest of the line
        tput el 2>/dev/null
        
        sleep 0.1
    done
    
    # Final update to 100%
    tput rc 2>/dev/null
    printf "${prefix} ✓ ["
    printf "%${bar_width}s" | tr ' ' "$FILL_CHAR"
    printf "] ${GREEN}%3d%%${NC}" 100
    
    # Clear rest of the line and move to next line
    tput el 2>/dev/null
    echo
}

# Function to open browser
open_browser() {
    local url=$1
    echo "DEBUG: Attempting to open browser: $url" >> "$DEBUG_LOG" 2>&1
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "$url" >/dev/null 2>&1
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "$url" >/dev/null 2>&1
    fi
}

# Function to check if Docker is available and running
check_docker() {
    echo "DEBUG: Checking Docker availability" >> "$DEBUG_LOG" 2>&1
    if ! command_exists docker; then
        print_status "$RED" "✗" "Docker is not installed"
        echo "DEBUG: Docker is not installed" >> "$DEBUG_LOG" 2>&1
        DOCKER_AVAILABLE=false
        DOCKER_COMPOSE_AVAILABLE=false
        return 1
    fi
    
    if ! docker info >/dev/null 2>&1; then
        print_status "$RED" "✗" "Docker daemon is not running"
        echo "DEBUG: Docker daemon is not running" >> "$DEBUG_LOG" 2>&1
        DOCKER_AVAILABLE=false
        return 1
    fi
    
    # Docker is available, now check docker-compose
    if ! command_exists docker-compose; then
        print_status "$YELLOW" "⚠" "Docker Compose is not installed"
        echo "DEBUG: Docker Compose is not installed" >> "$DEBUG_LOG" 2>&1
        DOCKER_COMPOSE_AVAILABLE=false
    else
        echo "DEBUG: Docker Compose is available" >> "$DEBUG_LOG" 2>&1
        DOCKER_COMPOSE_AVAILABLE=true
    fi
    
    echo "DEBUG: Docker is available and running" >> "$DEBUG_LOG" 2>&1
    DOCKER_AVAILABLE=true
    return 0
}

# Function to check if required application files exist
check_application_files() {
    local missing_files=false
    
    echo "DEBUG: Checking application files" >> "$DEBUG_LOG" 2>&1
    
    # Check for key application files
    if [ ! -f "docker-compose.yml" ]; then
        print_status "$YELLOW" "⚠" "docker-compose.yml not found (Redis service will not work)"
        echo "DEBUG: docker-compose.yml not found" >> "$DEBUG_LOG" 2>&1
        missing_files=true
    fi
    
    if [ ! -d "ai_service" ] || [ ! -f "ai_service/api/main.py" ]; then
        print_status "$YELLOW" "⚠" "AI Service code not found (AI service will not work)"
        echo "DEBUG: AI Service code not found" >> "$DEBUG_LOG" 2>&1
        missing_files=true
    fi
    
    if [ ! -f "package.json" ]; then
        print_status "$YELLOW" "⚠" "package.json not found (Frontend will not work)"
        echo "DEBUG: package.json not found" >> "$DEBUG_LOG" 2>&1
        missing_files=true
    fi
    
    if [ "$missing_files" = true ]; then
        print_status "$YELLOW" "ℹ" "Some required files are missing, not all services may work correctly"
        return 1
    fi
    
    echo "DEBUG: All required application files found" >> "$DEBUG_LOG" 2>&1
    return 0
}

# Function to display a banner
show_banner() {
    echo -e "${BLUE}${BOLD}"
    echo " _____                _          ___                                   "
    echo "|   __|___ ___ _ _ _|_|___ ___ |  _|___ ___ ___ ___ ___ ___ ___      "
    echo "|__   | -_|  _| | | | |  _| -_|  | | -_|   |  _| . | -_|  _|- _|     "
    echo "|_____|___|_| |_____|_|___|___|| |_|___|_|_|___|___|___|_| |___|     "
    echo "                               |___|                                   "
    echo -e "${NC}"
    echo -e "${CYAN}Service Management Script v1.0${NC}"
    echo
}

# Function to check service health
check_service_health() {
    local service=$1
    local port=$2
    local endpoint=$3
    local retries=5
    local delay=1
    local attempt=1
    local curl_timeout=3
    
    echo "DEBUG: Checking health for $service on port $port, endpoint $endpoint" >> "$DEBUG_LOG" 2>&1
    while [ $attempt -le $retries ]; do
        echo "DEBUG: Health check attempt $attempt for $service" >> "$DEBUG_LOG" 2>&1
        if curl -s --connect-timeout $curl_timeout --max-time $curl_timeout "http://localhost:$port$endpoint" > /dev/null 2>&1; then
            echo "DEBUG: Health check success for $service" >> "$DEBUG_LOG" 2>&1
            return 0
        fi
        
        # Check if the port is even open/listening before continuing
        if ! lsof -i :$port > /dev/null 2>&1 && [ $attempt -gt 2 ]; then
            echo "DEBUG: Port $port is not open for $service after multiple attempts, exiting early" >> "$DEBUG_LOG" 2>&1
            break
        fi
        
        attempt=$((attempt + 1))
        sleep $delay
    done
    
    echo "DEBUG: Health check failed for $service after $retries attempts" >> "$DEBUG_LOG" 2>&1
    return 1
} 