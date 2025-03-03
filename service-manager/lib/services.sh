#!/bin/bash

# ===========================================
# Service Management Functions
# ===========================================

# Source common functions and configuration
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LIB_DIR/common.sh"
source "$LIB_DIR/config.sh"

# Service process IDs
REDIS_PID=""
AI_SERVICE_PID=""
FRONTEND_PID=""

# Service start times
REDIS_START_TIME=0
AI_SERVICE_START_TIME=0
FRONTEND_START_TIME=0

# Service restart attempts
REDIS_RESTART_ATTEMPTS=0
AI_SERVICE_RESTART_ATTEMPTS=0
FRONTEND_RESTART_ATTEMPTS=0

# Service last restart time
REDIS_LAST_RESTART=0
AI_SERVICE_LAST_RESTART=0
FRONTEND_LAST_RESTART=0

# Function to check if a service is running
check_service_running() {
    local service=$1
    local pid_var="${service}_PID"
    local pid=${!pid_var}
    
    echo "DEBUG: Checking if $service is running, PID: $pid" >> "$DEBUG_LOG" 2>&1
    
    if [ -z "$pid" ]; then
        echo "DEBUG: $service PID is empty" >> "$DEBUG_LOG" 2>&1
        return 1
    fi
    
    if ! ps -p "$pid" > /dev/null 2>&1; then
        echo "DEBUG: $service process not found with PID $pid" >> "$DEBUG_LOG" 2>&1
        return 1
    fi
    
    echo "DEBUG: $service is running with PID $pid" >> "$DEBUG_LOG" 2>&1
    return 0
}

# Function to start the Redis service
start_redis() {
    ensure_log_dir
    
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    
    echo "DEBUG: Starting Redis on port $redis_port" >> "$DEBUG_LOG" 2>&1
    
    # Check if Redis is already running
    if check_service_running "REDIS"; then
        print_status "$BLUE" "ℹ" "Redis is already running on port $redis_port"
        return 0
    fi
    
    # Check if the port is already in use by another process
    if check_port_in_use $redis_port; then
        print_status "$YELLOW" "⚠" "Port $redis_port is already in use by another process"
        
        # Ask user if they want to kill the process using the port
        read -p "Do you want to kill the process using port $redis_port? (y/n): " kill_process
        if [ "$kill_process" = "y" ] || [ "$kill_process" = "Y" ]; then
            if ! kill_process_on_port $redis_port true; then
                print_status "$RED" "✗" "Failed to kill process on port $redis_port"
                return 1
            fi
        else
            print_status "$RED" "✗" "Cannot start Redis on port $redis_port as it's already in use"
            return 1
        fi
    fi
    
    # Check if Redis server is installed
    if ! command_exists redis-server; then
        print_status "$RED" "✗" "Redis server not found. Please install Redis and try again."
        return 1
    fi
    
    # Start Redis server in the background
    print_status "$YELLOW" "⚙" "Starting Redis server on port $redis_port..."
    
    # Using nohup to keep the process running after the script exits
    nohup redis-server --port "$redis_port" > "$REDIS_LOG" 2>&1 &
    REDIS_PID=$!
    
    # Verify that Redis started successfully
    sleep 1
    if ! check_service_running "REDIS"; then
        print_status "$RED" "✗" "Failed to start Redis server. Check $REDIS_LOG for details."
        REDIS_PID=""
        return 1
    fi
    
    # Record the start time
    REDIS_START_TIME=$(date +%s)
    REDIS_RESTART_ATTEMPTS=0
    
    print_status "$GREEN" "✓" "Redis server started on port $redis_port (PID: $REDIS_PID)"
    return 0
}

