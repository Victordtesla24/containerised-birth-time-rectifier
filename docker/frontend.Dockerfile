# Base stage
FROM node:20-slim as base

# Set working directory
WORKDIR /app

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
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000/health || exit 1

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
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/api/health || curl -f http://localhost:3000/health || exit 1

# Start production server
CMD ["npm", "start"]
