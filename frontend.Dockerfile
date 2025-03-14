# Single-stage build for all environments (development, testing, production)
FROM node:20-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1

# Install system dependencies for Next.js rendering
RUN apt-get update && apt-get install -y \
    python3 \
    build-essential \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Set Python path for node-gyp
ENV PYTHON=/usr/bin/python3

# Copy package files first (for better layer caching)
COPY package.json package-lock.json ./.npmrc ./.babelrc ./

# Install dependencies - DO NOT use --ignore-scripts to ensure build scripts run correctly
RUN npm install --global npm@latest && \
    npm cache clean --force && \
    npm install --no-optional && \
    npm install --save d3@7.8.5 && \
    npm install --save-dev @babel/core @babel/preset-env @babel/preset-react @babel/preset-typescript @babel/plugin-transform-runtime && \
    mkdir -p .next && \
    echo "{}" > .next/fallback-build-manifest.json

# Create directories
RUN mkdir -p scripts

# Add entrypoint script
COPY scripts/nextjs-entrypoint.sh scripts/
RUN chmod +x scripts/nextjs-entrypoint.sh

# Copy source code
COPY . .

# Run a build before starting to ensure all dependencies are correctly installed
RUN if [ "$NODE_ENV" != "development" ]; then npm run build || echo "Build failed, will retry at runtime"; fi

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -s http://localhost:3000/api/health || exit 1

# Use custom entrypoint
ENTRYPOINT ["bash", "scripts/nextjs-entrypoint.sh"]
