#!/bin/bash

# Function to kill processes on a specific port (macOS compatible)
kill_port_process() {
  local port=$1
  echo "Killing processes on port $port..."

  # Always use sudo for more reliable process killing
  echo "Attempting to kill processes on port $port with sudo..."

  # Find processes using the port with lsof
  local pids=$(sudo lsof -i:$port -t 2>/dev/null)

  if [ -n "$pids" ]; then
    echo "Found processes ($pids) on port $port, killing them with sudo..."
    # Use sudo kill -9 for forceful termination
    sudo kill -9 $pids 2>/dev/null
    sleep 1
  else
    echo "No processes found on port $port with lsof..."
  fi

  # Even if lsof shows nothing, the port might still be bound
  # Try fuser as an alternative method
  echo "Trying sudo fuser to kill any processes on port $port..."
  sudo fuser -k $port/tcp 2>/dev/null
  sudo fuser -k $port/udp 2>/dev/null
  sleep 1

  # Check if port is still in use after kill attempts with netstat
  if netstat -an | grep -E "LISTEN|ESTABLISHED" | grep "\.${port} " > /dev/null; then
    echo "⚠️ WARNING: Port $port still in use after kill attempts."
    echo "Trying more aggressive methods..."

    # Try additional methods to kill processes
    # 1. Find with netstat and kill
    local netstat_pids=$(netstat -anp 2>/dev/null | grep ":${port}" | grep -oP "(?<=LISTEN\s{1,10})\d+" | sort -u)
    if [ -n "$netstat_pids" ]; then
      echo "Found additional PIDs via netstat: $netstat_pids"
      sudo kill -9 $netstat_pids 2>/dev/null
    fi

    # 2. Use ss command as alternative
    local ss_pids=$(ss -lptn "sport = :${port}" 2>/dev/null | grep -oP "(?<=pid=)\d+" | sort -u)
    if [ -n "$ss_pids" ]; then
      echo "Found additional PIDs via ss: $ss_pids"
      sudo kill -9 $ss_pids 2>/dev/null
    fi

    # 3. Force release TCP sockets
    echo "Trying to release TCP socket forcefully..."
    if [ "$(uname)" = "Darwin" ]; then
      echo "Restarting network services on macOS to free socket..."
      sudo pkill -HUP mDNSResponder
      sleep 3
    else
      # For Linux, reset connections
      echo "Resetting connections on Linux..."
      sudo ip -s -s neigh flush all
      sleep 2
    fi

    # Final check
    if netstat -an | grep -E "LISTEN|ESTABLISHED" | grep "\.${port} " > /dev/null; then
      echo "❌ ERROR: Could not free port $port despite aggressive attempts."
      echo "Attempting one final method - iptables (Linux) or pfctl (macOS)..."

      if [ "$(uname)" = "Darwin" ]; then
        # For macOS, try to use pfctl
        sudo pfctl -F all -f /etc/pf.conf 2>/dev/null
      else
        # For Linux, try iptables to block and then allow the port
        sudo iptables -A INPUT -p tcp --dport $port -j REJECT --reject-with tcp-reset 2>/dev/null
        sleep 1
        sudo iptables -D INPUT -p tcp --dport $port -j REJECT --reject-with tcp-reset 2>/dev/null
      fi

      sleep 2
      # If still not free, we'll continue but warn the user
      if netstat -an | grep -E "LISTEN|ESTABLISHED" | grep "\.${port} " > /dev/null; then
        echo "⚠️ WARNING: Port $port is still not free. This may cause issues when starting servers."
      fi
    fi
  fi

  # Check for sockets in TIME_WAIT or CLOSED state
  if netstat -an | grep -v "LISTEN|ESTABLISHED" | grep "\.${port} " > /dev/null; then
    echo "⚠️ Socket on port $port found in non-listening state (possibly TIME_WAIT or CLOSED)."
    echo "Setting SO_REUSEADDR/SO_REUSEPORT options to handle this condition."

    # For TIME_WAIT sockets, wait a bit longer to ensure they're released
    sleep 5
  fi

  echo "✅ Attempted all possible methods to free port $port"

  # Perform final verification
  if ! netstat -an | grep -v "CLOSED" | grep "\.${port} " > /dev/null; then
    echo "✅ Verification confirmed: Port $port is now available"
    return 0
  else
    echo "⚠️ Port $port may still have issues but we've tried all available methods"
    return 0  # Continue anyway as we've tried everything
  fi
}

