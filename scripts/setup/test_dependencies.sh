#!/bin/bash
set -e

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

echo -e "${BLUE}[INFO]${NC} Pre-testing Dependencies for Docker Build"

# Create a file with just the essential requirements
cat > essential_requirements.txt << EOF
fastapi==0.100.0
uvicorn==0.22.0
pydantic==1.10.12
pyswisseph==2.10.3.2
flatlib==0.2.0
EOF

# Create a Docker file that tests the dependencies
cat > Dockerfile.test << EOF
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    gcc \\
    libgcc-s1 \\
    python3-dev \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables
ENV PYTHONPATH="/usr/local/lib/python3.11/site-packages:/app"

# Install dependencies
COPY essential_requirements.txt requirements.txt
RUN pip install --upgrade pip setuptools wheel && \\
    pip install -r requirements.txt

# Create a test script to verify imports
COPY test_imports.py .

# Run test script
CMD ["python", "test_imports.py"]
EOF

# Create a test script
cat > test_imports.py << 'EOF'
#!/usr/bin/env python
import sys
import importlib
import os
import platform

print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Architecture: {platform.machine()}")
print(f"System: {platform.system()}")

def test_module(module_name):
    """Test if a module can be imported."""
    print(f"\nTesting module: {module_name}")
    try:
        module = importlib.import_module(module_name)
        print(f"- Successfully imported {module_name} version {getattr(module, '__version__', 'unknown')}")
        print(f"- Module located at: {getattr(module, '__file__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"- Failed to import {module_name}: {e}")
        return False

# Test core dependencies
core_deps = ["fastapi", "uvicorn", "pydantic"]
failed_core = [name for name in core_deps if not test_module(name)]

# Test astrological libraries
astro_deps = ["pyswisseph", "flatlib"]
failed_astro = [name for name in astro_deps if not test_module(name)]

# Print summary
print("\n" + "=" * 50)
print("DEPENDENCY TEST SUMMARY")
print("=" * 50)

if failed_core:
    print(f"Core dependencies with issues: {failed_core}")
    sys.exit(1)
else:
    print("✓ All core dependencies imported successfully")

if failed_astro:
    if len(failed_astro) == len(astro_deps):
        print(f"✗ No astrological libraries were imported successfully: {failed_astro}")
        sys.exit(1)
    else:
        print(f"⚠ Some astrological libraries failed: {failed_astro}")
        print(f"✓ But at least one library is available for calculations")
else:
    print("✓ All astrological libraries imported successfully")

print("\nDependency test passed!")
EOF

# Build and run Docker container to test dependencies
echo -e "${BLUE}[INFO]${NC} Building and running test container..."
if docker build -t dependency-test -f Dockerfile.test .; then
    echo -e "${GREEN}[SUCCESS]${NC} Test image built successfully"

    # Run the test container
    if docker run --rm dependency-test; then
        echo -e "${GREEN}[SUCCESS]${NC} All required dependencies are compatible"
        echo -e "${GREEN}[SUCCESS]${NC} Your requirements.txt is ready for container build"

        # Check if there was a warning about astrological libraries
        if docker run --rm dependency-test | grep -q "Some astrological libraries failed"; then
            echo -e "${YELLOW}[WARNING]${NC} Some astrological libraries have issues but alternatives are available"
            echo -e "${YELLOW}[RECOMMENDATION]${NC} Use the following in your Dockerfile:"
            echo "   - Replace libgcc-9-dev with libgcc-s1"
            echo "   - Add python3-dev to build dependencies"
            echo "   - Set PYTHONPATH to include site-packages directory"
        fi
    else
        echo -e "${RED}[ERROR]${NC} Dependency test failed"
        echo -e "${RED}[ERROR]${NC} Fix the incompatible dependencies before building containers"
        exit 1
    fi
else
    echo -e "${RED}[ERROR]${NC} Failed to build test image"
    echo -e "${RED}[ERROR]${NC} This indicates incompatible dependencies"
    exit 1
fi

echo -e "${YELLOW}[NOTE]${NC} For the ai_service.Dockerfile, use these essential fixes:"
echo "1. Use the libgcc-s1 package instead of libgcc-9-dev"
echo "2. Add python3-dev to build dependencies"
echo "3. Set PYTHONPATH to include site-packages directory"
echo "4. If pyswisseph fails, ensure flatlib is available as a fallback"