# Function to start the AI service
start_ai_service() {
    ensure_log_dir
    
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    
    echo "DEBUG: Starting AI Service on port $api_port" >> "$DEBUG_LOG" 2>&1
    
    # Check if AI Service is already running
    if check_service_running "AI_SERVICE"; then
        print_status "$BLUE" "ℹ" "AI Service is already running on port $api_port"
        return 0
    fi
    
    # Check if the port is already in use by another process
    if check_port_in_use $api_port; then
        print_status "$YELLOW" "⚠" "Port $api_port is already in use by another process"
        
        # Ask user if they want to kill the process using the port
        read -p "Do you want to kill the process using port $api_port? (y/n): " kill_process
        if [ "$kill_process" = "y" ] || [ "$kill_process" = "Y" ]; then
            if ! kill_process_on_port $api_port true; then
                print_status "$RED" "✗" "Failed to kill process on port $api_port"
                return 1
            fi
        else
            print_status "$RED" "✗" "Cannot start AI Service on port $api_port as it's already in use"
            return 1
        fi
    fi
    
    # Check for Python and required modules
    echo "DEBUG: Checking for Python3..." >> "$DEBUG_LOG" 2>&1
    local python_cmd
    if command_exists python3; then
        echo "DEBUG: Python3 found" >> "$DEBUG_LOG" 2>&1
        print_status "$GREEN" "✓" "Python3 found: $(python3 --version 2>&1)"
        # Set python_cmd to python3
        python_cmd="python3"
    else
        echo "DEBUG: Python3 not found" >> "$DEBUG_LOG" 2>&1
        print_status "$YELLOW" "!" "Python3 not found, checking for Python..."
        
        echo "DEBUG: Checking for Python..." >> "$DEBUG_LOG" 2>&1
        if command_exists python; then
            echo "DEBUG: Python found" >> "$DEBUG_LOG" 2>&1
            print_status "$GREEN" "✓" "Python found: $(python --version 2>&1)"
            # Set python_cmd to python
            python_cmd="python"
        else
            echo "DEBUG: Python not found" >> "$DEBUG_LOG" 2>&1
            print_status "$RED" "✗" "Python not found"
            print_status "$RED" "✗" "Python not found. Please install Python 3 and try again."
            return 1
        fi
    fi
    
    # Check if the AI service script exists
    if [ ! -f "ai_service/api/main.py" ]; then
        print_status "$RED" "✗" "AI Service not found. Expected at ai_service/api/main.py"
        return 1
    fi
    
    # Check for required Python modules
    local required_modules=("uvicorn" "fastapi" "redis" "pydantic")
    for module in "${required_modules[@]}"; do
        if ! $python_cmd -c "import $module" > /dev/null 2>&1; then
            print_status "$YELLOW" "!" "Required Python module '$module' not found. Attempting to install..."
            $python_cmd -m pip install "$module" > /dev/null 2>&1
            
            # Verify installation
            if ! $python_cmd -c "import $module" > /dev/null 2>&1; then
                print_status "$RED" "✗" "Failed to install required Python module '$module'"
                return 1
            fi
        fi
    done
    
    # Start the AI service
    print_status "$YELLOW" "⚙" "Starting AI Service on port $api_port..."
    
    # Build command with proper environment variables
    cd ai_service && nohup $python_cmd -m uvicorn api.main:app --host 0.0.0.0 --port "$api_port" > "../$AI_SERVICE_LOG" 2>&1 &
    AI_SERVICE_PID=$!
    cd ..
    
    # Check that the service started
    sleep 2
    if ! check_service_running "AI_SERVICE"; then
        print_status "$RED" "✗" "Failed to start AI Service. Check $AI_SERVICE_LOG for details."
        AI_SERVICE_PID=""
        debug_ai_service_failure
        return 1
    fi
    
    # Record the start time
    AI_SERVICE_START_TIME=$(date +%s)
    AI_SERVICE_RESTART_ATTEMPTS=0
    
    print_status "$GREEN" "✓" "AI Service started on port $api_port (PID: $AI_SERVICE_PID)"
    return 0
}

# Function to check if a port is in use
check_port_in_use() {
    local port=$1
    
    echo "DEBUG: Checking if port $port is in use" >> "$DEBUG_LOG" 2>&1
    
    if command -v lsof >/dev/null 2>&1; then
        if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
            echo "DEBUG: Port $port is in use" >> "$DEBUG_LOG" 2>&1
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tuln | grep -q ":$port "; then
            echo "DEBUG: Port $port is in use" >> "$DEBUG_LOG" 2>&1
            return 0
        fi
    fi
    
    echo "DEBUG: Port $port is not in use" >> "$DEBUG_LOG" 2>&1
    return 1
}

# Function to kill process on a specific port
kill_process_on_port() {
    local port=$1
    local force=$2
    
    echo "DEBUG: Attempting to kill process on port $port" >> "$DEBUG_LOG" 2>&1
    
    # Find PID of process using the port
    local pid=""
    
    if command -v lsof >/dev/null 2>&1; then
        pid=$(lsof -t -i:$port 2>/dev/null)
    elif command -v netstat >/dev/null 2>&1; then
        pid=$(netstat -tuln 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1)
    fi
    
    if [ -n "$pid" ]; then
        echo "DEBUG: Found process (PID: $pid) on port $port" >> "$DEBUG_LOG" 2>&1
        
        if [ "$force" = "true" ]; then
            echo "DEBUG: Force killing process (PID: $pid) on port $port" >> "$DEBUG_LOG" 2>&1
            kill -9 $pid 2>/dev/null
        else
            echo "DEBUG: Gracefully terminating process (PID: $pid) on port $port" >> "$DEBUG_LOG" 2>&1
            kill $pid 2>/dev/null
        fi
        
        # Wait for the port to be free
        local max_wait=5
        local waited=0
        while check_port_in_use $port && [ $waited -lt $max_wait ]; do
            sleep 1
            waited=$((waited + 1))
        done
        
        if check_port_in_use $port; then
            echo "DEBUG: Failed to free port $port after killing process" >> "$DEBUG_LOG" 2>&1
            return 1
        else
            echo "DEBUG: Successfully freed port $port" >> "$DEBUG_LOG" 2>&1
            return 0
        fi
    else
        echo "DEBUG: No process found using port $port" >> "$DEBUG_LOG" 2>&1
        return 0
    fi
}

