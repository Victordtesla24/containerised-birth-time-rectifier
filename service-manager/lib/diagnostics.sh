#!/bin/bash

# ===========================================
# Diagnostics and Troubleshooting Functions
# ===========================================

# Source common functions and configuration
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LIB_DIR/common.sh"
source "$LIB_DIR/config.sh"

# Function to get system resources (CPU, memory, disk)
get_system_resources() {
    ensure_log_dir
    
    echo "DEBUG: Getting system resources" >> "$DEBUG_LOG" 2>&1
    
    # Initialize variables
    local cpu_usage=""
    local memory_info=""
    local disk_info=""
    
    echo -e "${CYAN}${BOLD}System Resources${NC}"
    
    # CPU information - different commands based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo -e "${BLUE}CPU Usage:${NC}"
        top -l 1 -n 0 | grep "CPU usage" | sed 's/^[[:space:]]*/  /'
        
        echo -e "${BLUE}Memory Usage:${NC}"
        vm_stat | perl -ne '/page size of (\d+)/ and $size=$1; /Pages free: (\d+)/ and print "  Free Memory: " . $1 * $size / 1048576 . " MB\n"; /Pages active: (\d+)/ and print "  Active Memory: " . $1 * $size / 1048576 . " MB\n"; /Pages inactive: (\d+)/ and print "  Inactive Memory: " . $1 * $size / 1048576 . " MB\n"; /Pages speculative: (\d+)/ and print "  Speculative Memory: " . $1 * $size / 1048576 . " MB\n"; /Pages wired down: (\d+)/ and print "  Wired Memory: " . $1 * $size / 1048576 . " MB\n";' | awk '{printf "  %s %.2f MB\n", $1" "$2, $3}'
        
        echo -e "${BLUE}Disk Usage:${NC}"
        df -h | grep -v "map " | awk 'NR==1 || /disk/ {printf "  %s\n", $0}'
    else
        # Linux and other Unix-like systems
        if command_exists mpstat; then
            echo -e "${BLUE}CPU Usage:${NC}"
            mpstat 1 1 | grep -A 5 "CPU" | tail -n 1 | awk '{print "  User: " $3 "%, System: " $5 "%, Idle: " $12 "%"}'
        elif command_exists top; then
            echo -e "${BLUE}CPU Usage:${NC}"
            top -bn1 | grep "Cpu(s)" | sed 's/^[[:space:]]*/  /'
        fi
        
        if command_exists free; then
            echo -e "${BLUE}Memory Usage:${NC}"
            free -h | grep -v + | awk 'NR==1 {print "  "$1 " " $2 " " $3 " " $4 " " $5 " " $6 " " $7} NR==2 {print "  "$1 " " $2 " " $3 " " $4 " " $5 " " $6 " " $7}'
        fi
        
        echo -e "${BLUE}Disk Usage:${NC}"
        df -h | grep -v "tmpfs" | awk 'NR==1 || /\/$/ || /\/home/ {printf "  %s\n", $0}'
    fi
    
    echo -e "${BLUE}Running Processes:${NC}"
    
    # List processes of interest: Redis, Node (Frontend), Python (AI Service)
    if command_exists ps; then
        echo -e "  ${DIM}Redis processes:${NC}"
        ps aux | grep -v grep | grep redis-server | awk '{printf "    PID: %s, CPU: %s%%, MEM: %s%%, CMD: %s\n", $2, $3, $4, $11}' || echo "    None found"
        
        echo -e "  ${DIM}Node.js processes:${NC}"
        ps aux | grep -v grep | grep node | awk '{printf "    PID: %s, CPU: %s%%, MEM: %s%%, CMD: %s\n", $2, $3, $4, $11}' || echo "    None found"
        
        echo -e "  ${DIM}Python processes:${NC}"
        ps aux | grep -v grep | grep python | awk '{printf "    PID: %s, CPU: %s%%, MEM: %s%%, CMD: %s\n", $2, $3, $4, $11}' || echo "    None found"
    fi
}

