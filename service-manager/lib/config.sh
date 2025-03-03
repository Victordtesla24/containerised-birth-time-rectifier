#!/bin/bash

# ===========================================
# Configuration Management Functions
# ===========================================

# Source common functions
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LIB_DIR/common.sh"

# Function to initialize configuration with default values
initialize_config() {
    ensure_log_dir
    
    echo "DEBUG: Initializing configuration" >> "$DEBUG_LOG" 2>&1
    
    # Create default configuration if it doesn't exist
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "DEBUG: Creating default configuration file" >> "$DEBUG_LOG" 2>&1
        cat > "$CONFIG_FILE" << EOF
{
  "redis_port": $DEFAULT_REDIS_PORT,
  "api_port": $DEFAULT_API_PORT,
  "frontend_port": $DEFAULT_FRONTEND_PORT,
  "verbose": $DEFAULT_VERBOSE,
  "log_level": "$DEFAULT_LOG_LEVEL",
  "environment": "$DEFAULT_ENV",
  "max_restart_attempts": 3,
  "restart_cooldown": 30,
  "auto_open_browser": true,
  "check_updates": true,
  "skip_redis": false
}
EOF
        print_status "$GREEN" "✓" "Default configuration created"
    else
        echo "DEBUG: Configuration file already exists" >> "$DEBUG_LOG" 2>&1
        print_status "$BLUE" "ℹ" "Using existing configuration"
    fi
}

# Function to create default configuration (for backward compatibility)
create_default_config() {
    echo "DEBUG: Creating default configuration" >> "$DEBUG_LOG" 2>&1
    initialize_config
}

# Function to read a specific configuration value
get_config_value() {
    local key=$1
    local default_value=$2
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "DEBUG: Config file not found. Using default value for $key: $default_value" >> "$DEBUG_LOG" 2>&1
        echo "$default_value"
        return
    fi
    
    # Check if jq is available
    if command_exists jq; then
        value=$(jq -r ".$key // \"$default_value\"" "$CONFIG_FILE" 2>/dev/null)
    else
        # Fallback to grep if jq is not available
        value=$(grep -o "\"$key\": [^,}]*" "$CONFIG_FILE" 2>/dev/null | sed "s/\"$key\"://;s/\"//g;s/^[ \t]*//")
        if [ -z "$value" ]; then
            value="$default_value"
        fi
    fi
    
    echo "DEBUG: Retrieved config $key = $value" >> "$DEBUG_LOG" 2>&1
    echo "$value"
}

# Function to update a configuration value
update_config_value() {
    local key=$1
    local value=$2
    
    echo "DEBUG: Updating config $key = $value" >> "$DEBUG_LOG" 2>&1
    
    if [ ! -f "$CONFIG_FILE" ]; then
        initialize_config
    fi
    
    # Check if jq is available
    if command_exists jq; then
        # Create a temporary file
        local temp_file=$(mktemp)
        
        # Determine if the value is a string, boolean, or number
        if [[ "$value" == "true" || "$value" == "false" || "$value" =~ ^[0-9]+$ ]]; then
            # Boolean or number, no quotes
            jq ".$key = $value" "$CONFIG_FILE" > "$temp_file"
        else
            # String, use quotes
            jq ".$key = \"$value\"" "$CONFIG_FILE" > "$temp_file"
        fi
        
        # Replace the original file with the updated one
        mv "$temp_file" "$CONFIG_FILE"
    else
        # Fallback to sed if jq is not available
        local pattern
        if [[ "$value" == "true" || "$value" == "false" || "$value" =~ ^[0-9]+$ ]]; then
            # Boolean or number, no quotes
            pattern="s/\"$key\": [^,}]*/\"$key\": $value/g"
        else
            # String, use quotes
            pattern="s/\"$key\": [^,}]*/\"$key\": \"$value\"/g"
        fi
        
        # Check if the key exists in the file
        if grep -q "\"$key\":" "$CONFIG_FILE"; then
            # Key exists, update it
            sed -i.bak "$pattern" "$CONFIG_FILE" && rm -f "${CONFIG_FILE}.bak"
        else
            # Key doesn't exist, add it before the last closing brace
            sed -i.bak "s/}$/,\n  \"$key\": $value\n}/" "$CONFIG_FILE" && rm -f "${CONFIG_FILE}.bak"
        fi
    fi
    
    print_status "$GREEN" "✓" "Updated configuration: $key = $value"
}

