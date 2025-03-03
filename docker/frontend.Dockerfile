# Base stage for both development and production
FROM node:20-slim as base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
ENV NODE_ENV=production

# Development stage
FROM base as development
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# Copy package files
COPY package*.json ./

# Install dependencies with cache optimization
RUN mkdir -p /app/node_modules && chown -R node:node /app/
USER node
RUN npm ci

# Copy source code with correct permissions
COPY --chown=node:node . .

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start development server
CMD ["npm", "run", "dev"]

# Build stage
FROM base as builder
COPY package*.json ./
RUN mkdir -p /app/node_modules && chown -R node:node /app/
USER node
RUN npm ci
COPY --chown=node:node . .
RUN npm run build

# Production stage
FROM base as production
RUN mkdir -p /app/node_modules && chown -R node:node /app/
USER node
COPY --chown=node:node --from=builder /app/package*.json ./
RUN npm ci --only=production
COPY --chown=node:node --from=builder /app/.next ./.next
COPY --chown=node:node --from=builder /app/public ./public
COPY --chown=node:node --from=builder /app/next.config.js ./

# Set environment variables
ENV PORT=3000 \
    NEXT_TELEMETRY_DISABLED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Expose the port
EXPOSE 3000

# Start the application
CMD ["npm", "start"]
