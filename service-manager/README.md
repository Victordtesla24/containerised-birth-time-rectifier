# Service Manager

A comprehensive tool for managing microservices in development and production environments. This service manager handles Redis, AI Service (Python), and Frontend (Node.js) services with features for monitoring, diagnostics, and configuration management.

## Features

- **Service Management**: Start, stop, and monitor services individually or together
- **Real-time Monitoring**: Watch service health with automatic restart capabilities
- **Comprehensive Diagnostics**: Check system, dependencies, and service health
- **Configuration Management**: Manage service ports and settings via JSON config
- **Interactive Menus**: User-friendly terminal interface
- **Command-line Interface**: Support for scripting and automation
- **Smart Error Handling**: Auto-detection and resolution of common issues
- **Detailed Logging**: Debugging and troubleshooting support

## Prerequisites

- Bash shell (version 4+)
- Required commands: bash, grep, sed, awk, ps, kill
- Recommended: jq, lsof, netstat, curl, wget
- Service dependencies:
  - Redis server
  - Python 3 with uvicorn, fastapi, redis, and pydantic modules
  - Node.js and npm

## Directory Structure

```
service-manager/
├── lib/                          # Core library modules
│   ├── common.sh                 # Common functions and constants
│   ├── config.sh                 # Configuration management
│   ├── diagnostics.sh            # Diagnostics and troubleshooting
│   └── services.sh               # Service management functions
├── logs/                         # Log files directory
│   ├── frontend.log              # Frontend service logs
│   ├── ai_service.log            # AI service logs
│   ├── redis.log                 # Redis server logs
│   ├── error.log                 # Error messages
│   └── debug.log                 # Debug information
├── service-manager.sh            # Main script
└── README.md                     # Documentation
```

## Installation

1. Clone or download this repository
2. Make sure the script is executable:
   ```bash
   chmod +x service-manager/service-manager.sh
   ```
3. Run the script:
   ```bash
   cd service-manager
   ./service-manager.sh
   ```

## Usage

### Interactive Mode

Run the script without arguments to enter interactive mode:

```bash
./service-manager.sh
```

This will display the main menu with options to:
- Start All Services
- Stop All Services
- Monitor Services
- Run Diagnostics
- Access Advanced Options
- Exit

### Command-line Arguments

The script supports various command-line arguments for automation:

```bash
# Start all services
./service-manager.sh start all

# Start a specific service
./service-manager.sh start redis
./service-manager.sh start ai
./service-manager.sh start frontend

# Stop services
./service-manager.sh stop all
./service-manager.sh stop frontend

# Restart services
./service-manager.sh restart all
./service-manager.sh restart ai

# Monitor services
./service-manager.sh monitor

# Run diagnostics
./service-manager.sh diagnostics

# View logs
./service-manager.sh logs redis
./service-manager.sh logs ai
./service-manager.sh logs frontend
./service-manager.sh logs error
./service-manager.sh logs debug

# Flush logs
./service-manager.sh flush-logs

# Configuration management
./service-manager.sh config show
./service-manager.sh config set api_port 8001
./service-manager.sh config reset

# Help
./service-manager.sh help
```

## Configuration

The script uses a JSON configuration file (`.service_config.json`) with these default settings:

```json
{
  "redis_port": 6379,
  "api_port": 8000,
  "frontend_port": 3000,
  "verbose": false,
  "log_level": "info",
  "environment": "development",
  "max_restart_attempts": 3,
  "restart_cooldown": 30,
  "auto_open_browser": true,
  "check_updates": true
}
```

You can modify this configuration using:
- The port configuration menu
- The toggle verbose mode option
- The `config set` command

## Troubleshooting

If you encounter issues:

1. Run diagnostics to check system and services: 
   ```bash
   ./service-manager.sh diagnostics
   ```

2. Check debug logs:
   ```bash
   ./service-manager.sh logs debug
   ```

3. Check error logs:
   ```bash
   ./service-manager.sh logs error
   ```

4. If a service fails to start, try:
   ```bash
   ./service-manager.sh start <service>
   ```
   This will run the service with detailed error handling.

5. If you encounter port conflicts, use the port configuration menu or:
   ```bash
   ./service-manager.sh config set <service>_port <new_port>
   ```

## License

This project is open-source and available under the MIT License.

## Contributing

Contributions, issues, and feature requests are welcome! 