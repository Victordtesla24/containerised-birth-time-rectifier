# Single-stage build for all environments
FROM node:20-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=development
# Use SWC instead of Babel
ENV NEXT_SWCMINIFY=true

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    build-essential \
    bash \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set Python path for node-gyp
ENV PYTHON=/usr/bin/python3

# Copy package files first (for better layer caching)
COPY package.json package-lock.json ./.npmrc ./

# Install dependencies - allow Next.js to use SWC
RUN npm install --global npm@latest && \
    npm cache clean --force && \
    npm install && \
    npm install --save d3@7.8.5 && \
    # Create needed directories
    mkdir -p .next && \
    echo "{}" > .next/fallback-build-manifest.json && \
    chmod -R 777 .next && \
    chmod -R 777 node_modules

# Create directories with proper permissions
RUN mkdir -p scripts && chmod 777 scripts

# Add simplified entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
echo "Running Next.js entrypoint script..."\n\
\n\
# Create the necessary directories and files\n\
mkdir -p .next\n\
echo "{}" > .next/fallback-build-manifest.json\n\
chmod -R 777 .next\n\
\n\
echo "Starting Next.js in development mode..."\n\
exec npm run dev\n\
' > scripts/nextjs-entrypoint.sh && chmod +x scripts/nextjs-entrypoint.sh

# Copy source code
COPY . .
RUN rm -f .babelrc babel.config.js # Remove any Babel configuration to use SWC
RUN chmod -R 777 /app

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -s http://localhost:3000/api/health || exit 1

# Use custom entrypoint
ENTRYPOINT ["bash", "scripts/nextjs-entrypoint.sh"]