# Function to check if a port is in use
check_port_in_use() {
    local port=$1
    local in_use=false
    
    echo "DEBUG: Checking if port $port is in use" >> "$DEBUG_LOG" 2>&1
    
    if command_exists lsof; then
        if lsof -i :"$port" > /dev/null 2>&1; then
            in_use=true
            local pid=$(lsof -ti :"$port")
            local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            echo -e "  Port ${YELLOW}$port${NC} is in use by ${YELLOW}$cmd${NC} (PID: $pid)"
        else
            echo -e "  Port ${GREEN}$port${NC} is ${GREEN}available${NC}"
        fi
    elif command_exists netstat; then
        if netstat -tuln | grep -q ":$port "; then
            in_use=true
            echo -e "  Port ${YELLOW}$port${NC} is ${YELLOW}in use${NC}"
        else
            echo -e "  Port ${GREEN}$port${NC} is ${GREEN}available${NC}"
        fi
    else
        echo -e "  ${YELLOW}Could not check port $port (lsof or netstat not available)${NC}"
    fi
    
    return $([ "$in_use" == "true" ] && echo 1 || echo 0)
}

# Function to check for port conflicts and suggest resolution
smart_port_conflict_handler() {
    local port=$1
    local service=$2
    
    echo "DEBUG: Smart port conflict handling for $service on port $port" >> "$DEBUG_LOG" 2>&1
    
    # Check if port is in use
    if command_exists lsof; then
        local pid=$(lsof -ti :"$port" 2>/dev/null)
        if [ -n "$pid" ]; then
            local cmd=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
            print_status "$YELLOW" "!" "Port $port for $service is in use by $cmd (PID: $pid)"
            
            # Offer options to resolve
            echo -e "  ${BLUE}Options to resolve:${NC}"
            echo -e "  1. Kill the process using port $port"
            echo -e "  2. Choose a different port for $service"
            echo -e "  3. Skip and continue"
            echo
            
            read -p "Enter your choice (1-3): " choice
            
            case $choice in
                1)
                    print_status "$YELLOW" "⚙" "Attempting to kill process $pid..."
                    
                    # Try with normal permissions
                    if kill -15 "$pid" > /dev/null 2>&1; then
                        sleep 1
                        if ! lsof -ti :"$port" > /dev/null 2>&1; then
                            print_status "$GREEN" "✓" "Process terminated successfully"
                            return 0
                        else
                            # Process still running, try with SIGKILL
                            kill -9 "$pid" > /dev/null 2>&1
                            sleep 1
                            if ! lsof -ti :"$port" > /dev/null 2>&1; then
                                print_status "$GREEN" "✓" "Process terminated with SIGKILL"
                                return 0
                            else
                                # If still failed, try with sudo
                                print_status "$YELLOW" "!" "Failed to kill process. Attempting with sudo..."
                                sudo kill -9 "$pid" > /dev/null 2>&1
                                
                                sleep 1
                                if ! lsof -ti :"$port" > /dev/null 2>&1; then
                                    print_status "$GREEN" "✓" "Process terminated with sudo"
                                    return 0
                                else
                                    print_status "$RED" "✗" "Failed to kill process even with sudo"
                                    return 1
                                fi
                            fi
                        fi
                    else
                        # Try with sudo
                        print_status "$YELLOW" "!" "Failed to kill process. Attempting with sudo..."
                        sudo kill -15 "$pid" > /dev/null 2>&1
                        
                        sleep 1
                        if ! lsof -ti :"$port" > /dev/null 2>&1; then
                            print_status "$GREEN" "✓" "Process terminated with sudo"
                            return 0
                        else
                            # Try with SIGKILL
                            sudo kill -9 "$pid" > /dev/null 2>&1
                            sleep 1
                            if ! lsof -ti :"$port" > /dev/null 2>&1; then
                                print_status "$GREEN" "✓" "Process terminated with sudo SIGKILL"
                                return 0
                            else
                                print_status "$RED" "✗" "Failed to kill process even with sudo SIGKILL"
                                return 1
                            fi
                        fi
                    fi
                    ;;
                    
                2)
                    # Choose a new port
                    local new_port=""
                    local valid_port=false
                    
                    while ! $valid_port; do
                        read -p "Enter new port for $service (1024-65535): " new_port
                        
                        # Validate port
                        if ! [[ "$new_port" =~ ^[0-9]+$ ]]; then
                            print_status "$RED" "✗" "Invalid port: $new_port (must be a number)"
                            continue
                        fi
                        
                        if [ "$new_port" -lt 1024 ] || [ "$new_port" -gt 65535 ]; then
                            print_status "$RED" "✗" "Invalid port: $new_port (must be between 1024 and 65535)"
                            continue
                        fi
                        
                        # Check if the new port is also in use
                        if command_exists lsof; then
                            if lsof -i :"$new_port" > /dev/null 2>&1; then
                                print_status "$YELLOW" "!" "Port $new_port is also in use. Please choose another port."
                                continue
                            fi
                        elif command_exists netstat; then
                            if netstat -tuln | grep -q ":$new_port "; then
                                print_status "$YELLOW" "!" "Port $new_port is also in use. Please choose another port."
                                continue
                            fi
                        fi
                        
                        valid_port=true
                    done
                    
                    # Update configuration with the new port
                    case "$service" in
                        "Redis")
                            update_config_value "redis_port" "$new_port"
                            ;;
                        "AI Service")
                            update_config_value "api_port" "$new_port"
                            ;;
                        "Frontend")
                            update_config_value "frontend_port" "$new_port"
                            ;;
                    esac
                    
                    print_status "$GREEN" "✓" "Port for $service updated to $new_port"
                    return 0
                    ;;
                    
                3)
                    print_status "$BLUE" "ℹ" "Skipping port conflict resolution for $service"
                    return 2
                    ;;
                    
                *)
                    print_status "$YELLOW" "!" "Invalid choice. Skipping port conflict resolution for $service"
                    return 2
                    ;;
            esac
        fi
    elif command_exists netstat; then
        if netstat -tuln | grep -q ":$port "; then
            print_status "$YELLOW" "!" "Port $port for $service is in use, but process details cannot be determined"
            
            # Offer to change the port
            read -p "Would you like to choose a different port for $service? (y/n): " response
            if [[ "$response" =~ ^[Yy]$ ]]; then
                local new_port=""
                local valid_port=false
                
                while ! $valid_port; do
                    read -p "Enter new port for $service (1024-65535): " new_port
                    
                    # Validate port
                    if ! [[ "$new_port" =~ ^[0-9]+$ ]]; then
                        print_status "$RED" "✗" "Invalid port: $new_port (must be a number)"
                        continue
                    fi
                    
                    if [ "$new_port" -lt 1024 ] || [ "$new_port" -gt 65535 ]; then
                        print_status "$RED" "✗" "Invalid port: $new_port (must be between 1024 and 65535)"
                        continue
                    fi
                    
                    # Check if the new port is also in use
                    if netstat -tuln | grep -q ":$new_port "; then
                        print_status "$YELLOW" "!" "Port $new_port is also in use. Please choose another port."
                        continue
                    fi
                    
                    valid_port=true
                done
                
                # Update configuration with the new port
                case "$service" in
                    "Redis")
                        update_config_value "redis_port" "$new_port"
                        ;;
                    "AI Service")
                        update_config_value "api_port" "$new_port"
                        ;;
                    "Frontend")
                        update_config_value "frontend_port" "$new_port"
                        ;;
                esac
                
                print_status "$GREEN" "✓" "Port for $service updated to $new_port"
                return 0
            else
                print_status "$BLUE" "ℹ" "Keeping current port configuration for $service"
                return 2
            fi
        fi
    fi
    
    # Port not in use
    return 0
}

