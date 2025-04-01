# Birth Time Rectifier

![Birth Time Rectifier Logo](docs/images/logo.png)

A sophisticated application for astrological birth time rectification using AI analysis of life events.

## Overview

The Birth Time Rectifier is a comprehensive tool designed to help astrologers and astrology enthusiasts determine more accurate birth times through analysis of significant life events. By leveraging advanced astrological calculations and AI-driven analysis, the application suggests corrections to uncertain birth times, improving the accuracy of astrological charts and interpretations.

## Current Implementation Status

The application consists of three main components in active development:

1. **AI Service (Python/FastAPI)**: Backend service with astrological calculations, OpenAI integration, and chart verification
   - Session management with Redis integration
   - Chart generation and verification against Vedic standards
   - Comprehensive error handling and validation
   - WebSocket support for real-time updates during rectification

2. **API Gateway (Python/FastAPI)**: Central routing service that handles client requests
   - Request forwarding to appropriate microservices
   - Session management and authentication
   - Error handling and standardization
   - WebSocket proxy for real-time communication

3. **Frontend (React/TypeScript)**: User interface for interacting with the application
   - Interactive chart visualization components
   - Birth data entry and validation
   - Questionnaire system for life events
   - Chart comparison views

### Implemented Features

- ✅ Session initialization and management
- ✅ Location geocoding and timezone detection
- ✅ Birth data validation and chart generation
- ✅ OpenAI integration for chart verification against Vedic standards
- ✅ Interactive chart visualization
- ✅ Error handling and recovery mechanisms
- ✅ WebSocket communication for real-time updates

### Features in Progress

- 🔄 Questionnaire system for life event analysis
- 🔄 AI-powered birth time rectification algorithms
- 🔄 Chart comparison and difference analysis
- 🔄 PDF export and sharing options

## Features

- **Accurate Astrological Calculations**: Precise calculations for all planetary positions, including specialized calculations for Ketu and Ascendant positions
- **Interactive Chart Visualization**: Dynamic and interactive display of astrological charts with multiple view options
- **AI-Powered Birth Time Rectification**: Advanced algorithms analyze life events to suggest the most likely birth time
- **Comprehensive Questionnaire System**: Detailed collection of life events for accurate rectification
- **Chart Comparison**: Side-by-side and overlay comparison between original and rectified charts
- **Multiple Export Options**: Save and share charts and rectification results in various formats
- **User-Friendly Interface**: Intuitive design for both beginners and professional astrologers
- **Multi-Platform Support**: Works on desktop and mobile devices

## Troubleshooting

### NPM Installation Issues

If you encounter npm installation issues, please refer to the [NPM Installation Fixes](docs/npm-installation-fixes.md) documentation for detailed solutions.

Common issues include:
- Permission errors with npm cache directory
- Permission errors with node_modules directory

We've provided several scripts to automatically fix these issues:
```bash
# Fix npm permissions
./scripts/fix-npm-permissions.sh

# Comprehensive fix for npm installation issues
./scripts/fix-npm-installation.sh
```

## Technology Stack

### Backend
- Python 3.10+ with FastAPI framework
- Swiss Ephemeris for astrological calculations
- OpenAI API for AI verification and rectification
- Redis for caching and session management
- PostgreSQL for data storage
- WebSockets for real-time communication

### Frontend
- React with TypeScript
- D3.js for chart visualization
- Material-UI for component library
- Redux for state management
- Axios for API communication

## Installation

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- PostgreSQL 14 or higher
- Redis 6 or higher
- Docker and Docker Compose (optional, for containerized deployment)