# Function to save configuration (used in start_services.sh)
save_config() {
    echo "DEBUG: Saving configuration" >> "$DEBUG_LOG" 2>&1
    
    # Get the current values
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    local verbose=$(get_config_value "verbose" "$DEFAULT_VERBOSE")
    local log_level=$(get_config_value "log_level" "$DEFAULT_LOG_LEVEL")
    local environment=$(get_config_value "environment" "$DEFAULT_ENV")
    local skip_redis=$(get_config_value "skip_redis" "false")
    
    cat > "$CONFIG_FILE" << EOL
{
    "redis_port": $redis_port,
    "api_port": $api_port,
    "frontend_port": $frontend_port,
    "verbose": $verbose,
    "log_level": "$log_level",
    "environment": "$environment",
    "skip_redis": $skip_redis,
    "max_restart_attempts": 3,
    "restart_cooldown": 30,
    "auto_open_browser": true,
    "check_updates": true
}
EOL
}

# Function to display all configuration
display_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        print_status "$YELLOW" "!" "No configuration file found. Initializing..."
        initialize_config
    fi
    
    echo -e "${CYAN}${BOLD}Current Configuration:${NC}"
    
    # Check if jq is available
    if command_exists jq; then
        echo -e "${DIM}$(jq -r 'to_entries | .[] | "  \(.key): \(.value)"' "$CONFIG_FILE" | sort)${NC}"
    else
        # Fallback to grep and formatting
        echo -e "${DIM}$(grep -o "\"[^\"]*\": [^,}]*" "$CONFIG_FILE" | sed "s/\"//g;s/: /: /g;s/^/  /")${NC}"
    fi
}

# Function to reset configuration to defaults
reset_config() {
    echo "DEBUG: Resetting configuration to defaults" >> "$DEBUG_LOG" 2>&1
    
    # Backup the existing configuration if it exists
    if [ -f "$CONFIG_FILE" ]; then
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
        echo "DEBUG: Backup created at ${CONFIG_FILE}.bak" >> "$DEBUG_LOG" 2>&1
        print_status "$BLUE" "ℹ" "Configuration backup created at ${CONFIG_FILE}.bak"
    fi
    
    # Remove the existing configuration
    rm -f "$CONFIG_FILE"
    
    # Create a new default configuration
    initialize_config
    
    print_status "$GREEN" "✓" "Configuration reset to defaults"
}

# Function to validate port configuration
validate_port() {
    local port=$1
    local service=$2
    
    # Check if port is a number
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
        print_status "$RED" "✗" "Invalid port for $service: $port (must be a number)"
        return 1
    fi
    
    # Check if port is in valid range
    if [ "$port" -lt 1024 ] || [ "$port" -gt 65535 ]; then
        print_status "$RED" "✗" "Invalid port for $service: $port (must be between 1024 and 65535)"
        return 1
    fi
    
    # Check if port is in use
    if command_exists lsof; then
        if lsof -i :"$port" > /dev/null 2>&1; then
            print_status "$YELLOW" "!" "Port $port for $service is already in use by another process"
            return 2
        fi
    elif command_exists netstat; then
        if netstat -tuln | grep -q ":$port "; then
            print_status "$YELLOW" "!" "Port $port for $service is already in use by another process"
            return 2
        fi
    fi
    
    echo "DEBUG: Port $port validated successfully for $service" >> "$DEBUG_LOG" 2>&1
    return 0
}

