# Technical Context

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **API Design**: RESTful API with standardized response formats
- **Computational Engine**: Custom Python astrological calculation library
- **AI/ML**: TensorFlow/PyTorch for rectification algorithms
- **Database**: PostgreSQL for persistent storage
- **Authentication**: JWT-based authentication system
- **Deployment**: Docker containers with Kubernetes orchestration
- **Testing**: Pytest for unit and integration tests

### Frontend
- **Framework**: React with TypeScript
- **State Management**: Redux or Context API
- **UI Components**: Material-UI or Chakra UI
- **Chart Visualization**: D3.js for interactive astrological charts
- **API Communication**: Axios for REST API requests
- **Real-time Updates**: WebSocket for progress monitoring (to be implemented)
- **Testing**: Jest and React Testing Library

### DevOps & Infrastructure
- **CI/CD**: GitHub Actions
- **Containerization**: Docker
- **Orchestration**: Kubernetes
- **Monitoring**: Prometheus with Grafana dashboards
- **Logging**: ELK Stack (Elasticsearch, Logstash, Kibana)
- **Cloud Provider**: AWS/Azure/GCP

## Development Setup

### Local Development Environment
- Docker Compose for local service orchestration
- Python virtual environments for backend development
- Node.js environment for frontend development
- PostgreSQL database (containerized)
- Git for version control with GitHub Flow branching strategy
- ESLint/Prettier for code formatting
- Pre-commit hooks for code quality

### Testing Environment
- Isolated testing containers
- Mock database for test data
- Test coverage reporting
- End-to-end testing with Cypress
- Performance testing with Locust

### Staging/Production Environment
- Kubernetes cluster for container orchestration
- Separate database instances for staging/production
- CDN for static assets
- Load balancing for high availability
- Automated backups and disaster recovery
- Horizontal scaling capabilities

## API Architecture

The application implements a dual-registration pattern for API endpoints:

1. **Primary Endpoints** - Registered with `/api/` prefix:
   - Chart-related endpoints: `/api/chart/...`
   - Other services: `/api/geocode`, `/api/health`, etc.

2. **Alternative Endpoints** - Registered without `/api/` prefix:
   - Chart-related endpoints: `/chart/...`
   - Other direct endpoints: `/geocode`, `/health`, etc.

This architecture ensures backward compatibility with existing clients while following modern API design principles.

## Technical Constraints

### Performance Requirements
- **API Response Time**: < 500ms for standard operations
- **Chart Generation**: < 2 seconds
- **Rectification Process**: < 30 seconds for completion
- **Concurrent Users**: Support for 1000+ simultaneous users
- **Availability**: 99.9% uptime SLA

### Security Requirements
- HTTPS/TLS encryption for all communications
- Secure authentication with JWT tokens
- Input validation to prevent injection attacks
- Rate limiting to prevent abuse
- GDPR compliance for user data
- Regular security audits

### Scalability Considerations
- Stateless API design for horizontal scaling
- Database connection pooling
- Caching strategy for frequently accessed data
- Asynchronous processing for long-running tasks
- Microservice architecture for independent scaling

### Technical Debt and Known Issues
- **API Router Issue**: The `/api` prefix routing is not working correctly, requiring dual-registration
- **Session Management**: Not fully implemented
- **Authentication**: Basic implementation needed
- **Chart Comparison**: Incomplete implementation
- **Interpretation Service**: Documentation and implementation incomplete
- **Real-time Updates**: WebSocket integration missing for progress tracking

## Integration Points

### External Services
- **Geocoding API**: Integration with third-party geocoding services for location data
- **Time Zone Database**: External service for accurate timezone calculations
- **Ephemeris Data**: Astronomical calculations based on Swiss Ephemeris
- **Email Service**: For user notifications and account management
- **Payment Gateway**: For premium features (future integration)

### Internal Service Communication
- REST API for synchronous operations
- Message queues for asynchronous processing
- WebSockets for real-time updates (planned)
- Event-driven architecture for decoupled services

## Development Roadmap

### Phase 1: Critical Infrastructure
- Fix API Router issue
- Implement Session Management
- Add Authentication/Authorization

### Phase 2: Feature Completion
- Complete Chart Comparison Service
- Standardize Error Handling
- Add WebSocket Support

### Phase 3: Service Enhancements
- Improve Documentation
- Enhance Questionnaire Flow
- Implement Interpretation Service

## Monitoring and Observability

- API health checks and endpoint monitoring
- Error rate tracking and alerting
- Performance metrics collection
- User behavior analytics
- Resource utilization monitoring
- Log aggregation and analysis
