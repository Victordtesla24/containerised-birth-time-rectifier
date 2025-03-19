#!/bin/bash

# ===========================================
# Service Manager - Main Script
# ===========================================

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source all library scripts
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/config.sh"
source "$SCRIPT_DIR/lib/services.sh"
source "$SCRIPT_DIR/lib/diagnostics.sh"
source "$SCRIPT_DIR/lib/error_handler.sh"
source "$SCRIPT_DIR/lib/health_monitor.sh"
source "$SCRIPT_DIR/lib/visual_reporter.sh"

# Function to check dependencies
check_dependencies() {
    ensure_log_dir

    echo "DEBUG: Checking dependencies" >> "$DEBUG_LOG" 2>&1

    # Check for required commands
    local required_commands=("bash" "grep" "sed" "awk" "ps" "kill")
    local missing_commands=()

    for cmd in "${required_commands[@]}"; do
        if ! command_exists "$cmd"; then
            missing_commands+=("$cmd")
        fi
    done

    if [ ${#missing_commands[@]} -gt 0 ]; then
        echo "ERROR: Missing required dependencies: ${missing_commands[*]}" >> "$ERROR_LOG" 2>&1
        print_status "$RED" "✗" "Missing required dependencies: ${missing_commands[*]}"
        print_status "$RED" "✗" "Please install these dependencies and try again."
        exit 1
    fi

    # Initialize configuration
    initialize_config
}

# Function to prepare system for service startup
# This ensures no conflicting processes are running on required ports
prepare_system_for_services() {
    print_status "$BLUE" "ℹ" "Preparing system for services..."

    # Kill any processes on the service ports (8000, 3000, 9000)
    force_kill_port_processes 8000 3000 9000

    print_status "$GREEN" "✓" "System prepared for service startup"
}

# Function to start all services with preparation
start_all_services() {
    # First, prepare the system by killing any processes on the required ports
    prepare_system_for_services

    # Start Redis if not already running
    if ! check_service_running "REDIS"; then
        start_redis
    else
        print_status "$BLUE" "ℹ" "Redis is already running"
    fi

    # Start AI Service if not already running
    if ! check_service_running "AI_SERVICE"; then
        start_ai_service
    else
        print_status "$BLUE" "ℹ" "AI Service is already running"
    fi

    # Start Frontend if not already running
    if ! check_service_running "FRONTEND"; then
        start_frontend
    else
        print_status "$BLUE" "ℹ" "Frontend is already running"
    fi

    print_status "$GREEN" "✓" "All services started"
}

# Function to clean temporary files
clean_temporary_files() {
    echo "DEBUG: Cleaning temporary files" >> "$DEBUG_LOG" 2>&1

    print_status "$YELLOW" "⚙" "Cleaning temporary files..."

    # Clean up progress counter
    rm -f /tmp/progress_step

    # Clean up any other temporary files that might be created by the script
    rm -f /tmp/service_manager_*

    print_status "$GREEN" "✓" "Temporary files cleaned"
}

# Function to toggle verbose mode
toggle_verbose_mode() {
    local current_verbose=$(get_config_value "verbose" "$DEFAULT_VERBOSE")

    if [ "$current_verbose" == "true" ]; then
        update_config_value "verbose" "false"
        print_status "$BLUE" "ℹ" "Verbose mode disabled"
    else
        update_config_value "verbose" "true"
        print_status "$BLUE" "ℹ" "Verbose mode enabled"
    fi
}

# Function to handle advanced options menu
advanced_menu() {
    while true; do
        clear
        show_banner

        echo -e "${CYAN}${BOLD}Advanced Options${NC}"
        echo

        local verbose_status=$(get_config_value "verbose" "$DEFAULT_VERBOSE")
        local verbose_display=$([ "$verbose_status" == "true" ] && echo "${GREEN}Enabled${NC}" || echo "${YELLOW}Disabled${NC}")

        echo -e "${BLUE}Available options:${NC}"
        echo -e "  1. Service Management"
        echo -e "  2. Port Configuration"
        echo -e "  3. Toggle Verbose Mode (Currently: $verbose_display)"
        echo -e "  4. Clean Temporary Files"
        echo -e "  5. Flush Log Files"
        echo -e "  6. View Logs"
        echo -e "  7. Reset to Default Configuration"
        echo -e "  8. Return to Main Menu"
        echo

        read -p "Enter your choice (1-8): " choice

        case $choice in
            1)
                service_management_menu
                ;;
            2)
                port_configuration_menu
                ;;
            3)
                toggle_verbose_mode
                sleep 2
                ;;
            4)
                clean_temporary_files
                sleep 2
                ;;
            5)
                flush_logs
                sleep 2
                ;;
            6)
                view_logs
                ;;
            7)
                read -p "Are you sure you want to reset to default configuration? (y/n): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    reset_config
                    sleep 2
                fi
                ;;
            8)
                return
                ;;
            *)
                print_status "$YELLOW" "!" "Invalid choice. Please try again."
                sleep 1
                ;;
        esac
    done
}

