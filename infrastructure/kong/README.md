# Kong API Gateway Configuration

This directory contains the Kong Gateway configuration for the AI Offer Agent system.

## Overview

Kong Gateway provides:
- **Rate Limiting**: 100 requests/minute per client (configurable per service)
- **API Key Authentication**: For A2A protocol and external integrations
- **JWT Authentication**: For admin portal access
- **CORS Configuration**: Secure cross-origin requests
- **Security Headers**: HSTS, CSP, X-Frame-Options, etc.
- **Request/Response Transformation**: Add security headers, remove sensitive headers
- **Metrics**: Prometheus integration for monitoring
- **Health Checks**: Active and passive upstream health monitoring

## Architecture

```
Client → Kong Gateway → Backend Services
           ↓
      Redis (Rate Limiting)
      PostgreSQL (Configuration)
      Prometheus (Metrics)
```

## Services Configured

### 1. Conversation Service (`/v1/conversations`)
- **Rate Limit**: 100 requests/minute
- **Authentication**: API Key (X-API-Key header)
- **Protocols**: HTTP, HTTPS
- **Features**: Rate limiting, CORS, security headers, metrics

### 2. Offer Service (`/v1/offers`)
- **Rate Limit**: 100 requests/minute
- **Authentication**: API Key
- **Protocols**: HTTP, HTTPS
- **Features**: Same as Conversation Service

### 3. Customer Service (`/v1/customers`)
- **Rate Limit**: 50 requests/minute (stricter for PII data)
- **Authentication**: API Key (hidden from logs)
- **Protocols**: HTTPS only (PII protection)
- **Features**: Enhanced security headers, restricted CORS, PII logging exclusion

### 4. Admin Service (`/v1/approvals`)
- **Rate Limit**: 100 requests/minute
- **Authentication**: JWT (Bearer token)
- **Protocols**: HTTPS only
- **Features**: JWT validation, Keycloak integration, admin-specific security

### 5. Health Check Service (`/health`, `/ready`)
- **Rate Limit**: 1000 requests/minute (high for monitoring)
- **Authentication**: None
- **Protocols**: HTTP, HTTPS
- **Features**: No auth required for load balancers

## Configuration Files

- **kong.yml**: Declarative configuration (DB-less mode compatible)
- **docker-compose.yml**: Kong Gateway, Kong Database, Kong Migration services

## Environment Variables

Required environment variables in `.env`:

```bash
# Kong Database
KONG_POSTGRES_DB=kong
KONG_POSTGRES_USER=kong
KONG_POSTGRES_PASSWORD=kong_password

# Kong Ports
KONG_PROXY_PORT=8000          # HTTP proxy
KONG_PROXY_SSL_PORT=8443      # HTTPS proxy
KONG_ADMIN_PORT=8001          # Admin API
KONG_ADMIN_GUI_PORT=8002      # Admin GUI

# API Keys
A2A_API_KEY=your-a2a-api-key
FRONTEND_API_KEY=your-frontend-api-key
MONITORING_API_KEY=your-monitoring-api-key

# Redis (for rate limiting)
REDIS_PASSWORD=your-redis-password

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000
```

## Deployment

### 1. Start Kong with Docker Compose

```bash
# Start all services including Kong
docker-compose up -d

# Check Kong status
docker-compose ps kong
docker-compose logs kong

# Verify Kong is running
curl http://localhost:8001/status
```

### 2. Verify Configuration

```bash
# Check declarative config is loaded
curl http://localhost:8001/

# List services
curl http://localhost:8001/services

# List routes
curl http://localhost:8001/routes

# List plugins
curl http://localhost:8001/plugins

# List consumers (API key holders)
curl http://localhost:8001/consumers
```

### 3. Test Rate Limiting

```bash
# Make multiple requests to test rate limiting
for i in {1..105}; do
  curl -H "X-API-Key: your-api-key" \
       http://localhost:8000/v1/conversations
done

# Expected: First 100 succeed, then 429 Too Many Requests
```

### 4. Test API Key Authentication

```bash
# Without API key (should fail)
curl http://localhost:8000/v1/conversations
# Expected: 401 Unauthorized

# With valid API key (should succeed)
curl -H "X-API-Key: a2a-test-key-change-in-production" \
     http://localhost:8000/v1/conversations
# Expected: 200 OK or backend response
```

### 5. Test Security Headers

```bash
# Check security headers in response
curl -I http://localhost:8000/health

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains
# Content-Security-Policy: default-src 'self'
```

## API Key Management

### Creating New API Keys

Kong uses consumers with key-auth credentials. Consumers are defined in `kong.yml`:

```yaml
consumers:
  - username: new-client
    custom_id: client-001
    tags:
      - external
    keyauth_credentials:
      - key: ${NEW_CLIENT_API_KEY}
```

### Managing API Keys via Admin API

```bash
# Create consumer
curl -X POST http://localhost:8001/consumers \
  -d "username=new-client" \
  -d "custom_id=client-001"

# Create API key for consumer
curl -X POST http://localhost:8001/consumers/new-client/key-auth \
  -d "key=your-new-api-key"

# List all API keys for a consumer
curl http://localhost:8001/consumers/new-client/key-auth

# Delete API key
curl -X DELETE http://localhost:8001/consumers/new-client/key-auth/{key-id}
```

## Rate Limiting

### Per-Service Rate Limits

Configured in `kong.yml` under each service's plugins:

```yaml
plugins:
  - name: rate-limiting
    config:
      minute: 100           # 100 requests per minute
      policy: redis         # Use Redis for distributed rate limiting
      redis_host: redis
      redis_port: 6379
      redis_password: ${REDIS_PASSWORD}
```