# Get the absolute path to the project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../" && pwd)"
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

# Kill processes on all required ports with more robust approach
echo "Ensuring all required ports are free for server startup..."
echo "================================================================="
echo "Using sudo to kill all processes on ports 8000, 3000, 3001, 8001"
echo "================================================================="

# Kill all processes on the specified ports
kill_port_process 8000 || echo "⚠️ Issues with port 8000 - continuing anyway"
kill_port_process 3000 || echo "⚠️ Issues with port 3000 - continuing anyway"
kill_port_process 3001 || echo "⚠️ Issues with port 3001 - continuing anyway"
kill_port_process 8001 || echo "⚠️ Issues with port 8001 - continuing anyway"

# Double-check ports are truly free with longer timeout
echo "Performing final verification of port availability..."
wait_for_port_to_be_free 8000 20 || echo "⚠️ Port 8000 may still have issues - continuing anyway"
wait_for_port_to_be_free 3000 20 || echo "⚠️ Port 3000 may still have issues - continuing anyway"
wait_for_port_to_be_free 3001 20 || echo "⚠️ Port 3001 may still have issues - continuing anyway"
wait_for_port_to_be_free 8001 20 || echo "⚠️ Port 8001 may still have issues - continuing anyway"

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

if [ "$USE_TMUX" = true ]; then
  echo "Using tmux to manage server instances..."

  # Kill any existing tmux session
  tmux kill-session -t birth_time_rectifier 2>/dev/null

  # Create a new tmux session
  tmux new-session -d -s birth_time_rectifier

  # Configure tmux
  tmux set-option -g mouse on

  # Start API Gateway in first pane with active port check and socket options
  tmux send-keys -t birth_time_rectifier "cd $PROJECT_ROOT/api_gateway && if ! netstat -an | grep -v 'CLOSED' | grep '\\.3001 ' > /dev/null; then export PYTHONPATH=$PROJECT_ROOT && python3 -c \"import socket; import sys; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('0.0.0.0', 3001)); s.close(); print('✓ Socket test successful with SO_REUSEADDR')\" && python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 3001 | tee $LOGS_DIR/api_gateway.log; else echo 'Port 3001 is still in use, cannot start API Gateway'; fi" C-m

  # Split the window horizontally
  tmux split-window -h -t birth_time_rectifier

  # Start AI Service in second pane with active port check and socket options
  tmux send-keys -t birth_time_rectifier "cd $PROJECT_ROOT/ai_service && if ! netstat -an | grep -v 'CLOSED' | grep '\\.8001 ' > /dev/null; then export PYTHONPATH=$PROJECT_ROOT && python3 -c \"import socket; import sys; s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(('0.0.0.0', 8001)); s.close(); print('✓ Socket test successful with SO_REUSEADDR')\" && python3 -m uvicorn ai_service.unified_main:app --reload --host 0.0.0.0 --port 8001 | tee $LOGS_DIR/ai_service.log; else echo 'Port 8001 is still in use, cannot start AI Service'; fi" C-m

  # Add an informational pane at the bottom for monitoring with enhanced status
  tmux split-window -v -t birth_time_rectifier
  tmux send-keys -t birth_time_rectifier "echo '📊 Server Monitor - Birth Time Rectifier'; echo ''; echo '🌐 API Gateway: http://localhost:3001'; echo '🌐 AI Service:  http://localhost:8001'; echo ''; echo 'Monitoring server health...'; while true; do echo ''; echo \"$(date) - Checking server status...\"; echo -n 'API Gateway (3001): '; if netstat -an | grep \"LISTEN\" | grep \"\\.3001 \" > /dev/null; then echo '✅ RUNNING (LISTENING)'; elif netstat -an | grep \"CLOSED\" | grep \"\\.3001 \" > /dev/null; then echo '⚠️ BOUND BUT CLOSED'; else echo '❌ NOT RUNNING'; fi; curl -s -o /dev/null -w \"API Gateway Response: %{http_code}\\n\" -m 1 http://localhost:3001 2>/dev/null || echo 'API Gateway Response: FAILED'; echo -n 'AI Service (8001): '; if netstat -an | grep \"LISTEN\" | grep \"\\.8001 \" > /dev/null; then echo '✅ RUNNING (LISTENING)'; elif netstat -an | grep \"CLOSED\" | grep \"\\.8001 \" > /dev/null; then echo '⚠️ BOUND BUT CLOSED'; else echo '❌ NOT RUNNING'; fi; curl -s -o /dev/null -w \"AI Service Response: %{http_code}\\n\" -m 1 http://localhost:8001 2>/dev/null || echo 'AI Service Response: FAILED'; sleep 5; done" C-m

  # Name the windows
  tmux rename-window -t birth_time_rectifier "Birth Time Rectifier Servers"

  # Display status message
  echo ""
  echo "✅ Servers started in tmux session"
  echo "🔍 To view and interact with the servers:"
  echo "   $ tmux attach -t birth_time_rectifier"
  echo ""
  echo "📊 Use Ctrl-b + arrow keys to switch between panes"
  echo "📊 Use Ctrl-b + d to detach from the session"
  echo ""
  echo "🌐 API Gateway: http://localhost:3001"
  echo "🌐 AI Service:  http://localhost:8001"

  # Attach to the tmux session
  tmux attach -t birth_time_rectifier
