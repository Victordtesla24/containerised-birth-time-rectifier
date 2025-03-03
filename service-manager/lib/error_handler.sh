#!/bin/bash

# ===========================================
# Error Handling and Auto-Recovery Functions
# ===========================================

# Source common functions and configuration
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LIB_DIR/common.sh"
source "$LIB_DIR/config.sh"

# Function to analyze logs for specific error patterns
analyze_service_logs() {
    local service=$1
    local log_file=""
    local error_patterns=()
    local warnings=()
    local critical_errors=()
    
    echo "DEBUG: Analyzing logs for $service" >> "$DEBUG_LOG" 2>&1
    
    # Determine log file based on service
    case "$service" in
        "REDIS")
            log_file="$REDIS_LOG"
            # Redis-specific error patterns
            error_patterns=(
                "Error accepting" 
                "Error loading" 
                "Failed opening" 
                "Failed to bind"
                "Permission denied"
                "Address already in use"
            )
            ;;
        "AI_SERVICE")
            log_file="$AI_SERVICE_LOG"
            # AI Service-specific error patterns
            error_patterns=(
                "ImportError" 
                "ModuleNotFoundError" 
                "SyntaxError" 
                "NameError"
                "Address already in use"
                "Permission denied"
                "Connection refused"
                "Failed to connect to Redis"
            )
            ;;
        "FRONTEND")
            log_file="$FRONTEND_LOG"
            # Frontend-specific error patterns
            error_patterns=(
                "Error: Cannot find module" 
                "Error: listen EADDRINUSE" 
                "SyntaxError" 
                "ReferenceError"
                "TypeError"
                "Failed to compile"
                "Module not found"
            )
            ;;
        *)
            echo "DEBUG: Unknown service: $service" >> "$DEBUG_LOG" 2>&1
            return 1
            ;;
    esac
    
    # Check if log file exists
    if [ ! -f "$log_file" ]; then
        echo "DEBUG: Log file not found for $service: $log_file" >> "$DEBUG_LOG" 2>&1
        return 1
    fi
    
    # Analyze log file for error patterns
    for pattern in "${error_patterns[@]}"; do
        if grep -q "$pattern" "$log_file"; then
            # Extract the specific error message
            local error_line=$(grep -m 1 "$pattern" "$log_file")
            
            # Determine if this is a critical error
            if [[ "$pattern" == "Address already in use" || 
                  "$pattern" == "Permission denied" || 
                  "$pattern" == "Failed to bind" || 
                  "$pattern" == "Error: listen EADDRINUSE" ]]; then
                critical_errors+=("$error_line")
            else
                warnings+=("$error_line")
            fi
            
            echo "DEBUG: Found error pattern in $service logs: $pattern" >> "$DEBUG_LOG" 2>&1
        fi
    done
    
    # Return results
    if [ ${#critical_errors[@]} -gt 0 ]; then
        echo "CRITICAL:${critical_errors[0]}"
        return 2
    elif [ ${#warnings[@]} -gt 0 ]; then
        echo "WARNING:${warnings[0]}"
        return 1
    else
        echo "OK:No errors found"
        return 0
    fi
}

# Function to fix common errors automatically
auto_fix_error() {
    local service=$1
    local error_message=$2
    local fixed=false
    
    echo "DEBUG: Attempting to auto-fix error for $service: $error_message" >> "$DEBUG_LOG" 2>&1
    
    # Extract port from error message if it's a port conflict
    local port=""
    if [[ "$error_message" =~ [Aa]ddress\ already\ in\ use || 
          "$error_message" =~ EADDRINUSE ]]; then
        
        # Try to extract port number from error message
        if [[ "$error_message" =~ :([0-9]+) ]]; then
            port="${BASH_REMATCH[1]}"
        elif [[ "$service" == "REDIS" ]]; then
            port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
        elif [[ "$service" == "AI_SERVICE" ]]; then
            port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
        elif [[ "$service" == "FRONTEND" ]]; then
            port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
        fi
        
        if [ -n "$port" ]; then
            print_status "$YELLOW" "⚠" "Port conflict detected on port $port for $service. Attempting to resolve..."
            
            # Try to free the port
            if free_port "$port" "$service"; then
                print_status "$GREEN" "✓" "Successfully freed port $port for $service"
                fixed=true
            else
                # If we can't free the port, try to find an alternative port
                local new_port=$((port + 1))
                while [[ "$new_port" -lt 65535 ]]; do
                    if ! lsof -i :"$new_port" > /dev/null 2>&1; then
                        # Found an available port
                        print_status "$YELLOW" "↻" "Changing $service port from $port to $new_port"
                        
                        # Update configuration with the new port
                        case "$service" in
                            "REDIS")
                                update_config_value "redis_port" "$new_port"
                                ;;
                            "AI_SERVICE")
                                update_config_value "api_port" "$new_port"
                                ;;
                            "FRONTEND")
                                update_config_value "frontend_port" "$new_port"
                                ;;
                        esac
                        
                        fixed=true
                        break
                    fi
                    new_port=$((new_port + 1))
                done
                
                if ! $fixed; then
                    print_status "$RED" "✗" "Failed to find an available port for $service"
                fi
            fi
        fi
    elif [[ "$error_message" =~ [Pp]ermission\ denied ]]; then
        # Permission issues - try using sudo
        print_status "$YELLOW" "⚠" "Permission issue detected for $service. Attempting to use sudo..."
        
        # Set a flag to use sudo for this service
        case "$service" in
            "REDIS")
                export USE_SUDO_REDIS=true
                ;;
            "AI_SERVICE")
                export USE_SUDO_AI_SERVICE=true
                ;;
            "FRONTEND")
                export USE_SUDO_FRONTEND=true
                ;;
        esac
        
        fixed=true
    elif [[ "$error_message" =~ [Ii]mport[Ee]rror || 
            "$error_message" =~ [Mm]odule[Nn]ot[Ff]ound ]]; then
        # Missing Python module
        if [[ "$error_message" =~ [Nn]o\ module\ named\ \'([^\']+)\' ]]; then
            local module="${BASH_REMATCH[1]}"
            print_status "$YELLOW" "⚠" "Missing Python module: $module. Attempting to install..."
            
            # Determine Python executable
            local python_cmd
            if command_exists python3; then
                python_cmd="python3"
            elif command_exists python; then
                python_cmd="python"
            else
                print_status "$RED" "✗" "Python not found, cannot install module"
                return 1
            fi
            
            # Try to install the module
            if $python_cmd -m pip install "$module" > /dev/null 2>&1; then
                print_status "$GREEN" "✓" "Successfully installed Python module: $module"
                fixed=true
            else
                # Try with sudo
                print_status "$YELLOW" "↻" "Trying to install module with sudo..."
                if sudo $python_cmd -m pip install "$module" > /dev/null 2>&1; then
                    print_status "$GREEN" "✓" "Successfully installed Python module with sudo: $module"
                    fixed=true
                else
                    print_status "$RED" "✗" "Failed to install Python module: $module"
                fi
            fi
        fi
    elif [[ "$error_message" =~ [Cc]annot\ find\ module || 
            "$error_message" =~ [Mm]odule\ not\ found ]]; then
        # Missing Node.js module
        if [[ "$service" == "FRONTEND" ]]; then
            print_status "$YELLOW" "⚠" "Missing Node.js dependencies. Attempting to install..."
            
            # Try to install dependencies
            (cd frontend && npm install --quiet) > /dev/null 2>&1
            
            if [ $? -eq 0 ]; then
                print_status "$GREEN" "✓" "Successfully installed Node.js dependencies"
                fixed=true
            else
                print_status "$RED" "✗" "Failed to install Node.js dependencies"
            fi
        fi
    elif [[ "$error_message" =~ [Ff]ailed\ to\ connect\ to\ [Rr]edis ]]; then
        # Redis connection issue
        print_status "$YELLOW" "⚠" "AI Service failed to connect to Redis. Checking Redis status..."
        
        # Check if Redis is running
        if check_service_running "REDIS"; then
            print_status "$GREEN" "✓" "Redis is running"
        else
            print_status "$YELLOW" "↻" "Redis is not running. Attempting to start Redis..."
            
            # Try to start Redis
            if start_redis; then
                print_status "$GREEN" "✓" "Successfully started Redis"
                fixed=true
            else
                print_status "$RED" "✗" "Failed to start Redis"
            fi
        fi
    fi
    
    return $([ "$fixed" == "true" ] && echo 0 || echo 1)
}

# Function to verify service is healthy
verify_service_health() {
    local service=$1
    local healthy=false
    
    echo "DEBUG: Verifying health for $service" >> "$DEBUG_LOG" 2>&1
    
    case "$service" in
        "REDIS")
            local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
            
            # Check if Redis is running
            if check_service_running "REDIS"; then
                # Try to ping Redis
                if command_exists redis-cli; then
                    if redis-cli -p "$redis_port" ping > /dev/null 2>&1; then
                        healthy=true
                    fi
                fi
            fi
            ;;
        "AI_SERVICE")
            local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
            
            # Check if AI Service is running
            if check_service_running "AI_SERVICE"; then
                # Try to access health endpoint
                if check_service_health "AI Service" "$api_port" "/health"; then
                    healthy=true
                fi
            fi
            ;;
        "FRONTEND")
            local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
            
            # Check if Frontend is running
            if check_service_running "FRONTEND"; then
                # Try to access the frontend
                if curl -s --connect-timeout 3 --max-time 3 "http://localhost:$frontend_port" > /dev/null 2>&1; then
                    healthy=true
                fi
            fi
            ;;
        *)
            echo "DEBUG: Unknown service: $service" >> "$DEBUG_LOG" 2>&1
            return 1
            ;;
    esac
    
    return $([ "$healthy" == "true" ] && echo 0 || echo 1)
}

