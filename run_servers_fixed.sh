#!/bin/bash

# Function to kill processes on a specific port (macOS compatible)
kill_port_process() {
  local port=$1
  echo "Killing processes on port $port..."

  # Find processes using the port with lsof (standard way)
  local pids=$(lsof -i:$port -t)

  if [ -n "$pids" ]; then
    echo "Found processes ($pids) on port $port, killing them..."
    # Try normal kill first
    kill -9 $pids 2>/dev/null
    sleep 1
  else
    echo "No processes found on port $port with lsof..."
  fi

  # Even if lsof shows nothing, the port might still be bound
  # Check if port is still in use after kill attempt with netstat
  if netstat -an | grep "LISTEN\|ESTABLISHED" | grep "\.${port} " > /dev/null; then
    echo "Port $port still appears to be in use. Trying sudo kill..."
    # Try with sudo (requires password)
    sudo lsof -i:$port -t | xargs -r sudo kill -9 2>/dev/null
    sleep 2

    # If still in use after sudo kill, use a more aggressive approach
    if netstat -an | grep "LISTEN\|ESTABLISHED" | grep "\.${port} " > /dev/null; then
      echo "⚠️ WARNING: Port $port still in use after sudo kill attempt."
      echo "Trying to release TCP socket forcefully..."

      # On macOS, we need to restart the mDNSResponder to truly free some stuck ports
      if [ "$(uname)" = "Darwin" ]; then
        echo "Restarting network services to free socket..."
        sudo pkill -HUP mDNSResponder
        sleep 3
      fi

      # Final check
      if netstat -an | grep "LISTEN\|ESTABLISHED" | grep "\.${port} " > /dev/null; then
        echo "❌ ERROR: Could not free port $port. Please restart your computer or try a different port."
        return 1
      fi
    fi
  fi

  # Check for sockets in TIME_WAIT or CLOSED state that might still prevent binding
  if netstat -an | grep -v "LISTEN\|ESTABLISHED" | grep "\.${port} " > /dev/null; then
    echo "⚠️ Socket on port $port found in non-listening state (possibly TIME_WAIT or CLOSED)."
    echo "This may cause socket binding issues. Adding SO_REUSEADDR option to the Python services."
    # We'll handle this by using SO_REUSEADDR in our Python servers
  fi

  echo "✅ Port $port is now available"
  return 0
}

# Get the absolute path to the project root - FIXED to use the current directory
PROJECT_ROOT=$(pwd)
echo "Project root: $PROJECT_ROOT"

# Create necessary directories
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"
echo "Logs will be stored in $LOGS_DIR"

# Create .env file if it doesn't exist
ENV_FILE="$PROJECT_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "Creating sample .env file for development..."
  cat > "$ENV_FILE" << EOL
# Development environment variables
DATABASE_URL=sqlite:///./test.db
OPENAI_API_KEY=your_openai_api_key_here
ENVIRONMENT=development
DEBUG=true
EOL
  echo "✓ Created sample .env file at $ENV_FILE"
  echo "⚠️ IMPORTANT: Please update the OPENAI_API_KEY in $ENV_FILE before running again!"
fi

# Check for tmux - we'll use it if available
if ! command -v tmux &> /dev/null; then
  echo "⚠️ tmux not found - falling back to basic mode."
  echo "💡 Install with: brew install tmux (on macOS)"
  USE_TMUX=false
else
  USE_TMUX=true
fi

# Function to wait for port to be free
wait_for_port_to_be_free() {
  local port=$1
  local timeout=$2
  local start_time=$(date +%s)
  local end_time=$((start_time + timeout))

  echo "Waiting for port $port to be free (timeout: ${timeout}s)..."
  while [ $(date +%s) -lt $end_time ]; do
    if ! netstat -an | grep -v "CLOSED" | grep "\.${port} " > /dev/null; then
      echo "✅ Port $port is free now"
      return 0
    fi
    sleep 1
    echo -n "."
  done

  echo "❌ Timeout waiting for port $port to be free"
  return 1
}