### Local Development Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/birth-time-rectifier.git
   cd birth-time-rectifier
   ```

2. Set up the backend:
   ```bash
   # Create and activate a virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Set up environment variables
   cp .env.example .env
   # Edit .env with your configuration

   # Run migrations
   alembic upgrade head

   # Start the backend server
   uvicorn ai_service.main:app --reload
   ```

3. Set up the frontend:
   ```bash
   # Navigate to the frontend directory
   cd src

   # Install dependencies
   npm install

   # Start the development server
   npm start
   ```

4. Access the application at http://localhost:3000

### Docker Deployment

1. Build and start the containers:
   ```bash
   docker-compose up -d
   ```

2. Access the application at http://localhost:8080

## Project Structure

```
birth-time-rectifier/
├── ai_service/              # Backend FastAPI application
│   ├── api/                 # API endpoints and routers
│   ├── core/                # Core functionality and validators
│   │   └── rectification/   # Birth time rectification algorithms
│   ├── models/              # Data models
│   ├── services/            # Business logic services
│   │   ├── chart_service.py # Chart calculation and management
│   │   ├── openai_service.py # OpenAI integration
│   │   └── chart_verification.py # Vedic chart verification
│   ├── database/            # Database models and connections
│   └── utils/               # Utility functions
├── api_gateway/             # API Gateway service
│   ├── middleware/          # Middleware components
│   ├── routes/              # Route definitions
│   ├── main.py              # Gateway application entry point
│   └── websocket_proxy.py   # WebSocket proxy implementation
├── src/                     # Frontend React application
│   ├── components/          # React components
│   │   └── charts/          # Chart visualization components
│   ├── pages/               # Page components
│   ├── services/            # API services
│   └── utils/               # Utility functions
├── tests/                   # Test suite
│   ├── integration/         # Integration tests
│   └── unit/                # Unit tests
├── docs/                    # Documentation
├── scripts/                 # Utility scripts
├── .github/                 # GitHub Actions workflows
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker configuration for backend
├── Dockerfile.frontend      # Docker configuration for frontend
└── README.md                # This file
```

## Documentation

- [User Guide](user_docs/user_guide.md)
- [API Documentation](api_docs/api_documentation.md)
- [Developer Guide](docs/developer_guide.md)
- [Testing Framework](tests/README.md)

## Contributing

We welcome contributions to the Birth Time Rectifier project! Please see our [Contributing Guidelines](CONTRIBUTING.md) for more information.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Testing

Run the backend tests:
```bash
pytest tests/
```

Run the frontend tests:
```bash
cd src
npm test
```

For more details on our testing framework, see the [Testing Documentation](tests/README.md).

## Deployment

The application can be deployed using Docker to various cloud platforms or directly to Vercel:

### Cloud Platforms
- [AWS Deployment Guide](docs/deployment/aws.md)
- [Azure Deployment Guide](docs/deployment/azure.md)
- [Google Cloud Deployment Guide](docs/deployment/gcp.md)

### Vercel Deployment

This project is configured for deployment on Vercel. For detailed instructions, see [Vercel Deployment Guide](docs/vercel-deployment-guide.md).

[![Vercel Production Deployment](https://github.com/Victordtesla24/containerised-birth-time-rectifier/actions/workflows/vercel-deploy.yml/badge.svg)](https://github.com/Victordtesla24/containerised-birth-time-rectifier/actions/workflows/vercel-deploy.yml)

#### Quick Start

1. **Prerequisites**
   - Vercel account
   - GitHub account
   - Required environment variables (see .env.example)

2. **Setup**
   - Fork/clone this repository
   - Link it to your Vercel account
   - Set up the required environment variables

3. **Deployment**
   - Push to main branch for production deployment
   - Create pull requests for preview deployments

## Environment Setup for OpenAI Integration

This application uses real OpenAI API calls for chart verification and birth time rectification. To ensure the system works correctly, you need to set up your environment variables properly.

### Setting Up Your `.env` File

1. Create a `.env` file in the root directory of the project (or use the provided template)
2. Add your OpenAI API key to the file:

```
OPENAI_API_KEY=your_actual_api_key_here
```

3. Additional configuration can be added to the `.env` file:

```
# OpenAI Model Configuration
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7