# Function to start the Frontend service
start_frontend() {
    ensure_log_dir

    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")

    echo "DEBUG: Starting Frontend on port $frontend_port" >> "$DEBUG_LOG" 2>&1

    # Check if Frontend is already running
    if check_service_running "FRONTEND"; then
        print_status "$BLUE" "ℹ" "Frontend is already running on port $frontend_port"
        return 0
    fi
    
    # Check if the port is already in use by another process
    if check_port_in_use $frontend_port; then
        print_status "$YELLOW" "⚠" "Port $frontend_port is already in use by another process"
        
        # Ask user if they want to kill the process using the port
        read -p "Do you want to kill the process using port $frontend_port? (y/n): " kill_process
        if [ "$kill_process" = "y" ] || [ "$kill_process" = "Y" ]; then
            if ! kill_process_on_port $frontend_port true; then
                print_status "$RED" "✗" "Failed to kill process on port $frontend_port"
                return 1
            fi
        else
            print_status "$RED" "✗" "Cannot start Frontend on port $frontend_port as it's already in use"
            return 1
        fi
    fi
    
    # Check if Node.js is installed
    if ! command_exists node || ! command_exists npm; then
        print_status "$RED" "✗" "Node.js or npm not found. Please install Node.js and try again."
        return 1
    fi
    
    # Check if the frontend directory exists
    if [ ! -d "frontend" ]; then
        print_status "$RED" "✗" "Frontend directory not found. Expected at frontend/"
        return 1
    fi
    
    # Check if package.json exists
    if [ ! -f "frontend/package.json" ]; then
        print_status "$RED" "✗" "Frontend package.json not found. Expected at frontend/package.json"
        return 1
    fi
    
    # Check if node_modules exists, if not, install dependencies
    if [ ! -d "frontend/node_modules" ]; then
        print_status "$YELLOW" "!" "Frontend node_modules not found. Installing dependencies..."
        (cd frontend && npm install --quiet) || {
            print_status "$RED" "✗" "Failed to install Frontend dependencies"
            return 1
        }
    fi
    
    # Start the frontend
    print_status "$YELLOW" "⚙" "Starting Frontend on port $frontend_port..."
    
    # Set environment variables for the frontend
    export PORT="$frontend_port"
    export REACT_APP_API_URL="http://localhost:$(get_config_value "api_port" "$DEFAULT_API_PORT")"
    
    # Start the frontend in the background
    (cd frontend && nohup npm start > "../$FRONTEND_LOG" 2>&1) &
    FRONTEND_PID=$!
    
    # Wait for the frontend to start
    sleep 3
    if ! check_frontend_running; then
        print_status "$RED" "✗" "Failed to start Frontend. Check $FRONTEND_LOG for details."
        FRONTEND_PID=""
        return 1
    fi
    
    # Record the start time
    FRONTEND_START_TIME=$(date +%s)
    FRONTEND_RESTART_ATTEMPTS=0
    
    print_status "$GREEN" "✓" "Frontend started on port $frontend_port (PID: $FRONTEND_PID)"
    
    # Open browser if configured
    if [ "$(get_config_value "auto_open_browser" "true")" == "true" ]; then
        sleep 2
        open_browser "http://localhost:$frontend_port"
    fi
    
    return 0
}

