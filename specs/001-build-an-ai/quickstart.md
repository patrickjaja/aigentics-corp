# Quickstart: AI Offer Agent

**Feature**: AI Offer Agent for IT Consulting
**Date**: 2025-09-24
**Branch**: 001-build-an-ai

## Prerequisites

Ensure you have the following installed:
- Docker 24.0+ and Docker Compose 2.20+
- Python 3.12+
- Node.js 20+ and npm 10+
- PostgreSQL client tools
- Redis client (optional, for debugging)

## Setup Instructions

### 1. Clone and Setup Repository

```bash
# Clone repository
git clone <repository-url>
cd aigentics-corp
git checkout 001-build-an-ai

# Create environment file
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with required configurations:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=offer_agent
POSTGRES_USER=offer_agent
POSTGRES_PASSWORD=secure_password

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=redis_password

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Application Settings
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
JWT_SECRET=your_jwt_secret
API_RATE_LIMIT=100

# GDPR Settings
DATA_RETENTION_YEARS=10
DELETION_GRACE_PERIOD_YEARS=4
```

### 3. Start Infrastructure Services

```bash
# Start all infrastructure services
docker-compose up -d postgres redis qdrant

# Wait for services to be ready
docker-compose exec postgres pg_isready
docker-compose exec redis redis-cli ping
```

### 4. Setup Database

```bash
# Run database migrations
cd backend
python -m alembic upgrade head

# Load initial data (templates, COCOMO parameters)
python scripts/load_initial_data.py
```

### 5. Start Backend Services

```bash
# Install Python dependencies
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Start microservices (in separate terminals)
python -m services.conversation.main    # Port 8001
python -m services.offer.main           # Port 8002
python -m services.customer.main        # Port 8003
python -m services.estimation.main      # Port 8004
python -m services.notification.main    # Port 8005

# Start API Gateway
python -m gateway.main                  # Port 8000
```

### 6. Start Frontend Application

```bash
# Install frontend dependencies
cd frontend
npm install

# Start development server
npm run dev
# Application will be available at http://localhost:3000
```

## Validation Scenarios

### Scenario 1: Basic Offer Generation

```bash
# Test conversation API
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "language": "en"
  }'

# Expected: Conversation ID and initial questions

# Send project requirements
curl -X POST http://localhost:8000/v1/conversations/{conversation_id}/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We need a new e-commerce platform with React frontend and Node.js backend"
  }'

# Complete conversation
curl -X POST http://localhost:8000/v1/conversations/{conversation_id}/complete

# Generate offer
curl -X POST http://localhost:8000/v1/offers \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "{project_id}",
    "conversation_id": "{conversation_id}"
  }'

# Expected: Offer generated within 30 seconds
```

### Scenario 2: High-Value Offer Approval

```bash
# Create high-value project (>EUR 100k)
# Use frontend to enter large enterprise project requirements

# Check approval workflow created
curl -X GET http://localhost:8000/v1/admin/approvals/pending \
  -H "Authorization: Bearer {admin_token}"

# Expected: Approval request in pending list
```

### Scenario 3: Multi-Language Support

```bash
# Start German conversation
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{
    "language": "de"
  }'

# Expected: Questions in German

# Generate offer preview in German
curl -X GET http://localhost:8000/v1/offers/{offer_id}/preview?language=de

# Expected: German formatted offer with DIN 5008 compliance
```

### Scenario 4: GDPR Compliance

```bash
# Create customer with consent
curl -X POST http://localhost:8000/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test GmbH",
    "contact_person": "Max Mustermann",
    "email": "max@test.de",
    "gdpr_consent": {
      "given": true,
      "purposes": ["offer_generation"],
      "consent_text_version": "1.0"
    }
  }'

# Download offer (requires consent)
curl -X POST http://localhost:8000/v1/offers/{offer_id}/download \
  -H "Content-Type: application/json" \
  -d '{
    "customer_data": {
      "company_name": "Test GmbH",
      "contact_person": "Max Mustermann",
      "email": "max@test.de",
      "gdpr_consent": {
        "given": true,
        "purposes": ["offer_generation"],
        "consent_text_version": "1.0"
      }
    }
  }'

# Expected: PDF download with proper formatting
```

### Scenario 5: API Integration (A2A)

```bash
# External agent integration
curl -X POST http://localhost:8000/v1/conversations \
  -H "X-API-Key: test_api_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "en"
  }'

# Test rate limiting (100 req/min)
for i in {1..101}; do
  curl -X GET http://localhost:8000/v1/offers \
    -H "X-API-Key: test_api_key_123"
done

# Expected: 429 Too Many Requests after 100th request
```

## Performance Validation

### Load Testing

```bash
# Install Locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --users=100 \
  --spawn-rate=10

# Expected metrics:
# - Offer generation: <30s p95
# - API response: <3s p95
# - 1000 concurrent users supported
```

### Database Performance

```bash
# Check event sourcing performance
psql -U offer_agent -d offer_agent -c "
  SELECT
    COUNT(*) as event_count,
    AVG(EXTRACT(EPOCH FROM (occurred_at - LAG(occurred_at) OVER (ORDER BY occurred_at)))) as avg_event_interval
  FROM events
  WHERE aggregate_type = 'Offer'
  AND occurred_at > NOW() - INTERVAL '1 hour';
"
```

## Monitoring & Observability

### Health Checks

```bash
# Check all services health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "conversation": "healthy",
    "offer": "healthy",
    "customer": "healthy",
    "estimation": "healthy",
    "notification": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy"
  }
}
```

### Metrics Dashboard

```bash
# Access Grafana dashboard
open http://localhost:3001
# Default credentials: admin/admin

# Key metrics to verify:
# - Offer generation time: <30s
# - API response time: <3s
# - Error rate: <1%
# - Circuit breaker status: Closed
```

### Logs

```bash
# View aggregated logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f conversation-service

# Search for errors
docker-compose logs | grep ERROR
```

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check PostgreSQL is running
   docker-compose ps postgres

   # Check connection
   psql -h localhost -U offer_agent -d offer_agent
   ```

2. **OpenAI API Errors**
   ```bash
   # Verify API key
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```

3. **Redis Connection Issues**
   ```bash
   # Test Redis connection
   redis-cli -h localhost ping
   ```

4. **Port Conflicts**
   ```bash
   # Check port usage
   lsof -i :8000  # API Gateway
   lsof -i :3000  # Frontend
   lsof -i :5432  # PostgreSQL
   ```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python -m services.conversation.main --debug

# Enable SQL query logging
export SQLALCHEMY_ECHO=true
```

## Cleanup

```bash
# Stop all services
docker-compose down

# Remove volumes (WARNING: Deletes data)
docker-compose down -v

# Clean Python cache
find . -type d -name __pycache__ -exec rm -rf {} +

# Clean Node modules
cd frontend && rm -rf node_modules
```

## Success Criteria

✅ All 5 validation scenarios pass
✅ Performance metrics meet requirements:
   - Offer generation <30s
   - API response <3s
   - 100% GDPR consent before download
✅ Multi-language support working (DE/EN)
✅ High-value offers trigger approval workflow
✅ Rate limiting enforced (100 req/min)
✅ Event sourcing captures all state changes
✅ PDF generation follows DIN 5008 standards

---
*Quickstart guide created: 2025-09-24*