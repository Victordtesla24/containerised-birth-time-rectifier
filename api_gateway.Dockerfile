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

# Install pytest and test dependencies
RUN pip install --no-cache-dir pytest pytest-asyncio pytest-cov httpx

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

# Stage for production
FROM base as production

# Install production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./api_gateway /app/api_gateway

# Expose port
EXPOSE 8000

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Create required directories
RUN mkdir -p /app/logs /app/cache && \
    chmod -R 777 /app/logs /app/cache

# Command to run the application with workers for better performance
CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