# Function to start all services
start_all_services() {
    # Export configuration to environment variables
    export_config_to_env
    
    print_status "$BLUE" "ℹ" "Starting all services..."
    
    # Start Redis
    start_redis || print_status "$YELLOW" "!" "Failed to start Redis, continuing with other services"
    
    # Check if Python is available
    if command_exists python3 || command_exists python; then
        # Start AI Service (after Redis)
        if start_ai_service; then
            # Start Frontend (after AI Service)
            start_frontend || print_status "$YELLOW" "!" "Failed to start Frontend"
        else
            print_status "$YELLOW" "!" "Failed to start AI Service, skipping Frontend"
        fi
    else
        print_status "$YELLOW" "!" "Python not found. Skipping AI Service and Frontend."
        print_status "$BLUE" "ℹ" "To run all services, please install Python 3 using one of these methods:"
        print_status "$BLUE" "•" "Download from https://www.python.org/downloads/"
        print_status "$BLUE" "•" "Install Homebrew (https://brew.sh/) and then run: brew install python"
    fi
    
    # Report status of all services
    echo
    print_status "$BLUE" "ℹ" "Service Status Summary:"
    
    if check_service_running "REDIS"; then
        local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
        print_status "$GREEN" "✓" "Redis is running on port $redis_port (PID: $REDIS_PID)"
    else
        print_status "$RED" "✗" "Redis is not running"
    fi
    
    if check_service_running "AI_SERVICE"; then
        local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
        print_status "$GREEN" "✓" "AI Service is running on port $api_port (PID: $AI_SERVICE_PID)"
    else
        print_status "$RED" "✗" "AI Service is not running"
    fi
    
    if check_service_running "FRONTEND"; then
        local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
        print_status "$GREEN" "✓" "Frontend is running on port $frontend_port (PID: $FRONTEND_PID)"
    else
        print_status "$RED" "✗" "Frontend is not running"
    fi
}

# Function to stop a specific service
stop_service() {
    local service=$1
    local pid_var="${service}_PID"
    local pid=${!pid_var}
    
    echo "DEBUG: Stopping $service with PID $pid" >> "$DEBUG_LOG" 2>&1
    
    if [ -z "$pid" ] || ! ps -p "$pid" > /dev/null 2>&1; then
        print_status "$BLUE" "ℹ" "$service is not running"
        eval "${service}_PID=\"\""
        return 0
    fi
    
    print_status "$YELLOW" "⚙" "Stopping $service (PID: $pid)..."
    
    # First try a gentle SIGTERM
    kill -15 "$pid" > /dev/null 2>&1
    
    # Wait for process to stop
    local timeout=5
    while [ $timeout -gt 0 ] && ps -p "$pid" > /dev/null 2>&1; do
        sleep 1
        ((timeout--))
    done
    
    # If process is still running, force kill
    if ps -p "$pid" > /dev/null 2>&1; then
        echo "DEBUG: $service did not stop gracefully, forcing kill" >> "$DEBUG_LOG" 2>&1
        kill -9 "$pid" > /dev/null 2>&1
    fi
    
    # Clear the PID variable
    eval "${service}_PID=\"\""
    
    print_status "$GREEN" "✓" "$service stopped"
    return 0
}

# Function to stop all services
stop_all_services() {
    print_status "$BLUE" "ℹ" "Stopping all services..."
    
    # Stop services in reverse order: Frontend, AI Service, Redis
    stop_service "FRONTEND"
    stop_service "AI_SERVICE"
    stop_service "REDIS"
    
    print_status "$GREEN" "✓" "All services stopped"
}

# Function to restart a specific service
restart_service() {
    local service=$1
    
    echo "DEBUG: Restarting $service" >> "$DEBUG_LOG" 2>&1
    
    # Stop the service
    stop_service "$service"
    
    # Start the service based on its name
    case "$service" in
        "REDIS")
            start_redis
            ;;
        "AI_SERVICE")
            start_ai_service
            ;;
        "FRONTEND")
            start_frontend
            ;;
        *)
            print_status "$RED" "✗" "Unknown service: $service"
            return 1
            ;;
    esac
    
    return $?
}

# Function to restart all services
restart_all_services() {
    print_status "$BLUE" "ℹ" "Restarting all services..."
    
    # Stop all services
    stop_all_services
    
    # Start all services
    start_all_services
}

