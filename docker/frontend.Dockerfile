# Base stage
FROM node:20-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies for Playwright and build tools
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    build-essential \
    pkg-config \
    libpixman-1-dev \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libexpat1 \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set Python path for node-gyp
ENV PYTHON=/usr/bin/python3

# Set environment variables
ENV NEXT_TELEMETRY_DISABLED=1

# Build stage
FROM base as builder

# Set environment variables for build
ENV NODE_ENV=development

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --ignore-scripts --legacy-peer-deps

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Development stage (for development with hot reloading)
FROM base as development

# Set environment variables for development
ENV NODE_ENV=development
ENV PORT=3000

# Copy package files
COPY package*.json ./

# Install development dependencies
RUN npm ci --legacy-peer-deps

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=60s --timeout=60s --start-period=30s --retries=5 \
    CMD node -e "const http = require('http'); const req = http.get('http://localhost:3000/api/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); }); req.on('error', () => process.exit(1));"

# Start development server
CMD ["npm", "run", "dev"]

# Production stage
FROM base as production

# Set environment variables for production
ENV NODE_ENV=production

# Copy package files, built app, and public directory from build stage
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

# Install production dependencies only
RUN npm ci --omit=dev --legacy-peer-deps

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=60s --timeout=60s --start-period=30s --retries=5 \
    CMD node -e "const http = require('http'); const req = http.get('http://localhost:3000/api/health', (res) => { process.exit(res.statusCode === 200 ? 0 : 1); }); req.on('error', () => process.exit(1));"

# Start production server
CMD ["npm", "start"]
