# Birth Time Rectifier

![Birth Time Rectifier Logo](docs/images/logo.png)

A sophisticated application for astrological birth time rectification using AI analysis of life events.

## Overview

The Birth Time Rectifier is a comprehensive tool designed to help astrologers and astrology enthusiasts determine more accurate birth times through analysis of significant life events. By leveraging advanced astrological calculations and AI-driven analysis, the application can suggest corrections to uncertain birth times, improving the accuracy of astrological charts and interpretations.

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
- Python 3.10+
- FastAPI for API development
- Swiss Ephemeris for astrological calculations
- TensorFlow for AI rectification models
- Redis for caching and session management
- PostgreSQL for data storage

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
│   ├── api/                 # API endpoints
│   ├── core/                # Core functionality
│   ├── models/              # Data models
│   └── services/            # Business logic services
├── src/                     # Frontend React application
│   ├── components/          # React components
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
- [TensorFlow](https://www.tensorflow.org/) for AI capabilities
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
