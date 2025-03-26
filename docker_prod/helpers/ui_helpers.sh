#!/bin/bash
#
# UI Helper Functions for Docker Scripts
# Purpose: Provides UI components like spinners, progress bars, and formatted text
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Terminal colors and formatting
RESET="\033[0m"
BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
MAGENTA="\033[35m"
CYAN="\033[36m"
GRAY="\033[37m"

# Progress spinner characters
SPINNER_CHARS=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')

# Global variables for spinner
SPIN_PID=""
SPIN_MESSAGE=""

# Start a spinner with a message
function start_spinner() {
    SPIN_MESSAGE="$1"

    # Define the spinner function
    _spin() {
        local i=0
        while true; do
            printf "\r${BLUE}%s${RESET} %s" "${SPINNER_CHARS[$i]}" "$SPIN_MESSAGE"
            i=$(( (i + 1) % ${#SPINNER_CHARS[@]} ))
            sleep 0.1
        done
    }

    # Start the spinner in the background
    _spin &
    SPIN_PID=$!

    # Disown so it doesn't output anything when killed
    disown $SPIN_PID 2>/dev/null
}

# Stop the spinner and set status
function stop_spinner() {
    local status=$1
    local message=${2:-$SPIN_MESSAGE}

    # Kill the spinner process
    [[ -n $SPIN_PID ]] && kill $SPIN_PID 2>/dev/null

    # Print the final status
    if [[ "$status" == "success" ]]; then
        printf "\r${GREEN}✓${RESET} %s\n" "$message"
    elif [[ "$status" == "warning" ]]; then
        printf "\r${YELLOW}⚠${RESET} %s\n" "$message"
    elif [[ "$status" == "error" ]]; then
        printf "\r${RED}✗${RESET} %s\n" "$message"
    else
        printf "\r${BLUE}i${RESET} %s\n" "$message"
    fi

    SPIN_PID=""
    SPIN_MESSAGE=""
}

# Print a progress bar
function print_progress_bar() {
    local current=$1
    local total=$2
    local title=${3:-"Progress"}
    local width=50
    local percent=$((current * 100 / total))
    local progress=$((current * width / total))

    # Build the progress bar string
    local bar="["
    for ((i=0; i<width; i++)); do
        if ((i < progress)); then
            bar+="="
        elif ((i == progress)); then
            bar+=">"
        else
            bar+=" "
        fi
    done
    bar+="] $percent%"

    # Print the progress bar
    printf "\r${BLUE}%s${RESET}: %s " "$title" "$bar"

    # Print newline if we're done
    if ((current >= total)); then
        echo
    fi
}

# Print a header
function print_header() {
    local title=$1
    local width=$(tput cols)
    local padding=$(( (width - ${#title} - 4) / 2 ))

    echo
    printf "%${width}s\n" | tr ' ' '='
    printf "%${padding}s ${BOLD}%s${RESET} %${padding}s\n" "" "$title" ""
    printf "%${width}s\n" | tr ' ' '='
    echo
}

# Print a section header
function print_section() {
    local title=$1

    echo
    echo -e "${BOLD}${BLUE}=== $title ===${RESET}"
    echo
}

# Print success message
function print_success() {
    echo -e "\n${GREEN}${BOLD}✓ $1${RESET}\n"
}

# Print error message
function print_error() {
    echo -e "\n${RED}${BOLD}✗ $1${RESET}\n"
}

# Print warning message
function print_warning() {
    echo -e "\n${YELLOW}${BOLD}⚠ $1${RESET}\n"
}

# Print info message
function print_info() {
    echo -e "\n${BLUE}${BOLD}ℹ $1${RESET}\n"
}

# Display an interactive menu
function display_menu() {
    clear
    print_header "Birth Time Rectifier - Docker Production Builder"

    echo -e "${BOLD}Please select what to build:${RESET}\n"
    echo "1) Build all containers"
    echo "2) Build frontend container only"
    echo "3) Build API Gateway container only"
    echo "4) Build AI Service container only"
    echo "5) Build and push to registry"
    echo "6) Exit"
    echo

    read -p "Enter choice [1-6]: " choice

    case $choice in
        1)
            BUILD_ALL=true
            ;;
        2)
            BUILD_FRONTEND=true
            ;;
        3)
            BUILD_API_GATEWAY=true
            ;;
        4)
            BUILD_AI_SERVICE=true
            ;;
        5)
            BUILD_ALL=true
            PUSH_TO_REGISTRY=true

            # Ask for registry if not set
            if [[ -z "$REGISTRY" ]]; then
                echo
                read -p "Enter registry URL: " REGISTRY
            fi
            ;;
        6)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid choice. Please try again.${RESET}"
            sleep 2
            display_menu
            ;;
    esac
}

# Function to handle process interruptions
function handle_interrupt() {
    echo
    print_error "Process interrupted!"
    [[ -n $SPIN_PID ]] && kill $SPIN_PID 2>/dev/null
    exit 1
}

# Set up trap for interrupt signal
trap handle_interrupt INT

# Test if terminal supports colors
if [[ -t 1 ]]; then
    ncolors=$(tput colors)
    if [[ -n "$ncolors" && $ncolors -ge 8 ]]; then
        # Terminal supports colors
        :
    else
        # Terminal doesn't support colors, disable them
        RESET=""
        BOLD=""
        RED=""
        GREEN=""
        YELLOW=""
        BLUE=""
        MAGENTA=""
        CYAN=""
        GRAY=""
    fi
fi
