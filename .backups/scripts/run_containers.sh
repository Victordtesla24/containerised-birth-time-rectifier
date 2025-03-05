#!/bin/bash

# Exit on any error
set -e

# Function to check if NVIDIA Container Toolkit is installed
check_nvidia_docker() {
    if ! command -v nvidia-docker &> /dev/null; then
        echo "NVIDIA Container Toolkit not found. Please install it first."
        echo "Visit: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html"
        exit 1
    fi
}

# Function to check if Docker is running
check_docker() {
    if ! docker info &> /dev/null; then
        echo "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to check if required ports are available
check_ports() {
    local ports=(3000 8000 6379)
    for port in "${ports[@]}"; do
        if lsof -i :$port > /dev/null; then
            echo "Port $port is already in use. Please free it up before continuing."
            exit 1
        fi
    done
}

# Function to build and run containers
run_containers() {
    local mode=$1
    
    echo "Building and starting containers in $mode mode..."
    
    if [ "$mode" = "dev" ]; then
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
    else
        docker compose up --build
    fi
}

# Main script
main() {
    local mode=${1:-"prod"}  # Default to production mode
    
    echo "=== Birth Time Rectifier Container Setup ==="
    echo "Mode: $mode"
    
    # Run checks
    echo -n "Checking Docker... "
    check_docker
    echo "✓"
    
    echo -n "Checking ports... "
    check_ports
    echo "✓"
    
    # Check NVIDIA Docker only in production mode
    if [ "$mode" = "prod" ]; then
        echo -n "Checking NVIDIA Docker... "
        check_nvidia_docker
        echo "✓"
    fi
    
    # Run containers
    run_containers "$mode"
}

# Parse command line arguments
case "$1" in
    "dev"|"prod")
        main "$1"
        ;;
    *)
        echo "Usage: $0 [dev|prod]"
        echo "  dev  - Run in development mode"
        echo "  prod - Run in production mode (default)"
        exit 1
        ;;
esac 