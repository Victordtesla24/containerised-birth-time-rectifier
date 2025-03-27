#!/bin/bash
#
# Spinner and progress bar module for code duplication detection
#

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"
source "${SCRIPT_DIR}/utils.sh"

# State variables
SPINNER_PID=0
SPINNER_RUNNING=false
SPINNER_MSG=""
SPINNER_CHARS=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
SPINNER_TYPES=("default" "dots" "pulse" "bounce" "flow")

# Progress bar state variables
PROGRESS_RUNNING=false
PROGRESS_PID=0
PROGRESS_CURRENT=0
PROGRESS_TOTAL=0
PROGRESS_MSG=""
PROGRESS_START_TIME=$(date +%s)

# Check if terminal supports colors
if [ -t 1 ] && [ -n "$TERM" ] && [ "$TERM" != "dumb" ]; then
    HAS_COLOR=true
else
    HAS_COLOR=false
fi

# Display a spinner animation
_spinner() {
    local delay=$SPINNER_DELAY
    local spinstr='|/-\'
    local type="${1:-default}"

    case "$type" in
        "dots")
            spinstr=".oO@*"
            ;;
        "pulse")
            spinstr="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
            ;;
        "bounce")
            spinstr="⠁⠂⠄⠂"
            ;;
        "flow")
            spinstr="⠋⠙⠚⠞⠖⠦⠴⠲⠳⠓"
            ;;
        *)
            spinstr='|/-\'
            ;;
    esac

    while true; do
        for i in $(seq 0 ${#spinstr}); do
            local temp=${spinstr:i:1}
            if [ -z "$temp" ]; then
                temp=" "
            fi

            echo -en "\r\033[K\033[1m\033[0;34m$temp\033[0m ${SPINNER_MSG}"
            sleep $delay
        done
    done
}

# Start the spinner animation
start_spinner() {
    local message="$1"
    local type="${2:-default}"

    # Kill any existing spinner before starting a new one
    if [ "$SPINNER_RUNNING" = true ]; then
        stop_spinner_no_message
    fi

    # Set the message
    SPINNER_MSG="$message"

    # Start spinner in background
    _spinner "$type" &
    SPINNER_PID=$!
    SPINNER_RUNNING=true

    # Mark process for automatic cleanup
    disown $SPINNER_PID 2>/dev/null || true
}

# Stop the spinner animation
stop_spinner() {
    local success=${1:-true}

    # Skip if not running
    if [ "$SPINNER_RUNNING" = false ]; then
        return
    fi

    # Kill the spinner process
    kill $SPINNER_PID 2>/dev/null
    SPINNER_PID=0
    SPINNER_RUNNING=false

    # Clear the spinner
    echo -en "\r\033[K"

    # Show completion message
    if [ "$success" = true ]; then
        if [ "$HAS_COLOR" = true ]; then
            echo -e "\r\033[K\033[1m\033[0;32m✓\033[0m ${SPINNER_MSG}"
        else
            echo -e "\r✓ ${SPINNER_MSG}"
        fi
    else
        if [ "$HAS_COLOR" = true ]; then
            echo -e "\r\033[K\033[1m\033[0;31m✗\033[0m ${SPINNER_MSG}"
        else
            echo -e "\r✗ ${SPINNER_MSG}"
        fi
    fi

    # Reset the message
    SPINNER_MSG=""
}

# Update spinner message
update_spinner() {
    local message=$1
    SPINNER_MSG=$message
}

# Start progress bar
start_progress() {
    local total=$1
    local message=$2

    # Kill previous progress bar if still running
    if [ "$PROGRESS_RUNNING" = true ]; then
        stop_progress_no_message
    fi

    PROGRESS_CURRENT=0
    PROGRESS_TOTAL=$total
    PROGRESS_MSG=$message
    PROGRESS_START_TIME=$(date +%s)

    # Start a new progress bar in the background
    (
        show_progress $PROGRESS_CURRENT $PROGRESS_TOTAL "$PROGRESS_MSG"
        while :; do
            sleep 0.5
        done
    ) &

    PROGRESS_PID=$!
    PROGRESS_RUNNING=true
    disown $PROGRESS_PID 2>/dev/null || true
}

# Stop progress bar without showing completion message
stop_progress_no_message() {
    # Skip if not running
    if [ "$PROGRESS_RUNNING" = false ]; then
        return
    fi

    # Kill the progress bar process
    kill $PROGRESS_PID 2>/dev/null
    PROGRESS_PID=0
    PROGRESS_RUNNING=false

    # Clear the progress bar
    echo -en "\r\033[K"
}

# Stop progress bar and show completion
stop_progress() {
    local success=$1

    # Stop the progress bar
    stop_progress_no_message

    # Show completion status
    if [ "$HAS_COLOR" = true ]; then
        if [ "$success" = true ]; then
            show_progress $PROGRESS_TOTAL $PROGRESS_TOTAL "$PROGRESS_MSG"
            echo -e "\n${BOLD}${GREEN}✓${RESET} ${PROGRESS_MSG} completed successfully"
        else
            echo -e "${BOLD}${RED}✗${RESET} ${PROGRESS_MSG} failed"
        fi
    else
        if [ "$success" = true ]; then
            show_progress $PROGRESS_TOTAL $PROGRESS_TOTAL "$PROGRESS_MSG"
            echo -e "\n[OK] ${PROGRESS_MSG} completed successfully"
        else
            echo -e "[FAILED] ${PROGRESS_MSG} failed"
        fi
    fi
}

# Update progress value
update_progress() {
    local value=$1
    local message=$2

    PROGRESS_CURRENT=$value

    if [ -n "$message" ]; then
        PROGRESS_MSG=$message
    fi

    # If the progress bar is running, kill and restart it to update
    if [ -n "$PROGRESS_PID" ]; then
        kill $PROGRESS_PID 2>/dev/null || true
        wait $PROGRESS_PID 2>/dev/null || true

        # Start updated progress bar
        (
            show_progress $PROGRESS_CURRENT $PROGRESS_TOTAL "$PROGRESS_MSG"
            while :; do
                sleep 0.5
            done
        ) &

        PROGRESS_PID=$!
        disown $PROGRESS_PID 2>/dev/null || true
    fi
}

# Display progress bar
show_progress() {
    local current=$1
    local total=$2
    local message=$3

    # Prevent division by zero
    if [ "$total" -le 0 ]; then
        total=1
    fi

    # Calculate percentage and progress bar display
    local percentage=$((current * 100 / total))
    local filled=$((percentage * PROGRESS_WIDTH / 100))
    local empty=$((PROGRESS_WIDTH - filled))

    # Ensure filled and empty are non-negative
    [ "$filled" -lt 0 ] && filled=0
    [ "$empty" -lt 0 ] && empty=0

    # Display the progress bar with animated chars
    if [ "$HAS_COLOR" = true ]; then
        printf "\r${BOLD}["

        # Filled portion with gradient color
        local r=0
        local g=255
        local b=0

        if [ "$percentage" -lt 50 ]; then
            # Yellow to green gradient
            r=$((255 - percentage * 255 / 50))
            g=255
            b=0
        else
            # Green stays as is
            r=0
            g=255
            b=0
        fi

        printf "\033[38;2;${r};${g};${b}m"
        printf "%${filled}s" | tr ' ' '█'

        # Empty portion
        printf "${RESET}"
        printf "%${empty}s" | tr ' ' '░'

        printf "${BOLD}]${RESET} %3d%% ${BOLD}%s${RESET}" "$percentage" "$message"
    else
        printf "\r["
        printf "%${filled}s" | tr ' ' '#'
        printf "%${empty}s" | tr ' ' '-'
        printf "] %3d%% %s" "$percentage" "$message"
    fi

    # Print ETA if we have enough data
    if [ "$current" -gt 0 ] && [ "$total" -gt 0 ]; then
        local elapsed_time=$(( $(date +%s) - PROGRESS_START_TIME ))
        if [ "$elapsed_time" -gt 0 ]; then
            local items_per_second=$(( current * 1000 / elapsed_time ))
            if [ "$items_per_second" -gt 0 ]; then
                local remaining_items=$(( total - current ))
                local eta_seconds=$(( remaining_items * 1000 / items_per_second ))
                local eta_display

                if [ "$eta_seconds" -gt 3600 ]; then
                    eta_display="$(( eta_seconds / 3600 ))h $(( (eta_seconds % 3600) / 60 ))m"
                elif [ "$eta_seconds" -gt 60 ]; then
                    eta_display="$(( eta_seconds / 60 ))m $(( eta_seconds % 60 ))s"
                else
                    eta_display="${eta_seconds}s"
                fi

                printf " (ETA: %s)" "$eta_display"
            fi
        fi
    fi
}

# Display multi-line status with color
show_status() {
    local title=$1
    shift
    local lines=("$@")

    # Display the title
    if [ "$HAS_COLOR" = true ]; then
        echo -e "\n${BOLD}${title}${RESET}"
    else
        echo -e "\n${title}"
    fi

    # Display each status line
    for line in "${lines[@]}"; do
        echo "  - $line"
    done

    echo ""
}

# Display status banner for sections
show_banner() {
    local message=$1
    local width=$(tput cols 2>/dev/null || echo 80)

    # If width is too small, adjust it
    [ "$width" -lt 40 ] && width=40

    # Calculate padding
    local padding=$(( (width - ${#message} - 4) / 2 ))
    [ "$padding" -lt 1 ] && padding=1

    # Create padding string
    local pad_str=$(printf "%${padding}s" | tr ' ' '=')

    # Print banner
    if [ "$HAS_COLOR" = true ]; then
        echo -e "\n${BOLD}${BLUE}${pad_str} ${message} ${pad_str}${RESET}\n"
    else
        echo -e "\n${pad_str} ${message} ${pad_str}\n"
    fi
}

# Initialize enhanced spinner with style option
enhanced_spinner() {
    local message="$1"
    local style="${2:-dots}"  # Default to dots spinner

    # Define spinner styles
    local spinner_styles

    case "$style" in
        dots)
            spinner_styles=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
            ;;
        line)
            spinner_styles=("-" "\\" "|" "/")
            ;;
        bounce)
            spinner_styles=("▖" "▘" "▝" "▗")
            ;;
        pulse)
            spinner_styles=("█" "▓" "▒" "░" "▒" "▓")
            ;;
        flow)
            spinner_styles=("▁" "▂" "▃" "▄" "▅" "▆" "▇" "█" "▇" "▆" "▅" "▄" "▃" "▂")
            ;;
        *)
            spinner_styles=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
            ;;
    esac

    # Kill previous spinner if still running
    stop_spinner_no_message

    # Start a new spinner in the background
    (
        local i=0
        local spinner_chars=("${spinner_styles[@]}")
        while :; do
            if [ "$HAS_COLOR" = true ]; then
                char="${spinner_chars[$i]}"
                # Use a randomly shifting color for more visual interest
                r=$((RANDOM % 200 + 55))
                g=$((RANDOM % 200 + 55))
                b=$((RANDOM % 200 + 55))
                echo -ne "\r\033[38;2;${r};${g};${b}m${BOLD}${char}${RESET} ${message}"
            else
                char="${spinner_chars[$i]}"
                echo -ne "\r${char} ${message}"
            fi
            sleep $SPINNER_DELAY
            i=$(( (i+1) % ${#spinner_chars[@]} ))
        done
    ) &

    SPINNER_PID=$!
    disown $SPINNER_PID 2>/dev/null || true
}

# Start fancy spinner with predefined style
start_fancy_spinner() {
    local message="$1"
    local style="${2:-dots}"

    # Kill any existing spinner before starting a new one
    if [ "$SPINNER_RUNNING" = true ]; then
        stop_spinner_no_message
    fi

    if [ "$HAS_COLOR" = true ]; then
        enhanced_spinner "$message" "$style"
    else
        start_spinner "$message"
    fi

    # Track start time for ETA calculations
    PROGRESS_START_TIME=$(date +%s)
    SPINNER_MSG="$message"
    SPINNER_RUNNING=true
}

# Animate progress bar
_progress_bar() {
    local style="${1:-simple}"
    local width=$PROGRESS_WIDTH
    local animated_chars=("◐" "◓" "◑" "◒")
    local animated_index=0

    while true; do
        # Calculate current percentage
        local percentage=$((PROGRESS_CURRENT * 100 / PROGRESS_TOTAL))
        if [ $percentage -gt 100 ]; then
            percentage=100
        fi

        # Calculate filled and empty portions
        local filled=$((percentage * width / 100))
        local empty=$((width - filled))
        if [ $filled -lt 0 ]; then filled=0; fi
        if [ $empty -lt 0 ]; then empty=0; fi

        # Calculate elapsed time
        local elapsed=$(($(date +%s) - PROGRESS_START_TIME))
        local elapsed_str=$(printf "%02d:%02d" $((elapsed / 60)) $((elapsed % 60)))

        # Calculate estimated time remaining
        local eta="--:--"
        if [ $PROGRESS_CURRENT -gt 0 ]; then
            local total_seconds=$((elapsed * PROGRESS_TOTAL / PROGRESS_CURRENT))
            local remaining=$((total_seconds - elapsed))
            if [ $remaining -gt 0 ]; then
                eta=$(printf "%02d:%02d" $((remaining / 60)) $((remaining % 60)))
            else
                eta="00:00"
            fi
        fi

        # Get next animation character
        animated_index=$(( (animated_index + 1) % ${#animated_chars[@]} ))
        local anim_char=${animated_chars[$animated_index]}

        if [ "$HAS_COLOR" = true ]; then
            case "$style" in
                "gradient")
                    # Gradient-colored progress bar
                    local color=$(_get_gradient_color $percentage)
                    printf "\r\033[K\033[1m["

                    # Print filled portion with gradient
                    for i in $(seq 1 $filled); do
                        local pct=$((i * 100 / width))
                        local c=$(_get_gradient_color $pct)
                        printf "\033[38;2;${c}m█\033[0m"
                    done

                    # Print empty portion
                    if [ $empty -gt 0 ]; then
                        printf "%${empty}s" | tr ' ' '.'
                    fi

                    printf "] \033[1m%3d%%\033[0m %s [%s/%s] %s" $percentage "$PROGRESS_MSG" "$elapsed_str" "$eta" "$anim_char"
                    ;;
                "animated")
                    # Animated progress bar
                    printf "\r\033[K\033[1m["

                    # Print filled portion
                    if [ $filled -gt 0 ]; then
                        printf "\033[0;32m%${filled}s\033[0m" | tr ' ' '█'
                    fi

                    # Print animated character at boundary
                    if [ $filled -lt $width ]; then
                        printf "\033[0;33m${anim_char}\033[0m"
                        filled=$((filled + 1))
                    fi

                    # Print empty portion
                    if [ $empty -gt 1 ]; then
                        printf "%$((empty - 1))s" | tr ' ' '.'
                    fi

                    printf "] \033[1m%3d%%\033[0m %s [%s/%s]" $percentage "$PROGRESS_MSG" "$elapsed_str" "$eta"
                    ;;
                *)
                    # Simple progress bar
                    printf "\r\033[K\033[1m["

                    # Print filled portion
                    if [ $filled -gt 0 ]; then
                        printf "\033[0;32m%${filled}s\033[0m" | tr ' ' '#'
                    fi

                    # Print empty portion
                    if [ $empty -gt 0 ]; then
                        printf "%${empty}s" | tr ' ' '-'
                    fi

                    printf "] \033[1m%3d%%\033[0m %s [%s/%s]" $percentage "$PROGRESS_MSG" "$elapsed_str" "$eta"
                    ;;
            esac
        else
            # Non-colored version
            printf "\r["
            printf "%${filled}s" | tr ' ' '#'
            printf "%${empty}s" | tr ' ' '-'
            printf "] %3d%% %s [%s/%s]" $percentage "$PROGRESS_MSG" "$elapsed_str" "$eta"
        fi

        sleep $SPINNER_DELAY
    done
}

# Start a fancy progress bar
start_fancy_progress() {
    local total="$1"
    local message="$2"
    local style="${3:-simple}"

    # Kill previous progress bar if still running
    if [ "$PROGRESS_RUNNING" = true ]; then
        stop_progress_no_message
    fi

    # Store state
    PROGRESS_TOTAL=$total
    PROGRESS_CURRENT=0
    PROGRESS_MSG="$message"
    PROGRESS_START_TIME=$(date +%s)
    PROGRESS_RUNNING=true

    # Start progress bar in background
    _progress_bar "$style" &
    PROGRESS_PID=$!
    disown $PROGRESS_PID 2>/dev/null || true
}

# Update custom spinner style
update_spinner_style() {
    local style="$1"
    local new_message="$2"

    # Kill and restart with new style
    stop_spinner_no_message
    start_fancy_spinner "${new_message:-$SPINNER_MSG}" "$style"
}

# Update the fancy progress bar
update_fancy_progress() {
    local value="$1"
    local message="$2"
    local style="$3"

    PROGRESS_CURRENT=$value

    if [ -n "$message" ]; then
        PROGRESS_MSG=$message
    fi

    if [ -n "$style" ]; then
        style="$style"
    fi

    # If the progress bar is running, kill and restart it to update
    if [ -n "$PROGRESS_PID" ]; then
        kill $PROGRESS_PID 2>/dev/null || true
        wait $PROGRESS_PID 2>/dev/null || true

        # Start updated progress bar
        (
            show_progress $PROGRESS_CURRENT $PROGRESS_TOTAL "$PROGRESS_MSG"

            # Animation loop if needed
            local frame=0
            while :; do
                if [ "$HAS_COLOR" = true ] && [ "$style" = "animated" ]; then
                    frame=$(( (frame + 1) % 4 ))
                    sleep 0.1
                else
                    sleep 0.5
                fi
            done
        ) &

        PROGRESS_PID=$!
        disown $PROGRESS_PID 2>/dev/null || true
    fi
}

# Show status with enhanced formatting
show_enhanced_status() {
    local title=$1
    shift
    local lines=("$@")

    # Get terminal width
    local term_width=$(tput cols 2>/dev/null || echo 80)

    # Display the title with divider
    if [ "$HAS_COLOR" = true ]; then
        echo -e "\n${BOLD}${BLUE}${title}${RESET}"
        printf "${CYAN}%*s${RESET}\n" $term_width | tr ' ' '─'
    else
        echo -e "\n${title}"
        printf "%*s\n" $term_width | tr ' ' '-'
    fi

    # Display each status line with symbol
    for line in "${lines[@]}"; do
        if [ "$HAS_COLOR" = true ]; then
            echo -e "  ${GREEN}➤${RESET} $line"
        else
            echo -e "  * $line"
        fi
    done

    echo ""
}

# Show banner with animated border for sections
show_animated_banner() {
    local message=$1
    local type="${2:-default}"
    local duration="${3:-1.5}"
    local width=$((${#message} + 8))

    # Ensure minimum width
    if [ $width -lt 60 ]; then
        width=60
    fi

    if [ "$HAS_COLOR" = true ]; then
        # Draw top line
        printf "\n\033[1m\033[0;34m"
        printf "="%.0s $(seq 1 $width)
        printf "\033[0m\n"

        # Animate middle line
        for i in $(seq 1 $width); do
            printf "\r\033[1m\033[0;36m"
            printf "=" %.0s $(seq 1 $i)
            printf "\033[0m"
            sleep 0.005
        done

        # Print message
        printf "\r\033[1m\033[0;36m%*s\033[0m\n" $(( (width + ${#message}) / 2 )) "$message"

        # Draw bottom line
        printf "\033[1m\033[0;34m"
        printf "="%.0s $(seq 1 $width)
        printf "\033[0m\n\n"
    else
        printf "\n"
        printf "="%.0s $(seq 1 $width)
        printf "\n%*s\n" $(( (width + ${#message}) / 2 )) "$message"
        printf "="%.0s $(seq 1 $width)
        printf "\n\n"
    fi
}

# Calculate color gradient
_get_gradient_color() {
    local percentage=$1
    local r g b

    # Green to yellow to red gradient (0-100%)
    if [ $percentage -lt 50 ]; then
        # Green to yellow (0-50%)
        r=$((255 * percentage / 50))
        g=255
        b=0
    else
        # Yellow to red (50-100%)
        r=255
        g=$((255 * (100 - percentage) / 50))
        b=0
    fi

    printf "%03d;%03d;%03d" $r $g $b
}

# Initialize spinner module
init_spinner() {
    # Reset state variables
    SPINNER_PID=0
    SPINNER_RUNNING=false
    SPINNER_MSG=""

    PROGRESS_RUNNING=false
    PROGRESS_PID=0
    PROGRESS_CURRENT=0
    PROGRESS_TOTAL=0
    PROGRESS_MSG=""
    PROGRESS_START_TIME=$(date +%s)

    # Set up traps for clean exit
    trap cleanup_spinners EXIT INT TERM

    # Return success
    return 0
}

# Stop spinner without showing success/failure message
stop_spinner_no_message() {
    # Skip if not running
    if [ "$SPINNER_RUNNING" = false ]; then
        return
    fi

    # Kill the spinner process
    kill $SPINNER_PID 2>/dev/null
    SPINNER_PID=0
    SPINNER_RUNNING=false

    # Clear the spinner
    echo -en "\r\033[K"

    # Reset the message
    SPINNER_MSG=""
}

# Ensure cleanup on exit
cleanup_spinners() {
    # Kill all spinner and progress processes
    if [ "$SPINNER_RUNNING" = true ] && [ -n "$SPINNER_PID" ]; then
        kill $SPINNER_PID 2>/dev/null || true
        SPINNER_RUNNING=false
        SPINNER_PID=0
    fi

    if [ "$PROGRESS_RUNNING" = true ] && [ -n "$PROGRESS_PID" ]; then
        kill $PROGRESS_PID 2>/dev/null || true
        PROGRESS_RUNNING=false
        PROGRESS_PID=0
    fi

    # Clear any spinner or progress output
    echo -en "\r\033[K"
}

# Export all functions
export -f start_spinner
export -f stop_spinner
export -f stop_spinner_no_message
export -f show_animated_banner
export -f show_enhanced_status
export -f start_fancy_progress
export -f update_fancy_progress
export -f stop_progress
export -f stop_progress_no_message
export -f start_fancy_spinner
export -f init_spinner
export -f cleanup_spinners

# Set trap for script exit
trap cleanup_spinners EXIT INT TERM
