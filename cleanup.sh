#!/bin/bash
#
# Birth Time Rectifier - Cleanup Script
# Purpose: Organizes root directory and cleans up temporary files
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Set strict error handling
set -eo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="${SCRIPT_DIR}/tests/shell_scripts/cleanup/cleanup.sh"
DUPLICATION_SCRIPT="${SCRIPT_DIR}/tests/shell_scripts/cleanup/duplication_identifier.sh"

# Check if the cleanup script exists
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "Error: Cleanup script not found at $CLEANUP_SCRIPT"
    exit 1
fi

# Check if the duplication script exists
if [ ! -f "$DUPLICATION_SCRIPT" ]; then
    echo "Error: Duplication identifier script not found at $DUPLICATION_SCRIPT"
    exit 1
fi

# Make sure the scripts are executable
chmod +x "$CLEANUP_SCRIPT" "$DUPLICATION_SCRIPT" 2>/dev/null || true

# Show usage information
function show_usage() {
    echo -e "\033[1mBirth Time Rectifier - Cleanup Utility\033[0m"
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "OPTIONS:"
    echo "  -d, --dry-run              Preview changes without making them"
    echo "  -c, --clean-only           Clean cache and temporary files only (no reorganization)"
    echo "  -a, --analyze-duplicates   Analyze code duplication"
    echo "  -s, --strict-cleanup       Strictly remove all duplicate configuration files from root"
    echo "  -k, --keep-days DAYS       Days to keep logs (default: 7)"
    echo "  -v, --verbose              Show detailed output"
    echo "  -h, --help                 Show this help message"
    echo
    echo "EXAMPLES:"
    echo "  $0                         # Standard cleanup"
    echo "  $0 --dry-run               # Preview what would be cleaned"
    echo "  $0 --strict-cleanup        # Strictly remove all duplicate files"
    echo "  $0 --analyze-duplicates    # Also analyze code duplication"
}

# Parse arguments
ARGS=()
while [ $# -gt 0 ]; do
    case "$1" in
        -d|--dry-run)
            ARGS+=("--dry-run")
            shift
            ;;
        -c|--clean-only)
            ARGS+=("--no-root-cleanup")
            shift
            ;;
        -a|--analyze-duplicates)
            ARGS+=("--analyze-duplicates")
            shift
            ;;
        -s|--strict-cleanup)
            # Strict cleanup - no special treatment
            shift
            ;;
        -k|--keep-days)
            ARGS+=("--keep-days" "$2")
            shift 2
            ;;
        -v|--verbose)
            ARGS+=("--verbose")
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Add special flag to keep this script in root directory
ARGS+=("--keep-in-root" "cleanup.sh")

# Run the cleanup script with the passed arguments
"$CLEANUP_SCRIPT" "${ARGS[@]}"