# Enable caching for API calls (reduces costs and improves performance)
ENABLE_CACHE=true
CACHE_TTL=3600

# Logging Configuration
LOG_LEVEL=INFO

# Application Configuration
PORT=8000
DEBUG=false
```

## Roadmap

- [ ] Mobile application for iOS and Android
- [ ] Integration with popular astrological software
- [ ] Advanced transit analysis
- [ ] Multi-language support
- [ ] Enhanced AI models for higher accuracy
- [ ] Batch processing for professional astrologers

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

- [Swiss Ephemeris](https://www.astro.com/swisseph/) for astrological calculations
- [OpenAI](https://openai.com/) for AI capabilities
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [React](https://reactjs.org/) for the frontend framework
- All contributors who have helped shape this project

## Contact

For questions, support, or collaboration, please contact us at:
- Email: contact@birthrectifier.example.com
- Twitter: [@BirthRectifier](https://twitter.com/BirthRectifier)
- Website: [https://birthrectifier.example.com](https://birthrectifier.example.com)

## Visual Testing

This project includes visual regression testing to ensure UI components maintain their appearance across changes.

### Running Visual Tests

To run the visual tests:

```bash
# Start the development server
npm run dev

# In a separate terminal, run the visual tests
npm run test:visual
```

The first time you run the tests, they will create baseline snapshots in the `__image_snapshots__` directory. Subsequent runs will compare against these baselines.

### Updating Visual Snapshots

If you've made intentional UI changes, you'll need to update the baseline snapshots:

```bash
npm run test:update-visual
```

### How Visual Testing Works

1. The tests use Puppeteer to launch a headless browser and navigate to components
2. Screenshots are taken of the components in various states
3. These screenshots are compared against baseline images using jest-image-snapshot
4. If the difference exceeds the threshold, the test fails and generates diff images

### Visual Test Files

Visual tests are located in `src/__tests__` with the naming pattern `*.visual.test.jsx`.

## Environment Setup for Real API Calls

This application is configured to use real OpenAI API calls without fallbacks or mockups. To ensure the system works correctly, you need to set up your environment variables properly.

### Setting Up Your `.env` File

1. Create a `.env` file in the root directory of the project (or use the provided template)
2. Add your OpenAI API key to the file:

```
OPENAI_API_KEY=your_actual_api_key_here
```

3. Additional configuration can be added to the `.env` file:

```
# OpenAI Model Configuration
OPENAI_MODEL=gpt-4-turbo-preview
OPENAI_TEMPERATURE=0.7

# Enable caching for API calls (reduces costs and improves performance)
ENABLE_CACHE=true
CACHE_TTL=3600

# Logging Configuration
LOG_LEVEL=INFO

# Application Configuration
PORT=8000
DEBUG=false
```

### Obtaining an OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Sign in or create an account
3. Create a new API key
4. Copy the key and add it to your `.env` file

### Important Notes

- **Never commit your `.env` file to version control.** The `.env` file has been added to `.gitignore`.
- The application is designed to fail with clear error messages if the API key is not available.
- There are **no fallbacks to mock implementations** - this ensures you're always testing with real API calls.

### Requirements

To use the `.env` file loading, make sure to install the required dependency:

```bash
pip install python-dotenv
```

## Running the Application

Once your `.env` file is set up:

```bash
python -m ai_service.main
```

## Running Tests with Real API Calls

To run tests with real API calls:

```bash
pytest -xvs tests/
```

Note that running tests with real API calls will consume API credits and may incur costs.

## Running Tests

### Using Docker Test Environment

You can use our streamlined test script for managing Docker test containers:

```bash
# Run the test script (shows interactive menu)
./test.sh

# Or use commands directly
./test.sh run --type integration          # Run all integration tests
./test.sh run --path tests/integration/birth_time_rectification/test_integration_birth_time_01_session_init.py  # Run specific test
./test.sh rebuild --filter "session_init" # Rebuild containers and run tests matching filter
./test.sh clean                           # Clean up test environment
```

### Manual Docker Test Setup

If you prefer to use docker-compose directly:

```bash
# Build and run using docker-compose.test.yml
export OPENAI_API_KEY="your-openai-api-key"
docker-compose -f docker-compose.test.yml up --build test-runner

