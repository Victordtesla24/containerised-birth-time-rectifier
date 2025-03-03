#!/bin/bash

# ===========================================
# Service Health Monitoring Functions
# ===========================================

# Source common functions and configuration
LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$LIB_DIR/common.sh"
source "$LIB_DIR/config.sh"
source "$LIB_DIR/error_handler.sh"

# Global variables for monitoring
MONITOR_INTERVAL=10  # Check interval in seconds
MONITOR_RUNNING=false
MONITOR_PID=""

# Service health status
REDIS_HEALTH_STATUS="unknown"
AI_SERVICE_HEALTH_STATUS="unknown"
FRONTEND_HEALTH_STATUS="unknown"

# Service uptime tracking
REDIS_START_TIME=0
AI_SERVICE_START_TIME=0
FRONTEND_START_TIME=0

# Service restart counts
REDIS_RESTART_COUNT=0
AI_SERVICE_RESTART_COUNT=0
FRONTEND_RESTART_COUNT=0

# Function to get service uptime
get_service_uptime() {
    local service=$1
    local start_time_var="${service}_START_TIME"
    local start_time=${!start_time_var}
    
    if [ "$start_time" -eq 0 ]; then
        echo "N/A"
        return
    fi
    
    local current_time=$(date +%s)
    local uptime=$((current_time - start_time))
    
    # Format uptime as HH:MM:SS
    printf "%02d:%02d:%02d" $((uptime/3600)) $((uptime%3600/60)) $((uptime%60))
}

# Function to check service health
check_service_health_status() {
    local service=$1
    local previous_status_var="${service}_HEALTH_STATUS"
    local previous_status=${!previous_status_var}
    local current_status="unknown"
    
    echo "DEBUG: Checking health status for $service (previous: $previous_status)" >> "$DEBUG_LOG" 2>&1
    
    # Check if service is running and healthy
    if verify_service_health "$service"; then
        current_status="healthy"
    elif check_service_running "$service"; then
        current_status="running"
    else
        current_status="stopped"
    fi
    
    # Update global status variable
    eval "${service}_HEALTH_STATUS=\"$current_status\""
    
    # Return status change
    if [ "$previous_status" != "$current_status" ]; then
        echo "changed:$previous_status:$current_status"
    else
        echo "unchanged:$current_status"
    fi
}

# Function to display service health status with color
display_service_health() {
    local service=$1
    local status=$2
    local service_name=""
    
    # Get service display name
    case "$service" in
        "REDIS")
            service_name="Redis"
            ;;
        "AI_SERVICE")
            service_name="AI Service"
            ;;
        "FRONTEND")
            service_name="Frontend"
            ;;
        *)
            service_name="$service"
            ;;
    esac
    
    # Display status with appropriate color
    case "$status" in
        "healthy")
            print_status "$GREEN" "✓" "$service_name is healthy"
            ;;
        "running")
            print_status "$YELLOW" "⚠" "$service_name is running but may not be healthy"
            ;;
        "stopped")
            print_status "$RED" "✗" "$service_name is not running"
            ;;
        *)
            print_status "$BLUE" "?" "$service_name status is unknown"
            ;;
    esac
    
    # Display additional information
    local uptime=$(get_service_uptime "$service")
    local restart_count_var="${service}_RESTART_COUNT"
    local restart_count=${!restart_count_var}
    
    echo -e "   ${DIM}Uptime: $uptime | Restarts: $restart_count${NC}"
}

# Function to handle service health change
handle_service_health_change() {
    local service=$1
    local previous_status=$2
    local current_status=$3
    
    echo "DEBUG: Service health change for $service: $previous_status -> $current_status" >> "$DEBUG_LOG" 2>&1
    
    # Handle status change based on current status
    case "$current_status" in
        "stopped")
            # Service stopped unexpectedly
            if [ "$previous_status" == "healthy" ] || [ "$previous_status" == "running" ]; then
                print_status "$RED" "!" "$service stopped unexpectedly. Attempting to restart..."
                
                # Increment restart counter
                local restart_count_var="${service}_RESTART_COUNT"
                eval "$restart_count_var=\$((\${$restart_count_var} + 1))"
                
                # Restart the service
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
                esac
            fi
            ;;
        
        "running")
            # Service is running but not healthy
            if [ "$previous_status" == "healthy" ]; then
                print_status "$YELLOW" "⚠" "$service is running but may not be healthy. Checking for issues..."
                
                # Check for issues and try to fix
                fix_and_restart_service "$service"
            elif [ "$previous_status" == "stopped" ] || [ "$previous_status" == "unknown" ]; then
                print_status "$YELLOW" "↻" "$service started but may not be fully healthy yet. Monitoring..."
            fi
            ;;
        
        "healthy")
            # Service is now healthy
            if [ "$previous_status" != "healthy" ]; then
                print_status "$GREEN" "✓" "$service is now healthy"
                
                # Update start time if it was previously stopped
                if [ "$previous_status" == "stopped" ] || [ "$previous_status" == "unknown" ]; then
                    local start_time_var="${service}_START_TIME"
                    eval "$start_time_var=$(date +%s)"
                fi
            fi
            ;;
    esac
}

