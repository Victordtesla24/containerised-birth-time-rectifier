FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libgcc-s1 \
    python3-dev \
    curl \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set up environment variables
ENV PYTHONPATH="/app"
ENV SWISSEPH_PATH="/app/ephemeris"
ENV MEDIA_ROOT="/app/media"
ENV TEMP_DIR="/app/temp"
ENV EXPORT_DIR="/app/exports"
ENV LOG_DIR="/app/logs"

# Create required directories
RUN mkdir -p /app/ephemeris /app/media /app/temp /app/exports /app/logs /app/cache && \
    chmod -R 777 /app/ephemeris /app/media /app/temp /app/exports /app/logs /app/cache

# Install dependencies in a specific order to avoid conflicts
COPY python/essential_requirements.txt /app/requirements.txt
COPY python/constraints.txt /app/
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt -c /app/constraints.txt

# Install astrological libraries (which often cause problems)
RUN pip install pyswisseph==2.10.3.2 --no-cache-dir && \
    pip install flatlib==0.2.0 --no-cache-dir && \
    python -c "import sys; print(sys.path); import swisseph; print('Swisseph imported successfully'); import flatlib; print('Flatlib imported successfully')" || \
    echo "Import verification failed - check environment"

# Create symbolic link for pyswisseph
RUN ln -sf /usr/local/lib/python3.11/site-packages/swisseph.py /usr/local/lib/python3.11/site-packages/pyswisseph.py && \
    ln -sf /usr/local/lib/python3.11/site-packages/swisseph /usr/local/lib/python3.11/site-packages/pyswisseph

# Download ephemeris files
COPY scripts/setup/download_ephemeris.sh /app/scripts/setup/
RUN chmod +x /app/scripts/setup/download_ephemeris.sh && \
    /app/scripts/setup/download_ephemeris.sh

# Copy application code
COPY ai_service /app/ai_service
COPY tests /app/tests
COPY scripts /app/scripts

# Create a test verification script
RUN echo '#!/bin/bash\n\
echo "Checking test environment"\n\
python -c "import sys; print(\"Python path:\"); [print(p) for p in sys.path]"\n\
echo "Testing key imports:"\n\
python -c "import swisseph; import flatlib; print(\"Astrological libraries importing OK\")"\n\
python -c "import pytest; print(\"Pytest importing OK\")"\n\
python -c "import openai; print(\"OpenAI library importing OK\")"\n\
python -c "import numpy; import pandas; print(\"Data libraries importing OK\")"\n\
echo "Running test: $*"\n\
exec "$@"' > /app/run_tests.sh && \
    chmod +x /app/run_tests.sh

# Set the script as entrypoint
ENTRYPOINT ["/app/run_tests.sh"]

# Default command runs a simple import test
CMD ["python", "-c", "import swisseph, flatlib, pytest; print('Test environment ready')"]