# Run specific test files with a custom command
docker-compose -f docker-compose.test.yml run test-runner pytest -xvs tests/integration/birth_time_rectification/test_integration_birth_time_01_session_init.py
```

### Running Tests Locally

1. Set up the Python environment:

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

2. Run the tests:

```bash
# Run all tests
pytest tests/

# Run specific tests
pytest tests/unit/ -v
pytest tests/integration/birth_time_rectification/ -v
```

## Building Docker Images for Production

Use our streamlined build script for managing production Docker images:

```bash
# Run the build script (shows interactive menu)
./build.sh

# Or use commands directly
./build.sh --all                        # Build all containers
./build.sh --service                    # Build AI service container only
./build.sh --gateway                    # Build API gateway container only
./build.sh --push --registry myregistry # Build and push to registry
```

### Manual Production Build

If you prefer to build containers directly:

```bash
# Build AI service container
docker build -t birth-rectifier-ai-service:latest -f ai_service.Dockerfile .

# Build API gateway container
docker build -t birth-rectifier-api-gateway:latest -f api_gateway.Dockerfile --target production .
```

## Directory Structure

The codebase has been reorganized for better clarity and maintainability:

- `ai_service/` - Core AI service and astrological calculations
- `api_gateway/` - API Gateway for client requests
- `docker/` - Docker files (Dockerfiles, docker-compose files)
- `config/` - Configuration files for various tools and frameworks
- `python/` - Python-specific files (requirements, constraints)
- `env/` - Environment configuration files
- `tests/` - Test files and utilities
- `scripts/` - Utility and helper scripts
- `src/` - Frontend source code

To build Docker containers: `cd docker_prod && ./build_docker_container.sh`
To run tests: `cd tests/shell_scripts && ./test_manager.sh`

All other configuration files have been moved to their appropriate directories
and can be found in the respective subdirectories.

## Running Tests

### Using Test Scripts

You can run tests using the provided script in the scripts directory:

```bash
./scripts/test.sh          # Shows interactive menu with test options
./scripts/test.sh run      # Run integration tests
./scripts/test.sh help     # Show usage information
```

### Manual Test Setup

If you prefer to run tests manually:

```bash
# Run integration tests
python -m pytest tests/integration -v

# Run unit tests
python -m pytest tests/unit -v

# Run specific test
python -m pytest tests/integration/birth_time_rectification/test_integration_birth_time_01_session_init.py -v
```

## Building Docker Containers

### Using Build Script

You can build Docker containers using the provided script:

```bash
./scripts/build.sh         # Shows interactive menu
./scripts/build.sh --all   # Build all containers
./scripts/build.sh --help  # Show usage information
```

### Manual Docker Build

If you prefer to build manually:

```bash
# Build and run using docker-compose
cd docker
docker-compose up --build

# Build individual containers
docker build -f docker/ai_service.Dockerfile -t birth-rectifier-ai-service:latest .
docker build -f docker/api_gateway.Dockerfile -t birth-rectifier-api-gateway:latest .
docker build -f docker/frontend.Dockerfile -t birth-rectifier-frontend:latest .
```

## Development Setup

1. Install dependencies:
   ```bash
   # Python dependencies
   pip install -r python/requirements.txt

   # Node dependencies
   npm install
   ```

2. Set up environment variables:
   ```bash
   cp env/.env.example env/.env
   # Edit .env with your configuration
   ```

3. Start the development server:
   ```bash
   # Start AI service
   cd ai_service
   uvicorn app_wrapper:app_wrapper --reload --port 8000

   # Start frontend
   npm run dev
   ```

## Development Tools

### Containerized Duplication Analysis

A containerized tool is available for detecting code duplications and quality issues. The tool runs in Docker with GPU acceleration (if available) to free up your main machine resources.

```bash
# Run analysis on specific directories
./run_duplication_analysis.sh ai_service api_gateway