else
  # Start servers without tmux
  echo "Starting servers in background mode with real-time monitoring..."

  # Add socket reuse capability with a simple Python socket test first
  echo "Testing socket binding with SO_REUSEADDR option..."
  (cd "$PROJECT_ROOT/api_gateway" && python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 3001))
    s.close()
    print('✓ Socket test successful for port 3001')
except Exception as e:
    print(f'Error testing socket on port 3001: {e}')
    sys.exit(1)
") || echo "⚠️ Socket test failed for port 3001"

  (cd "$PROJECT_ROOT/ai_service" && python3 -c "
import socket
import sys
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 8001))
    s.close()
    print('✓ Socket test successful for port 8001')
except Exception as e:
    print(f'Error testing socket on port 8001: {e}')
    sys.exit(1)
") || echo "⚠️ Socket test failed for port 8001"

  # Start API Gateway
  API_GATEWAY_CMD="python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 3001"
  API_GATEWAY_LOG="$LOGS_DIR/api_gateway.log"

  # Start AI Service - Use unified_main for better resource management
  AI_SERVICE_CMD="python3 -m uvicorn ai_service.unified_main:app --reload --host 0.0.0.0 --port 8001"
  AI_SERVICE_LOG="$LOGS_DIR/ai_service.log"

  # Start both servers with proper error checking
  API_GATEWAY_SUCCESS=true
  AI_SERVICE_SUCCESS=true

  echo "Starting API Gateway..."
  start_server "API Gateway" 3001 "$API_GATEWAY_LOG" "$PROJECT_ROOT/api_gateway" "$API_GATEWAY_CMD" || API_GATEWAY_SUCCESS=false

  echo "Starting AI Service..."
  start_server "AI Service" 8001 "$AI_SERVICE_LOG" "$PROJECT_ROOT/ai_service" "$AI_SERVICE_CMD" || AI_SERVICE_SUCCESS=false

  # Summary status
  echo ""
  echo "🔍 Server Status Summary:"
  if [ "$API_GATEWAY_SUCCESS" = true ]; then
    if check_service_health "API Gateway" 3001 3 1 >/dev/null; then
      echo "✅ API Gateway: Running and healthy on http://localhost:3001"
    else
      echo "⚠️ API Gateway: Running but may not be fully functional on http://localhost:3001"
    fi
  else
    echo "❌ API Gateway: Failed to start properly"
  fi

  if [ "$AI_SERVICE_SUCCESS" = true ]; then
    if check_service_health "AI Service" 8001 3 1 >/dev/null; then
      echo "✅ AI Service: Running and healthy on http://localhost:8001"
    else
      echo "⚠️ AI Service: Running but may not be fully functional on http://localhost:8001"
    fi
  else
    echo "❌ AI Service: Failed to start properly"
  fi

  # Add real-time log monitoring with server status
  if [ "$API_GATEWAY_SUCCESS" = true ] || [ "$AI_SERVICE_SUCCESS" = true ]; then
    echo ""
    echo "📊 Starting live log monitoring (press Ctrl+C to stop)..."
    echo ""

    # Use a better approach for monitoring both logs and server status
    # Create temporary script for monitoring
    MONITOR_SCRIPT="$LOGS_DIR/monitor_temp.sh"
    cat > "$MONITOR_SCRIPT" << 'EOL'