# Function to monitor services with enhanced health checks
monitor_services() {
    # Start continuous monitoring with auto-recovery
    run_continuous_monitoring
}

# Function to run diagnostics with enhanced visuals
run_diagnostics() {
    # Run enhanced diagnostics
    run_enhanced_diagnostics
}

# Function to show main menu
main_menu() {
    while true; do
        clear
        show_banner

        echo -e "${CYAN}${BOLD}Main Menu${NC}"
        echo

        echo -e "${BLUE}Available options:${NC}"
        echo -e "  1. Start All Services"
        echo -e "  2. Stop All Services"
        echo -e "  3. Monitor Services"
        echo -e "  4. Run Diagnostics"
        echo -e "  5. Advanced Options"
        echo -e "  6. Exit"
        echo

        read -p "Enter your choice (1-6): " choice

        case $choice in
            1)
                start_all_services
                # Ensure all services are running and healthy
                ensure_all_services_running
                read -p "Press Enter to continue..."
                ;;
            2)
                stop_all_services
                read -p "Press Enter to continue..."
                ;;
            3)
                monitor_services
                ;;
            4)
                run_diagnostics
                ;;
            5)
                advanced_menu
                ;;
            6)
                # Check if any services are running before exit
                local services_running=false

                if check_service_running "REDIS" || check_service_running "AI_SERVICE" || check_service_running "FRONTEND"; then
                    services_running=true
                fi

                if $services_running; then
                    read -p "Services are still running. Do you want to stop them before exiting? (y/n): " stop_confirm
                    if [[ "$stop_confirm" =~ ^[Yy]$ ]]; then
                        stop_all_services
                    fi
                fi

                echo "Exiting Service Manager..."
                clean_temporary_files >/dev/null 2>&1
                exit 0
                ;;
            *)
                print_status "$YELLOW" "!" "Invalid choice. Please try again."
                sleep 1
                ;;
        esac
    done
}

