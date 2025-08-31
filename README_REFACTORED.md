# LMS Backend - Refactored Microservices Architecture

## Overview

This is a comprehensive Learning Management System (LMS) backend that has been refactored from a monolithic architecture into a scalable microservices architecture. The system provides AI-powered course generation, user management, progress tracking, assessments, and analytics.

## Architecture

### Microservices Design

The system is now organized into the following independent services:

#### 1. API Gateway (`services/api-gateway/`)
- **Port**: 8000
- **Purpose**: Main entry point, request routing, and load balancing
- **Features**:
  - Routes requests to appropriate services
  - Health monitoring of all services
  - Request/response transformation
  - Rate limiting and security

#### 2. Auth Service (`services/auth-service/`)
- **Port**: 8001
- **Purpose**: User authentication and authorization
- **Features**:
  - JWT token management
  - User registration/login
  - Role-based access control (RBAC)
  - Password hashing with bcrypt

#### 3. Course Service (`services/course-service/`)
- **Port**: 8002
- **Purpose**: Course management and content delivery
- **Features**:
  - Course CRUD operations
  - AI-powered course generation
  - Lesson management
  - Progress tracking
  - Quiz generation and management

#### 4. User Service (`services/user-service/`)
- **Port**: 8003
- **Purpose**: User profiles and personalized features
- **Features**:
  - User profile management
  - Career development tracking
  - Study plan generation (replaces mock data)
  - Skill gap analysis (replaces mock data)
  - Achievement system

#### 5. AI Service (`services/ai-service/`)
- **Port**: 8004
- **Purpose**: AI-powered content generation and analysis
- **Features**:
  - Course content generation using Gemini AI
  - Content enhancement and optimization
  - Quiz generation
  - Performance analysis
  - Personalized learning recommendations

#### 6. Assessment Service (`services/assessment-service/`)
- **Port**: 8005
- **Purpose**: Assignment and quiz management
- **Features**:
  - Assignment creation and management
  - AI-powered grading
  - Plagiarism detection
  - Quiz administration
  - Performance analytics

#### 7. Analytics Service (`services/analytics-service/`)
- **Port**: 8006
- **Purpose**: Learning analytics and reporting
- **Features**:
  - Course analytics (replaces mock data)
  - Student performance metrics
  - Learning pattern analysis
  - Progress reporting

#### 8. Notification Service (`services/notification-service/`)
- **Port**: 8007
- **Purpose**: Real-time notifications and communication
- **Features**:
  - WebSocket support for real-time updates
  - Email notifications
  - Push notifications
  - In-app messaging

#### 9. File Service (`services/file-service/`)
- **Port**: 8008
- **Purpose**: File upload, storage, and management
- **Features**:
  - Secure file uploads
  - File type validation
  - Storage management
  - Access control

## Technology Stack

### Core Technologies
- **Python 3.11**: Primary programming language
- **FastAPI**: High-performance web framework
- **MongoDB**: NoSQL database for flexible data storage
- **Redis**: Caching and session management
- **Docker**: Containerization for all services
- **Docker Compose**: Multi-container orchestration

### AI & ML
- **Google Gemini AI**: Content generation and analysis
- **Natural Language Processing**: Text analysis and enhancement
- **Machine Learning**: Performance prediction and personalization

### Infrastructure
- **Nginx**: Load balancing and reverse proxy
- **Celery**: Background task processing
- **WebSocket**: Real-time communication
- **JWT**: Secure authentication tokens

## Key Improvements Made

### 1. Eliminated Mock Data
- **Before**: Hardcoded study plans, skill gaps, career readiness
- **After**: Real data-driven calculations based on user progress and performance

### 2. Modular Architecture
- **Before**: Monolithic application with tight coupling
- **After**: Independent services that can be developed, deployed, and scaled separately

### 3. Real Database Integration
- **Before**: Some routes used mock responses
- **After**: All services use MongoDB with proper schemas and indexing

### 4. AI-Powered Features
- **Before**: Basic AI integration
- **After**: Comprehensive AI features for content generation, grading, and personalization

### 5. Production-Ready Infrastructure
- **Before**: Development setup
- **After**: Docker-based deployment with health checks, monitoring, and scalability

## Getting Started

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- MongoDB connection
- Redis instance
- Google Gemini API key

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lms-backend
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Configure environment variables**
   ```env
   MONGO_URL=mongodb://mongodb:27017/lms_prod
   REDIS_URL=redis://redis:6379
   JWT_SECRET=your-secure-jwt-secret
   GEMINI_API_KEY=your-gemini-api-key
   ENVIRONMENT=production
   ```

### Running the System

1. **Start all services**
   ```bash
   docker-compose up -d
   ```

2. **Check service health**
   ```bash
   docker-compose ps
   ```

3. **View logs**
   ```bash
   docker-compose logs -f api-gateway
   ```

