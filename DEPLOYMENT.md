# 🚀 LMS Microservices Deployment Guide

## Overview

This document provides comprehensive instructions for deploying the refactored LMS (Learning Management System) microservices architecture. The system has been completely refactored from a monolithic structure to a production-ready microservices architecture with 9 independent services.

## Architecture Overview

### Services

1. **API Gateway** (Port 8000) - Central entry point and request routing
2. **Auth Service** (Port 8001) - User authentication and authorization
3. **Course Service** (Port 8002) - Course management and content delivery
4. **User Service** (Port 8003) - User profiles and personalized features
5. **AI Service** (Port 8004) - AI-powered content generation and analysis
6. **Assessment Service** (Port 8005) - Assignment and quiz management
7. **Analytics Service** (Port 8006) - Learning analytics and reporting
8. **Notification Service** (Port 8007) - Real-time notifications and WebSocket connections
9. **File Service** (Port 8008) - File upload, storage, and management

### Infrastructure Components

- **MongoDB** (Port 27017) - Primary database
- **Redis** (Port 6379) - Caching and session management
- **Celery Worker** - Background task processing

## Prerequisites

### System Requirements

- **OS**: Linux/Windows/macOS with Docker support
- **RAM**: Minimum 8GB, Recommended 16GB+
- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **Storage**: 20GB+ free space
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

### Network Requirements

- All services communicate via Docker internal network
- External access only through API Gateway (Port 8000)
- Database ports bound to localhost for security

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd lms-microservices
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Database Configuration
MONGO_URL=mongodb://admin:secure_password@mongodb:27017/lms_prod?authSource=admin
MONGO_ROOT_PASSWORD=your_secure_mongo_password

# Redis Configuration
REDIS_URL=redis://redis:6379
REDIS_PASSWORD=your_secure_redis_password

# Security
JWT_SECRET=your_super_secure_jwt_secret_64_chars_minimum
JWT_SECRET_FILE=/run/secrets/jwt_secret

# AI Service
GEMINI_API_KEY=your_google_gemini_api_key

# Environment
ENVIRONMENT=production

# Service URLs (for inter-service communication)
AUTH_SERVICE_URL=http://auth-service:8001
COURSE_SERVICE_URL=http://course-service:8002
USER_SERVICE_URL=http://user-service:8003
AI_SERVICE_URL=http://ai-service:8004
ASSESSMENT_SERVICE_URL=http://assessment-service:8005
ANALYTICS_SERVICE_URL=http://analytics-service:8006
NOTIFICATION_SERVICE_URL=http://notification-service:8007
FILE_SERVICE_URL=http://file-service:8008
```

### 3. Secrets Management

For production deployments, use Docker secrets:

```bash
# Create secrets
echo "your_super_secure_jwt_secret" | docker secret create jwt_secret -
echo "your_secure_mongo_password" | docker secret create mongo_password -
echo "your_gemini_api_key" | docker secret create gemini_api_key -
```

## Deployment Methods

### Method 1: Docker Compose (Recommended for Development/Testing)

#### Quick Start

```bash
# 1. Start all services
docker-compose up -d

# 2. Check service health
docker-compose ps

# 3. View logs
docker-compose logs -f

# 4. Run system tests
python test_system.py
```

#### Service-Specific Commands

```bash
# Start individual service
docker-compose up auth-service

# Scale services
docker-compose up -d --scale course-service=3

# Update services
docker-compose pull && docker-compose up -d

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Method 2: Production Deployment with Swarm

#### Initialize Swarm

```bash
# Initialize Docker Swarm
docker swarm init

# Create overlay network
docker network create --driver overlay --attachable lms-network
```

#### Deploy Stack

```bash
# Deploy the entire stack
docker stack deploy -c docker-compose.yml lms

# Check service status
docker stack services lms

# Scale services
docker service scale lms_course-service=5
```

### Method 3: Kubernetes Deployment

#### Prerequisites

- Kubernetes cluster (v1.19+)
- kubectl configured
- Helm (optional)

#### Deploy with kubectl

```bash
# Create namespace
kubectl create namespace lms

# Apply configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n lms
kubectl get services -n lms
```

## Configuration Management

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MONGO_URL` | MongoDB connection string | Yes | - |
| `REDIS_URL` | Redis connection string | Yes | - |
| `JWT_SECRET` | JWT signing secret | Yes | - |
| `GEMINI_API_KEY` | Google Gemini API key | Yes | - |
| `ENVIRONMENT` | Deployment environment | No | development |

### Service Configuration

Each service can be configured independently:

```yaml
# Example: Scale course service
course-service:
  deploy:
    replicas: 3
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
```

## Monitoring and Observability

### Health Checks

All services include health check endpoints:

```bash
# Check individual service health
curl http://localhost:8001/health

