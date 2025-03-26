#!/bin/bash
#
# Docker Helper Functions for Test Scripts
# Purpose: Docker-specific functions for test container management
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

# Function to check if docker-compose is available
function check_docker_compose_available() {
    start_spinner "Checking docker-compose availability"

    if ! command -v docker-compose >/dev/null 2>&1; then
        stop_spinner "error" "docker-compose not found. Please install docker-compose and try again."
        return 1
    fi

    stop_spinner "success" "docker-compose is available"
    return 0
}

# Function to copy test files to a container
function copy_test_files_to_container() {
    local container=$1
    local source_dir=$2
    local target_dir=$3

    start_spinner "Copying test files to container"

    # Create target directory if it doesn't exist
    if ! docker exec "$container" mkdir -p "$target_dir" >/dev/null 2>&1; then
        stop_spinner "error" "Failed to create target directory in container"
        return 1
    fi

    # Copy files to container
    if ! docker cp "$source_dir" "$container:$target_dir" >/dev/null 2>&1; then
        stop_spinner "error" "Failed to copy test files to container"
        return 1
    fi

    stop_spinner "success" "Test files copied to container"
    return 0
}

# Function to get container logs
function get_container_logs() {
    local container=$1
    local lines=${2:-50}

    echo -e "\n${YELLOW}${BOLD}Container logs for $container:${RESET}\n"
    docker logs --tail "$lines" "$container"
    echo
}

# Function to check container health
function check_container_health() {
    local container=$1
    local max_attempts=${2:-30}
    local sleep_time=${3:-2}

    start_spinner "Checking health of container $container"

    local attempt=0
    while ((attempt < max_attempts)); do
        # Check if container exists
        if ! docker ps -a | grep -q "$container" >/dev/null 2>&1; then
            stop_spinner "error" "Container $container does not exist"
            return 1
        fi

        # Check if container is running
        if ! docker ps | grep -q "$container" >/dev/null 2>&1; then
            stop_spinner "error" "Container $container is not running"
            return 1
        fi

        # Check if container has a health check
        local has_health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$container" 2>/dev/null)

        if [[ "$has_health" == "none" ]]; then
            # Container has no health check, assume it's healthy if running
            stop_spinner "success" "Container $container is running (no health check)"
            return 0
        elif [[ "$has_health" == "healthy" ]]; then
            # Container is healthy
            stop_spinner "success" "Container $container is healthy"
            return 0
        elif [[ "$has_health" == "starting" ]]; then
            # Container is still starting up
            ((attempt++))
            sleep "$sleep_time"
        else
            # Container is unhealthy
            stop_spinner "error" "Container $container is unhealthy: $has_health"
            return 1
        fi
    done

    stop_spinner "error" "Timed out waiting for container $container to become healthy"
    return 1
}

# Function to run command in container
function run_in_container() {
    local container=$1
    local command="$2"
    local log_file=${3:-/dev/null}

    start_spinner "Running command in container: $command"

    # Check if container exists
    if ! docker ps | grep -q "$container" >/dev/null 2>&1; then
        stop_spinner "error" "Container $container does not exist or is not running"
        return 1
    fi

    # Run command in container
    if ! docker exec "$container" bash -c "$command" >"$log_file" 2>&1; then
        stop_spinner "error" "Command failed in container"
        return 1
    fi

    stop_spinner "success" "Command completed successfully"
    return 0
}

# Function to stop and remove container
function stop_and_remove_container() {
    local container=$1

    start_spinner "Stopping and removing container $container"

    # Check if container exists
    if ! docker ps -a | grep -q "$container" >/dev/null 2>&1; then
        stop_spinner "info" "Container $container does not exist"
        return 0
    fi

    # Stop container if it's running
    if docker ps | grep -q "$container" >/dev/null 2>&1; then
        if ! docker stop "$container" >/dev/null 2>&1; then
            stop_spinner "warning" "Failed to stop container $container"
        fi
    fi

    # Remove container
    if ! docker rm "$container" >/dev/null 2>&1; then
        stop_spinner "error" "Failed to remove container $container"
        return 1
    fi

    stop_spinner "success" "Container $container stopped and removed"
    return 0
}

# Function to pull Docker image
function pull_docker_image() {
    local image=$1

    start_spinner "Pulling Docker image: $image"

    if ! docker pull "$image" >/dev/null 2>&1; then
        stop_spinner "error" "Failed to pull Docker image: $image"
        return 1
    fi

    stop_spinner "success" "Docker image pulled: $image"
    return 0
}

# Function to build Docker image
function build_docker_image() {
    local tag=$1
    local dockerfile=$2
    local context=$3
    local build_args=${4:-""}

    start_spinner "Building Docker image: $tag"

    if ! docker build $build_args -t "$tag" -f "$dockerfile" "$context" >/dev/null 2>&1; then
        stop_spinner "error" "Failed to build Docker image: $tag"
        return 1
    fi

    stop_spinner "success" "Docker image built: $tag"
    return 0
}

# Function to run docker-compose test environment
function start_test_environment() {
    local compose_file=$1
    local log_file=${2:-/dev/null}

    start_spinner "Starting test environment with docker-compose"

    if ! docker-compose -f "$compose_file" up -d >"$log_file" 2>&1; then
        stop_spinner "error" "Failed to start test environment"
        return 1
    fi

    stop_spinner "success" "Test environment started"
    return 0
}

# Function to stop docker-compose test environment
function stop_test_environment() {
    local compose_file=$1
    local log_file=${2:-/dev/null}

    start_spinner "Stopping test environment"

    if ! docker-compose -f "$compose_file" down >"$log_file" 2>&1; then
        stop_spinner "warning" "Failed to stop test environment cleanly"
        return 1
    fi

    stop_spinner "success" "Test environment stopped"
    return 0
}

# Make sure directory exists
mkdir -p "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null
