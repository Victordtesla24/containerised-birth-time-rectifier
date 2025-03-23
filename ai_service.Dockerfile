FROM python:3.11-slim as base

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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for GPU usage
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV GPU_ENABLED=false

# Set environment variable for ephemeris files location
ENV SWISSEPH_PATH=/app/ephemeris

# Create Python virtual environment
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Stage for development
FROM base as development

# Install dependencies in a single RUN command to reduce layers
RUN pip install --no-cache-dir pip==23.2.1 setuptools==68.2.2 wheel==0.41.2 && \
    pip install --no-cache-dir pyswisseph==2.10.3.2 websocket-client==1.7.0 && \
    mkdir -p /app/cache /app/logs /app/ephemeris && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris

# Copy requirements and constraints files
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Copy ephemeris files and setup script
COPY ephemeris/* /app/ephemeris/
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh

# Expose port
EXPOSE 8000

# Health check with direct health endpoint that uses the ASGI wrapper
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -s -f http://localhost:8000/health || exit 1

# Command to run the application using the wrapper which bypasses middleware for health checks
CMD ["uvicorn", "ai_service.app_wrapper:app_wrapper", "--host", "0.0.0.0", "--port", "8000", "--reload", "--preload", "--log-level", "info"]

# Stage for production
FROM base as production

# Install all dependencies in one RUN command with pinned versions
RUN pip install --no-cache-dir pip==23.2.1 setuptools==68.2.2 wheel==0.41.2 && \
    pip install --no-cache-dir pyswisseph==2.10.3.2 websocket-client==1.7.0 && \
    mkdir -p /app/cache /app/logs /app/ephemeris && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris

# Copy requirements and constraints files
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

# Copy application code
COPY . .

# Execute ephemeris download script in production
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh

# Expose port
EXPOSE 8000

# Health check with direct health endpoint that uses the ASGI wrapper
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -s -f http://localhost:8000/health || exit 1

# Command to run the application using the wrapper which bypasses middleware for health checks
# - preload ensures models are initialized before handling requests
# - timeout settings prevent long-running operations from crashing the server
CMD ["uvicorn", "ai_service.app_wrapper:app_wrapper", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--preload", "--timeout-keep-alive", "120", "--timeout-graceful-shutdown", "180", "--log-level", "info", "--proxy-headers"]