# Check all services via API Gateway
curl http://localhost:8000/health/services
```

### Logging

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs auth-service

# Follow logs in real-time
docker-compose logs -f api-gateway
```

### Metrics Collection

Services expose Prometheus metrics at `/metrics` endpoints:

```bash
# API Gateway metrics
curl http://localhost:8000/metrics

# Individual service metrics
curl http://localhost:8001/metrics
```

## Security Configuration

### Network Security

- Services communicate only through Docker internal network
- External access restricted to API Gateway
- Database ports bound to localhost only

### Authentication & Authorization

- JWT-based authentication
- Role-based access control (RBAC)
- Password hashing with bcrypt
- Secure token management

### Container Security

- Non-root user execution
- Read-only file systems where possible
- Security options: `no-new-privileges:true`
- Resource limits and reservations

## Scaling and Performance

### Horizontal Scaling

```bash
# Scale with Docker Compose
docker-compose up -d --scale course-service=5

# Scale with Docker Swarm
docker service scale lms_course-service=5

# Scale with Kubernetes
kubectl scale deployment course-service --replicas=5
```

### Performance Optimization

#### Database Optimization

```javascript
// Create indexes for better performance
db.users.createIndex({ "email": 1 }, { unique: true });
db.courses.createIndex({ "owner_id": 1 });
db.course_progress.createIndex({ "user_id": 1, "course_id": 1 });
```

#### Caching Strategy

- Redis for session storage
- API response caching
- Database query result caching

#### Resource Allocation

```yaml
services:
  ai-service:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
```

## Backup and Recovery

### Database Backup

```bash
# MongoDB backup
docker exec lms_mongodb_1 mongodump --db lms_prod --out /backup

# Redis backup
docker exec lms_redis_1 redis-cli save
```

### Service Recovery

```bash
# Restart failed services
docker-compose restart <service-name>

# Rollback deployment
docker-compose down
docker-compose up -d --no-deps <service-name>
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service logs
docker-compose logs <service-name>

# Check service dependencies
docker-compose ps

# Restart service
docker-compose restart <service-name>
```

#### Database Connection Issues

```bash
# Check MongoDB status
docker-compose exec mongodb mongo --eval "db.stats()"

# Reset database
docker-compose exec mongodb mongo lms_prod --eval "db.dropDatabase()"
```

#### High Memory Usage

```bash
# Check container resources
docker stats

# Adjust memory limits
services:
  ai-service:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Performance Issues

```bash
# Check service metrics
curl http://localhost:8000/metrics

# Profile application performance
python -m cProfile services/auth-service/app/main.py
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy LMS
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.prod.yml up -d
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                sh 'docker-compose build'
            }
        }
        stage('Test') {
            steps {
                sh 'docker-compose -f docker-compose.test.yml up -d'
                sh 'pytest tests/'
            }
        }
        stage('Deploy') {
            steps {
                sh 'docker-compose up -d'
            }
        }
    }
}
```

## Maintenance

### Regular Tasks

#### Log Rotation

```bash
# Configure log rotation
services:
  api-gateway:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### Database Maintenance

```bash
# MongoDB maintenance
docker-compose exec mongodb mongo lms_prod --eval "db.repairDatabase()"

# Redis maintenance
docker-compose exec redis redis-cli FLUSHDB
```

#### Security Updates

```bash
# Update all images
docker-compose pull

# Update specific service
docker-compose pull auth-service
docker-compose up -d auth-service
```

## Support and Monitoring

### Alerting

Set up alerts for:

- Service downtime
- High error rates
- Resource exhaustion
- Performance degradation

### Monitoring Dashboard

Access monitoring dashboards:

- **API Gateway**: http://localhost:8000/monitoring
- **Individual Services**: http://localhost:{port}/metrics
- **Health Checks**: http://localhost:8000/health/services

## Migration from Monolithic

### Zero-Downtime Migration

1. **Deploy new microservices alongside existing system**
2. **Configure API Gateway to route traffic gradually**
3. **Migrate data using database migration scripts**
4. **Update client applications to use new endpoints**
5. **Decommission old monolithic system**

### Data Migration

```python
# Example migration script
from motor.motor_asyncio import AsyncIOMotorClient

async def migrate_users():
    client = AsyncIOMotorClient("mongodb://old_system")
    new_client = AsyncIOMotorClient("mongodb://new_system")

    # Migrate user data
    users = await client.old_db.users.find({}).to_list(None)
    await new_client.lms_prod.users.insert_many(users)
```

## Conclusion

This deployment guide provides comprehensive instructions for deploying and maintaining the LMS microservices architecture. The system is designed for scalability, security, and maintainability with production-ready features including monitoring, logging, and automated deployment capabilities.

For additional support or questions, refer to the service documentation or contact the development team.