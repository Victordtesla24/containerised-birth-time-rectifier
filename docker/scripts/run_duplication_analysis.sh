#!/bin/bash
#
# Containerized Code Duplication Analyzer Runner
# Builds and runs the duplication analysis in a Docker container with GPU support
#

set -eo pipefail

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Default directories to scan
DEFAULT_DIRS=("ai_service" "api_gateway")

# Parse command line arguments
SERVER_MODE=false
DIRECTORIES=()
GPU_ENABLED=true
QUICK_MODE=false
VERBOSE=false

print_help() {
    echo "Containerized Code Duplication Analyzer"
    echo ""
    echo "Usage: $0 [options] [directory1] [directory2] ..."
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -s, --server        Run in server mode to keep container running"
    echo "  --no-gpu            Disable GPU support"
    echo "  -q, --quick         Run quick analysis (faster but less accurate)"
    echo "  -v, --verbose       Enable verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 ai_service api_gateway     # Analyze both services"
    echo "  $0 -q ai_service              # Quick analysis of AI service"
    echo "  $0 -s                         # Analyze default dirs and start server"
    echo ""
}

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            print_help
            exit 0
            ;;
        -s|--server)
            SERVER_MODE=true
            shift
            ;;
        --no-gpu)
            GPU_ENABLED=false
            shift
            ;;
        -q|--quick)
            QUICK_MODE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -*)
            echo "Unknown option: $1"
            print_help
            exit 1
            ;;
        *)
            DIRECTORIES+=("$1")
            shift
            ;;
    esac
done

# If no directories specified, use defaults
if [ ${#DIRECTORIES[@]} -eq 0 ]; then
    DIRECTORIES=("${DEFAULT_DIRS[@]}")
fi

# Prepare mounted directories
REPORTS_DIR="${PROJECT_ROOT}/reports/duplication"
mkdir -p "${REPORTS_DIR}"

# Detect GPU
if [ "$GPU_ENABLED" = true ]; then
    if command -v nvidia-smi &> /dev/null; then
        echo "✅ NVIDIA GPU detected"
        GPU_RUNTIME="--gpus all"
    else
        echo "⚠️ NVIDIA GPU not detected. Running in CPU-only mode."
        GPU_RUNTIME=""
    fi
else
    echo "🔒 GPU support disabled by user"
    GPU_RUNTIME=""
fi

# Build the container
echo "🔨 Building duplication analyzer container..."
docker build -t code-duplication-analyzer:latest -f "${PROJECT_ROOT}/docker/duplication_identifier.Dockerfile" "${PROJECT_ROOT}"

# Prepare arguments
ANALYZER_ARGS=""
[ "$VERBOSE" = true ] && ANALYZER_ARGS="${ANALYZER_ARGS} -v"
[ "$QUICK_MODE" = true ] && ANALYZER_ARGS="${ANALYZER_ARGS} -q"

# Convert directories to container paths
for dir in "${DIRECTORIES[@]}"; do
    ANALYZER_ARGS="${ANALYZER_ARGS} /code/${dir}"
done

# Run the container
echo "🚀 Running analysis on directories: ${DIRECTORIES[*]}"
if [ "$SERVER_MODE" = true ]; then
    docker run -it --rm \
        ${GPU_RUNTIME} \
        -v "${PROJECT_ROOT}:/code" \
        -v "${REPORTS_DIR}:/mounted_reports" \
        -p 8050:8050 \
        -e SERVER_MODE=true \
        code-duplication-analyzer:latest ${ANALYZER_ARGS}
else
    docker run -it --rm \
        ${GPU_RUNTIME} \
        -v "${PROJECT_ROOT}:/code" \
        -v "${REPORTS_DIR}:/mounted_reports" \
        code-duplication-analyzer:latest ${ANALYZER_ARGS}
fi

# Print report paths if not in server mode
if [ "$SERVER_MODE" = false ]; then
    latest_report=$(find "${REPORTS_DIR}" -type f -name "duplication_report.html" -mtime -1 | head -n 1)
    if [ -n "$latest_report" ]; then
        echo ""
        echo "✨ Analysis complete!"
        echo "📊 View the report at: file://${latest_report}"
        echo ""
    fi
fi
