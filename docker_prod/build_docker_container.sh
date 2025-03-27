#!/bin/bash
#
# Docker Production Container Build Script
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Source helper scripts
source "${SCRIPT_DIR}/helpers/ui_helpers.sh"
source "${SCRIPT_DIR}/helpers/docker_helpers.sh"

# Build Docker containers for production
print_header "Birth Time Rectifier - Production Docker Build"

# Build the AI Service container
print_section "Building AI Service Container"
docker build -t birth-rectifier-ai-service:prod -f "${PROJECT_ROOT}/docker/ai_service.Dockerfile" "${PROJECT_ROOT}"

# Build the API Gateway container
print_section "Building API Gateway Container"
docker build -t birth-rectifier-api-gateway:prod -f "${PROJECT_ROOT}/docker/api_gateway.Dockerfile" "${PROJECT_ROOT}"

print_success "Production Docker containers built successfully!"