# Function to retry starting AI service with different configurations
retry_start_ai_service() {
    print_status "$YELLOW" "↻" "Trying alternative methods to start AI service..."
    echo "DEBUG: Trying alternative methods to start AI service" >> "$DEBUG_LOG" 2>&1
    
    # Try different Python paths
    local temp_file="/tmp/ai_service_retry.log"
    > "$temp_file"
    
    # Method 1: Try with absolute path
    echo "DEBUG: Method 1 - Using absolute path" >> "$DEBUG_LOG" 2>&1
    (
        cd "$(pwd)"
        if [ -d ".venv" ]; then
            source .venv/bin/activate
        fi
        
        # Set PYTHONPATH to current directory
        export PYTHONPATH="$(pwd)"
        python3 -m uvicorn ai_service.api.main:app --host 0.0.0.0 --port "$api_port" &
        echo $! > /tmp/ai_pid
    ) > "$temp_file" 2>&1
    
    # Wait a moment to see if it starts
    sleep 5
    if check_service_health "AI Service" "$api_port" "/health"; then
        print_status "$GREEN" "✓" "AI Service started with absolute path method"
        echo "DEBUG: AI Service started with absolute path method" >> "$DEBUG_LOG" 2>&1
        return 0
    fi
    
    # Method 2: Try with simplified command
    echo "DEBUG: Method 2 - Using simplified command" >> "$DEBUG_LOG" 2>&1
    kill $(cat /tmp/ai_pid 2>/dev/null) >/dev/null 2>&1 || true
    (
        cd ai_service
        if [ -d "../.venv" ]; then
            source ../.venv/bin/activate
        fi
        
        # Try simplified path
        export PYTHONPATH="$(pwd)/.."
        python3 -m uvicorn api.main:app --host 0.0.0.0 --port "$api_port" &
        echo $! > /tmp/ai_pid
    ) > "$temp_file" 2>&1
    
    # Wait a moment to see if it starts
    sleep 5
    if check_service_health "AI Service" "$api_port" "/health"; then
        print_status "$GREEN" "✓" "AI Service started with simplified command method"
        echo "DEBUG: AI Service started with simplified command method" >> "$DEBUG_LOG" 2>&1
        return 0
    fi
    
    # Method 3: Try with direct script execution
    echo "DEBUG: Method 3 - Using direct script execution" >> "$DEBUG_LOG" 2>&1
    kill $(cat /tmp/ai_pid 2>/dev/null) >/dev/null 2>&1 || true
    (
        if [ -d ".venv" ]; then
            source .venv/bin/activate
        fi
        
        # Try creating a temporary runner script
        echo "from ai_service.api.main import app
import uvicorn
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=$api_port)" > /tmp/run_ai.py
        
        export PYTHONPATH="$(pwd)"
        python3 /tmp/run_ai.py &
        echo $! > /tmp/ai_pid
    ) > "$temp_file" 2>&1
    
    # Wait a moment to see if it starts
    sleep 5
    if check_service_health "AI Service" "$api_port" "/health"; then
        print_status "$GREEN" "✓" "AI Service started with direct script method"
        echo "DEBUG: AI Service started with direct script method" >> "$DEBUG_LOG" 2>&1
        return 0
    fi
    
    print_status "$RED" "✗" "All methods to start AI service failed"
    echo "DEBUG: All methods to start AI service failed" >> "$DEBUG_LOG" 2>&1
    cat "$temp_file" >> "$AI_SERVICE_LOG"
    echo "DEBUG: Retry log appended to AI service log" >> "$DEBUG_LOG" 2>&1
    return 1
}

