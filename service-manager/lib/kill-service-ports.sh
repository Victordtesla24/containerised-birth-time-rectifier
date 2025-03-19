#!/bin/bash

# ===========================================
# Kill Service Ports Script
# ===========================================
# This script kills any processes running on the ports used by
# the birth time rectifier services (8000, 3000, 9000)

# Print colored status messages
print_status() {
    local color=$1
    local symbol=$2
    local message=$3
    echo -e "${color}${symbol} ${message}\033[0m"
}

# ANSI color codes
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
CYAN="\033[0;36m"
BOLD="\033[1m"
NC="\033[0m" # No Color

# Check if a port is in use
check_port_in_use() {
    local port=$1

    if command -v lsof >/dev/null 2>&1; then
        if lsof -i :$port -sTCP:LISTEN >/dev/null 2>&1; then
            return 0
        fi
    elif command -v netstat >/dev/null 2>&1; then
        if netstat -tuln | grep -q ":$port "; then
            return 0
        fi
    fi

    return 1
}

# Get process info for a specific port
get_process_info() {
    local port=$1

    if command -v lsof >/dev/null 2>&1; then
        lsof -i :$port -sTCP:LISTEN
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep ":$port " | awk '{print $7}'
    fi
}

# Display API ports in use
display_ports_in_use() {
    local ports=("$@")

    echo -e "${CYAN}${BOLD}Current API services running:${NC}"

    local any_port_in_use=false

    for port in "${ports[@]}"; do
        if check_port_in_use "$port"; then
            any_port_in_use=true
            echo -e "${YELLOW}Port $port is in use by:${NC}"
            if command -v lsof >/dev/null 2>&1; then
                lsof -i :$port -sTCP:LISTEN | tail -n +2 | while read line; do
                    local pid=$(echo "$line" | awk '{print $2}')
                    local user=$(echo "$line" | awk '{print $3}')
                    local program=$(echo "$line" | awk '{print $1}')
                    echo -e "  PID: ${RED}$pid${NC}, User: $user, Program: $program"
                done
            else
                echo "  (Install lsof for detailed process information)"
            fi
        fi
    done

    if ! $any_port_in_use; then
        echo -e "${GREEN}No API services currently running on ports ${ports[*]}${NC}"
    fi
    echo ""
}

# Kill processes on a specific port
kill_port_process() {
    local port=$1
    local use_sudo=$2

    if check_port_in_use "$port"; then
        print_status "$YELLOW" "!" "Port $port is in use. Killing process..."

        if [ "$use_sudo" = true ]; then
            sudo lsof -ti:$port -sTCP:LISTEN | xargs -r sudo kill -9
        else
            lsof -ti:$port -sTCP:LISTEN | xargs -r kill -9
        fi

        sleep 1
        if ! check_port_in_use "$port"; then
            print_status "$GREEN" "✓" "Successfully killed process on port $port"
            return 0
        else
            print_status "$RED" "✗" "Failed to kill process on port $port"
            return 1
        fi
    else
        print_status "$BLUE" "ℹ" "Port $port is not in use"
        return 0
    fi
}

# Main function
main() {
    echo -e "${CYAN}${BOLD}Kill Service Ports Utility${NC}"
    echo "This utility will kill processes on service ports (8000, 3000, 9000)"
    echo ""

    # Default to not using sudo
    use_sudo=false

    # Check for --sudo flag
    for arg in "$@"; do
        if [ "$arg" = "--sudo" ]; then
            use_sudo=true
            print_status "$BLUE" "ℹ" "Using sudo to kill processes"
            break
        fi
    done

    # Define ports
    local ports=(8000 3000 9000)

    # Display current processes using the ports
    display_ports_in_use "${ports[@]}"

    # Ask for confirmation
    read -p "Do you want to kill all processes on these ports? (y/n): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        echo "Operation cancelled."
        exit 0
    fi

    echo "Killing processes on service ports (8000, 3000, 9000)..."

    # Kill processes on service ports
    for port in "${ports[@]}"; do
        kill_port_process $port $use_sudo
    done

    echo -e "\n${GREEN}${BOLD}Done!${NC}"
}

# Call main function with all arguments
main "$@"
