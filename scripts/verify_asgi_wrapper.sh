#!/bin/bash
# Verification script for the ASGI wrapper solution
# This script confirms that the ASGI wrapper is properly intercepting health check requests

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Container name
CONTAINER_NAME="birth-rectifier-ai"

echo -e "${YELLOW}Verifying ASGI wrapper implementation...${NC}"
echo "==============================================="

# 1. Check if the container is running
echo -e "${YELLOW}1. Checking container status...${NC}"
if docker inspect --format="{{.State.Running}}" ${CONTAINER_NAME} 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}✓ Container ${CONTAINER_NAME} is running${NC}"
else
    echo -e "${RED}✗ Container ${CONTAINER_NAME} is not running${NC}"
    echo "  Try starting it with: docker-compose up -d ai_service"
    exit 1
fi

# 2. Check if the container is using the correct entry point
echo -e "\n${YELLOW}2. Checking container command...${NC}"
COMMAND=$(docker inspect --format="{{.Config.Cmd}}" ${CONTAINER_NAME})
if echo "${COMMAND}" | grep -q "app_wrapper"; then
    echo -e "${GREEN}✓ Container is using the ASGI wrapper entry point${NC}"
    echo "  Command: ${COMMAND}"
else
    echo -e "${RED}✗ Container is not using the ASGI wrapper entry point${NC}"
    echo "  Current command: ${COMMAND}"
    echo "  Update docker-compose.yml or restart with correct entry point"
    exit 1
fi

# 3. Check if health endpoint is working
echo -e "\n${YELLOW}3. Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(docker exec ${CONTAINER_NAME} curl -s http://localhost:8000/health)
if echo "${HEALTH_RESPONSE}" | grep -q "middleware_bypassed"; then
    echo -e "${GREEN}✓ Health endpoint is working and middleware is bypassed${NC}"
    echo "  Response: ${HEALTH_RESPONSE}"
else
    echo -e "${RED}✗ Health endpoint is not working correctly${NC}"
    echo "  Response: ${HEALTH_RESPONSE}"
    exit 1
fi

# 4. Check all health endpoints
echo -e "\n${YELLOW}4. Testing all health endpoints...${NC}"
ENDPOINTS=("/health" "/api/v1/health" "/system/health" "/health/readiness" "/health/liveness")
ALL_PASSED=true

for endpoint in "${ENDPOINTS[@]}"; do
    STATUS_CODE=$(docker exec ${CONTAINER_NAME} curl -s -o /dev/null -w "%{http_code}" http://localhost:8000${endpoint})

    if [ "$STATUS_CODE" -eq 200 ]; then
        echo -e "${GREEN}✓ Endpoint ${endpoint} returned 200 OK${NC}"
    else
        echo -e "${RED}✗ Endpoint ${endpoint} returned ${STATUS_CODE}${NC}"
        ALL_PASSED=false
    fi
done

if [ "$ALL_PASSED" = true ]; then
    echo -e "\n${GREEN}All verification tests passed!${NC}"
    echo -e "${GREEN}The ASGI wrapper is correctly installed and working.${NC}"
    exit 0
else
    echo -e "\n${RED}Some verification tests failed.${NC}"
    echo -e "${RED}Check the logs for more information: docker logs ${CONTAINER_NAME}${NC}"
    exit 1
fi
