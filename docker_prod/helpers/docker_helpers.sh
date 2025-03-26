#!/bin/bash
#
# Docker Helper Functions
# Purpose: Docker-specific helper functions for container building and management
# Author: AI-Assisted Development Team
# Date: 2024-03-26
#

# Function to check if Docker is available
function check_docker_available() {
    start_spinner "Checking Docker availability"

    if ! command -v docker >/dev/null 2>&1; then
        stop_spinner "error" "Docker not found. Please install Docker and try again."
        return 1
    fi

    if ! docker info >/dev/null 2>&1; then
        stop_spinner "error" "Docker daemon is not running. Start Docker and try again."
        return 1
    fi

    stop_spinner "success" "Docker is available"
    return 0
}

# Function to build the frontend container
function build_frontend() {
    print_section "Building Frontend Container"

    # Set image name
    local image_name="${REGISTRY:+$REGISTRY/}${CONTAINER_PREFIX}-frontend:latest"

    # Log the build start
    echo "Building frontend image: $image_name" | tee -a "$LOG_FILE"

    # Check if frontend.Dockerfile exists
    if [[ ! -f "${ROOT_DIR}/frontend.Dockerfile" ]]; then
        print_error "frontend.Dockerfile not found in project root"
        return 1
    fi

    # Begin build
    start_spinner "Building frontend container"

    # Perform the build
    if docker build \
        --no-cache=$([ "$REBUILD_DEPS" == "true" ] && echo "true" || echo "false") \
        -t "$image_name" \
        -f "${ROOT_DIR}/frontend.Dockerfile" \
        "${ROOT_DIR}" >>"$LOG_FILE" 2>&1; then

        stop_spinner "success" "Frontend container built successfully: $image_name"

        # Tag with date for versioning
        local date_tag="${image_name%:*}:$(date +%Y%m%d)"
        docker tag "$image_name" "$date_tag" >>"$LOG_FILE" 2>&1
        echo "Tagged image as: $date_tag" | tee -a "$LOG_FILE"

        return 0
    else
        stop_spinner "error" "Failed to build frontend container"
        echo -e "\n${RED}Build log (last 10 lines):${RESET}"
        tail -n 10 "$LOG_FILE"
        return 1
    fi
}

# Function to build the API Gateway container
function build_api_gateway() {
    print_section "Building API Gateway Container"

    # Set image name
    local image_name="${REGISTRY:+$REGISTRY/}${CONTAINER_PREFIX}-api-gateway:latest"

    # Log the build start
    echo "Building API Gateway image: $image_name" | tee -a "$LOG_FILE"

    # Check if api_gateway.Dockerfile exists
    if [[ ! -f "${ROOT_DIR}/api_gateway.Dockerfile" ]]; then
        print_error "api_gateway.Dockerfile not found in project root"
        return 1
    fi

    # Begin build
    start_spinner "Building API Gateway container"

    # Perform the build
    if docker build \
        --target production \
        --no-cache=$([ "$REBUILD_DEPS" == "true" ] && echo "true" || echo "false") \
        -t "$image_name" \
        -f "${ROOT_DIR}/api_gateway.Dockerfile" \
        "${ROOT_DIR}" >>"$LOG_FILE" 2>&1; then

        stop_spinner "success" "API Gateway container built successfully: $image_name"

        # Tag with date for versioning
        local date_tag="${image_name%:*}:$(date +%Y%m%d)"
        docker tag "$image_name" "$date_tag" >>"$LOG_FILE" 2>&1
        echo "Tagged image as: $date_tag" | tee -a "$LOG_FILE"

        return 0
    else
        stop_spinner "error" "Failed to build API Gateway container"
        echo -e "\n${RED}Build log (last 10 lines):${RESET}"
        tail -n 10 "$LOG_FILE"
        return 1
    fi
}