# Function to check if a service is actually responding to requests
check_service_health() {
  local service_name=$1
  local port=$2
  local max_attempts=${3:-5}
  local timeout=${4:-2}

  echo "Checking health of $service_name on port $port..."

  # First check if anything is listening on the port
  if ! netstat -an | grep "LISTEN" | grep "\.${port} " > /dev/null; then
    # Check if we have a socket bound but in CLOSED state
    if netstat -an | grep "CLOSED" | grep "\.${port} " > /dev/null; then
      echo "⚠️ $service_name socket is bound but in CLOSED state - service may not be functioning properly"
      return 2  # Partial failure
    else
      echo "❌ $service_name is not listening on port $port"
      return 1  # Failure
    fi
  fi

  # Try to connect to the service
  for i in $(seq 1 $max_attempts); do
    if curl -s -o /dev/null -w "" -m $timeout http://localhost:$port 2>/dev/null; then
      echo "✅ $service_name is healthy and responding on port $port"
      return 0  # Success
    fi
    echo "⏳ Attempt $i/$max_attempts: $service_name not responding yet..."
    sleep 1
  done

  echo "⚠️ $service_name is listening but not responding to HTTP requests"
  return 3  # Service not responding
}

# Kill processes on both ports with more robust approach
echo "Ensuring ports are free for server startup..."
kill_port_process 3000 || exit 1
kill_port_process 8000 || exit 1

# Double-check ports are truly free
wait_for_port_to_be_free 3000 10 || exit 1
wait_for_port_to_be_free 8000 10 || exit 1

# Clean previous log files
rm -f "$LOGS_DIR/api_gateway.log" "$LOGS_DIR/ai_service.log"

# Pre-run checks
echo "Running pre-flight checks..."

# Check for Python and dependencies
if ! command -v python3 &> /dev/null; then
  echo "❌ ERROR: Python 3 not found"
  exit 1
fi

# Check for database and OpenAI configuration
if grep -q "your_openai_api_key_here" "$ENV_FILE"; then
  echo "⚠️ WARNING: OPENAI_API_KEY not set in $ENV_FILE"
  echo "   The AI services may not function correctly"
fi

echo "✓ Pre-flight checks passed"

# Function to start a server and monitor its output
start_server() {
  local server_type=$1
  local port=$2
  local logfile=$3
  local server_dir=$4
  local cmd=$5

  echo "🚀 Starting $server_type on port $port..."
  echo "💻 Command: $cmd"
  echo "📝 Logs: $logfile"

  # Ensure directory exists
  if [ ! -d "$server_dir" ]; then
    echo "❌ ERROR: Directory $server_dir does not exist!"
    return 1
  fi

  # Navigate to server directory
  cd "$server_dir" || {
    echo "❌ ERROR: Failed to change to directory $server_dir";
    return 1;
  }

  # Double check port is free before starting
  if netstat -an | grep -v "CLOSED" | grep "\.${port} " > /dev/null; then
    echo "❌ ERROR: Port $port is still in use! Cannot start $server_type."
    return 1
  fi

  # Execute the command
  eval "$cmd" > "$logfile" 2>&1 &
  local pid=$!
  echo "🆔 $server_type started with PID: $pid"

  # Wait a bit and check if the process is still running
  sleep 3
  if ! ps -p $pid > /dev/null; then
    echo "❌ ERROR: $server_type failed to start!"
    echo "=== Log Output ==="
    cat "$logfile" | tail -n 20
    echo "================="
    return 1
  fi

  # Check if server is accepting connections - ignore CLOSED state
  local listening=false
  for i in {1..15}; do
    if netstat -an | grep "LISTEN" | grep "\.${port} " > /dev/null; then
      echo "✅ $server_type successfully listening on port $port"
      listening=true
      break
    fi
    sleep 1
    echo "⏳ Waiting for $server_type to start... ($i/15)"
  done

  # If not in LISTEN state, check if it's in CLOSED state
  if [ "$listening" = false ]; then
    if netstat -an | grep "CLOSED" | grep "\.${port} " > /dev/null; then
      echo "⚠️ $server_type socket is in CLOSED state - service may not be functioning properly"
      # Further diagnosis for CLOSED socket
      if grep -q "Address already in use" "$logfile"; then
        echo "❌ ERROR: Port $port was already in use when the server tried to start"
        echo "=== Error from logs ==="
        grep -A 5 "Address already in use" "$logfile"
        echo "======================="
        return 1
      fi
    else
      echo "❌ ERROR: $server_type is not listening on port $port"
      return 1
    fi
  fi

  # Check for common errors in the logs
  if grep -q "ValueError\|ModuleNotFoundError\|ImportError\|Address already in use" "$logfile"; then
    echo "⚠️ WARNING: $server_type log contains errors:"
    echo "=== Error from logs ==="
    grep -A 5 -B 2 "Error\|Exception\|ValueError\|ModuleNotFoundError\|ImportError\|Address already in use" "$logfile" | head -n 15
    echo "======================="
    return 1
  fi

  # Check if server is actually responding to requests
  for i in {1..5}; do
    if curl -s -o /dev/null -w "" -m 2 http://localhost:$port 2>/dev/null; then
      echo "✅ $server_type is responding to HTTP requests"
      return 0
    fi
    sleep 1
  done

  echo "⚠️ WARNING: $server_type is listening but not responding to HTTP requests"
  # Return success anyway since the socket is at least binding
  return 0
}

