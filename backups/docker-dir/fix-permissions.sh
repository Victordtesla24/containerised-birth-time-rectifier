#!/bin/bash

# Script to fix permissions in Docker containers
# This ensures proper access to volumes and mapped files

set -e  # Exit immediately if a command exits with a non-zero status

# Get the user ID and group ID
USER_ID=${LOCAL_USER_ID:-9001}
GROUP_ID=${LOCAL_GROUP_ID:-9001}

echo "Starting with UID: $USER_ID, GID: $GROUP_ID"

# Create the user and group if they don't exist
groupadd -g $GROUP_ID usergroup 2>/dev/null || true
useradd -u $USER_ID -g $GROUP_ID -m -s /bin/bash appuser 2>/dev/null || true

# Fix node_modules permissions in frontend container
if [ -d "/app/node_modules" ]; then
    echo "Fixing node_modules permissions..."
    find /app/node_modules -type d -exec chmod 755 {} \;
    find /app/node_modules -type f -exec chmod 644 {} \;
    chown -R $USER_ID:$GROUP_ID /app/node_modules
fi

# Fix .next directory permissions in frontend container
if [ -d "/app/.next" ]; then
    echo "Fixing .next directory permissions..."
    find /app/.next -type d -exec chmod 755 {} \;
    find /app/.next -type f -exec chmod 644 {} \;
    chown -R $USER_ID:$GROUP_ID /app/.next
fi

# Fix Python virtual environment permissions in backend container
if [ -d "/app/.venv" ]; then
    echo "Fixing Python virtual environment permissions..."
    find /app/.venv -type d -exec chmod 755 {} \;
    find /app/.venv -type f -exec chmod 644 {} \;
    find /app/.venv/bin -type f -exec chmod +x {} \;
    chown -R $USER_ID:$GROUP_ID /app/.venv
fi

# Fix ephemeris data permissions
if [ -d "/app/ephemeris" ]; then
    echo "Fixing ephemeris data permissions..."
    chmod -R 755 /app/ephemeris
    chown -R $USER_ID:$GROUP_ID /app/ephemeris
fi

echo "Permissions fixed successfully."

# Execute the provided command with the specified user
if [ $# -gt 0 ]; then
    exec gosu $USER_ID:$GROUP_ID "$@"
fi