# Function to debug AI service startup failure
debug_ai_service_failure() {
    echo "DEBUG: Running AI service failure diagnostics" >> "$DEBUG_LOG" 2>&1
    print_status "$YELLOW" "!" "AI Service failed to start. Running diagnostics..."
    
    # Check AI service log for common errors
    if [ -f "$AI_SERVICE_LOG" ]; then
        local error_message=""
        
        # Check for port in use
        if grep -q "Address already in use" "$AI_SERVICE_LOG"; then
            local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
            error_message="Port $api_port is already in use by another process"
            
            # Try to find the process using the port
            local pid_using_port=""
            if command_exists lsof; then
                pid_using_port=$(lsof -ti :$api_port)
            elif command_exists netstat; then
                pid_using_port=$(netstat -ltnp 2>/dev/null | grep ":$api_port " | awk '{print $7}' | cut -d/ -f1)
            fi
            
            if [ -n "$pid_using_port" ]; then
                error_message="$error_message (PID: $pid_using_port)"
                
                # Offer to kill the conflicting process
                print_status "$YELLOW" "!" "$error_message"
                read -p "Do you want to kill the process and try again? (y/n): " response
                if [[ "$response" =~ ^[Yy]$ ]]; then
                    print_status "$YELLOW" "⚙" "Attempting to kill process $pid_using_port..."
                    
                    # Try with normal permissions
                    if kill -15 "$pid_using_port" > /dev/null 2>&1; then
                        sleep 1
                        print_status "$GREEN" "✓" "Process terminated"
                        
                        # Try starting AI service again
                        start_ai_service
                        return
                    else
                        # Try with sudo
                        print_status "$YELLOW" "!" "Failed to kill process. Attempting with sudo..."
                        sudo kill -15 "$pid_using_port" > /dev/null 2>&1
                        
                        if [ $? -eq 0 ]; then
                            sleep 1
                            print_status "$GREEN" "✓" "Process terminated with sudo"
                            
                            # Try starting AI service again
                            start_ai_service
                            return
                        else
                            print_status "$RED" "✗" "Failed to kill process even with sudo. Please free the port manually."
                        fi
                    fi
                fi
            else
                print_status "$RED" "✗" "$error_message"
                print_status "$YELLOW" "!" "Please free the port or change the API port in configuration."
            fi
        # Check for missing module
        elif grep -q "ModuleNotFoundError: No module named" "$AI_SERVICE_LOG"; then
            local missing_module=$(grep "ModuleNotFoundError: No module named" "$AI_SERVICE_LOG" | sed "s/.*No module named '\([^']*\)'.*/\1/")
            error_message="Missing Python module: $missing_module"
            
            # Offer to install the missing module
            print_status "$YELLOW" "!" "$error_message"
            read -p "Do you want to install the missing module? (y/n): " response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                print_status "$YELLOW" "⚙" "Attempting to install $missing_module..."
                
                # Determine Python executable
                local python_cmd
                if command_exists python3; then
                    python_cmd="python3"
                else
                    python_cmd="python"
                fi
                
                # Try to install the module
                $python_cmd -m pip install "$missing_module"
                
                if [ $? -eq 0 ]; then
                    print_status "$GREEN" "✓" "Module installed successfully"
                    
                    # Try starting AI service again
                    start_ai_service
                    return
                else
                    print_status "$RED" "✗" "Failed to install the module. Please install manually."
                fi
            fi
        # Other errors
        else
            local last_error=$(tail -5 "$AI_SERVICE_LOG" | grep -E 'Error|Exception|Failed' | head -1)
            if [ -n "$last_error" ]; then
                error_message="Error message: $last_error"
            else
                error_message="Unknown error. Check $AI_SERVICE_LOG for details."
            fi
            
            print_status "$RED" "✗" "$error_message"
        fi
    else
        print_status "$RED" "✗" "No AI service log file found ($AI_SERVICE_LOG)"
    fi
    
    # Offer general advice
    print_status "$BLUE" "ℹ" "Try the following:"
    print_status "$BLUE" "•" "Check if all required dependencies are installed"
    print_status "$BLUE" "•" "Make sure Redis is running"
    print_status "$BLUE" "•" "Check for file permissions issues"
    print_status "$BLUE" "•" "Run the diagnostics menu option for more details"
}

