# Birth Time Rectifier - Docker Setup

This document provides instructions on how to run the Birth Time Rectifier application using Docker and how to execute end-to-end tests.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose installed (usually comes with Docker Desktop)

## Project Structure

- `docker-compose.yml`: Main Docker Compose file for running the application
- `docker-compose.test.yml`: Docker Compose file for running end-to-end tests
- `run-application-and-tests.sh`: Shell script to easily run the application and tests
- `docker/`: Directory containing Dockerfiles and configuration files
  - `frontend.Dockerfile`: Dockerfile for the frontend service
  - `ai_service.Dockerfile`: Dockerfile for the AI service
  - `redis.conf`: Redis configuration file
  - `redis/log/`: Directory for Redis logs

## Running the Application

You can use the provided shell script to run the application:

```bash
./run-application-and-tests.sh
```

This script provides the following options:
1. Run application only
2. Run end-to-end tests only
3. Run application and then tests
4. Stop running application

Alternatively, you can use Docker Compose commands directly:

```bash
# Start the application
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up -d

# Check the logs
docker compose -f docker-compose.yml logs -f

# Stop the application
docker compose -f docker-compose.yml down
```

## Running End-to-End Tests

To run the end-to-end tests:

```bash
# Using the script
./run-application-and-tests.sh
# Then select option 2 or 3

# Or using Docker Compose directly
docker compose -f docker-compose.test.yml build
docker compose -f docker-compose.test.yml up --abort-on-container-exit
docker compose -f docker-compose.test.yml down
```

## Services

The application consists of the following services:

1. **Frontend** (Next.js):
   - Development port: 3000
   - Health check endpoint: `/api/health`

2. **AI Service** (FastAPI):
   - Development port: 8000
   - Health check endpoint: `/health`

3. **Redis**:
   - Port: 6379
   - Used for caching and message queuing

## Troubleshooting

### Permission Issues

The Birth Time Rectifier containers are configured with robust permission handling. If you encounter permission issues, you can:

1. Use the provided troubleshooting script:
   ```bash
   ./docker/fix-permissions.sh
   ```

   This script will:
   - Check if Docker is running
   - Check for port conflicts and offer to resolve them with sudo
   - Diagnose container health
   - Apply appropriate permission fixes based on container type

2. For specific container permission fixes:
   ```bash
   ./docker/fix-permissions.sh birth-rectifier-frontend
   ```

3. Manual permission fixes:
   - For frontend container:
     ```bash
     docker exec -it birth-rectifier-frontend bash -c "sudo chown -R node:node /app/.next"
     ```
   - For AI service container:
     ```bash
     docker exec -it birth-rectifier-ai bash -c "mkdir -p /app/.venv && chmod -R 777 /app/.venv"
     ```

### Port Conflicts

If you encounter port conflicts, you can use sudo to resolve them:

```bash
# Check for processes using required ports
sudo lsof -i :3000,8000,6379

# Kill processes if necessary
sudo kill -9 <PID>
```

The `fix-permissions.sh` script can handle this automatically.

### Rebuilding Containers

If issues persist after permission fixes, rebuild the affected containers:

```bash
docker-compose build frontend
docker-compose build ai_service
docker-compose up -d
```

## Development

For development purposes, the Docker setup mounts the source code directories as volumes, so changes to the code will be reflected in the running containers without rebuilding the images.

- Frontend code changes will trigger automatic reloading thanks to Next.js development server
- AI service code changes will trigger automatic reloading thanks to uvicorn's `--reload` flag