# Function to monitor all services
monitor_all_services() {
    local redis_status=""
    local ai_service_status=""
    local frontend_status=""
    
    # Check Redis health
    redis_status=$(check_service_health_status "REDIS")
    local redis_changed=$(echo "$redis_status" | cut -d':' -f1)
    
    if [ "$redis_changed" == "changed" ]; then
        local redis_previous=$(echo "$redis_status" | cut -d':' -f2)
        local redis_current=$(echo "$redis_status" | cut -d':' -f3)
        handle_service_health_change "REDIS" "$redis_previous" "$redis_current"
    fi
    
    # Check AI Service health
    ai_service_status=$(check_service_health_status "AI_SERVICE")
    local ai_service_changed=$(echo "$ai_service_status" | cut -d':' -f1)
    
    if [ "$ai_service_changed" == "changed" ]; then
        local ai_service_previous=$(echo "$ai_service_status" | cut -d':' -f2)
        local ai_service_current=$(echo "$ai_service_status" | cut -d':' -f3)
        handle_service_health_change "AI_SERVICE" "$ai_service_previous" "$ai_service_current"
    fi
    
    # Check Frontend health
    frontend_status=$(check_service_health_status "FRONTEND")
    local frontend_changed=$(echo "$frontend_status" | cut -d':' -f1)
    
    if [ "$frontend_changed" == "changed" ]; then
        local frontend_previous=$(echo "$frontend_status" | cut -d':' -f2)
        local frontend_current=$(echo "$frontend_status" | cut -d':' -f3)
        handle_service_health_change "FRONTEND" "$frontend_previous" "$frontend_current"
    fi
}

# Function to display service health dashboard
display_health_dashboard() {
    clear
    show_banner
    
    echo -e "${CYAN}${BOLD}Service Health Monitor${NC}"
    echo -e "${DIM}Press 'q' to exit monitoring${NC}"
    echo
    
    # Display system information
    echo -e "${BLUE}${BOLD}System Information:${NC}"
    echo -e "  ${DIM}Monitoring Interval: ${MONITOR_INTERVAL}s${NC}"
    echo -e "  ${DIM}Monitor Running Time: $(get_monitor_uptime)${NC}"
    echo
    
    # Display service health status
    echo -e "${BLUE}${BOLD}Service Health:${NC}"
    
    # Redis
    display_service_health "REDIS" "$REDIS_HEALTH_STATUS"
    
    # AI Service
    display_service_health "AI_SERVICE" "$AI_SERVICE_HEALTH_STATUS"
    
    # Frontend
    display_service_health "FRONTEND" "$FRONTEND_HEALTH_STATUS"
    
    echo
    echo -e "${YELLOW}Press 'q' to exit monitoring...${NC}"
}

# Function to get monitor uptime
get_monitor_uptime() {
    local current_time=$(date +%s)
    local uptime=$((current_time - MONITOR_START_TIME))
    
    # Format uptime as HH:MM:SS
    printf "%02d:%02d:%02d" $((uptime/3600)) $((uptime%3600/60)) $((uptime%60))
}

# Function to start monitoring services
start_monitoring() {
    if $MONITOR_RUNNING; then
        print_status "$YELLOW" "!" "Monitoring is already running"
        return
    fi
    
    MONITOR_RUNNING=true
    MONITOR_START_TIME=$(date +%s)
    
    # Reset health status
    REDIS_HEALTH_STATUS="unknown"
    AI_SERVICE_HEALTH_STATUS="unknown"
    FRONTEND_HEALTH_STATUS="unknown"
    
    # Start monitoring in background
    monitor_services_background &
    MONITOR_PID=$!
    
    print_status "$GREEN" "✓" "Service monitoring started (PID: $MONITOR_PID)"
}

# Function to stop monitoring services
stop_monitoring() {
    if ! $MONITOR_RUNNING; then
        print_status "$YELLOW" "!" "Monitoring is not running"
        return
    fi
    
    # Kill monitoring process
    if [ -n "$MONITOR_PID" ]; then
        kill $MONITOR_PID >/dev/null 2>&1
    fi
    
    MONITOR_RUNNING=false
    MONITOR_PID=""
    
    print_status "$BLUE" "ℹ" "Service monitoring stopped"
}

# Function to monitor services in background
monitor_services_background() {
    # Save terminal settings
    local old_tty_settings=$(stty -g 2>/dev/null || echo "")
    
    # Set terminal to raw mode if possible
    if [ -n "$old_tty_settings" ]; then
        stty raw -echo min 0 time 0 2>/dev/null || true
    fi
    
    # Initialize monitoring
    local monitor_running=true
    local last_check_time=0
    
    while $monitor_running; do
        # Get current time
        local current_time=$(date +%s)
        
        # Check if it's time to monitor services
        if [ $((current_time - last_check_time)) -ge $MONITOR_INTERVAL ]; then
            # Monitor services
            monitor_all_services
            
            # Update last check time
            last_check_time=$current_time
        fi
        
        # Display dashboard
        display_health_dashboard
        
        # Check for user input (non-blocking)
        local input=""
        read -t 0 input
        
        # Process input
        if [[ "$input" == "q" || "$input" == "Q" ]]; then
            monitor_running=false
        fi
        
        # Sleep briefly to avoid high CPU usage
        sleep 0.5
    done
    
    # Restore terminal settings if possible
    if [ -n "$old_tty_settings" ]; then
        stty "$old_tty_settings" 2>/dev/null || true
    fi
    
    # Signal that monitoring has stopped
    MONITOR_RUNNING=false
}

# Function to run continuous monitoring with auto-recovery
run_continuous_monitoring() {
    # Start monitoring
    start_monitoring
    
    # Display initial message
    print_status "$BLUE" "ℹ" "Continuous monitoring started. Press Ctrl+C to stop."
    
    # Wait for monitoring to finish
    while $MONITOR_RUNNING; do
        sleep 1
    done
    
    # Cleanup
    stop_monitoring
}