# Function to flush logs
flush_logs() {
    ensure_log_dir
    
    echo "DEBUG: Flushing logs" >> "$DEBUG_LOG" 2>&1
    
    print_status "$YELLOW" "⚙" "Flushing log files..."
    
    # Check if we should backup logs first
    read -p "Do you want to backup logs before flushing? (y/n): " backup_choice
    
    if [[ "$backup_choice" =~ ^[Yy]$ ]]; then
        # Create a backup directory with timestamp
        local timestamp=$(date +"%Y%m%d_%H%M%S")
        local backup_dir="${LOG_DIR}/backup_${timestamp}"
        
        mkdir -p "$backup_dir" || {
            print_status "$RED" "✗" "Failed to create backup directory"
            return 1
        }
        
        # Backup each log file if it exists
        for log_file in "$FRONTEND_LOG" "$AI_SERVICE_LOG" "$REDIS_LOG" "$ERROR_LOG" "$DEBUG_LOG"; do
            if [ -f "$log_file" ]; then
                cp "$log_file" "$backup_dir/$(basename "$log_file")" || {
                    print_status "$YELLOW" "!" "Failed to backup $log_file"
                }
            fi
        done
        
        print_status "$GREEN" "✓" "Logs backed up to $backup_dir"
    fi
    
    # Flush each log file
    for log_file in "$FRONTEND_LOG" "$AI_SERVICE_LOG" "$REDIS_LOG" "$ERROR_LOG" "$DEBUG_LOG"; do
        if [ -f "$log_file" ]; then
            echo "Flushed log at $(date)" > "$log_file" || {
                print_status "$RED" "✗" "Failed to flush $log_file"
            }
        else
            # Create the file if it doesn't exist
            echo "Log started at $(date)" > "$log_file" || {
                print_status "$RED" "✗" "Failed to create $log_file"
            }
        fi
    done
    
    print_status "$GREEN" "✓" "All logs flushed successfully"
}

