#!/bin/bash
set -e

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

echo -e "${BLUE}[INFO]${NC} Testing ai_service.Dockerfile build..."

# Create a temporary directory
TEMP_DIR=$(mktemp -d)
echo -e "${BLUE}[INFO]${NC} Using temporary directory: ${TEMP_DIR}"

cleanup() {
  echo -e "${BLUE}[INFO]${NC} Cleaning up temporary environment..."
  rm -rf "${TEMP_DIR}"
}

# Set cleanup to run on script exit
trap cleanup EXIT

# Create simplified download_ephemeris.sh
mkdir -p "${TEMP_DIR}/scripts/setup"
cat > "${TEMP_DIR}/scripts/setup/download_ephemeris.sh" << 'EOF'
#!/bin/bash
set -e

echo "Creating ephemeris directory structure..."
mkdir -p /app/ephemeris
touch /app/ephemeris/sample_ephe_file.txt
echo "Ephemeris directory created successfully"
EOF
chmod +x "${TEMP_DIR}/scripts/setup/download_ephemeris.sh"

# Copy the ai_service.Dockerfile to temp dir
cp ai_service.Dockerfile "${TEMP_DIR}/"

# Create a minimal requirements.txt
cat > "${TEMP_DIR}/requirements.txt" << 'EOF'
# Core libraries
fastapi==0.100.0
uvicorn==0.22.0
pydantic==1.10.12

# Swiss Ephemeris library
pyswisseph==2.10.3.2
flatlib==0.2.0

# Utilities
python-multipart==0.0.19
httpx==0.26.0
websocket-client==1.7.0
EOF

# Create a minimal constraints.txt
cat > "${TEMP_DIR}/constraints.txt" << 'EOF'
# Constraints file to prevent dependency conflicts
pydantic>=1.10.12,<2.0.0
pyswisseph==2.10.3.2
flatlib==0.2.0
EOF

# Create a test script
mkdir -p "${TEMP_DIR}/ai_service/core/rectification"
cat > "${TEMP_DIR}/ai_service/core/rectification/chart_calculator.py" << 'EOF'
import os
import pyswisseph as swe

def test_pyswisseph():
    """Test if pyswisseph works correctly."""
    print("Testing pyswisseph functionality...")

    # Set ephemeris path
    ephe_path = os.environ.get('SWISSEPH_PATH', '/app/ephemeris')
    print(f"Using ephemeris path: {ephe_path}")

    # Initialize Swiss Ephemeris
    swe.set_ephe_path(ephe_path)
    print(f"Swiss Ephemeris library path: {swe.get_library_path()}")

    # Get Julian day for J2000.0
    julday = swe.julday(2000, 1, 1, 12.0)
    print(f"Julian day for 2000-01-01 12:00: {julday}")

    # Calculate planetary positions
    sun_result = swe.calc_ut(julday, swe.SUN)
    print(f"Sun position: {sun_result}")

    print("PySwissEph test completed successfully!")
    return True
EOF

# Create a simple app_wrapper.py
mkdir -p "${TEMP_DIR}/ai_service"
cat > "${TEMP_DIR}/ai_service/app_wrapper.py" << 'EOF'
from fastapi import FastAPI
from ai_service.core.rectification.chart_calculator import test_pyswisseph

app_wrapper = FastAPI()

@app_wrapper.get("/health")
async def health_check():
    """Simple health check endpoint."""
    # Test the pyswisseph functionality
    pyswisseph_ok = test_pyswisseph()

    return {
        "status": "healthy" if pyswisseph_ok else "unhealthy",
        "service": "ai_service",
        "pyswisseph": "ok" if pyswisseph_ok else "error"
    }
EOF

# Create __init__.py files
touch "${TEMP_DIR}/ai_service/__init__.py"
touch "${TEMP_DIR}/ai_service/core/__init__.py"
touch "${TEMP_DIR}/ai_service/core/rectification/__init__.py"

# Change to the temporary directory
cd "${TEMP_DIR}"

# Build the Docker image
echo -e "${BLUE}[INFO]${NC} Building the builder stage..."
if docker build --target builder -t ai-service-test-builder -f ai_service.Dockerfile .; then
    echo -e "${GREEN}[SUCCESS]${NC} Builder stage built successfully"
else
    echo -e "${RED}[ERROR]${NC} Builder stage build failed"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Building the base stage..."
if docker build --target base -t ai-service-test-base -f ai_service.Dockerfile .; then
    echo -e "${GREEN}[SUCCESS]${NC} Base stage built successfully"
else
    echo -e "${RED}[ERROR]${NC} Base stage build failed"
    exit 1
fi

echo -e "${BLUE}[INFO]${NC} Building the development stage..."
if docker build --target development -t ai-service-test-dev -f ai_service.Dockerfile .; then
    echo -e "${GREEN}[SUCCESS]${NC} Development stage built successfully"
else
    echo -e "${RED}[ERROR]${NC} Development stage build failed"
    exit 1
fi

# Run the container and test the health endpoint
echo -e "${BLUE}[INFO]${NC} Running the development container..."
if docker run --rm -d -p 8000:8000 --name ai-service-test ai-service-test-dev; then
    echo -e "${GREEN}[SUCCESS]${NC} Container started successfully"

    # Wait for container to initialize
    echo -e "${BLUE}[INFO]${NC} Waiting for container to initialize..."
    sleep 5

    # Test the health endpoint
    echo -e "${BLUE}[INFO]${NC} Testing the health endpoint..."
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo -e "${GREEN}[SUCCESS]${NC} Health endpoint returned healthy status"
    else
        echo -e "${RED}[ERROR]${NC} Health endpoint did not return healthy status"
        docker stop ai-service-test
        exit 1
    fi

    # Stop the container
    docker stop ai-service-test
else
    echo -e "${RED}[ERROR]${NC} Failed to start container"
    exit 1
fi

echo -e "${GREEN}[SUCCESS]${NC} ai_service.Dockerfile test passed!"
echo -e "${GREEN}[SUCCESS]${NC} The fixes for pyswisseph work correctly"
echo -e "${YELLOW}[NOTE]${NC} Replace libgcc-9-dev with libgcc-s1 and add python3-dev in your Dockerfile"