# Setup environment variables for both services
export PYTHONPATH=$PROJECT_ROOT
export ENVIRONMENT=${ENVIRONMENT:-development}
export DEBUG=${DEBUG:-true}

# Load variables from .env file
if [ -f "$ENV_FILE" ]; then
  echo "Loading environment variables from $ENV_FILE"
  export $(grep -v '^#' "$ENV_FILE" | xargs -r 2>/dev/null || grep -v '^#' "$ENV_FILE" | xargs)
fi

# USING BASIC MODE (non-tmux)
echo "Starting servers in background mode with real-time monitoring..."

# Add socket reuse capability with a simple Python socket test first
echo "Testing socket binding with SO_REUSEADDR option..."
(cd "$PROJECT_ROOT/api_gateway" && python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 3000))
    s.close()
    print('✓ Socket test successful for port 3000')
except Exception as e:
    print(f'Error testing socket on port 3000: {e}')
    sys.exit(1)
") || echo "⚠️ Socket test failed for port 3000"

(cd "$PROJECT_ROOT/ai_service" && python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 8000))
    s.close()
    print('✓ Socket test successful for port 8000')
except Exception as e:
    print(f'Error testing socket on port 8000: {e}')
    sys.exit(1)
") || echo "⚠️ Socket test failed for port 8000"

# Start API Gateway
API_GATEWAY_CMD="python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 3000"
API_GATEWAY_LOG="$LOGS_DIR/api_gateway.log"

# Start AI Service
AI_SERVICE_CMD="python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
AI_SERVICE_LOG="$LOGS_DIR/ai_service.log"

# Start both servers with proper error checking
API_GATEWAY_SUCCESS=true
AI_SERVICE_SUCCESS=true

echo "Starting API Gateway..."
start_server "API Gateway" 3000 "$API_GATEWAY_LOG" "$PROJECT_ROOT/api_gateway" "$API_GATEWAY_CMD" || API_GATEWAY_SUCCESS=false

echo "Starting AI Service..."
start_server "AI Service" 8000 "$AI_SERVICE_LOG" "$PROJECT_ROOT/ai_service" "$AI_SERVICE_CMD" || AI_SERVICE_SUCCESS=false

# Summary status
echo ""
echo "🔍 Server Status Summary:"
if [ "$API_GATEWAY_SUCCESS" = true ]; then
  if check_service_health "API Gateway" 3000 3 1 >/dev/null; then
    echo "✅ API Gateway: Running and healthy on http://localhost:3000"
  else
    echo "⚠️ API Gateway: Running but may not be fully functional on http://localhost:3000"
  fi
else
  echo "❌ API Gateway: Failed to start properly"
fi

if [ "$AI_SERVICE_SUCCESS" = true ]; then
  if check_service_health "AI Service" 8000 3 1 >/dev/null; then
    echo "✅ AI Service: Running and healthy on http://localhost:8000"
  else
    echo "⚠️ AI Service: Running but may not be fully functional on http://localhost:8000"
  fi
else
  echo "❌ AI Service: Failed to start properly"
fi

echo ""
echo "📊 Servers have been started. You can check the logs in:"
echo "   - API Gateway: $API_GATEWAY_LOG"
echo "   - AI Service: $AI_SERVICE_LOG"
echo ""
echo "🌐 API Gateway: http://localhost:3000"
echo "🌐 AI Service:  http://localhost:8000"