# Function to view logs
view_logs() {
    ensure_log_dir
    
    while true; do
        clear
        show_banner
        
        echo -e "${CYAN}${BOLD}View Logs${NC}"
        echo
        
        echo -e "${BLUE}Available logs:${NC}"
        echo -e "  1. Frontend Log"
        echo -e "  2. AI Service Log"
        echo -e "  3. Redis Log"
        echo -e "  4. Error Log"
        echo -e "  5. Debug Log"
        echo -e "  6. Return to previous menu"
        echo
        
        read -p "Enter your choice (1-6): " log_choice
        
        case $log_choice in
            1)
                if [ -f "$FRONTEND_LOG" ]; then
                    clear
                    echo -e "${CYAN}${BOLD}Frontend Log${NC}"
                    echo -e "${DIM}Press q to exit, or use arrow keys to navigate${NC}"
                    echo
                    less -R "$FRONTEND_LOG" || cat "$FRONTEND_LOG" | more
                else
                    print_status "$YELLOW" "!" "Frontend log not found"
                    sleep 2
                fi
                ;;
            
            2)
                if [ -f "$AI_SERVICE_LOG" ]; then
                    clear
                    echo -e "${CYAN}${BOLD}AI Service Log${NC}"
                    echo -e "${DIM}Press q to exit, or use arrow keys to navigate${NC}"
                    echo
                    less -R "$AI_SERVICE_LOG" || cat "$AI_SERVICE_LOG" | more
                else
                    print_status "$YELLOW" "!" "AI Service log not found"
                    sleep 2
                fi
                ;;
            
            3)
                if [ -f "$REDIS_LOG" ]; then
                    clear
                    echo -e "${CYAN}${BOLD}Redis Log${NC}"
                    echo -e "${DIM}Press q to exit, or use arrow keys to navigate${NC}"
                    echo
                    less -R "$REDIS_LOG" || cat "$REDIS_LOG" | more
                else
                    print_status "$YELLOW" "!" "Redis log not found"
                    sleep 2
                fi
                ;;
            
            4)
                if [ -f "$ERROR_LOG" ]; then
                    clear
                    echo -e "${CYAN}${BOLD}Error Log${NC}"
                    echo -e "${DIM}Press q to exit, or use arrow keys to navigate${NC}"
                    echo
                    less -R "$ERROR_LOG" || cat "$ERROR_LOG" | more
                else
                    print_status "$YELLOW" "!" "Error log not found"
                    sleep 2
                fi
                ;;
            
            5)
                if [ -f "$DEBUG_LOG" ]; then
                    clear
                    echo -e "${CYAN}${BOLD}Debug Log${NC}"
                    echo -e "${DIM}Press q to exit, or use arrow keys to navigate${NC}"
                    echo
                    less -R "$DEBUG_LOG" || cat "$DEBUG_LOG" | more
                else
                    print_status "$YELLOW" "!" "Debug log not found"
                    sleep 2
                fi
                ;;
            
            6)
                return
                ;;
            
            *)
                print_status "$YELLOW" "!" "Invalid choice. Please try again."
                sleep 1
                ;;
        esac
    done
}