# Function to parse command-line arguments
parse_arguments() {
    # First, make sure configuration is initialized
    initialize_config

    # If no arguments, show main menu
    if [ $# -eq 0 ]; then
        main_menu
        return
    fi

    # Parse arguments
    case "$1" in
        "start")
            if [ $# -gt 1 ]; then
                case "$2" in
                    "redis")
                        # Kill any process on Redis port before starting
                        force_kill_port_processes $(get_config_value "redis_port" "$DEFAULT_REDIS_PORT")
                        start_redis
                        ;;
                    "ai" | "api" | "ai-service")
                        # Kill any process on AI service port before starting
                        force_kill_port_processes $(get_config_value "api_port" "$DEFAULT_API_PORT")
                        start_ai_service
                        ;;
                    "frontend" | "web" | "ui")
                        # Kill any process on Frontend port before starting
                        force_kill_port_processes $(get_config_value "frontend_port" "$DEFAULT_FRONTEND_PORT")
                        start_frontend
                        ;;
                    "all")
                        start_all_services
                        ;;
                    *)
                        print_status "$RED" "✗" "Unknown service: $2"
                        echo "Usage: $0 start {redis|ai|frontend|all}"
                        exit 1
                        ;;
                esac
            else
                start_all_services
            fi
            ;;

        "stop")
            if [ $# -gt 1 ]; then
                case "$2" in
                    "redis")
                        stop_service "REDIS"
                        ;;
                    "ai" | "api" | "ai-service")
                        stop_service "AI_SERVICE"
                        ;;
                    "frontend" | "web" | "ui")
                        stop_service "FRONTEND"
                        ;;
                    "all")
                        stop_all_services
                        ;;
                    *)
                        print_status "$RED" "✗" "Unknown service: $2"
                        echo "Usage: $0 stop {redis|ai|frontend|all}"
                        exit 1
                        ;;
                esac
            else
                stop_all_services
            fi
            ;;

        "restart")
            if [ $# -gt 1 ]; then
                case "$2" in
                    "redis")
                        restart_service "REDIS"
                        ;;
                    "ai" | "api" | "ai-service")
                        restart_service "AI_SERVICE"
                        ;;
                    "frontend" | "web" | "ui")
                        restart_service "FRONTEND"
                        ;;
                    "all")
                        restart_all_services
                        ;;
                    *)
                        print_status "$RED" "✗" "Unknown service: $2"
                        echo "Usage: $0 restart {redis|ai|frontend|all}"
                        exit 1
                        ;;
                esac
            else
                restart_all_services
            fi
            ;;

        "monitor")
            monitor_services
            ;;

        "diagnostics" | "diag")
            run_diagnostics
            ;;

        "logs" | "log")
            if [ $# -gt 1 ]; then
                case "$2" in
                    "redis")
                        if [ -f "$REDIS_LOG" ]; then
                            less "$REDIS_LOG" || cat "$REDIS_LOG" | more
                        else
                            print_status "$RED" "✗" "Redis log not found"
                        fi
                        ;;
                    "ai" | "api" | "ai-service")
                        if [ -f "$AI_SERVICE_LOG" ]; then
                            less "$AI_SERVICE_LOG" || cat "$AI_SERVICE_LOG" | more
                        else
                            print_status "$RED" "✗" "AI Service log not found"
                        fi
                        ;;
                    "frontend" | "web" | "ui")
                        if [ -f "$FRONTEND_LOG" ]; then
                            less "$FRONTEND_LOG" || cat "$FRONTEND_LOG" | more
                        else
                            print_status "$RED" "✗" "Frontend log not found"
                        fi
                        ;;
                    "error")
                        if [ -f "$ERROR_LOG" ]; then
                            less "$ERROR_LOG" || cat "$ERROR_LOG" | more
                        else
                            print_status "$RED" "✗" "Error log not found"
                        fi
                        ;;
                    "debug")
                        if [ -f "$DEBUG_LOG" ]; then
                            less "$DEBUG_LOG" || cat "$DEBUG_LOG" | more
                        else
                            print_status "$RED" "✗" "Debug log not found"
                        fi
                        ;;
                    *)
                        print_status "$RED" "✗" "Unknown log: $2"
                        echo "Usage: $0 logs {redis|ai|frontend|error|debug}"
                        exit 1
                        ;;
                esac
            else
                view_logs
            fi
            ;;

        "flush-logs" | "flush")
            flush_logs
            ;;

        "config")
            if [ $# -gt 1 ]; then
                case "$2" in
                    "reset")
                        reset_config
                        ;;
                    "show")
                        display_config
                        ;;
                    "set")
                        if [ $# -lt 4 ]; then
                            print_status "$RED" "✗" "Missing key and/or value"
                            echo "Usage: $0 config set <key> <value>"
                            exit 1
                        fi

                        update_config_value "$3" "$4"
                        ;;
                    *)
                        print_status "$RED" "✗" "Unknown config operation: $2"
                        echo "Usage: $0 config {reset|show|set <key> <value>}"
                        exit 1
                        ;;
                esac
            else
                display_config
            fi
            ;;

        "help" | "--help" | "-h")
            echo "Service Manager - Help"
            echo
            echo "Usage: $0 [command] [options]"
            echo
            echo "Commands:"
            echo "  start {redis|ai|frontend|all}  - Start services"
            echo "  stop {redis|ai|frontend|all}   - Stop services"
            echo "  restart {redis|ai|frontend|all}- Restart services"
            echo "  monitor                        - Monitor services"
            echo "  diagnostics                    - Run system diagnostics"
            echo "  logs {redis|ai|frontend|error|debug} - View logs"
            echo "  flush-logs                     - Flush all logs"
            echo "  config {reset|show|set}        - Manage configuration"
            echo "  help                           - Show this help"
            echo
            echo "Examples:"
            echo "  $0                             - Show interactive menu"
            echo "  $0 start all                   - Start all services"
            echo "  $0 stop frontend               - Stop only frontend service"
            echo "  $0 logs ai                     - View AI service logs"
            echo "  $0 config set api_port 8001    - Change API port to 8001"
            ;;

        *)
            print_status "$RED" "✗" "Unknown command: $1"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Main function
main() {
    # Ensure log directory exists
    ensure_log_dir

    # Log script start
    echo "DEBUG: Service Manager started at $(date)" >> "$DEBUG_LOG" 2>&1

    # Check dependencies first
    check_dependencies

    # Parse command-line arguments
    parse_arguments "$@"

    # Log script end
    echo "DEBUG: Service Manager ended at $(date)" >> "$DEBUG_LOG" 2>&1
}

# Call main function with all arguments
main "$@"
