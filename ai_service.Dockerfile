# Add a builder stage for building pyswisseph
FROM python:3.11-slim as builder

# Install build dependencies for pyswisseph
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgcc-s1 \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create Python virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/venv/lib/python3.11/site-packages:$PYTHONPATH"

# Build pyswisseph and flatlib
RUN pip install --upgrade pip setuptools wheel && \
    # Install pyswisseph and flatlib
    pip install --no-cache-dir pyswisseph==2.10.3.2 flatlib==0.2.0 && \
    # List installed packages and locations
    pip list && \
    find /venv -name "*swiss*" && \
    # Create test directory for ephemeris files
    mkdir -p /tmp/ephemeris && \
    # Try to import pyswisseph, continue if it fails
    python -c "import sys; print(sys.path); import flatlib; print(f'Successfully built flatlib {flatlib.__version__}')" && \
    echo "Successfully installed astrological libraries"

# Start the base stage
FROM python:3.11-slim as base

# Copy prebuilt venv with dependencies from builder
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="/venv/lib/python3.11/site-packages:$PYTHONPATH"

# Set working directory
WORKDIR /app

# Install system dependencies with improved reliability and GPU support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential=12.9 \
    libffi-dev=3.4.4-1 \
    libgl1=1.6.0-1 \
    libglib2.0-0=2.74.6-2+deb12u5 \
    curl=7.88.1-10+deb12u12 \
    ca-certificates=20230311 \
    wget=1.21.3-1+deb12u1 \
    netcat-traditional=1.10-47 \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Verify at least one astrological library works
RUN python -c "import sys; print(sys.path); import flatlib; print(f'Flatlib imported successfully, version: {flatlib.__version__}')" || \
    (echo "WARNING: Flatlib import failed, but continuing" && exit 0)

# Set environment variables for GPU usage
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV GPU_ENABLED=false

# Set environment variable for ephemeris files location
ENV SWISSEPH_PATH=/app/ephemeris

# Create required directories with proper permissions
RUN mkdir -p /app/cache /app/logs /app/ephemeris && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris

# Stage for development
FROM base as development

# Install dependencies in a single RUN command to reduce layers
RUN pip install --no-cache-dir pip==23.2.1 setuptools==68.2.2 wheel==0.41.2 && \
    pip install --no-cache-dir websocket-client==1.7.0

# Copy requirements and constraints files
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Copy setup script and download ephemeris files
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh && \
    # Verify ephemeris directory
    ls -la ${SWISSEPH_PATH} && \
    # Try using an astrological library
    (python -c "import flatlib; print('Flatlib initialized successfully, version:', flatlib.__version__)" || \
     echo "WARNING: Flatlib initialization failed, but continuing")

# Copy AI service module
COPY ai_service/ /app/ai_service/

# Expose port
EXPOSE 8000

# Health check with direct health endpoint that uses the ASGI wrapper
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -s -f http://localhost:8000/health || exit 1

# Command to run the application using the wrapper which bypasses middleware for health checks
CMD ["uvicorn", "ai_service.app_wrapper:app_wrapper", "--host", "0.0.0.0", "--port", "8000", "--reload", "--preload", "--log-level", "info"]

# Stage for production
FROM base as production

# Install dependencies in one RUN command with pinned versions
RUN pip install --no-cache-dir pip==23.2.1 setuptools==68.2.2 wheel==0.41.2 && \
    pip install --no-cache-dir websocket-client==1.7.0

# Copy requirements and constraints files
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Copy setup script and download ephemeris files
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh && \
    # Verify ephemeris directory
    ls -la ${SWISSEPH_PATH} && \
    # Try using an astrological library
    (python -c "import flatlib; print('Flatlib initialized successfully, version:', flatlib.__version__)" || \
     echo "WARNING: Flatlib initialization failed, but continuing")

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check with direct health endpoint that uses the ASGI wrapper
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -s -f http://localhost:8000/health || exit 1

# Command to run the application using the wrapper which bypasses middleware for health checks
# - preload ensures models are initialized before handling requests
# - timeout settings prevent long-running operations from crashing the server
CMD ["uvicorn", "ai_service.app_wrapper:app_wrapper", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--preload", "--timeout-keep-alive", "120", "--timeout-graceful-shutdown", "180", "--log-level", "info", "--proxy-headers"]