# Function to monitor services and auto-restart if needed
monitor_services() {
    clear
    show_banner
    
    # Get configuration for restart behavior
    local max_restart_attempts=$(get_config_value "max_restart_attempts" "3")
    local restart_cooldown=$(get_config_value "restart_cooldown" "30")
    
    echo -e "${CYAN}${BOLD}Service Monitor${NC}"
    echo -e "${DIM}Press 'q' to quit monitoring${NC}"
    echo
    
    # Current monitor step
    local current_step=0
    
    # Starting timestamp
    local start_time=$(date +%s)
    
    # Set up non-blocking read for input
    exec 3< <(cat)
    
    # Save terminal settings
    local old_tty_settings=$(stty -g)
    
    # Set terminal to raw mode
    stty raw -echo min 0 time 0
    
    local monitor_running=true
    while $monitor_running; do
        # Current timestamp for uptime calculation
        local current_time=$(date +%s)
        local uptime=$((current_time - start_time))
        
        # Format uptime as HH:MM:SS
        local uptime_formatted=$(printf "%02d:%02d:%02d" $((uptime/3600)) $((uptime%3600/60)) $((uptime%60)))
        
        # Clear the screen and show updated status
        clear
        show_banner
        
        echo -e "${CYAN}${BOLD}Service Monitor${NC} (Uptime: ${uptime_formatted})"
        echo -e "${DIM}Auto-restart: Enabled (Max attempts: $max_restart_attempts, Cooldown: ${restart_cooldown}s)${NC}"
        echo -e "${DIM}Press 'q' to quit monitoring${NC}"
        echo
        
        # Check Redis status
        if check_service_running "REDIS"; then
            local redis_uptime=$((current_time - REDIS_START_TIME))
            local redis_uptime_formatted=$(printf "%02d:%02d:%02d" $((redis_uptime/3600)) $((redis_uptime%3600/60)) $((redis_uptime%60)))
            print_status "$GREEN" "✓" "Redis is running (PID: $REDIS_PID, Uptime: $redis_uptime_formatted, Restarts: $REDIS_RESTART_ATTEMPTS)"
        else
            print_status "$RED" "✗" "Redis is not running"
            
            # Check if we should restart Redis based on cooldown and max attempts
            local should_restart=false
            
            if [ "$REDIS_RESTART_ATTEMPTS" -lt "$max_restart_attempts" ]; then
                # Check if cooldown period has passed
                if [ "$REDIS_LAST_RESTART" -eq 0 ] || [ $((current_time - REDIS_LAST_RESTART)) -gt "$restart_cooldown" ]; then
                    should_restart=true
                else
                    local cooldown_remaining=$((restart_cooldown - (current_time - REDIS_LAST_RESTART)))
                    print_status "$YELLOW" "!" "Redis cooldown: ${cooldown_remaining}s remaining"
                fi
            else
                print_status "$RED" "✗" "Redis max restart attempts reached ($max_restart_attempts)"
            fi
            
            # Restart Redis if needed
            if $should_restart; then
                print_status "$YELLOW" "⚙" "Auto-restarting Redis..."
                start_redis >/dev/null 2>&1
                REDIS_LAST_RESTART=$(date +%s)
                ((REDIS_RESTART_ATTEMPTS++))
            fi
        fi
        
        # Check AI Service status
        if check_service_running "AI_SERVICE"; then
            local ai_uptime=$((current_time - AI_SERVICE_START_TIME))
            local ai_uptime_formatted=$(printf "%02d:%02d:%02d" $((ai_uptime/3600)) $((ai_uptime%3600/60)) $((ai_uptime%60)))
            print_status "$GREEN" "✓" "AI Service is running (PID: $AI_SERVICE_PID, Uptime: $ai_uptime_formatted, Restarts: $AI_SERVICE_RESTART_ATTEMPTS)"
        else
            print_status "$RED" "✗" "AI Service is not running"
            
            # Check if we should restart AI Service
            local should_restart=false
            
            if [ "$AI_SERVICE_RESTART_ATTEMPTS" -lt "$max_restart_attempts" ]; then
                # Check if cooldown period has passed
                if [ "$AI_SERVICE_LAST_RESTART" -eq 0 ] || [ $((current_time - AI_SERVICE_LAST_RESTART)) -gt "$restart_cooldown" ]; then
                    should_restart=true
                else
                    local cooldown_remaining=$((restart_cooldown - (current_time - AI_SERVICE_LAST_RESTART)))
                    print_status "$YELLOW" "!" "AI Service cooldown: ${cooldown_remaining}s remaining"
                fi
            else
                print_status "$RED" "✗" "AI Service max restart attempts reached ($max_restart_attempts)"
            fi
            
            # Restart AI Service if needed
            if $should_restart; then
                print_status "$YELLOW" "⚙" "Auto-restarting AI Service..."
                start_ai_service >/dev/null 2>&1
                AI_SERVICE_LAST_RESTART=$(date +%s)
                ((AI_SERVICE_RESTART_ATTEMPTS++))
            fi
        fi
        
        # Check Frontend status
        if check_service_running "FRONTEND"; then
            local frontend_uptime=$((current_time - FRONTEND_START_TIME))
            local frontend_uptime_formatted=$(printf "%02d:%02d:%02d" $((frontend_uptime/3600)) $((frontend_uptime%3600/60)) $((frontend_uptime%60)))
            print_status "$GREEN" "✓" "Frontend is running (PID: $FRONTEND_PID, Uptime: $frontend_uptime_formatted, Restarts: $FRONTEND_RESTART_ATTEMPTS)"
        else
            print_status "$RED" "✗" "Frontend is not running"
            
            # Check if we should restart Frontend
            local should_restart=false
            
            if [ "$FRONTEND_RESTART_ATTEMPTS" -lt "$max_restart_attempts" ]; then
                # Check if cooldown period has passed
                if [ "$FRONTEND_LAST_RESTART" -eq 0 ] || [ $((current_time - FRONTEND_LAST_RESTART)) -gt "$restart_cooldown" ]; then
                    should_restart=true
                else
                    local cooldown_remaining=$((restart_cooldown - (current_time - FRONTEND_LAST_RESTART)))
                    print_status "$YELLOW" "!" "Frontend cooldown: ${cooldown_remaining}s remaining"
                fi
            else
                print_status "$RED" "✗" "Frontend max restart attempts reached ($max_restart_attempts)"
            fi
            
            # Restart Frontend if needed
            if $should_restart; then
                print_status "$YELLOW" "⚙" "Auto-restarting Frontend..."
                start_frontend >/dev/null 2>&1
                FRONTEND_LAST_RESTART=$(date +%s)
                ((FRONTEND_RESTART_ATTEMPTS++))
            fi
        fi
        
        # Check for user input (non-blocking)
        if read -t 0 -u 3 input; then
            if [[ "$input" == "q" || "$input" == "Q" ]]; then
                monitor_running=false
            fi
        fi
        
        # Wait before checking again
        sleep 2
    done
    
    # Reset terminal settings
    stty "$old_tty_settings"
    
    # Close the file descriptor
    exec 3<&-
    
    echo
    print_status "$BLUE" "ℹ" "Exiting monitoring mode"
}