4. **Run system tests**
   ```bash
   python test_system.py
   ```

### Service URLs

- **API Gateway**: http://localhost:8000
- **Auth Service**: http://localhost:8001
- **Course Service**: http://localhost:8002
- **User Service**: http://localhost:8003
- **AI Service**: http://localhost:8004
- **Assessment Service**: http://localhost:8005
- **Analytics Service**: http://localhost:8006
- **Notification Service**: http://localhost:8007
- **File Service**: http://localhost:8008

## API Documentation

### Authentication
All API endpoints require authentication except registration and login.

**Register a new user:**
```bash
POST /auth/register
{
  "email": "user@example.com",
  "name": "User Name",
  "password": "securepassword"
}
```

**Login:**
```bash
POST /auth/login
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

### Course Management

**Create a course:**
```bash
POST /courses
Authorization: Bearer <token>
{
  "title": "Introduction to Python",
  "audience": "beginners",
  "difficulty": "intermediate"
}
```

**Generate AI course:**
```bash
POST /ai/generate-course
Authorization: Bearer <token>
{
  "topic": "Machine Learning",
  "audience": "intermediate",
  "difficulty": "advanced",
  "lesson_count": 15
}
```

### User Features

**Get study plan:**
```bash
GET /users/study-plan
Authorization: Bearer <token>
```

**Get skill gaps:**
```bash
GET /users/skill-gaps
Authorization: Bearer <token>
```

## Database Schema

### Collections

1. **users**: User accounts and profiles
2. **courses**: Course information and metadata
3. **course_progress**: User progress tracking
4. **assignments**: Assignment definitions
5. **submissions**: User assignment submissions
6. **user_profiles**: Extended user profile data
7. **career_profiles**: Career development data
8. **notifications**: System notifications
9. **analytics**: Learning analytics data

### Indexes

Optimized indexes are created for:
- User email lookups
- Course searches
- Progress tracking
- Assignment queries
- Analytics queries

## Monitoring and Health Checks

### Health Endpoints

Each service provides health check endpoints:
- `GET /health` - Service health status
- `GET /health/services` - All services health (API Gateway only)

### Monitoring

- **Prometheus**: Metrics collection
- **Grafana**: Dashboard visualization
- **Fluentd**: Log aggregation
- **Health checks**: Automatic service monitoring

## Security Features

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Secure token management

### Data Protection
- Input sanitization and validation
- XSS protection
- SQL injection prevention
- File upload security

### Infrastructure Security
- Container security best practices
- Network segmentation
- Secure API communication
- Rate limiting

## Scaling and Performance

### Horizontal Scaling
- Each service can be scaled independently
- Load balancing through API Gateway
- Database connection pooling
- Redis caching for performance

### Performance Optimizations
- Database query optimization
- Caching strategies
- Background task processing
- Response compression

## Development and Deployment

### Development
```bash
# Run specific service
docker-compose up auth-service

# Run with hot reload
docker-compose up --build
```

### Production Deployment
```bash
# Build and deploy
docker-compose -f docker-compose.yml up -d

# Scale services
docker-compose up -d --scale course-service=3
```

### CI/CD Pipeline
- Automated testing
- Container image building
- Deployment automation
- Rollback capabilities

## Troubleshooting

### Common Issues

1. **Service not starting**
   - Check environment variables
   - Verify database connectivity
   - Check service dependencies

2. **API Gateway routing issues**
   - Verify service URLs in configuration
   - Check service health status
   - Review API Gateway logs

3. **Database connection errors**
   - Verify MongoDB connection string
   - Check network connectivity
   - Validate database credentials

### Logs and Debugging

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs auth-service

# Follow logs in real-time
docker-compose logs -f api-gateway
```

## Contributing

### Code Organization
- Each service is self-contained
- Shared utilities in `shared/` directory
- Consistent error handling
- Comprehensive logging

### Testing
- Unit tests for each service
- Integration tests for service communication
- End-to-end testing
- Performance testing

### Documentation
- API documentation with OpenAPI/Swagger
- Code documentation
- Architecture documentation
- Deployment guides

## Future Enhancements

### Planned Features
- **Blockchain Credentials**: Digital certificate verification
- **Advanced Analytics**: Predictive learning models
- **Mobile App**: Native mobile application
- **Third-party Integrations**: LMS integrations (Canvas, Moodle)
- **Advanced AI**: Personalized learning paths, adaptive content

### Infrastructure Improvements
- **Kubernetes**: Container orchestration
- **Service Mesh**: Advanced service communication
- **Multi-region Deployment**: Global scalability
- **Advanced Monitoring**: Distributed tracing, APM

## Support

For support and questions:
- Check the troubleshooting section
- Review service logs
- Contact the development team
- Check GitHub issues

## License

This project is licensed under the MIT License - see the LICENSE file for details.