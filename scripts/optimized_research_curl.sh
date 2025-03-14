#!/usr/bin/env bash

# -----------------------------------------------------
# Enhanced cURL Command for Birth Time Rectifier Research
# -----------------------------------------------------

# Terminal colors for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

# API credentials and configuration
API_KEY="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"
API_URL="https://api.perplexity.ai/chat/completions"
MODEL="sonar-deep-research"  # For deep research capabilities
RESPONSE_FILE="perplexity_response.json"

# Show usage information
show_usage() {
  echo -e "${BOLD}Usage:${RESET} $0 [OPTION]"
  echo -e "${BOLD}Options:${RESET}"
  echo -e "  ${CYAN}architecture${RESET}    Research system architecture best practices"
  echo -e "  ${CYAN}error-fix${RESET}       Deep analysis for fixing persistent errors"
  echo -e "  ${CYAN}astro-algorithms${RESET} Research astronomical calculation algorithms"
  echo -e "  ${CYAN}optimize${RESET}        Performance optimization strategies"
  echo -e "  ${CYAN}api-design${RESET}      API design best practices"
  echo -e "  ${CYAN}custom \"QUERY\"${RESET}  Send a custom research query"
}

# Function to make the API call
call_perplexity_api() {
  local query="$1"
  local system_prompt="$2"

  echo -e "${YELLOW}Sending query to Perplexity AI...${RESET}"

  # Improved API call with more specific parameters
  curl --location "$API_URL" \
    --header 'accept: application/json' \
    --header 'content-type: application/json' \
    --header "Authorization: Bearer $API_KEY" \
    --data '{
      "model": "'$MODEL'",
      "messages": [
        {
          "role": "system",
          "content": "'"$system_prompt"'"
        },
        {
          "role": "user",
          "content": "'"$query"'"
        }
      ],
      "max_tokens": 4096,
      "temperature": 0.1,
      "top_p": 0.9,
      "frequency_penalty": 1,
      "presence_penalty": 0.2
    }' \
    --output "$RESPONSE_FILE"

  # Display the response with proper formatting
  echo -e "\n${GREEN}${BOLD}Response:${RESET}\n"

  if command -v jq &>/dev/null; then
    # Format with jq if available
    jq -r '.choices[0].message.content' "$RESPONSE_FILE" | less

    # Show token usage statistics
    echo -e "\n${BLUE}${BOLD}Token Usage:${RESET}"
    echo -e "Prompt tokens: $(jq '.usage.prompt_tokens' "$RESPONSE_FILE")"
    echo -e "Completion tokens: $(jq '.usage.completion_tokens' "$RESPONSE_FILE")"
    echo -e "Total tokens: $(jq '.usage.total_tokens' "$RESPONSE_FILE")"
  else
    # Fallback if jq is not available
    grep -o '"content":"[^"]*"' "$RESPONSE_FILE" | sed 's/"content":"//; s/"$//' | less
  fi
}

# Main script logic
case "$1" in
  "architecture")
    system_prompt="You are a senior software architect specializing in distributed systems, microservices, and astrological computation systems. You have extensive experience with FastAPI, React, Docker, and high-performance APIs. You provide meticulously detailed architectural guidance with emphasis on maintainability, performance, and scalability. Always include diagram descriptions, code examples, and implementation patterns."

    query="I'm enhancing a birth time rectification system that calculates astrological charts and performs time correction. The system consists of a FastAPI backend, React frontend, and Redis for session management. What are the best architectural patterns for:

1. Implementing the sequence diagram flow for the complete session-based user journey (from session initialization to chart comparison)
2. Optimizing chart calculation services for complex astrological calculations
3. Structuring API endpoints to ensure backward compatibility
4. Managing session state across multiple API calls
5. Implementing comparison logic for original vs. rectified charts

