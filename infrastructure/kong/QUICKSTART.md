# Kong Gateway & Middleware Quick Start

Get the API Gateway and middleware stack running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Ports available: 8000, 8001, 8443, 5432, 6379

## Step 1: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Optional: Edit .env to customize settings
# For quick start, defaults are fine
nano .env
```

## Step 2: Start All Services

```bash
# Start everything with Docker Compose
docker-compose up -d

# Wait for services to be healthy (30-60 seconds)
docker-compose ps
```

Expected output:
```
NAME                      STATUS
offer-agent-backend       Up (healthy)
offer-agent-grafana       Up
offer-agent-keycloak      Up
offer-agent-kong          Up (healthy)
offer-agent-kong-db       Up (healthy)
offer-agent-postgres      Up (healthy)
offer-agent-prometheus    Up
offer-agent-qdrant        Up (healthy)
offer-agent-redis         Up (healthy)
```

## Step 3: Verify Kong is Running

```bash
# Check Kong status
curl http://localhost:8001/status

# Expected response:
# {
#   "database": {
#     "reachable": true
#   },
#   "server": {
#     "connections_accepted": 1,
#     "connections_active": 1,
#     ...
#   }
# }
```

## Step 4: Test the API

### Test Health Check (No Authentication)

```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "service": "ai-offer-agent",
  "version": "1.0.0"
}
```

### Test with API Key

```bash
# Use the default test API key from .env.example
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: a2a-test-key-change-in-production" \
  -d '{"title": "Test Conversation"}'
```

### Test Rate Limiting

```bash
# Make 105 requests quickly
for i in {1..105}; do
  echo "Request $i:"
  curl -s -H "X-API-Key: a2a-test-key-change-in-production" \
       -w " (HTTP %{http_code})\n" \
       http://localhost:8000/health
done | tail -10
```

Expected: First 100 succeed (200), then rate limited (429)

### Test Security Headers

```bash
curl -I http://localhost:8000/health | grep -E "X-|Strict|Content-Security"
```

Expected headers:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; ...
```

## Step 5: View Logs

```bash
# View Kong access logs
docker-compose logs -f kong

# View backend application logs
docker-compose logs -f backend

# View all services
docker-compose logs -f
```

## Step 6: Access Monitoring

### Kong Admin GUI
- URL: http://localhost:8002
- Browse services, routes, plugins

### Prometheus Metrics
- URL: http://localhost:9090
- Query: `kong_http_requests_total`

### Grafana Dashboards
- URL: http://localhost:3001
- Username: `admin`
- Password: `admin` (from .env)
- Add Prometheus datasource: http://prometheus:9090
- Import Kong dashboard: ID 7424

## Common Issues & Solutions

### Issue: Kong Won't Start

```bash
# Check Kong database
docker-compose logs kong-database

# Check Kong migrations
docker-compose logs kong-migration

# Restart Kong
docker-compose restart kong
```

### Issue: 401 Unauthorized

```bash
# Verify API key is correct
docker exec offer-agent-kong env | grep A2A_API_KEY

# Test with correct key from .env
API_KEY=$(grep A2A_API_KEY .env | cut -d '=' -f2)
curl -H "X-API-Key: $API_KEY" http://localhost:8000/v1/conversations
```

### Issue: CORS Errors in Browser

```bash
# Check CORS configuration
docker exec offer-agent-kong env | grep FRONTEND_URL

# Update in .env to match your frontend URL
# Then restart Kong
docker-compose restart kong
```

### Issue: Rate Limiting Not Working

```bash
# Check Redis connection
docker exec offer-agent-redis redis-cli -a redis_password ping

# Should return: PONG

# Check rate limit plugin
curl http://localhost:8001/plugins | grep -A5 rate-limiting
```

## Next Steps

1. **Customize Configuration**
   - Edit `.env` with production values
   - Generate strong API keys
   - Configure Keycloak realm

2. **Review Documentation**
   - [Kong Configuration](./README.md) - Full Kong setup guide
   - [Middleware Documentation](../../backend/src/middleware/README.md) - Middleware details
   - [Integration Guide](../../backend/src/middleware/INTEGRATION.md) - Complete integration
   - [Architecture](./ARCHITECTURE.md) - System architecture diagrams

3. **Deploy to Production**
   - Use production environment variables
   - Enable HTTPS enforcement
   - Configure SSL certificates
   - Set up monitoring alerts

## Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Restart specific service
docker-compose restart [service-name]

# Check service health
docker-compose ps

# Access Kong Admin API
curl http://localhost:8001/

# List all services
curl http://localhost:8001/services

# List all routes
curl http://localhost:8001/routes

# List all plugins
curl http://localhost:8001/plugins

# List consumers (API key holders)
curl http://localhost:8001/consumers

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test with different API keys
export API_KEY="your-key-here"
curl -H "X-API-Key: $API_KEY" http://localhost:8000/v1/conversations
```

## API Endpoints Reference

| Endpoint | Auth | Rate Limit | Description |
|----------|------|------------|-------------|
| `/health` | None | 1000/min | Health check |
| `/v1/conversations` | API Key | 100/min | Conversation API |
| `/v1/offers` | API Key | 100/min | Offer API |
| `/v1/customers` | API Key | 50/min | Customer API (HTTPS only) |
| `/v1/approvals` | JWT | 100/min | Admin API (HTTPS only) |

## Default Ports

| Service | Port | Description |
|---------|------|-------------|
| Kong Proxy (HTTP) | 8000 | Main API gateway |
| Kong Proxy (HTTPS) | 8443 | SSL/TLS gateway |
| Kong Admin API | 8001 | Configuration API |
| Kong Admin GUI | 8002 | Web interface |
| Backend API | 8000* | Internal (proxied by Kong) |
| PostgreSQL | 5432 | Main database |
| Kong PostgreSQL | 5433 | Kong database |
| Redis | 6379 | Cache & rate limiting |
| Qdrant | 6333 | Vector database |
| Keycloak | 8080 | Authentication |
| Prometheus | 9090 | Metrics |
| Grafana | 3001 | Dashboards |

*Backend runs on same port as Kong proxy but on different network interface

## Environment Variables Quick Reference

```bash
# Minimal required configuration
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=redis_password
KONG_POSTGRES_PASSWORD=kong_password

# API Keys (change in production!)
A2A_API_KEY=a2a-test-key-change-in-production
FRONTEND_API_KEY=frontend-test-key-change-in-production
MONITORING_API_KEY=monitoring-test-key-change-in-production

# Security
ENFORCE_HTTPS=false  # Set to true in production
CORS_ORIGINS=http://localhost:3000

# Optional overrides
KONG_PROXY_PORT=8000
KONG_ADMIN_PORT=8001
GRAFANA_PORT=3001
```

## Success Checklist

After following this guide, you should have:

- [ ] All Docker containers running and healthy
- [ ] Kong Gateway responding on port 8000
- [ ] Health check endpoint accessible
- [ ] API key authentication working
- [ ] Rate limiting functioning (429 after 100 requests)
- [ ] Security headers present in responses
- [ ] Logs visible in docker-compose logs
- [ ] Grafana accessible at http://localhost:3001
- [ ] Prometheus metrics available

## Getting Help

- **Documentation**: See README.md files in this directory
- **Logs**: `docker-compose logs -f [service]`
- **Kong Status**: `curl http://localhost:8001/status`
- **Health Checks**: `curl http://localhost:8000/health`

## Clean Up

To completely remove all services and data:

```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes all data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```