### Custom Rate Limits

To set different rate limits for specific consumers:

```bash
# Apply custom rate limit to consumer
curl -X POST http://localhost:8001/consumers/high-priority-client/plugins \
  -d "name=rate-limiting" \
  -d "config.minute=500"
```

## Security Features

### 1. HTTPS Enforcement

- Customer and Admin services require HTTPS
- HTTP requests are redirected with 426 Upgrade Required
- HSTS headers ensure browsers always use HTTPS

### 2. CORS Configuration

- Configurable allowed origins via `FRONTEND_URL`
- Supports wildcard subdomains: `https://*.aigentics.com`
- Credentials enabled for authenticated requests
- Exposed headers for rate limit info

### 3. Security Headers

All responses include:
- **X-Content-Type-Options**: nosniff (prevent MIME sniffing)
- **X-Frame-Options**: DENY/SAMEORIGIN (prevent clickjacking)
- **X-XSS-Protection**: 1; mode=block (XSS protection)
- **Strict-Transport-Security**: HSTS with 1-year max-age
- **Content-Security-Policy**: Restrictive CSP policy
- **Referrer-Policy**: Control referrer information

### 4. PII Protection

Customer service has enhanced security:
- HTTPS only (no HTTP)
- Stricter rate limits (50/min vs 100/min)
- API keys hidden from logs
- Enhanced CSP policy
- Permissions-Policy restricts browser features

## Monitoring & Metrics

### Prometheus Metrics

Kong exposes Prometheus metrics on all services:

```bash
# Scrape Kong metrics
curl http://localhost:8001/metrics

# Metrics include:
# - Request counts per service/route
# - Latency percentiles
# - Bandwidth usage
# - Upstream health status
# - Rate limit hits
```

### Grafana Dashboards

Pre-built dashboards available at:
- http://localhost:3001 (Grafana)
- Default credentials: admin/admin

Import Kong dashboard: Dashboard ID 7424

### Logging

Kong logs are available in multiple formats:

```bash
# View access logs
docker-compose logs -f kong

# Access logs location (inside container)
/var/log/kong/access.log

# View logs with structured format
docker exec offer-agent-kong tail -f /var/log/kong/access.log
```

## Troubleshooting

### Kong Won't Start

```bash
# Check Kong database connection
docker-compose logs kong-database

# Verify migrations ran successfully
docker-compose logs kong-migration

# Check Kong configuration syntax
docker exec offer-agent-kong kong config parse /etc/kong/kong.yml
```

### Rate Limiting Not Working

```bash
# Verify Redis connection
docker exec offer-agent-kong redis-cli -h redis -a redis_password ping

# Check rate limiting plugin is active
curl http://localhost:8001/plugins | jq '.data[] | select(.name=="rate-limiting")'

# View rate limit state in Redis
docker exec offer-agent-redis redis-cli --raw -a redis_password
> KEYS rate_limit:*
> GET rate_limit:api_key:your-key
```

### 401 Unauthorized Errors

```bash
# Verify consumer exists
curl http://localhost:8001/consumers

# Check API key is configured
curl http://localhost:8001/consumers/{username}/key-auth

# Test with correct API key
curl -H "X-API-Key: a2a-test-key-change-in-production" \
     http://localhost:8000/v1/conversations
```

### CORS Errors

```bash
# Check CORS plugin configuration
curl http://localhost:8001/plugins | jq '.data[] | select(.name=="cors")'

# Verify FRONTEND_URL environment variable
docker exec offer-agent-kong env | grep FRONTEND_URL

# Test preflight request
curl -X OPTIONS http://localhost:8000/v1/conversations \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -v
```

## Production Considerations

### 1. TLS/SSL Certificates

For production HTTPS:

```bash
# Mount SSL certificates in docker-compose.yml
volumes:
  - ./ssl/cert.pem:/etc/kong/ssl/cert.pem:ro
  - ./ssl/key.pem:/etc/kong/ssl/key.pem:ro

# Configure SSL in Kong
environment:
  KONG_SSL_CERT: /etc/kong/ssl/cert.pem
  KONG_SSL_CERT_KEY: /etc/kong/ssl/key.pem
```

### 2. Database Mode vs DB-less Mode

Current setup uses database mode for persistent configuration.

For DB-less mode:
```yaml
environment:
  KONG_DATABASE: off
  KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yml
```

### 3. High Availability

For production HA:
- Run multiple Kong instances behind load balancer
- Use managed PostgreSQL (RDS, Cloud SQL)
- Use Redis Cluster for rate limiting
- Configure health checks in load balancer

### 4. Secrets Management

Replace hardcoded API keys with secret management:
- HashiCorp Vault
- AWS Secrets Manager
- Kubernetes Secrets
- Environment-specific .env files (not in git)

### 5. Monitoring Alerts

Configure alerts for:
- Rate limit threshold (>80% of limit)
- High latency (>3s response time)
- Error rate (>5% 5xx errors)
- Upstream failures
- Certificate expiration

## References

- [Kong Documentation](https://docs.konghq.com/)
- [Kong Declarative Config](https://docs.konghq.com/gateway/latest/production/deployment-topologies/db-less-and-declarative-config/)
- [Kong Plugins](https://docs.konghq.com/hub/)
- [Rate Limiting Plugin](https://docs.konghq.com/hub/kong-inc/rate-limiting/)
- [Key Authentication Plugin](https://docs.konghq.com/hub/kong-inc/key-auth/)
- [JWT Plugin](https://docs.konghq.com/hub/kong-inc/jwt/)
