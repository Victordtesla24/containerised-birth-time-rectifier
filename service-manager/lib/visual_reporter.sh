#!/bin/bash

# ===========================================
# Visual Reporting and Dashboard Functions
# ===========================================

# Source common functions and configuration
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LIB_DIR/common.sh"
source "$LIB_DIR/config.sh"

# Function to draw a horizontal line
draw_horizontal_line() {
    local width=${1:-$TERMINAL_WIDTH}
    local char=${2:-"─"}
    
    printf "%${width}s" | tr " " "$char"
    echo
}

# Function to draw a box with title
draw_box() {
    local title=$1
    local content=$2
    local width=${3:-$TERMINAL_WIDTH}
    local padding=${4:-1}
    
    # Calculate usable width
    local usable_width=$((width - 2))
    
    # Draw top border
    echo -n "┌"
    printf "%${usable_width}s" | tr " " "─"
    echo "┐"
    
    # Draw title if provided
    if [ -n "$title" ]; then
        echo -n "│"
        
        # Calculate padding for title
        local title_len=${#title}
        local left_padding=$(( (usable_width - title_len) / 2 ))
        local right_padding=$(( usable_width - title_len - left_padding ))
        
        printf "%${left_padding}s" ""
        echo -n "$title"
        printf "%${right_padding}s" ""
        
        echo "│"
        
        # Draw separator
        echo -n "├"
        printf "%${usable_width}s" | tr " " "─"
        echo "┤"
    fi
    
    # Draw content with padding
    echo "$content" | while IFS= read -r line; do
        echo -n "│"
        
        # Add left padding
        printf "%${padding}s" ""
        
        # Print line with right padding
        local line_len=${#line}
        echo -n "$line"
        local right_padding=$((usable_width - line_len - padding))
        printf "%${right_padding}s" ""
        
        echo "│"
    done
    
    # Draw bottom border
    echo -n "└"
    printf "%${usable_width}s" | tr " " "─"
    echo "┘"
}

# Function to draw a progress bar
draw_progress_bar() {
    local value=$1
    local max_value=$2
    local width=${3:-50}
    local title=${4:-""}
    
    # Calculate percentage
    local percentage=$((value * 100 / max_value))
    
    # Calculate filled width
    local filled_width=$((value * width / max_value))
    local empty_width=$((width - filled_width))
    
    # Determine color based on percentage
    local color=$GREEN
    if [ "$percentage" -lt 30 ]; then
        color=$RED
    elif [ "$percentage" -lt 70 ]; then
        color=$YELLOW
    fi
    
    # Draw title if provided
    if [ -n "$title" ]; then
        echo -n "$title: "
    fi
    
    # Draw progress bar
    echo -n "["
    printf "${color}%${filled_width}s${NC}" | tr " " "$FILL_CHAR"
    printf "%${empty_width}s" | tr " " "$EMPTY_CHAR"
    echo -n "] "
    
    # Draw percentage
    echo -e "${color}${percentage}%${NC}"
}

# Function to draw a horizontal bar chart
draw_horizontal_bar_chart() {
    local title=$1
    local labels=("${!2}")
    local values=("${!3}")
    local max_value=${4:-100}
    local width=${5:-40}
    
    # Draw title
    echo -e "${BOLD}${title}${NC}"
    
    # Draw bars
    local i=0
    while [ $i -lt ${#labels[@]} ]; do
        local label="${labels[$i]}"
        local value="${values[$i]}"
        
        # Calculate percentage
        local percentage=$((value * 100 / max_value))
        
        # Calculate bar width
        local bar_width=$((value * width / max_value))
        
        # Determine color based on percentage
        local color=$GREEN
        if [ "$percentage" -lt 30 ]; then
            color=$RED
        elif [ "$percentage" -lt 70 ]; then
            color=$YELLOW
        fi
        
        # Print label with padding
        printf "%-15s" "$label"
        
        # Print bar
        printf "${color}%${bar_width}s${NC}" | tr " " "█"
        
        # Print value
        echo -e " ${color}${value}${NC}"
        
        i=$((i + 1))
    done
}

# Function to draw a table
draw_table() {
    local title=$1
    local headers=("${!2}")
    local rows=("${!3}")
    local num_columns=${#headers[@]}
    local num_rows=${#rows[@]}
    local column_widths=()
    
    # Calculate column widths
    for ((i=0; i<num_columns; i++)); do
        local max_width=${#headers[$i]}
        
        for ((j=0; j<num_rows; j++)); do
            local index=$((j * num_columns + i))
            local cell_width=${#rows[$index]}
            
            if [ "$cell_width" -gt "$max_width" ]; then
                max_width=$cell_width
            fi
        done
        
        column_widths+=($max_width)
    done
    
    # Draw title
    if [ -n "$title" ]; then
        echo -e "${BOLD}${title}${NC}"
    fi
    
    # Draw top border
    echo -n "┌"
    for ((i=0; i<num_columns; i++)); do
        local width=${column_widths[$i]}
        printf "%$(($width + 2))s" | tr " " "─"
        
        if [ $i -lt $((num_columns - 1)) ]; then
            echo -n "┬"
        fi
    done
    echo "┐"
    
    # Draw headers
    echo -n "│"
    for ((i=0; i<num_columns; i++)); do
        local header=${headers[$i]}
        local width=${column_widths[$i]}
        
        printf " %-${width}s " "$header"
        echo -n "│"
    done
    echo
    
    # Draw header separator
    echo -n "├"
    for ((i=0; i<num_columns; i++)); do
        local width=${column_widths[$i]}
        printf "%$(($width + 2))s" | tr " " "─"
        
        if [ $i -lt $((num_columns - 1)) ]; then
            echo -n "┼"
        fi
    done
    echo "┤"
    
    # Draw rows
    for ((j=0; j<num_rows; j++)); do
        echo -n "│"
        
        for ((i=0; i<num_columns; i++)); do
            local index=$((j * num_columns + i))
            local cell=${rows[$index]}
            local width=${column_widths[$i]}
            
            printf " %-${width}s " "$cell"
            echo -n "│"
        done
        
        echo
    done
    
    # Draw bottom border
    echo -n "└"
    for ((i=0; i<num_columns; i++)); do
        local width=${column_widths[$i]}
        printf "%$(($width + 2))s" | tr " " "─"
        
        if [ $i -lt $((num_columns - 1)) ]; then
            echo -n "┴"
        fi
    done
    echo "┘"
}

# Function to draw a service status dashboard
draw_service_status_dashboard() {
    clear
    show_banner
    
    echo -e "${CYAN}${BOLD}Service Status Dashboard${NC}"
    echo
    
    # Get current timestamp
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${DIM}Last updated: $timestamp${NC}"
    echo
    
    # Draw system resources section
    echo -e "${BLUE}${BOLD}System Resources${NC}"
    draw_horizontal_line
    
    # Get system resources
    local resources=$(get_system_resources)
    local cpu_usage=$(echo $resources | cut -d'|' -f1)
    local memory_usage=$(echo $resources | cut -d'|' -f2)
    local disk_usage=$(echo $resources | cut -d'|' -f3)
    
    # Extract numeric values for progress bars
    local cpu_value=$(echo $cpu_usage | grep -o '[0-9]\+' | head -1)
    local memory_value=$(echo $memory_usage | grep -o '[0-9]\+' | head -1)
    local disk_value=$(echo $disk_usage | grep -o '[0-9]\+' | head -1)
    
    # Draw progress bars
    draw_progress_bar ${cpu_value:-0} 100 40 "CPU Usage"
    draw_progress_bar ${memory_value:-0} 100 40 "Memory Usage"
    draw_progress_bar ${disk_value:-0} 100 40 "Disk Usage"
    
    echo
    
    # Draw service status section
    echo -e "${BLUE}${BOLD}Service Status${NC}"
    draw_horizontal_line
    
    # Get service status
    local redis_status=$(check_service_running "REDIS" && echo "Running" || echo "Stopped")
    local ai_service_status=$(check_service_running "AI_SERVICE" && echo "Running" || echo "Stopped")
    local frontend_status=$(check_service_running "FRONTEND" && echo "Running" || echo "Stopped")
    
    # Get service ports
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    
    # Create table headers and rows
    local headers=("Service" "Status" "Port" "Uptime" "Restarts")
    local rows=(
        "Redis" "$(colorize_status "$redis_status")" "$redis_port" "$(get_service_uptime "REDIS")" "$REDIS_RESTART_COUNT"
        "AI Service" "$(colorize_status "$ai_service_status")" "$api_port" "$(get_service_uptime "AI_SERVICE")" "$AI_SERVICE_RESTART_COUNT"
        "Frontend" "$(colorize_status "$frontend_status")" "$frontend_port" "$(get_service_uptime "FRONTEND")" "$FRONTEND_RESTART_COUNT"
    )
    
    # Draw table
    draw_table "Service Status" headers[@] rows[@]
    
    echo
    
    # Draw health check section
    echo -e "${BLUE}${BOLD}Health Checks${NC}"
    draw_horizontal_line
    
    # Perform health checks
    local redis_health=$(verify_service_health "REDIS" && echo "Healthy" || echo "Unhealthy")
    local ai_service_health=$(verify_service_health "AI_SERVICE" && echo "Healthy" || echo "Unhealthy")
    local frontend_health=$(verify_service_health "FRONTEND" && echo "Healthy" || echo "Unhealthy")
    
    # Create table headers and rows
    local health_headers=("Service" "Health Status" "Endpoint")
    local health_rows=(
        "Redis" "$(colorize_status "$redis_health")" "redis://localhost:$redis_port"
        "AI Service" "$(colorize_status "$ai_service_health")" "http://localhost:$api_port/health"
        "Frontend" "$(colorize_status "$frontend_health")" "http://localhost:$frontend_port"
    )
    
    # Draw table
    draw_table "Health Checks" health_headers[@] health_rows[@]
    
    echo
    echo -e "${DIM}Press any key to return to menu...${NC}"
    read -n 1
}

# Function to colorize status text
colorize_status() {
    local status=$1
    
    case "$status" in
        "Running"|"Healthy")
            echo -e "${GREEN}$status${NC}"
            ;;
        "Stopped"|"Unhealthy")
            echo -e "${RED}$status${NC}"
            ;;
        *)
            echo -e "${YELLOW}$status${NC}"
            ;;
    esac
}

# Function to draw a diagnostic report
draw_diagnostic_report() {
    clear
    show_banner
    
    echo -e "${CYAN}${BOLD}Diagnostic Report${NC}"
    echo
    
    # Get current timestamp
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${DIM}Report generated: $timestamp${NC}"
    echo
    
    # Draw system information section
    echo -e "${BLUE}${BOLD}System Information${NC}"
    draw_horizontal_line
    
    # Get system information
    local os_info=$(uname -s)
    local os_version=$(uname -r)
    local hostname=$(hostname)
    
    # Create content for box
    local system_info_content="Operating System: $os_info $os_version
Hostname: $hostname
Terminal Size: ${TERMINAL_WIDTH}x$(tput lines 2>/dev/null || echo "N/A")"
    
    # Draw box
    draw_box "System Information" "$system_info_content"
    
    echo
    
    # Draw system resources section
    echo -e "${BLUE}${BOLD}System Resources${NC}"
    draw_horizontal_line
    
    # Get system resources
    local resources=$(get_system_resources)
    local cpu_usage=$(echo $resources | cut -d'|' -f1)
    local memory_usage=$(echo $resources | cut -d'|' -f2)
    local disk_usage=$(echo $resources | cut -d'|' -f3)
    
    # Create content for box
    local resources_content="CPU Usage: $cpu_usage
Memory Usage: $memory_usage
Disk Usage: $disk_usage"
    
    # Draw box
    draw_box "System Resources" "$resources_content"
    
    echo
    
    # Draw dependencies section
    echo -e "${BLUE}${BOLD}Dependencies${NC}"
    draw_horizontal_line
    
    # Check dependencies
    local dependencies=("bash" "grep" "sed" "awk" "ps" "kill" "curl" "jq" "docker" "docker-compose" "node" "npm" "python3" "redis-server")
    local dependency_status=()
    
    for dep in "${dependencies[@]}"; do
        if command_exists "$dep"; then
            local version=""
            
            # Get version information if available
            case "$dep" in
                "docker")
                    version=$(docker --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
                    ;;
                "docker-compose")
                    version=$(docker-compose --version 2>/dev/null | cut -d' ' -f3 | tr -d ',')
                    ;;
                "node")
                    version=$(node --version 2>/dev/null | tr -d 'v')
                    ;;
                "npm")
                    version=$(npm --version 2>/dev/null)
                    ;;
                "python3")
                    version=$(python3 --version 2>&1 | cut -d' ' -f2)
                    ;;
                "redis-server")
                    version=$(redis-server --version 2>&1 | cut -d'=' -f2 | cut -d' ' -f1)
                    ;;
            esac
            
            if [ -n "$version" ]; then
                dependency_status+=("$dep" "Installed" "$version")
            else
                dependency_status+=("$dep" "Installed" "N/A")
            fi
        else
            dependency_status+=("$dep" "Not Installed" "N/A")
        fi
    done
    
    # Create table headers
    local dep_headers=("Dependency" "Status" "Version")
    
    # Draw table
    draw_table "Dependencies" dep_headers[@] dependency_status[@]
    
    echo
    
    # Draw port status section
    echo -e "${BLUE}${BOLD}Port Status${NC}"
    draw_horizontal_line
    
    # Get port information
    local redis_port=$(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
    local api_port=$(get_config_value "api_port" "$DEFAULT_API_PORT")
    local frontend_port=$(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
    
    # Check port status
    local port_status=()
    
    # Check Redis port
    if lsof -i :$redis_port >/dev/null 2>&1; then
        local pid=$(lsof -ti :$redis_port 2>/dev/null)
        local process=$(ps -p $pid -o comm= 2>/dev/null || echo "Unknown")
        port_status+=("Redis" "$redis_port" "In Use" "$process ($pid)")
    else
        port_status+=("Redis" "$redis_port" "Available" "N/A")
    fi
    
    # Check API port
    if lsof -i :$api_port >/dev/null 2>&1; then
        local pid=$(lsof -ti :$api_port 2>/dev/null)
        local process=$(ps -p $pid -o comm= 2>/dev/null || echo "Unknown")
        port_status+=("AI Service" "$api_port" "In Use" "$process ($pid)")
    else
        port_status+=("AI Service" "$api_port" "Available" "N/A")
    fi
    
    # Check Frontend port
    if lsof -i :$frontend_port >/dev/null 2>&1; then
        local pid=$(lsof -ti :$frontend_port 2>/dev/null)
        local process=$(ps -p $pid -o comm= 2>/dev/null || echo "Unknown")
        port_status+=("Frontend" "$frontend_port" "In Use" "$process ($pid)")
    else
        port_status+=("Frontend" "$frontend_port" "Available" "N/A")
    fi
    
    # Create table headers
    local port_headers=("Service" "Port" "Status" "Process")
    
    # Draw table
    draw_table "Port Status" port_headers[@] port_status[@]
    
    echo
    
    # Draw service status section
    echo -e "${BLUE}${BOLD}Service Status${NC}"
    draw_horizontal_line
    
    # Check service status
    local service_status=()
    
    # Check Redis
    if check_service_running "REDIS"; then
        service_status+=("Redis" "Running" "$(get_service_uptime "REDIS")" "$REDIS_RESTART_COUNT")
    else
        service_status+=("Redis" "Stopped" "N/A" "$REDIS_RESTART_COUNT")
    fi
    
    # Check AI Service
    if check_service_running "AI_SERVICE"; then
        service_status+=("AI Service" "Running" "$(get_service_uptime "AI_SERVICE")" "$AI_SERVICE_RESTART_COUNT")
    else
        service_status+=("AI Service" "Stopped" "N/A" "$AI_SERVICE_RESTART_COUNT")
    fi
    
    # Check Frontend
    if check_service_running "FRONTEND"; then
        service_status+=("Frontend" "Running" "$(get_service_uptime "FRONTEND")" "$FRONTEND_RESTART_COUNT")
    else
        service_status+=("Frontend" "Stopped" "N/A" "$FRONTEND_RESTART_COUNT")
    fi
    
    # Create table headers
    local service_headers=("Service" "Status" "Uptime" "Restarts")
    
    # Draw table
    draw_table "Service Status" service_headers[@] service_status[@]
    
    echo
    
    # Draw log files section
    echo -e "${BLUE}${BOLD}Log Files${NC}"
    draw_horizontal_line
    
    # Check log files
    local log_files=()
    
    # Check Redis log
    if [ -f "$REDIS_LOG" ]; then
        local size=$(du -h "$REDIS_LOG" | cut -f1)
        local last_modified=$(date -r "$REDIS_LOG" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c "%y" "$REDIS_LOG" 2>/dev/null || echo "Unknown")
        log_files+=("Redis" "$REDIS_LOG" "$size" "$last_modified")
    else
        log_files+=("Redis" "$REDIS_LOG" "Not Found" "N/A")
    fi
    
    # Check AI Service log
    if [ -f "$AI_SERVICE_LOG" ]; then
        local size=$(du -h "$AI_SERVICE_LOG" | cut -f1)
        local last_modified=$(date -r "$AI_SERVICE_LOG" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c "%y" "$AI_SERVICE_LOG" 2>/dev/null || echo "Unknown")
        log_files+=("AI Service" "$AI_SERVICE_LOG" "$size" "$last_modified")
    else
        log_files+=("AI Service" "$AI_SERVICE_LOG" "Not Found" "N/A")
    fi
    
    # Check Frontend log
    if [ -f "$FRONTEND_LOG" ]; then
        local size=$(du -h "$FRONTEND_LOG" | cut -f1)
        local last_modified=$(date -r "$FRONTEND_LOG" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c "%y" "$FRONTEND_LOG" 2>/dev/null || echo "Unknown")
        log_files+=("Frontend" "$FRONTEND_LOG" "$size" "$last_modified")
    else
        log_files+=("Frontend" "$FRONTEND_LOG" "Not Found" "N/A")
    fi
    
    # Check Error log
    if [ -f "$ERROR_LOG" ]; then
        local size=$(du -h "$ERROR_LOG" | cut -f1)
        local last_modified=$(date -r "$ERROR_LOG" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c "%y" "$ERROR_LOG" 2>/dev/null || echo "Unknown")
        log_files+=("Error" "$ERROR_LOG" "$size" "$last_modified")
    else
        log_files+=("Error" "$ERROR_LOG" "Not Found" "N/A")
    fi
    
    # Check Debug log
    if [ -f "$DEBUG_LOG" ]; then
        local size=$(du -h "$DEBUG_LOG" | cut -f1)
        local last_modified=$(date -r "$DEBUG_LOG" "+%Y-%m-%d %H:%M:%S" 2>/dev/null || stat -c "%y" "$DEBUG_LOG" 2>/dev/null || echo "Unknown")
        log_files+=("Debug" "$DEBUG_LOG" "$size" "$last_modified")
    else
        log_files+=("Debug" "$DEBUG_LOG" "Not Found" "N/A")
    fi
    
    # Create table headers
    local log_headers=("Service" "Log File" "Size" "Last Modified")
    
    # Draw table
    draw_table "Log Files" log_headers[@] log_files[@]
    
    echo
    
    # Draw summary section
    echo -e "${BLUE}${BOLD}Summary${NC}"
    draw_horizontal_line
    
    # Count issues
    local critical_issues=0
    local warnings=0
    
    # Check for critical issues
    if ! check_service_running "REDIS" && ! $(get_config_value "skip_redis" "false"); then
        critical_issues=$((critical_issues + 1))
    fi
    
    if ! check_service_running "AI_SERVICE"; then
        critical_issues=$((critical_issues + 1))
    fi
    
    if ! check_service_running "FRONTEND"; then
        critical_issues=$((critical_issues + 1))
    fi
    
    # Check for warnings
    if ! command_exists "docker" || ! command_exists "docker-compose"; then
        warnings=$((warnings + 1))
    fi
    
    if ! command_exists "python3"; then
        warnings=$((warnings + 1))
    fi
    
    if ! command_exists "node" || ! command_exists "npm"; then
        warnings=$((warnings + 1))
    fi
    
    # Create content for box
    local summary_content="Critical Issues: $critical_issues
Warnings: $warnings
Services Running: $((3 - critical_issues))/3
Dependencies Installed: $((${#dependencies[@]} - warnings))/${#dependencies[@]}"
    
    # Draw box
    draw_box "Diagnostic Summary" "$summary_content"
    
    echo
    echo -e "${DIM}Press any key to return to menu...${NC}"
    read -n 1
}

# Function to run enhanced diagnostics
run_enhanced_diagnostics() {
    # Run diagnostics and display report
    draw_diagnostic_report
}

# Function to display service status dashboard
display_service_dashboard() {
    # Display service status dashboard
    draw_service_status_dashboard
}
