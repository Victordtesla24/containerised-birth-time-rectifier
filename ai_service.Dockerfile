FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies with improved reliability and GPU support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    wget \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for GPU usage
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV GPU_ENABLED=true

# Set environment variable for ephemeris files location
ENV SWISSEPH_PATH=/app/ephemeris

# Create Python virtual environment
RUN python -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

# Stage for development
FROM base as development

# Upgrade pip in virtual environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install development dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir websocket-client pyswisseph

# Create cache directories with appropriate permissions
RUN mkdir -p /app/cache /app/logs /app/ephemeris && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris

# Copy ephemeris files and setup script
COPY ephemeris/* /app/ephemeris/
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh

# Keep the container running for development
EXPOSE 8000

# Health check with direct service status endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -s -f http://localhost:8000/api/v1/ai/status || exit 1

# Command to run the application with robust configuration for development
CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--preload", "--log-level", "info"]

# Stage for production
FROM base as production

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir websocket-client pyswisseph

# Copy application code
COPY . .

# Create cache directories with appropriate permissions
RUN mkdir -p /app/cache /app/logs /app/ephemeris && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris

# Execute ephemeris download script in production
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh

# Expose port
EXPOSE 8000

# Health check with direct service status endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -s -f http://localhost:8000/api/v1/ai/status || exit 1

# Command to run the application with robust configuration for production
# - preload ensures models are initialized before handling requests
# - timeout settings prevent long-running operations from crashing the server
CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--preload", "--timeout-keep-alive", "120", "--timeout-graceful-shutdown", "180", "--log-level", "info", "--proxy-headers"]