# Run in quick mode
./run_duplication_analysis.sh -q ai_service

# Run with visualization server
./run_duplication_analysis.sh -s
```

The tool generates comprehensive HTML reports with visualizations. For more details, see [Containerized Duplication Analysis](docs/containerized_duplication_analysis.md).

### Additional Tools

# Code Duplication Removal

As part of ongoing code quality improvements, we've addressed and resolved several areas of duplication in the codebase:

1. **Geocoding Services**: Consolidated duplicate geocoding logic into a single canonical implementation in `ai_service/utils/geocoding.py`.

2. **WebSocket Management**:
   - Enhanced the WebSocketManager to support both services in a shared implementation
   - Consolidated WebSocket event handling into a single shared module
   - Standardized event types across all services with a comprehensive EventType enum

3. **Chart Services**: Implemented a proper delegation pattern for the API service's chart service that calls the canonical implementation.

4. **Authentication**: Created a shared JWT authentication utilities module to ensure consistent token handling across all services.

5. **Error Handling**:
   - Created a common error handler module in `/ai_service/utils/error_handler.py`
   - Both the API service and API Gateway now use this module
   - Fixed serialization issues with the error details
   - Updated the API Gateway error middleware to use the shared error handler
   - This provides consistent error responses across all endpoints

6. **Data Validation**: Implemented shared validation models for consistent data validation across the application.

These improvements have significantly enhanced code maintainability by following DRY (Don't Repeat Yourself) principles and ensuring consistent behavior across all components of the application.

# Birth Time Rectifier - Modular Implementation

A modular implementation of the Birth Time Rectifier following the sequence diagram from the architecture documentation.

## Overview

This application provides astrological birth time rectification through a series of steps:

1. **Session Initialization** - Establishes a session with the API
2. **Geocoding & Location** - Searches for and validates birth locations
3. **Chart Generation** - Validates birth details and generates an astrological chart
4. **Questionnaire** - Collects relevant life events and patterns for analysis
5. **Birth Time Rectification** - Uses AI to determine a rectified birth time
6. **Chart Comparison & Interpretation** - Compares original and rectified charts with detailed interpretation

## Modules

The implementation is divided into the following modules:

- `session.sh` - Session initialization (GET /api/session/init)
- `geocode.sh` - Geocoding and location search (GET /api/geocode)
- `chart.sh` - Chart validation and generation (POST /api/chart/validate, POST /api/chart/generate, GET /api/chart/{id})
- `questionnaire.sh` - Questionnaire functionality (POST /api/questionnaire/initialize, POST /api/questionnaire/{id}/answer, POST /api/questionnaire/complete)
- `rectify.sh` - Birth time rectification (POST /api/chart/rectify)
- `comparison.sh` - Chart comparison and interpretation (GET /api/chart/compare)
- `modular_birth_time_rectifier.sh` - Orchestration script that runs all modules in the correct sequence

## Usage

To run the complete birth time rectification process:

```bash
bash modular_birth_time_rectifier.sh --run-full
```

To run a specific module:

```bash
bash modular_birth_time_rectifier.sh
# Then select option 2 and choose the desired module
```

## Sequence Flow

The application follows the sequence detailed in the "Original Sequence Diagram - Full Implementation" section of the architecture documentation.

## Reports

After running the full process, the following reports are generated:

1. `birth_time_rectifier_report.md` - A technical report showing API responses and sequence flow
2. `chart_interpretation_report.txt` - A user-friendly report with chart comparison interpretation

## Features

- Interactive questionnaire for collecting life events
- AI-powered birth time rectification
- Detailed chart comparison showing differences between original and rectified charts
- Interpretation of chart differences with significance analysis
- Clean, modular implementation for easy maintenance and extension