# Function to check for port conflicts
check_port_conflicts() {
    local port=$1
    local service=$2
    local auto_fix=${3:-false}
    local diag_mode=${4:-false}
    local result=0
    
    echo "DEBUG: Checking port conflicts for $service:$port (auto_fix=$auto_fix, diag_mode=$diag_mode)" >> "$DEBUG_LOG" 2>&1
    
    # First check if port is in use
    if lsof -i :$port > /dev/null 2>&1; then
        # If in diagnostic mode, check if it's our own service using the port
        if [ "$diag_mode" = "true" ]; then
            local pid_info=$(lsof -i :$port -sTCP:LISTEN -P -n 2>/dev/null)
            echo "DEBUG: Port $port is in use, checking if by our service" >> "$DEBUG_LOG" 2>&1
            echo "DEBUG: Process info: $pid_info" >> "$DEBUG_LOG" 2>&1
            
            # Check if it's our own service based on process name
            case "$service" in
                "Redis")
                    if echo "$pid_info" | grep -q "redis-server"; then
                        echo "DEBUG: Redis port $port is in use by our Redis service" >> "$DEBUG_LOG" 2>&1
                        # This is our Redis service, not a conflict
                        return 0
                    fi
                    ;;
                "AI Service")
                    if echo "$pid_info" | grep -q "python\|uvicorn\|ai_service"; then
                        echo "DEBUG: API port $port is in use by our AI service" >> "$DEBUG_LOG" 2>&1
                        # This is our AI service, not a conflict
                        return 0
                    fi
                    ;;
                "Frontend")
                    if echo "$pid_info" | grep -q "node\|npm\|next"; then
                        echo "DEBUG: Frontend port $port is in use by our Frontend service" >> "$DEBUG_LOG" 2>&1
                        # This is our Frontend service, not a conflict
                        return 0
                    fi
                    ;;
            esac
        fi
        
        # If we get here, either it's not diagnostic mode or the port is used by something else
        if [ "$auto_fix" = "true" ]; then
            print_status "$YELLOW" "⚠" "Port conflict detected: $service port $port is already in use. Attempting to free..."
            if smart_port_conflict_handler $port "$service"; then
                print_status "$GREEN" "✓" "Port $port successfully freed for $service"
                result=0
            elif free_port $port $service; then
                print_status "$GREEN" "✓" "Port $port successfully freed for $service"
                result=0
            else
                print_status "$RED" "✗" "Port conflict: Failed to free $service port $port"
                result=1
            fi
        else
            print_status "$RED" "⚠" "Port conflict: $service port $port is already in use"
            result=1
        fi
    fi
    
    return $result
}

# Function to free up a port if it's in use
free_port() {
    local port=$1
    local service=$2
    local attempts=0
    local max_attempts=3
    local port_freed=false
    
    echo "DEBUG: Attempting to free port $port for $service" >> "$DEBUG_LOG" 2>&1
    
    while [ $attempts -lt $max_attempts ] && [ "$port_freed" = false ]; do
        if lsof -i :$port > /dev/null 2>&1; then
            attempts=$((attempts + 1))
            if [ $attempts -eq 1 ]; then
                print_status "$YELLOW" "↻" "Freeing up port $port for $service..."
                lsof -ti :$port | xargs kill -9 >/dev/null 2>&1
            elif [ $attempts -eq 2 ]; then
                print_status "$YELLOW" "↻" "Trying with sudo to free port $port..."
                sudo lsof -ti :$port | sudo xargs kill -9 >/dev/null 2>&1
            elif [ $attempts -eq 3 ]; then
                print_status "$RED" "!" "Final attempt to free port $port..."
                # Try more aggressive approach - find and kill by port directly
                pid=$(sudo lsof -ti :$port)
                if [ -n "$pid" ]; then
                    sudo kill -9 $pid >/dev/null 2>&1
                fi
            fi
            
            # Verify if port was freed
            sleep 2
            if ! lsof -i :$port > /dev/null 2>&1; then
                port_freed=true
                print_status "$GREEN" "✓" "Successfully freed port $port for $service"
                echo "DEBUG: Port $port freed for $service after $attempts attempts" >> "$DEBUG_LOG" 2>&1
            fi
        else
            port_freed=true
            echo "DEBUG: Port $port is already free" >> "$DEBUG_LOG" 2>&1
        fi
    done
    
    if [ "$port_freed" = false ]; then
        print_status "$RED" "✗" "Failed to free port $port after multiple attempts. Please free it manually."
        echo "DEBUG: Failed to free port $port after $max_attempts attempts" >> "$DEBUG_LOG" 2>&1
        return 1
    fi
    
    return 0
}

# Function to update port configuration interactively
port_configuration_menu() {
    clear
    show_banner
    
    echo -e "${CYAN}${BOLD}Port Configuration${NC}"
    echo
    
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    
    echo -e "${BLUE}Current port settings:${NC}"
    echo -e "  1. Redis Port: ${YELLOW}$redis_port${NC}"
    echo -e "  2. API Port: ${YELLOW}$api_port${NC}"
    echo -e "  3. Frontend Port: ${YELLOW}$frontend_port${NC}"
    echo -e "  4. Return to previous menu"
    echo
    
    read -p "Enter your choice (1-4): " choice
    
    case $choice in
        1)
            read -p "Enter new Redis port (1024-65535): " new_port
            if validate_port "$new_port" "Redis"; then
                update_config_value "redis_port" "$new_port"
            fi
            port_configuration_menu
            ;;
        2)
            read -p "Enter new API port (1024-65535): " new_port
            if validate_port "$new_port" "API"; then
                update_config_value "api_port" "$new_port"
            fi
            port_configuration_menu
            ;;
        3)
            read -p "Enter new Frontend port (1024-65535): " new_port
            if validate_port "$new_port" "Frontend"; then
                update_config_value "frontend_port" "$new_port"
            fi
            port_configuration_menu
            ;;
        4)
            # Return to previous menu
            return
            ;;
        *)
            print_status "$YELLOW" "!" "Invalid choice. Please try again."
            sleep 1
            port_configuration_menu
            ;;
    esac
}