# Function to handle service management menu
service_management_menu() {
    clear
    show_banner
    
    echo -e "${CYAN}${BOLD}Service Management${NC}"
    echo
    
    echo -e "${BLUE}Select a service to manage:${NC}"
    echo -e "  1. Redis"
    echo -e "  2. AI Service"
    echo -e "  3. Frontend"
    echo -e "  4. All Services"
    echo -e "  5. Return to previous menu"
    echo
    
    read -p "Enter your choice (1-5): " service_choice
    
    case $service_choice in
        1)
            clear
            show_banner
            echo -e "${CYAN}${BOLD}Redis Service Management${NC}"
            echo
            echo -e "${BLUE}Available actions:${NC}"
            echo -e "  1. Start Redis"
            echo -e "  2. Stop Redis"
            echo -e "  3. Restart Redis"
            echo -e "  4. Return to service menu"
            echo
            
            read -p "Enter your choice (1-4): " action_choice
            
            case $action_choice in
                1) start_redis ;;
                2) stop_service "REDIS" ;;
                3) restart_service "REDIS" ;;
                4) service_management_menu; return ;;
                *) 
                    print_status "$YELLOW" "!" "Invalid choice. Please try again."
                    sleep 1
                    service_management_menu
                    return
                    ;;
            esac
            ;;
            
        2)
            clear
            show_banner
            echo -e "${CYAN}${BOLD}AI Service Management${NC}"
            echo
            echo -e "${BLUE}Available actions:${NC}"
            echo -e "  1. Start AI Service"
            echo -e "  2. Stop AI Service"
            echo -e "  3. Restart AI Service"
            echo -e "  4. Return to service menu"
            echo
            
            read -p "Enter your choice (1-4): " action_choice
            
            case $action_choice in
                1) start_ai_service ;;
                2) stop_service "AI_SERVICE" ;;
                3) restart_service "AI_SERVICE" ;;
                4) service_management_menu; return ;;
                *) 
                    print_status "$YELLOW" "!" "Invalid choice. Please try again."
                    sleep 1
                    service_management_menu
                    return
                    ;;
            esac
            ;;
            
        3)
            clear
            show_banner
            echo -e "${CYAN}${BOLD}Frontend Service Management${NC}"
            echo
            echo -e "${BLUE}Available actions:${NC}"
            echo -e "  1. Start Frontend"
            echo -e "  2. Stop Frontend"
            echo -e "  3. Restart Frontend"
            echo -e "  4. Return to service menu"
            echo
            
            read -p "Enter your choice (1-4): " action_choice
            
            case $action_choice in
                1) start_frontend ;;
                2) stop_service "FRONTEND" ;;
                3) restart_service "FRONTEND" ;;
                4) service_management_menu; return ;;
                *) 
                    print_status "$YELLOW" "!" "Invalid choice. Please try again."
                    sleep 1
                    service_management_menu
                    return
                    ;;
            esac
            ;;
            
        4)
            clear
            show_banner
            echo -e "${CYAN}${BOLD}All Services Management${NC}"
            echo
            echo -e "${BLUE}Available actions:${NC}"
            echo -e "  1. Start All Services"
            echo -e "  2. Stop All Services"
            echo -e "  3. Restart All Services"
            echo -e "  4. Return to service menu"
            echo
            
            read -p "Enter your choice (1-4): " action_choice
            
            case $action_choice in
                1) start_all_services ;;
                2) stop_all_services ;;
                3) restart_all_services ;;
                4) service_management_menu; return ;;
                *) 
                    print_status "$YELLOW" "!" "Invalid choice. Please try again."
                    sleep 1
                    service_management_menu
                    return
                    ;;
            esac
            ;;
            
        5)
            # Return to previous menu
            return
            ;;
            
        *)
            print_status "$YELLOW" "!" "Invalid choice. Please try again."
            sleep 1
            service_management_menu
            return
            ;;
    esac
    
    # After performing an action, wait for user before returning to menu
    echo
    read -p "Press Enter to continue..."
    service_management_menu
}

# Function to check if frontend service is running
check_frontend_running() {
    # Check if the frontend port is in use
    if command -v lsof >/dev/null 2>&1; then
        if lsof -i :${FRONTEND_PORT} -sTCP:LISTEN >/dev/null 2>&1; then
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tuln | grep -q ":${FRONTEND_PORT} "; then
            return 0
        fi
    fi
    
    # Check if node is running with index.js or Next.js
    if ps aux | grep -v grep | grep -q "node.*index.js\|next"; then
        return 0
    fi
    
    return 1
}