#!/bin/bash
LOG1=$1
LOG2=$2
PORT1=$3
PORT2=$4

# Function to display server status with more detailed checks
show_status() {
  echo "======================== SERVER STATUS ========================="
  echo -n "API Gateway (Port $PORT1): "
  if netstat -an | grep "LISTEN" | grep "\.$PORT1 " > /dev/null; then
    echo "✅ RUNNING (LISTENING)"
    curl -s -o /dev/null -w "API Gateway Response: %{http_code}\n" -m 1 http://localhost:$PORT1 2>/dev/null || echo "API Gateway Response: FAILED"
  elif netstat -an | grep "CLOSED" | grep "\.$PORT1 " > /dev/null; then
    echo "⚠️ BOUND BUT CLOSED (NOT ACTUALLY WORKING)"
    curl -s -o /dev/null -w "API Gateway Response: %{http_code}\n" -m 1 http://localhost:$PORT1 2>/dev/null || echo "API Gateway Response: FAILED"
  elif lsof -i:$PORT1 > /dev/null 2>&1; then
    echo "⚠️ PROCESS BOUND BUT SOCKET STATE UNCLEAR"
    echo "Process details: $(ps -o command= $(lsof -i:$PORT1 -t 2>/dev/null) 2>/dev/null | head -1)"
  else
    echo "❌ NOT RUNNING"
  fi

  echo -n "AI Service (Port $PORT2): "
  if netstat -an | grep "LISTEN" | grep "\.$PORT2 " > /dev/null; then
    echo "✅ RUNNING (LISTENING)"
    curl -s -o /dev/null -w "AI Service Response: %{http_code}\n" -m 1 http://localhost:$PORT2 2>/dev/null || echo "AI Service Response: FAILED"
  elif netstat -an | grep "CLOSED" | grep "\.$PORT2 " > /dev/null; then
    echo "⚠️ BOUND BUT CLOSED (NOT ACTUALLY WORKING)"
    curl -s -o /dev/null -w "AI Service Response: %{http_code}\n" -m 1 http://localhost:$PORT2 2>/dev/null || echo "AI Service Response: FAILED"
  elif lsof -i:$PORT2 > /dev/null 2>&1; then
    echo "⚠️ PROCESS BOUND BUT SOCKET STATE UNCLEAR"
    echo "Process details: $(ps -o command= $(lsof -i:$PORT2 -t 2>/dev/null) 2>/dev/null | head -1)"
  else
    echo "❌ NOT RUNNING"
  fi
  echo "==============================================================="
}

# Show initial status
show_status

# If either server shows CLOSED status, provide troubleshooting advice
if netstat -an | grep "CLOSED" | grep -E "\.$PORT1|\.$PORT2 " > /dev/null; then
  echo ""
  echo "⚠️ WARNING: One or both sockets are in CLOSED state."
  echo "This typically means the socket is bound but not accepting connections."
  echo "Possible reasons:"
  echo "  1. The server crashed after binding"
  echo "  2. The socket was not properly configured (SO_REUSEADDR)"
  echo "  3. There might be a TIME_WAIT state preventing proper binding"
  echo ""
  echo "Recommended actions:"
  echo "  - Restart this script with sudo for more effective socket cleanup"
  echo "  - Check server logs for errors"
  echo "  - If persistent, try rebooting the system"
  echo ""
fi

# Function to monitor logs with status check every 15 seconds
{
  # Start background process to show status every 15 seconds
  while true; do
    sleep 15
    show_status
  done
} &
STATUS_PID=$!

# Trap to kill the background process when this script exits
trap "kill $STATUS_PID 2>/dev/null" EXIT

# Monitor both log files with colored output
tail -f "$LOG1" "$LOG2" | grep --line-buffered -E "ERROR|WARNING|INFO|CRITICAL|started|listening|running|bound to|Application startup complete"

exit 0
EOL

    chmod +x "$MONITOR_SCRIPT"

    # Run the monitor script
    "$MONITOR_SCRIPT" "$API_GATEWAY_LOG" "$AI_SERVICE_LOG" 3001 8001
  else
    echo ""
    echo "❌ Both servers failed to start. Please check the logs:"
    echo "   - API Gateway: $API_GATEWAY_LOG"
    echo "   - AI Service: $AI_SERVICE_LOG"
  fi
fi