# Function to check service status
check_service_status() {
    # Output service status
    echo -e "\n${BOLD}Current Service Status${NC}\n"
    
    # Get configuration values
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    local skip_redis=$(get_config_value "skip_redis" "false")
    
    # Check Redis
    if [ "$skip_redis" = "true" ]; then
        print_status "$BLUE" "ℹ" "Redis: Intentionally skipped (skip_redis=true)"
        echo "DEBUG: Redis is skipped by configuration" >> "$DEBUG_LOG" 2>&1
    elif check_service_running "REDIS"; then
        print_status "$GREEN" "✓" "Redis: Running on port $redis_port"
        echo "DEBUG: Redis is running" >> "$DEBUG_LOG" 2>&1
    else
        print_status "$RED" "✗" "Redis: Not running"
        echo "DEBUG: Redis is not running" >> "$DEBUG_LOG" 2>&1
    fi
    
    # Check AI service
    if check_service_running "AI_SERVICE"; then
        print_status "$GREEN" "✓" "AI Service: Running on port $api_port"
        echo "DEBUG: AI Service is running" >> "$DEBUG_LOG" 2>&1
    else
        print_status "$RED" "✗" "AI Service: Not running"
        echo "DEBUG: AI Service is not running" >> "$DEBUG_LOG" 2>&1
    fi
    
    # Check Frontend
    if check_service_running "FRONTEND"; then
        print_status "$GREEN" "✓" "Frontend: Running on port $frontend_port"
        print_status "$BLUE" "ℹ" "URL: http://localhost:$frontend_port"
        echo "DEBUG: Frontend is running" >> "$DEBUG_LOG" 2>&1
    else
        print_status "$RED" "✗" "Frontend: Not running"
        echo "DEBUG: Frontend is not running" >> "$DEBUG_LOG" 2>&1
    fi
}

