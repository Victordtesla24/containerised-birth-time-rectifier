FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    ca-certificates \
    wget \
    unzip \
    gcc \
    python3-dev \
    libc-dev \
    pkg-config \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create Python virtual environment
RUN python -m venv /app/venv
ENV PATH="/app/venv/bin:$PATH"

# Set environment variables
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV SWISSEPH_PATH=/app/ephemeris
ENV PYTHONPATH="/app"
ENV MEDIA_ROOT="/app/media"
ENV TEMP_DIR="/app/temp"
ENV EXPORT_DIR="/app/exports"
ENV LOG_DIR="/app/logs"

# Create required directories with proper permissions
RUN mkdir -p /app/cache /app/logs /app/ephemeris /app/tests /app/media /app/temp /app/exports && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris /app/tests /app/media /app/temp /app/exports

# Install dependencies
COPY python/constraints.txt /app/
RUN pip install --no-cache-dir --upgrade pip wheel setuptools

# Install astrological libraries first
RUN pip install --no-cache-dir --upgrade Cython
RUN pip install --no-cache-dir pyswisseph==2.10.3.2 flatlib==0.2.0

# Install only one multipart package to avoid conflicts
RUN pip install --no-cache-dir python-multipart==0.0.19 && \
    python -c "import python_multipart; print(f'Successfully installed {python_multipart.__file__}')" || echo "Failed to import python_multipart"

# Copy requirements and install main dependencies
COPY python/requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt && \
    pip install --no-cache-dir pytest pytest-asyncio pytest-cov pytest-mock pytest-env pytest-timeout websocket-client

# Download ephemeris files
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    SWISSEPH_PATH=/app/ephemeris /app/scripts/setup/download_ephemeris.sh

# Copy application code
COPY ./ai_service /app/ai_service

# Copy test files into container
COPY ./tests /app/tests

# Create a startup script to verify environment
RUN echo '#!/bin/bash\n\
# Ensure all required directories exist with proper permissions\n\
mkdir -p /app/cache /app/logs /app/ephemeris /app/tests /app/media /app/temp /app/exports\n\
chmod -R 777 /app/cache /app/logs /app/ephemeris /app/tests /app/media /app/temp /app/exports\n\
\n\
# Ensure ephemeris files are available\n\
if [ ! -f "/app/ephemeris/.ephemeris_downloaded" ] || [ "$(ls -A /app/ephemeris/*.se1 2>/dev/null | wc -l)" -eq 0 ]; then\n\
  echo "Ephemeris files missing or incomplete. Running download script..."\n\
  SWISSEPH_PATH=/app/ephemeris /app/scripts/setup/download_ephemeris.sh\n\
else\n\
  echo "Ephemeris files already present in /app/ephemeris"\n\
  find /app/ephemeris -type f -name "*.se1" | head -5\n\
  echo "... (more files)"\n\
fi\n\
\n\
# Verify imports work properly\n\
echo "Verifying Python imports..."\n\
python -c "import python_multipart; print(f\"python_multipart available at {python_multipart.__file__}\")" && \
echo "python_multipart import successful" || echo "WARNING: python_multipart import failed"\n\
\n\
python -c "import pyswisseph as swe; print(f\"pyswisseph version: {swe.__version__}\")" && \
echo "pyswisseph import successful" || echo "WARNING: pyswisseph import failed"\n\
\n\
# Set up environment variables if not already set\n\
if [ -z "$OPENAI_API_KEY" ]; then\n\
  if [ -f "/app/.env" ]; then\n\
    echo "Loading environment variables from .env file"\n\
    export $(grep -v "^#" /app/.env | xargs)\n\
  else\n\
    echo "WARNING: OPENAI_API_KEY not set and no .env file found."\n\
  fi\n\
fi\n\
\n\
# Continue with original command\n\
exec "$@"' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set the entrypoint to our startup script
ENTRYPOINT ["/app/entrypoint.sh"]

# Command to run the application
CMD ["uvicorn", "ai_service.app_wrapper:app_wrapper", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--timeout-keep-alive", "120", "--log-level", "info", "--proxy-headers"]
