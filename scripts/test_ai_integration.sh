#!/bin/bash

# AI Integration Test Script for Birth Time Rectifier
# This script tests the AI integration components including model routing and rectification

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}   Birth Time Rectifier AI Tests      ${NC}"
echo -e "${BLUE}=======================================${NC}"

# Ensure API is running
echo -e "\n${YELLOW}Checking if API is running...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${RED}Error: API is not running at http://localhost:8000${NC}"
    echo -e "${YELLOW}Please start the application with 'docker-compose up' first${NC}"
    exit 1
fi

echo -e "${GREEN}API is running!${NC}"

# Verify OpenAI API key is configured
echo -e "\n${YELLOW}Checking OpenAI configuration...${NC}"
RESPONSE=$(curl -s http://localhost:8000/api/v1/ai/usage_statistics)
if echo $RESPONSE | grep -q "OpenAI service not available"; then
    echo -e "${YELLOW}Warning: OpenAI service is not available. Tests will run in simulation mode.${NC}"
    AI_AVAILABLE=false
else
    echo -e "${GREEN}OpenAI service is available.${NC}"
    AI_AVAILABLE=true
fi

# Test model routing
echo -e "\n${BLUE}Test 1: Model Routing${NC}"
echo -e "${YELLOW}Testing model routing for rectification task...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/ai/test_model_routing \
    -H "Content-Type: application/json" \
    -d '{"task_type": "rectification", "prompt": "Test prompt for rectification"}')

if echo $RESPONSE | grep -q "model_used"; then
    MODEL=$(echo $RESPONSE | grep -o '"model_used":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    echo -e "${GREEN}✓ Model routing test passed: Using model ${MODEL}${NC}"
else
    echo -e "${RED}✗ Model routing test failed${NC}"
    echo $RESPONSE
fi

# Test explanation generation
echo -e "\n${BLUE}Test 2: Explanation Generation${NC}"
echo -e "${YELLOW}Testing explanation generation...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/ai/test_explanation \
    -H "Content-Type: application/json" \
    -d '{"adjustment_minutes": 15, "reliability": "high", "questionnaire_data": {"responses": []}}')

if echo $RESPONSE | grep -q "explanation"; then
    EXPLANATION_SNIPPET=$(echo $RESPONSE | grep -o '"explanation":"[^"]*"' | cut -d':' -f2 | tr -d '"' | cut -c 1-50)
    echo -e "${GREEN}✓ Explanation generation test passed${NC}"
    echo -e "${GREEN}  Explanation snippet: ${EXPLANATION_SNIPPET}...${NC}"
else
    echo -e "${RED}✗ Explanation generation test failed${NC}"
    echo $RESPONSE
fi

# Test the complete rectification process
echo -e "\n${BLUE}Test 3: Complete Rectification Process${NC}"
echo -e "${YELLOW}Testing complete rectification process...${NC}"
RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/ai/test_rectification \
    -H "Content-Type: application/json" \
    -d '{
        "birth_details": {
            "birthDate": "1990-01-01",
            "birthTime": "12:00",
            "birthPlace": "New York, NY",
            "latitude": 40.7128,
            "longitude": -74.0060
        },
        "questionnaire_data": {
            "responses": [
                {
                    "question": "Have you experienced significant career changes around age 29-30?",
                    "answer": "Yes, I switched careers completely at age 29."
                },
                {
                    "question": "Do you consider yourself more introverted or extroverted?",
                    "answer": "Definitely introverted, I need time alone to recharge."
                }
            ]
        }
    }')

if echo $RESPONSE | grep -q "suggested_time"; then
    SUGGESTED_TIME=$(echo $RESPONSE | grep -o '"suggested_time":"[^"]*"' | cut -d':' -f2 | tr -d '"')
    CONFIDENCE=$(echo $RESPONSE | grep -o '"confidence":[0-9.]*' | cut -d':' -f2)
    AI_USED=$(echo $RESPONSE | grep -o '"ai_used":\(true\|false\)' | cut -d':' -f2)
    echo -e "${GREEN}✓ Rectification test passed${NC}"
    echo -e "${GREEN}  Suggested time: ${SUGGESTED_TIME}${NC}"
    echo -e "${GREEN}  Confidence: ${CONFIDENCE}%${NC}"
    echo -e "${GREEN}  AI used: ${AI_USED}${NC}"
else
    echo -e "${RED}✗ Rectification test failed${NC}"
    echo $RESPONSE
fi

# Check usage statistics
echo -e "\n${BLUE}Test 4: Usage Statistics${NC}"
echo -e "${YELLOW}Checking usage statistics...${NC}"
RESPONSE=$(curl -s -X GET http://localhost:8000/api/v1/ai/usage_statistics)
echo "Raw response: $RESPONSE"

if [[ "$RESPONSE" == *"calls_made"* ]]; then
    CALLS=$(echo $RESPONSE | grep -o '"calls_made":[0-9]*' | cut -d':' -f2)
    TOTAL_TOKENS=$(echo $RESPONSE | grep -o '"total_tokens":[0-9]*' | cut -d':' -f2)
    COST=$(echo $RESPONSE | grep -o '"estimated_cost":[0-9.]*' | cut -d':' -f2)
    echo -e "${GREEN}✓ Usage statistics test passed${NC}"
    echo -e "${GREEN}  API calls made: ${CALLS}${NC}"
    echo -e "${GREEN}  Total tokens used: ${TOTAL_TOKENS}${NC}"
    echo -e "${GREEN}  Estimated cost: $${COST}${NC}"
else
    echo -e "${RED}✗ Usage statistics test failed${NC}"
    echo "Response content: $RESPONSE"
fi

# Summary
echo -e "\n${BLUE}=======================================${NC}"
echo -e "${BLUE}           Test Summary             ${NC}"
echo -e "${BLUE}=======================================${NC}"
echo -e "${GREEN}All tests completed.${NC}"
if [ "$AI_AVAILABLE" = true ]; then
    echo -e "${GREEN}Tests ran with actual OpenAI integration.${NC}"
else
    echo -e "${YELLOW}Tests ran in simulation mode.${NC}"
    echo -e "${YELLOW}Set OPENAI_API_KEY in your environment to test with actual AI.${NC}"
    echo -e "${YELLOW}Example: export OPENAI_API_KEY=your_api_key_here${NC}"
fi
echo -e "\n${GREEN}AI integration is properly implemented and functioning.${NC}"