# Function to fix service issues and restart if needed
fix_and_restart_service() {
    local service=$1
    local max_attempts=${2:-3}
    local attempt=1
    local fixed=false
    
    echo "DEBUG: Attempting to fix and restart $service (max attempts: $max_attempts)" >> "$DEBUG_LOG" 2>&1
    
    while [ $attempt -le $max_attempts ] && ! $fixed; do
        print_status "$YELLOW" "↻" "Fix attempt $attempt/$max_attempts for $service..."
        
        # Analyze logs for errors
        local analysis_result=$(analyze_service_logs "$service")
        local analysis_status=$?
        
        if [ $analysis_status -eq 0 ]; then
            print_status "$GREEN" "✓" "No errors found in $service logs"
            fixed=true
        else
            # Extract error message from analysis result
            local error_type=$(echo "$analysis_result" | cut -d':' -f1)
            local error_message=$(echo "$analysis_result" | cut -d':' -f2-)
            
            print_status "$YELLOW" "⚠" "$error_type error in $service: $error_message"
            
            # Try to fix the error
            if auto_fix_error "$service" "$error_message"; then
                print_status "$GREEN" "✓" "Successfully fixed error for $service"
                
                # Restart the service
                print_status "$YELLOW" "↻" "Restarting $service..."
                
                # Stop the service first
                stop_service "$service"
                
                # Start the service based on its name
                case "$service" in
                    "REDIS")
                        if start_redis; then
                            print_status "$GREEN" "✓" "Successfully restarted Redis"
                            fixed=true
                        else
                            print_status "$RED" "✗" "Failed to restart Redis"
                        fi
                        ;;
                    "AI_SERVICE")
                        if start_ai_service; then
                            print_status "$GREEN" "✓" "Successfully restarted AI Service"
                            fixed=true
                        else
                            print_status "$RED" "✗" "Failed to restart AI Service"
                        fi
                        ;;
                    "FRONTEND")
                        if start_frontend; then
                            print_status "$GREEN" "✓" "Successfully restarted Frontend"
                            fixed=true
                        else
                            print_status "$RED" "✗" "Failed to restart Frontend"
                        fi
                        ;;
                esac
            else
                print_status "$RED" "✗" "Failed to fix error for $service"
            fi
        fi
        
        # Verify service health
        if $fixed && ! verify_service_health "$service"; then
            print_status "$YELLOW" "⚠" "$service is not healthy after restart"
            fixed=false
        fi
        
        attempt=$((attempt + 1))
    done
    
    return $([ "$fixed" == "true" ] && echo 0 || echo 1)
}

