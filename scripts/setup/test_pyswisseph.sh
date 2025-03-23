#!/bin/bash
set -e

GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

echo -e "${BLUE}[INFO]${NC} Testing pyswisseph installation in Docker..."

# Create a temporary directory for the test
TEMP_DIR=$(mktemp -d)
echo -e "${BLUE}[INFO]${NC} Using temporary directory: ${TEMP_DIR}"

cleanup() {
  echo -e "${BLUE}[INFO]${NC} Cleaning up temporary environment..."
  rm -rf "${TEMP_DIR}"
}

# Set cleanup to run on script exit
trap cleanup EXIT

# Create a test Dockerfile with extensive diagnostics
cat > "${TEMP_DIR}/Dockerfile.pyswisseph" << EOF
FROM python:3.11-slim

WORKDIR /app

# Print Python version and platform info
RUN python --version && \\
    python -c "import platform; print(platform.platform())"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    build-essential \\
    gcc \\
    libgcc-s1 \\
    python3-dev \\
    && rm -rf /var/lib/apt/lists/*

# Try to diagnose compiler and module issues
RUN echo "Checking for compilers and Python dev files" && \\
    find /usr/ -name "Python.h" | sort && \\
    which gcc && \\
    gcc --version && \\
    python -c "import sys; print('Python include path:', *sys.path, sep='\\n')"

# Create a dedicated virtualenv
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Install Python dependencies and debug the installation process
RUN pip install --upgrade pip setuptools wheel && \\
    echo "Installing pyswisseph with verbose output" && \\
    pip install --verbose pyswisseph==2.10.3.2

# Find where the package was installed
RUN find /app/venv -name "*swiss*" | sort

# Create a test script that checks the module
RUN cat > /app/test_import.py << 'EOS'
import sys
import os
print("Python sys.path:")
for p in sys.path:
    print(f"  {p}")
try:
    import pyswisseph
    print(f"Successfully imported pyswisseph")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
EOS

# Run the test to see if we can import it
RUN python /app/test_import.py || echo "Failed to import, but continuing for diagnostics"

# Copy the diagnostic script for the full test
COPY test_pyswisseph.py /app/test_pyswisseph.py

# Set environment variable
ENV SWISSEPH_PATH=/app/ephemeris
RUN mkdir -p /app/ephemeris

# Run the diagnostics as the default command
CMD ["python", "test_pyswisseph.py"]
EOF

# Create a diagnostic test script
cat > "${TEMP_DIR}/test_pyswisseph.py" << EOF
#!/usr/bin/env python
import os
import sys
import platform
import importlib.util
import importlib.machinery
import subprocess

print("=" * 60)
print("DIAGNOSTIC REPORT FOR PYSWISSEPH")
print("=" * 60)
print(f"Python version: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"Architecture: {platform.machine()}")
print(f"System: {platform.system()}")
print(f"Python executable: {sys.executable}")

print("\n" + "=" * 60)
print("INSTALLED PACKAGES")
print("=" * 60)
try:
    packages = subprocess.check_output([sys.executable, "-m", "pip", "list"]).decode('utf-8')
    print(packages)
except Exception as e:
    print(f"Error listing packages: {e}")

print("\n" + "=" * 60)
print("MODULE SEARCH PATH")
print("=" * 60)
for path in sys.path:
    print(f" - {path}")
    if os.path.exists(path):
        try:
            contents = os.listdir(path)
            if any('swiss' in item.lower() for item in contents):
                print(f"   Found potential pyswisseph files: {[item for item in contents if 'swiss' in item.lower()]}")
        except:
            print(f"   Unable to list directory")

print("\n" + "=" * 60)
print("SEARCHING FOR PYSWISSEPH")
print("=" * 60)
# Search using find command
try:
    find_results = subprocess.check_output(["find", "/", "-name", "*swiss*", "-type", "f", "-o", "-type", "d", "-not", "-path", "*/proc/*", "-not", "-path", "*/sys/*"], stderr=subprocess.DEVNULL).decode('utf-8')
    print("Find results:")
    print(find_results)
except Exception as e:
    print(f"Error running find: {e}")

print("\n" + "=" * 60)
print("ATTEMPTING TO IMPORT PYSWISSEPH")
print("=" * 60)
try:
    # Import the module
    import pyswisseph as swe
    print(f"Successfully imported pyswisseph version {getattr(swe, '__version__', 'unknown')}")
    print(f"Module location: {getattr(swe, '__file__', 'unknown')}")

    # Test setting ephemeris path
    ephemeris_path = os.environ.get('SWISSEPH_PATH', '/app/ephemeris')
    print(f"Using ephemeris path: {ephemeris_path}")

    os.makedirs(ephemeris_path, exist_ok=True)
    swe.set_ephe_path(ephemeris_path)

    print(f"Swiss Ephemeris library path: {swe.get_library_path()}")
    print("All pyswisseph tests passed!")
    sys.exit(0)
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOF

# Change to the temporary directory
cd "${TEMP_DIR}"

# Build the test Docker image without failing on error for diagnostics
echo -e "${BLUE}[INFO]${NC} Building test Docker image..."
docker build -t pyswisseph-test -f Dockerfile.pyswisseph . || {
    echo -e "${YELLOW}[WARNING]${NC} Build had errors but we'll try to run for diagnostics"
}

# Run the test container anyway to gather diagnostics
echo -e "${BLUE}[INFO]${NC} Running pyswisseph test container for diagnostics..."
docker run --rm pyswisseph-test || {
    echo -e "${RED}[ERROR]${NC} Test container failed but we have the diagnostics"
}

echo -e "${YELLOW}[CONCLUSION]${NC} The pyswisseph installation issue requires special handling in Dockerfile."
echo -e "${YELLOW}[RECOMMENDATION]${NC} Use the following approach in your Docker build:"
echo "1. Use the libgcc-s1 package instead of libgcc-9-dev"
echo "2. Install the python3-dev package for Python.h header"
echo "3. Consider using a pre-compiled version or alternative package like flatlib"
echo "4. In ai_service.Dockerfile, move pyswisseph installation to after all system dependencies"

# Create a simplified patch for Dockerfile
echo -e "${BLUE}[INFO]${NC} Creating potential fix for ai_service.Dockerfile..."
cat > "${TEMP_DIR}/pyswisseph_fix.diff" << 'EOF'
--- ai_service.Dockerfile.orig
+++ ai_service.Dockerfile
@@ -5,18 +5,20 @@
 RUN apt-get update && apt-get install -y --no-install-recommends \
     build-essential \
     gcc \
-    libgcc-9-dev \
+    libgcc-s1 \
+    python3-dev \
     && apt-get clean \
     && rm -rf /var/lib/apt/lists/*

 # Create Python virtual environment
 RUN python -m venv /venv
 ENV PATH="/venv/bin:$PATH"

-# Build pyswisseph
+# Install base Python tools
 RUN pip install --upgrade pip setuptools wheel && \
-    pip install --no-cache-dir pyswisseph==2.10.3.2 && \
-    # Verify pyswisseph installation
-    python -c "import pyswisseph; print(f'Successfully built pyswisseph {pyswisseph.__version__}')"
+    pip install --no-cache-dir pyswisseph==2.10.3.2
+
+# Verify that we can import pyswisseph
+RUN python -c "import pyswisseph; print(f'Successfully imported pyswisseph {pyswisseph.__version__}')"

 # Start the base stage
EOF

echo -e "${GREEN}[SUCCESS]${NC} Diagnostic complete. Please review the output to understand the issue."
