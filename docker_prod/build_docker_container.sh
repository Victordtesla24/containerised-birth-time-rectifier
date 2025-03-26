#!/bin/bash
#
# Wrapper for Docker Production Container Build Script
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Execute the actual build script
exec "${PROJECT_ROOT}/docker_prod/build_docker_container.sh" "$@"