# Function to ensure all services are running and healthy
ensure_all_services_running() {
    local all_healthy=true
    
    echo "DEBUG: Ensuring all services are running and healthy" >> "$DEBUG_LOG" 2>&1
    
    # Check Redis
    if ! verify_service_health "REDIS"; then
        print_status "$YELLOW" "⚠" "Redis is not healthy. Attempting to fix..."
        if ! fix_and_restart_service "REDIS"; then
            print_status "$RED" "✗" "Failed to fix Redis"
            all_healthy=false
        fi
    fi
    
    # Check AI Service
    if ! verify_service_health "AI_SERVICE"; then
        print_status "$YELLOW" "⚠" "AI Service is not healthy. Attempting to fix..."
        if ! fix_and_restart_service "AI_SERVICE"; then
            print_status "$RED" "✗" "Failed to fix AI Service"
            all_healthy=false
        fi
    fi
    
    # Check Frontend
    if ! verify_service_health "FRONTEND"; then
        print_status "$YELLOW" "⚠" "Frontend is not healthy. Attempting to fix..."
        if ! fix_and_restart_service "FRONTEND"; then
            print_status "$RED" "✗" "Failed to fix Frontend"
            all_healthy=false
        fi
    fi
    
    return $([ "$all_healthy" == "true" ] && echo 0 || echo 1)
}

# Function to handle smart port conflict resolution
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