# Function to run comprehensive diagnostics
run_diagnostics() {
    ensure_log_dir
    
    clear
    show_banner
    
    echo -e "${CYAN}${BOLD}System Diagnostics${NC}"
    echo -e "${DIM}Running comprehensive system diagnostics...${NC}"
    echo
    
    # Start diagnostics
    echo "DEBUG: Running diagnostics at $(date)" >> "$DEBUG_LOG" 2>&1
    
    # Check for logs directory
    echo -e "${BLUE}Checking logs directory:${NC}"
    if [ -d "$LOG_DIR" ]; then
        print_status "$GREEN" "✓" "Logs directory exists"
    else
        print_status "$YELLOW" "!" "Logs directory does not exist, creating..."
        mkdir -p "$LOG_DIR"
        print_status "$GREEN" "✓" "Logs directory created"
    fi
    echo
    
    # Check system information
    echo -e "${BLUE}System Information:${NC}"
    echo -e "  ${DIM}OS:${NC} $(uname -s) $(uname -r)"
    echo -e "  ${DIM}Architecture:${NC} $(uname -m)"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "  ${DIM}macOS Version:${NC} $(sw_vers -productVersion)"
    elif [ -f /etc/os-release ]; then
        echo -e "  ${DIM}Linux Distribution:${NC} $(grep PRETTY_NAME /etc/os-release | sed 's/PRETTY_NAME=//;s/"//g')"
    fi
    echo
    
    # Check for required commands
    echo -e "${BLUE}Checking required dependencies:${NC}"
    
    local required_commands=("bash" "grep" "sed" "awk" "ps" "kill")
    for cmd in "${required_commands[@]}"; do
        if command_exists "$cmd"; then
            print_status "$GREEN" "✓" "$cmd is installed"
        else
            print_status "$RED" "✗" "$cmd is not installed"
        fi
    done
    echo
    
    # Check for optional but recommended commands
    echo -e "${BLUE}Checking recommended dependencies:${NC}"
    
    local recommended_commands=("jq" "lsof" "netstat" "curl" "wget")
    for cmd in "${recommended_commands[@]}"; do
        if command_exists "$cmd"; then
            print_status "$GREEN" "✓" "$cmd is installed"
        else
            print_status "$YELLOW" "!" "$cmd is not installed"
        fi
    done
    echo
    
    # Check for service dependencies
    echo -e "${BLUE}Checking service dependencies:${NC}"
    
    # Redis
    if command_exists redis-server; then
        local redis_version=$(redis-server --version | head -n 1)
        print_status "$GREEN" "✓" "Redis is installed: $redis_version"
    else
        print_status "$RED" "✗" "Redis is not installed"
    fi
    
    # Python (for AI Service)
    if command_exists python3; then
        local python_version=$(python3 --version 2>&1)
        print_status "$GREEN" "✓" "Python is installed: $python_version"
    elif command_exists python; then
        local python_version=$(python --version 2>&1)
        print_status "$GREEN" "✓" "Python is installed: $python_version"
    else
        print_status "$RED" "✗" "Python is not installed"
    fi
    
    # Node.js (for Frontend)
    if command_exists node; then
        local node_version=$(node --version 2>&1)
        print_status "$GREEN" "✓" "Node.js is installed: $node_version"
        
        if command_exists npm; then
            local npm_version=$(npm --version 2>&1)
            print_status "$GREEN" "✓" "npm is installed: $npm_version"
        else
            print_status "$RED" "✗" "npm is not installed"
        fi
    else
        print_status "$RED" "✗" "Node.js is not installed"
    fi
    
    # Docker (optional)
    if command_exists docker; then
        local docker_version=$(docker --version 2>&1)
        print_status "$GREEN" "✓" "Docker is installed: $docker_version"
    else
        print_status "$YELLOW" "!" "Docker is not installed (optional)"
    fi
    echo
    
    # Check ports
    echo -e "${BLUE}Checking service ports:${NC}"
    
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    
    check_port_in_use "$redis_port"
    check_port_in_use "$api_port"
    check_port_in_use "$frontend_port"
    echo
    
    # Check AI service Python modules
    echo -e "${BLUE}Checking required Python modules for AI service:${NC}"
    
    # Determine Python executable
    local python_cmd
    if command_exists python3; then
        python_cmd="python3"
    elif command_exists python; then
        python_cmd="python"
    else
        print_status "$RED" "✗" "Python not found, cannot check modules"
        echo
    fi
    
    if [ -n "$python_cmd" ]; then
        local required_modules=("uvicorn" "fastapi" "redis" "pydantic")
        for module in "${required_modules[@]}"; do
            if $python_cmd -c "import $module" > /dev/null 2>&1; then
                # Try to get version
                local version=$($python_cmd -c "import $module; print(getattr($module, '__version__', 'unknown'))" 2>/dev/null || echo "installed")
                print_status "$GREEN" "✓" "Python module $module is installed (version: $version)"
            else
                print_status "$RED" "✗" "Python module $module is not installed"
            fi
        done
        echo
    fi
    
    # Check for configuration file
    echo -e "${BLUE}Checking configuration:${NC}"
    
    if [ -f "$CONFIG_FILE" ]; then
        print_status "$GREEN" "✓" "Configuration file exists"
        
        # Display configuration if jq is available
        if command_exists jq; then
            echo -e "  ${DIM}Configuration values:${NC}"
            jq -r 'to_entries | .[] | "    \(.key): \(.value)"' "$CONFIG_FILE" | sort
        else
            echo -e "  ${DIM}Configuration file found, but jq is not installed to parse it.${NC}"
        fi
    else
        print_status "$YELLOW" "!" "Configuration file does not exist, using defaults"
    fi
    echo
    
    # Check for service directories
    echo -e "${BLUE}Checking service directories:${NC}"
    
    # AI Service directory
    if [ -d "ai_service" ]; then
        print_status "$GREEN" "✓" "AI Service directory exists"
        
        # Check for main.py
        if [ -f "ai_service/main.py" ]; then
            print_status "$GREEN" "✓" "AI Service main.py found"
        else
            print_status "$RED" "✗" "AI Service main.py not found"
        fi
    else
        print_status "$RED" "✗" "AI Service directory does not exist"
    fi
    
    # Frontend directory
    if [ -d "frontend" ]; then
        print_status "$GREEN" "✓" "Frontend directory exists"
        
        # Check for package.json
        if [ -f "frontend/package.json" ]; then
            print_status "$GREEN" "✓" "Frontend package.json found"
            
            # Check if node_modules exists
            if [ -d "frontend/node_modules" ]; then
                print_status "$GREEN" "✓" "Frontend node_modules found"
            else
                print_status "$YELLOW" "!" "Frontend node_modules not found (dependencies not installed)"
            fi
        else
            print_status "$RED" "✗" "Frontend package.json not found"
        fi
    else
        print_status "$RED" "✗" "Frontend directory does not exist"
    fi
    echo
    
    # Check service status
    echo -e "${BLUE}Checking service status:${NC}"
    
    # Use process detection to determine if services are running
    
    # Redis
    local redis_running=false
    if command_exists pgrep; then
        if pgrep -f "redis-server.*$redis_port" > /dev/null; then
            redis_running=true
        fi
    elif command_exists ps; then
        if ps aux | grep -v grep | grep -q "redis-server.*$redis_port"; then
            redis_running=true
        fi
    fi
    
    if $redis_running; then
        print_status "$GREEN" "✓" "Redis is running on port $redis_port"
    else
        print_status "$YELLOW" "!" "Redis is not running"
    fi
    
    # AI Service
    local ai_running=false
    if command_exists pgrep; then
        if pgrep -f "uvicorn.*$api_port" > /dev/null; then
            ai_running=true
        fi
    elif command_exists ps; then
        if ps aux | grep -v grep | grep -q "uvicorn.*$api_port"; then
            ai_running=true
        fi
    fi
    
    if $ai_running; then
        print_status "$GREEN" "✓" "AI Service is running on port $api_port"
    else
        print_status "$YELLOW" "!" "AI Service is not running"
    fi
    
    # Frontend
    local frontend_running=false
    if command_exists pgrep; then
        if pgrep -f "node.*$frontend_port" > /dev/null; then
            frontend_running=true
        fi
    elif command_exists ps; then
        if ps aux | grep -v grep | grep -q "node.*$frontend_port"; then
            frontend_running=true
        fi
    fi
    
    if $frontend_running; then
        print_status "$GREEN" "✓" "Frontend is running on port $frontend_port"
    else
        print_status "$YELLOW" "!" "Frontend is not running"
    fi
    echo
    
    # Check log files
    echo -e "${BLUE}Checking log files:${NC}"
    
    for log_file in "frontend.log" "ai_service.log" "redis.log" "error.log" "debug.log"; do
        local full_path="$LOG_DIR/$log_file"
        if [ -f "$full_path" ]; then
            local log_size=$(du -h "$full_path" | cut -f1)
            local log_updated=$(date -r "$full_path" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c "%y" "$full_path" 2>/dev/null || echo "unknown")
            print_status "$GREEN" "✓" "$log_file exists (size: $log_size, last updated: $log_updated)"
        else
            print_status "$YELLOW" "!" "$log_file does not exist"
        fi
    done
    echo
    
    # Check system resources
    get_system_resources
    echo
    
    # Summary
    echo -e "${BLUE}Diagnostics Summary:${NC}"
    
    local errors=0
    local warnings=0
    
    # Count error messages in the log
    errors=$(grep -c "ERROR" "$DEBUG_LOG" || echo 0)
    
    # Count warning messages in the log
    warnings=$(grep -c "WARNING" "$DEBUG_LOG" || echo 0)
    
    # Ensure errors and warnings are numeric
    errors=$(echo "$errors" | tr -cd '0-9')
    warnings=$(echo "$warnings" | tr -cd '0-9')
    
    # Default to 0 if empty
    errors=${errors:-0}
    warnings=${warnings:-0}
    
    if [ "$errors" -gt 0 ]; then
        print_status "$RED" "✗" "Diagnostics completed with $errors errors and $warnings warnings"
    elif [ "$warnings" -gt 0 ]; then
        print_status "$YELLOW" "!" "Diagnostics completed with $warnings warnings"
    else
        print_status "$GREEN" "✓" "Diagnostics completed successfully with no issues"
    fi
    
    # Recommendations based on diagnostics
    echo -e "${BLUE}Recommendations:${NC}"
    
    # Redis not installed
    if ! command_exists redis-server; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            print_status "$YELLOW" "•" "Install Redis using Homebrew: brew install redis"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command_exists apt-get; then
                print_status "$YELLOW" "•" "Install Redis: sudo apt-get install redis-server"
            elif command_exists yum; then
                print_status "$YELLOW" "•" "Install Redis: sudo yum install redis"
            else
                print_status "$YELLOW" "•" "Install Redis using your package manager"
            fi
        fi
    fi
    
    # Python modules missing
    if [ -n "$python_cmd" ]; then
        for module in "uvicorn" "fastapi" "redis" "pydantic"; do
            if ! $python_cmd -c "import $module" > /dev/null 2>&1; then
                print_status "$YELLOW" "•" "Install Python module $module: $python_cmd -m pip install $module"
            fi
        done
    fi
    
    # Node.js missing
    if ! command_exists node; then
        print_status "$YELLOW" "•" "Install Node.js from https://nodejs.org/"
    fi
    
    # Service not running
    if ! $redis_running && command_exists redis-server; then
        print_status "$YELLOW" "•" "Start Redis service using the service management menu"
    fi
    
    if ! $ai_running && [ -f "ai_service/main.py" ]; then
        print_status "$YELLOW" "•" "Start AI Service using the service management menu"
    fi
    
    if ! $frontend_running && [ -d "frontend" ]; then
        print_status "$YELLOW" "•" "Start Frontend using the service management menu"
    fi
    
    echo
    print_status "$BLUE" "ℹ" "Diagnostics report has been saved to $DEBUG_LOG"
    echo
    
    # Wait for user input before returning
    read -p "Press Enter to continue..."
}