# Function to export configuration to environment variables
export_config_to_env() {
    local config_file=$1
    if [ -z "$config_file" ]; then
        config_file="$CONFIG_FILE"
    fi
    
    echo "DEBUG: Exporting configuration to environment variables" >> "$DEBUG_LOG" 2>&1
    
    # Check if the config file exists
    if [ ! -f "$config_file" ]; then
        echo "DEBUG: Config file not found. Initializing..." >> "$DEBUG_LOG" 2>&1
        initialize_config
        config_file="$CONFIG_FILE"
    fi
    
    # Export configuration values to environment variables
    export REDIS_PORT=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    export API_PORT=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    export FRONTEND_PORT=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    export VERBOSE=$(get_config_value "verbose" "$DEFAULT_VERBOSE")
    export LOG_LEVEL=$(get_config_value "log_level" "$DEFAULT_LOG_LEVEL")
    export ENVIRONMENT=$(get_config_value "environment" "$DEFAULT_ENV")
    export MAX_RESTART_ATTEMPTS=$(get_config_value "max_restart_attempts" "3")
    export RESTART_COOLDOWN=$(get_config_value "restart_cooldown" "30")
    export AUTO_OPEN_BROWSER=$(get_config_value "auto_open_browser" "true")
    export CHECK_UPDATES=$(get_config_value "check_updates" "true")
    export SKIP_REDIS=$(get_config_value "skip_redis" "false")
    
    echo "DEBUG: Configuration exported to environment" >> "$DEBUG_LOG" 2>&1
}

# Function to load configuration from config file (backward compatibility)
load_config() {
    ensure_log_files
    echo "DEBUG: Loading configuration" >> "$DEBUG_LOG" 2>&1
    
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "DEBUG: Config file not found, creating default" >> "$DEBUG_LOG" 2>&1
        create_default_config
    fi
    
    # Apply settings from configuration (this is now done via export_config_to_env)
    export_config_to_env
    
    echo "DEBUG: Configuration loaded" >> "$DEBUG_LOG" 2>&1
}

# Function to setup environment configuration
setup_environment() {
    echo "DEBUG: Setting up environment" >> "$DEBUG_LOG" 2>&1
    
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    
    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        echo "DEBUG: Creating .env file" >> "$DEBUG_LOG" 2>&1
        cat > .env << EOL
NEXT_PUBLIC_API_URL=http://localhost:${api_port}
REDIS_URL=redis://redis:${redis_port}
GPU_ENABLED=false
EOL
    else
        echo "DEBUG: Updating .env file" >> "$DEBUG_LOG" 2>&1
        # Update ports in .env if they exist
        if grep -q "NEXT_PUBLIC_API_URL" .env; then
            sed -i.bak "s|NEXT_PUBLIC_API_URL=http://localhost:[0-9]*|NEXT_PUBLIC_API_URL=http://localhost:${api_port}|g" .env
        fi
        if grep -q "REDIS_URL" .env; then
            sed -i.bak "s|REDIS_URL=redis://redis:[0-9]*|REDIS_URL=redis://redis:${redis_port}|g" .env
        fi
        rm -f .env.bak >/dev/null 2>&1
    fi
    
    # Create Python virtual environment if needed
    if [ ! -d .venv ]; then
        echo "DEBUG: Creating Python virtual environment" >> "$DEBUG_LOG" 2>&1
        python3 -m venv .venv >/dev/null 2>&1
    fi
    
    # Create required directories
    echo "DEBUG: Creating required directories" >> "$DEBUG_LOG" 2>&1
    mkdir -p ai_service/api >/dev/null 2>&1
    touch ai_service/__init__.py >/dev/null 2>&1
    touch ai_service/api/__init__.py >/dev/null 2>&1
    
    echo "DEBUG: Environment setup completed" >> "$DEBUG_LOG" 2>&1
    return 0
}
