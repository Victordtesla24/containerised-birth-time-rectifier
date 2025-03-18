FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies with improved reliability
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    netcat-traditional \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
RUN pip install --no-cache-dir websocket-client

# Install WebSocket and test dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov httpx websockets>=10.4 websocket-client>=1.4.0 aiohttp>=3.8.0

# Expose port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create required directories
RUN mkdir -p /app/logs /app/cache && \
    chmod -R 777 /app/logs /app/cache

# Command to run the application
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]

# Keep the container running for development

# Stage for production
FROM base as production

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir websocket-client

# Install additional WebSocket dependencies
RUN pip install --no-cache-dir websockets>=10.4 websocket-client>=1.4.0 aiohttp>=3.8.0

# Copy application code
COPY ./api_gateway /app/api_gateway

# Expose port
EXPOSE 8000

# Add healthcheck with WebSocket verification
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health && \
        python -c "import websocket; websocket.create_connection('ws://localhost:8000/ws'); print('WebSocket OK')" || exit 1

# Create required directories
RUN mkdir -p /app/logs /app/cache && \
    chmod -R 777 /app/logs /app/cache

# Command to run the application with workers for better performance
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
