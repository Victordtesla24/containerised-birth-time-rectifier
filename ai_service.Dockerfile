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

# Create required directories
RUN mkdir -p /app/cache /app/logs /app/ephemeris /app/tests && \
    chmod -R 777 /app/cache /app/logs /app/ephemeris /app/tests

# Install dependencies
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir pip setuptools wheel

# Install pyswisseph before other dependencies - with explicit upgrade and forceful installation
RUN pip install --no-cache-dir --upgrade pip wheel setuptools
RUN pip install --no-cache-dir --upgrade wheel Cython
RUN pip install --no-cache-dir --upgrade pyswisseph==2.10.3.2 flatlib==0.2.0
RUN pip install --no-cache-dir --force-reinstall pyswisseph==2.10.3.2

# Install pyswisseph before other dependencies - with no-binary option for proper compilation
RUN pip install --no-cache-dir --upgrade pip wheel setuptools
RUN pip install --no-cache-dir --upgrade wheel Cython
RUN pip install --no-cache-dir --no-binary :all: pyswisseph==2.10.3.2
RUN pip install --no-cache-dir flatlib==0.2.0

# Verify pyswisseph installation directly in Python
RUN python -c "import sys; print(sys.path); import flatlib; print(f'flatlib version: {flatlib.__version__}');" || echo "Flatlib import failed"
RUN python -c "import sys; print(sys.path); import pyswisseph as swe; print(f'pyswisseph version: {swe.__version__}');" || echo "Pyswisseph import failed"
RUN python -c "import inspect; import pyswisseph as swe; print(inspect.getfile(swe)); print(dir(swe));" || echo "Pyswisseph details failed"
RUN python -c "import sys; print('Python path:'); [print(p) for p in sys.path]" || echo "Python path check failed"

# Install other dependencies
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt && \
    pip install --no-cache-dir websocket-client

# Download ephemeris files
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    SWISSEPH_PATH=/app/ephemeris /app/scripts/setup/download_ephemeris.sh

# Copy application code
COPY ./ai_service /app/ai_service

# Copy test files into container
COPY ./tests /app/tests

# Create a startup script to verify ephemeris files and tests
RUN echo '#!/bin/bash\n\
# Ensure ephemeris directory exists and has files\n\
mkdir -p /app/ephemeris\n\
\n\
# Run the download script if needed\n\
if [ ! -f "/app/ephemeris/.ephemeris_downloaded" ] || [ "$(ls -A /app/ephemeris/*.se1 2>/dev/null | wc -l)" -eq 0 ]; then\n\
  echo "Ephemeris files missing or incomplete. Running download script..."\n\
  SWISSEPH_PATH=/app/ephemeris /app/scripts/setup/download_ephemeris.sh\n\
else\n\
  echo "Ephemeris files already present in /app/ephemeris"\n\
  find /app/ephemeris -type f -name "*.se1" | head -5\n\
  echo "... (more files)"\n\
fi\n\
\n\
# Ensure test directory exists and has files\n\
if [ ! -d "/app/tests" ] || [ "$(ls -A /app/tests 2>/dev/null | wc -l)" -eq 0 ]; then\n\
  echo "Test files missing or directory empty. Check volume mounting."\n\
else\n\
  echo "Test files present in /app/tests"\n\
  find /app/tests -type f -name "*.py" | head -5\n\
  echo "... (more files)"\n\
fi\n\
\n\
# Verify Python can import pyswisseph\n\
if /app/venv/bin/python -c "import pyswisseph as swe; print(f\"pyswisseph version: {swe.__version__}\")"; then\n\
  echo "Astrological libraries successfully imported."\n\
else\n\
  echo "WARNING: Failed to import astrological libraries."\n\
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
