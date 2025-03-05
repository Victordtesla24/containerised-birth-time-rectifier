# Base Image with CUDA 12.2 and Node.js 20 LTS
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as builder

# System Dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    nodejs \
    npm \
    redis-server \
    libgl1 \
    libglib2.0-0 \
    libxi6 \
    libxext6 \
    libx11-6 \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./
COPY yarn.lock ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production image
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

# Copy built assets from builder
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json

# AI Framework Setup with version pinning
RUN pip install --no-cache-dir \
    torch==2.1.1+cu121 \
    transformers==4.38.2 \
    redis==5.0.1

# Install production dependencies
RUN npm install --production

# Environment variables
ENV NODE_ENV=production
ENV DOCKER_AI_AGENT=enabled
ENV GPU_MEMORY_FRACTION=0.7

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || exit 1

# Expose ports
EXPOSE 3000 8000 6379

# Start the application
CMD ["npm", "start"]

# Python image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "ai_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
