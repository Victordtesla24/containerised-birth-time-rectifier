#!/bin/bash

# Script to backup questionnaire tests to the persistent Docker volume
# This ensures test persistence across container rebuilds

# Set variables
CONTAINER_NAME=${CONTAINER_PREFIX:-birth-rectifier}-ai
TEST_SOURCE="/app/tests/integration/test_questionnaire.py"
TEST_BACKUP_DIR="/app/tests_backup/integration"

echo "Starting questionnaire test backup process..."

# Ensure the container is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "Error: Container $CONTAINER_NAME is not running!"
    exit 1
fi

# Create backup directory if it doesn't exist
docker exec $CONTAINER_NAME bash -c "mkdir -p $TEST_BACKUP_DIR"

# Copy the test file to the backup directory
docker exec $CONTAINER_NAME bash -c "cp $TEST_SOURCE $TEST_BACKUP_DIR/"

# Verify the backup was successful
if docker exec $CONTAINER_NAME bash -c "[ -f $TEST_BACKUP_DIR/test_questionnaire.py ]"; then
    echo "Backup successful: Questionnaire tests copied to persistent volume"
else
    echo "Error: Backup failed!"
    exit 1
fi

echo "Questionnaire test backup completed successfully."
