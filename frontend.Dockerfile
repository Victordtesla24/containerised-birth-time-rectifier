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
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3=3.11.2-1+b1 \
    build-essential=12.9 \
    bash=5.2.15-2+b7 \
    curl=7.88.1-10+deb12u12 \
    ca-certificates=20230311 \
    git=1:2.39.5-0+deb12u2 \
    && rm -rf /var/lib/apt/lists/*

# Set Python path for node-gyp
ENV PYTHON=/usr/bin/python3

# Create a package.json if it doesn't exist with required dependencies and install all in one step
RUN printf '{\n\
  "name": "birth-time-rectifier",\n\
  "version": "0.1.0",\n\
  "private": true,\n\
  "scripts": {\n\
    "dev": "next dev",\n\
    "build": "next build",\n\
    "start": "next start",\n\
    "lint": "next lint"\n\
  },\n\
  "dependencies": {\n\
    "next": "14.2.0",\n\
    "react": "18.2.0",\n\
    "react-dom": "18.2.0",\n\
    "d3": "7.8.5"\n\
  },\n\
  "devDependencies": {\n\
    "@babel/core": "7.23.5",\n\
    "@babel/preset-env": "7.23.5",\n\
    "@babel/preset-react": "7.23.3",\n\
    "babel-plugin-transform-runtime": "6.23.0"\n\
  }\n\
}' > /app/package.json && \
printf '{\n\
  "presets": [\n\
    ["@babel/preset-env", { "targets": { "node": "current" } }],\n\
    "@babel/preset-react"\n\
  ],\n\
  "plugins": ["transform-runtime"]\n\
}' > /app/babel.config.js && \
npm install --global npm@latest && \
npm cache clean --force && \
npm install && \
# Ensure React and ReactDOM are installed with exact versions
npm install --save react@18.2.0 react-dom@18.2.0 && \
mkdir -p .next public src/pages && \
echo "{}" > .next/fallback-build-manifest.json && \
chmod -R 777 .next && \
chmod -R 777 node_modules

# Create a basic page to ensure it works and prepare directories in one command
RUN printf 'import React from "react";\n\
\n\
export default function Home() {\n\
  return (\n\
    <div>\n\
      <h1>Birth Time Rectifier</h1>\n\
      <p>Frontend application is running!</p>\n\
    </div>\n\
  );\n\
}\n' > /app/src/pages/index.jsx && \
mkdir -p scripts src/styles src/pages/api && \
chmod 777 scripts && \
touch src/styles/globals.css && \
printf 'export default function handler(req, res) {\n\
  res.status(200).json({ status: "ok" });\n\
}' > src/pages/api/health.js

# Create a proper Next.js entrypoint script
RUN printf '#!/bin/bash\n\
set -e\n\
\n\
echo "Running Next.js entrypoint script..."\n\
\n\
# Create the necessary directories and files\n\
mkdir -p .next public src/pages\n\
chmod -R 777 .next\n\
\n\
# Create _app.js if it doesn\'t exist\n\
if [ ! -f "src/pages/_app.jsx" ]; then\n\
  printf "import React from \\"react\\";\n\
import \\"../styles/globals.css\\";\n\
\n\
function MyApp({ Component, pageProps }) {\n\
  return <Component {...pageProps} />;\n\
}\n\
\n\
export default MyApp;" > src/pages/_app.jsx\n\
  mkdir -p src/styles\n\
  touch src/styles/globals.css\n\
fi\n\
\n\
# Check if all required dependencies are installed\n\
if ! npm list react > /dev/null 2>&1 || ! npm list react-dom > /dev/null 2>&1; then\n\
  echo "Installing React and ReactDOM..."\n\
  npm install --save react@18.2.0 react-dom@18.2.0\n\
fi\n\
\n\
# Create an API health endpoint for the health check\n\
mkdir -p src/pages/api\n\
if [ ! -f "src/pages/api/health.js" ]; then\n\
  printf "export default function handler(req, res) {\n\
  res.status(200).json({ status: \\"ok\\" });\n\
}" > src/pages/api/health.js\n\
fi\n\
\n\
echo "Starting Next.js in development mode..."\n\
exec npx next dev\n' > scripts/nextjs-entrypoint.sh && chmod +x scripts/nextjs-entrypoint.sh

# Copy source code if available (will be overridden by volume mounts in dev)
COPY . .

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=60s --retries=3 \
    CMD curl -s http://localhost:3000/api/health || exit 1

# Use custom entrypoint
ENTRYPOINT ["bash", "scripts/nextjs-entrypoint.sh"]
