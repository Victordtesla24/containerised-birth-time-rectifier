# Birth Time Rectifier - Technical Context

## Technologies Used

### Frontend
- **Framework**: Next.js with React
- **State Management**: React Context API
- **Styling**: CSS Modules and Tailwind CSS
- **Visualization**: Three.js for 3D chart visualization
- **API Client**: Axios for API requests
- **Testing**: Jest and React Testing Library

### API Gateway
- **Framework**: FastAPI
- **Middleware**: Custom middleware for session management and error handling
- **Routing**: FastAPI router for API endpoint routing
- **Documentation**: OpenAPI/Swagger

### Backend Services
- **Framework**: FastAPI
- **Authentication**: JWT-based authentication
- **Session Management**: Redis for session storage
- **AI Integration**: OpenAI API for verification and rectification
- **Astronomical Calculations**: Custom ephemeris engine
- **Testing**: pytest for unit and integration tests

### Data Storage
- **Session Storage**: Redis
- **Persistent Storage**: File-based storage for chart data
- **Export Format**: PDF for chart exports

## Development Setup

### Local Development
- Docker Compose for local development environment
- Hot reloading for frontend and backend
- Environment variables for configuration
- Logging for debugging

### Testing
- Unit tests for core functionality
- Integration tests for API endpoints
- End-to-end tests for complete user flows

### Deployment
- Containerized deployment with Docker
- Kubernetes for orchestration
- CI/CD pipeline for automated testing and deployment

## Technical Constraints

### Performance
- Response time under 500ms for API requests
- Efficient chart calculation algorithms
- Optimized 3D visualization for web browsers

### Security
- Secure session management
- Input validation for all user inputs
- Rate limiting for API endpoints
- Data encryption for sensitive information

### Compatibility
- Cross-browser compatibility (Chrome, Firefox, Safari, Edge)
- Mobile-responsive design
- Accessibility compliance

### Scalability
- Horizontal scaling for backend services
- Load balancing for API requests
- Caching for improved performance

## Development Workflow

1. **Feature Development**
   - Feature branches from main branch
   - Pull request for code review
   - Automated tests on pull request
   - Code review by at least one team member
   - Merge to main branch after approval

2. **Release Process**
   - Version tagging for releases
   - Release notes generation
   - Automated deployment to staging
   - Manual testing on staging
   - Promotion to production

3. **Monitoring and Maintenance**
   - Error logging and monitoring
   - Performance monitoring
   - User feedback collection
   - Regular security updates