# Function to build the AI Service container
function build_ai_service() {
    print_section "Building AI Service Container"

    # Set image name
    local image_name="${REGISTRY:+$REGISTRY/}${CONTAINER_PREFIX}-ai-service:latest"

    # Log the build start
    echo "Building AI Service image: $image_name" | tee -a "$LOG_FILE"

    # Check if ai_service.Dockerfile exists
    if [[ ! -f "${ROOT_DIR}/ai_service.Dockerfile" ]]; then
        print_error "ai_service.Dockerfile not found in project root"
        return 1
    fi

    # Begin build
    start_spinner "Building AI Service container"

    # Perform the build
    if docker build \
        --no-cache=$([ "$REBUILD_DEPS" == "true" ] && echo "true" || echo "false") \
        -t "$image_name" \
        -f "${ROOT_DIR}/ai_service.Dockerfile" \
        "${ROOT_DIR}" >>"$LOG_FILE" 2>&1; then

        stop_spinner "success" "AI Service container built successfully: $image_name"

        # Tag with date for versioning
        local date_tag="${image_name%:*}:$(date +%Y%m%d)"
        docker tag "$image_name" "$date_tag" >>"$LOG_FILE" 2>&1
        echo "Tagged image as: $date_tag" | tee -a "$LOG_FILE"

        return 0
    else
        stop_spinner "error" "Failed to build AI Service container"
        echo -e "\n${RED}Build log (last 10 lines):${RESET}"
        tail -n 10 "$LOG_FILE"
        return 1
    fi
}

# Function to push images to registry
function push_to_registry() {
    print_section "Pushing Images to Registry"

    # Check if registry is specified
    if [[ -z "$REGISTRY" ]]; then
        print_error "No registry specified. Use --registry option or set in menu."
        return 1
    fi

    # Push frontend image if built
    if $BUILD_ALL || $BUILD_FRONTEND; then
        local frontend_image="${REGISTRY}/${CONTAINER_PREFIX}-frontend:latest"
        local frontend_dated="${REGISTRY}/${CONTAINER_PREFIX}-frontend:$(date +%Y%m%d)"

        start_spinner "Pushing frontend image to registry"
        if docker push "$frontend_image" >>"$LOG_FILE" 2>&1 && \
           docker push "$frontend_dated" >>"$LOG_FILE" 2>&1; then
            stop_spinner "success" "Pushed frontend image to registry"
        else
            stop_spinner "error" "Failed to push frontend image to registry"
            return 1
        fi
    fi

    # Push API Gateway image if built
    if $BUILD_ALL || $BUILD_API_GATEWAY; then
        local gateway_image="${REGISTRY}/${CONTAINER_PREFIX}-api-gateway:latest"
        local gateway_dated="${REGISTRY}/${CONTAINER_PREFIX}-api-gateway:$(date +%Y%m%d)"

        start_spinner "Pushing API Gateway image to registry"
        if docker push "$gateway_image" >>"$LOG_FILE" 2>&1 && \
           docker push "$gateway_dated" >>"$LOG_FILE" 2>&1; then
            stop_spinner "success" "Pushed API Gateway image to registry"
        else
            stop_spinner "error" "Failed to push API Gateway image to registry"
            return 1
        fi
    fi

    # Push AI Service image if built
    if $BUILD_ALL || $BUILD_AI_SERVICE; then
        local service_image="${REGISTRY}/${CONTAINER_PREFIX}-ai-service:latest"
        local service_dated="${REGISTRY}/${CONTAINER_PREFIX}-ai-service:$(date +%Y%m%d)"

        start_spinner "Pushing AI Service image to registry"
        if docker push "$service_image" >>"$LOG_FILE" 2>&1 && \
           docker push "$service_dated" >>"$LOG_FILE" 2>&1; then
            stop_spinner "success" "Pushed AI Service image to registry"
        else
            stop_spinner "error" "Failed to push AI Service image to registry"
            return 1
        fi
    fi

    print_success "All images pushed to registry: $REGISTRY"
    return 0
}

# Create directory structure if needed
mkdir -p "${SCRIPT_DIR}/helpers" 2>/dev/null