For each pattern, provide specific implementation approaches including directory structure, class/component relationships, and concrete code examples. Focus on systems that require high accuracy in astronomical calculations."
    ;;

  "error-fix")
    system_prompt="You are an expert FastAPI and Python troubleshooter with deep knowledge of astrological software systems, astronomical calculations, and backend API development. You specialize in systematic debugging of complex issues after multiple failed attempts. Your responses include comprehensive root cause analysis, solutions with code examples, and verification techniques."

    query="I've encountered persistent errors in my birth time rectification API implementation. After two attempts at fixing, I'm still seeing issues in the sequence flow:

1. Detail the systematic approach to debug sequence flow issues in a FastAPI-based API when tests show inconsistent results
2. Provide comprehensive debugging strategies for session management issues with Redis
3. How to properly implement retry logic and fallbacks for external astronomical calculation services
4. Step-by-step process for diagnosing chart comparison logic that works in isolation but fails in the complete sequence
5. Strategies for identifying memory leaks or performance bottlenecks in astrological calculation services

For each area, include specific diagnostic techniques, common root causes, and complete code examples for fixes that ensure robust solutions beyond simple workarounds."
    ;;

  "astro-algorithms")
    system_prompt="You are a senior developer specializing in astronomical and astrological calculation algorithms with expertise in high-precision ephemeris computations, coordinate transformations, and birth time rectification techniques. Your responses include scientific explanations, mathematical foundations, and optimized implementation patterns."

    query="I need to enhance the astrological calculation algorithms in my birth time rectification system:

1. What are the most accurate algorithms for calculating planetary positions for birth chart generation?
2. How should I implement house cusp calculations with support for different house systems (Placidus, Koch, etc.)?
3. What mathematical approaches provide the most accurate birth time rectification based on life events?
4. Techniques for comparing two charts to identify significant differences in planetary positions, house cusps, and aspects
5. Optimized algorithms for aspect calculation with configurable orbs and significance scoring

For each algorithm, provide the mathematical foundation, implementation considerations, and optimized Python code examples that balance accuracy with performance."
    ;;

  "optimize")
    system_prompt="You are a performance optimization expert with deep knowledge of Python backends, FastAPI, and complex computational systems. You specialize in improving response times, reducing resource usage, and scaling systems under load. Your advice includes profiling techniques, optimization patterns, and concrete implementation examples."

    query="I need to optimize my birth time rectification system that's currently experiencing performance issues:

1. Strategies for optimizing complex astronomical calculations in Python
2. Techniques for implementing efficient caching for chart generation results with Redis
3. How to implement parallel processing for multiple chart calculations
4. Performance patterns for comparing large datasets of chart points efficiently
5. Database query optimization for storing and retrieving astrological chart data

For each strategy, provide specific implementation approaches with code examples, expected performance improvements, and methods to measure and verify the optimization results."
    ;;

  "api-design")
    system_prompt="You are an API design expert specializing in RESTful services, versioning strategies, and backend architectures. You have extensive experience with FastAPI, system integration, and building robust APIs for complex applications. Your responses include detailed design patterns, standardization approaches, and practical implementation examples."

    query="I'm refining the API design for my birth time rectification system and need best practices for:

1. Designing a comprehensive session-based API flow from initialization to final results
2. Implementing proper versioning that maintains backward compatibility
3. Structuring endpoints for the sequence flow (session, geocoding, validation, chart generation, questionnaire, rectification, comparison)
4. Error handling patterns that provide meaningful responses across the entire API
5. Documentation approaches that clearly communicate the API's capabilities and requirements

For each area, provide specific implementation approaches including endpoint structure, request/response format examples, and code snippets demonstrating the patterns in FastAPI."
    ;;

  "custom")
    if [ -z "$2" ]; then
      echo -e "${RED}Error: Custom query required.${RESET}"
      show_usage
      exit 1
    fi

    system_prompt="You are a senior developer specializing in astrological software systems, astronomical calculations, API development, and software architecture. Your responses include technical explanations, code examples, and implementation best practices."
    query="$2"
    ;;

  *)
    show_usage
    exit 0
    ;;
esac

# Make the API call
call_perplexity_api "$query" "$system_prompt"

# Clean up
rm -f "$RESPONSE_FILE"
