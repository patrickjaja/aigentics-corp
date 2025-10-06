# Middleware Integration Guide

Complete guide for integrating all middleware components into the FastAPI application.

## Quick Start

### 1. Update main.py

```python
"""
AI Offer Agent - Main FastAPI Application with Full Middleware Stack
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
import os
import logging

from .api import api_router
from .infrastructure.middleware.rate_limit import shutdown_rate_limiter
from .middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TLSEnforcementMiddleware,
    setup_cors_middleware
)


# Configure structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Create FastAPI application
app = FastAPI(
    title="AI Offer Agent API",
    description="AI-powered offer generation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# ============================================================================
# MIDDLEWARE STACK (order matters!)
# ============================================================================

# 1. Security Headers (first - wraps all responses)
app.add_middleware(
    SecurityHeadersMiddleware,
    enforce_https=os.getenv("ENFORCE_HTTPS", "false").lower() == "true",
    hsts_max_age=31536000,  # 1 year
    frame_options="DENY",
    referrer_policy="strict-origin-when-cross-origin"
)

# 2. TLS Enforcement
app.add_middleware(
    TLSEnforcementMiddleware,
    min_tls_version="1.3",
    require_tls=os.getenv("ENVIRONMENT", "development") == "production"
)

# 3. Request/Response Logging (after security)
app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=False,  # Don't log bodies (PII safety)
    log_response_body=False,
    max_body_length=1000,
    skip_paths=["/health", "/ready", "/metrics"]
)

# 4. CORS (configured with helper function)
setup_cors_middleware(app)

# 5. GZip compression (last middleware)
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# ROUTES
# ============================================================================

# Include API routes
app.include_router(api_router)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint for load balancers."""
    return {
        "status": "healthy",
        "service": "ai-offer-agent",
        "version": "1.0.0"
    }


@app.get("/ready", tags=["system"])
async def readiness_check():
    """Readiness probe for Kubernetes."""
    # TODO: Add actual dependency checks
    return {"status": "ready"}


# ============================================================================
# APPLICATION LIFECYCLE
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("Starting AI Offer Agent API...")
    logger.info("Middleware stack configured:")
    logger.info("  ✓ Security Headers")
    logger.info("  ✓ TLS Enforcement")
    logger.info("  ✓ Request Logging (PII redaction enabled)")
    logger.info("  ✓ CORS")
    logger.info("  ✓ GZip Compression")
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("Shutting down AI Offer Agent API...")
    await shutdown_rate_limiter()
    logger.info("API shutdown complete")


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", tags=["system"])
async def root():
    """API root endpoint with service information."""
    return {
        "service": "AI Offer Agent API",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "security": {
            "authentication": "API Key (X-API-Key) or JWT (Authorization: Bearer)",
            "rate_limit": "100 requests/minute",
            "cors_enabled": True,
            "tls_enforced": os.getenv("ENVIRONMENT") == "production"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true"
    )
```

### 2. Update API Routes with Authentication

**Conversation API (backend/src/api/conversations.py)**

```python
from fastapi import APIRouter, Depends, Request
from middleware import verify_api_key, log_business_event

router = APIRouter(prefix="/v1/conversations", tags=["conversations"])


@router.post("/", dependencies=[Depends(verify_api_key)])
async def create_conversation(request: Request, data: ConversationCreate):
    """
    Create new conversation (requires API key).
    """
    conversation = await conversation_service.create(data)

    # Log business event
    log_business_event(
        event_type="conversation_created",
        request=request,
        data={"conversation_id": conversation.id}
    )

    return conversation


@router.post("/{id}/messages", dependencies=[Depends(verify_api_key)])
async def send_message(id: str, message: MessageCreate):
    """
    Send message in conversation (requires API key).
    """
    return await conversation_service.send_message(id, message)
```

**Admin API (backend/src/api/admin.py)**

```python
from fastapi import APIRouter, Depends
from middleware import verify_jwt_token, require_role, get_user_from_token

router = APIRouter(prefix="/v1/approvals", tags=["admin"])


@router.get("/pending")
async def list_pending_approvals(token: dict = Depends(verify_jwt_token)):
    """
    List pending approvals (requires JWT).
    """
    user = get_user_from_token(token)
    return await approval_service.list_pending(user_id=user["user_id"])


@router.post(
    "/{id}/approve",
    dependencies=[Depends(require_role("sales_manager"))]
)
async def approve_offer(id: str, token: dict = Depends(verify_jwt_token)):
    """
    Approve offer (requires sales_manager role).
    """
    user = get_user_from_token(token)
    return await approval_service.approve(id, approved_by=user["user_id"])
```

**Customer API (backend/src/api/customers.py)**

```python
from fastapi import APIRouter, Depends, Request
from middleware import verify_api_key, log_security_event

router = APIRouter(prefix="/v1/customers", tags=["customers"])


@router.post("/", dependencies=[Depends(verify_api_key)])
async def create_customer(request: Request, data: CustomerCreate):
    """
    Create customer (requires API key, GDPR consent required).
    """
    if not data.gdpr_consent:
        log_security_event(
            event_type="gdpr_consent_missing",
            request=request,
            details={"attempted_action": "customer_creation"},
            severity="warning"
        )
        raise HTTPException(400, "GDPR consent required")

    return await customer_service.create(data)


@router.delete("/{id}", dependencies=[Depends(verify_api_key)])
async def delete_customer(id: str, request: Request):
    """
    Delete customer - GDPR Right to Erasure (requires API key).
    """
    log_security_event(
        event_type="customer_deletion",
        request=request,
        details={"customer_id": id},
        severity="info"
    )

    return await customer_service.delete(id)
```

### 3. Environment Configuration

Create `.env` file:

```bash
# Copy from .env.example
cp .env.example .env

# Update with production values
# API Keys
VALID_API_KEYS=prod-key-1,prod-key-2,prod-key-3

# JWT
JWT_SECRET_KEY=your-production-secret-key
KEYCLOAK_ISSUER=https://keycloak.aigentics.com/realms/offer-agent

# Security
ENFORCE_HTTPS=true
CORS_ORIGINS=https://app.aigentics.com,https://admin.aigentics.com
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO

# Kong Gateway
A2A_API_KEY=your-a2a-production-key
FRONTEND_API_KEY=your-frontend-production-key
```

## Testing the Integration

### 1. Start Services

```bash
# Start all services with Docker Compose
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend kong
```

### 2. Test Health Check (No Auth)

```bash
# Should work without authentication
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "ai-offer-agent",
#   "version": "1.0.0"
# }
```

### 3. Test API Key Authentication

```bash
# Request without API key (should fail)
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"title": "New Project"}'

# Expected: 401 Unauthorized

# Request with valid API key (should succeed)
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -H "X-API-Key: a2a-test-key-change-in-production" \
  -d '{"title": "New Project"}'

# Expected: 200 OK with conversation data
```

### 4. Test JWT Authentication

```bash
# Get JWT token from Keycloak (replace with your values)
TOKEN=$(curl -X POST http://localhost:8080/realms/offer-agent/protocol/openid-connect/token \
  -d "client_id=offer-agent-api" \
  -d "client_secret=your-client-secret" \
  -d "grant_type=password" \
  -d "username=admin" \
  -d "password=admin" \
  | jq -r '.access_token')

# Use token to access admin API
curl http://localhost:8000/v1/approvals/pending \
  -H "Authorization: Bearer $TOKEN"

# Expected: 200 OK with pending approvals
```

### 5. Test Rate Limiting

```bash
# Make 105 requests quickly
for i in {1..105}; do
  curl -H "X-API-Key: a2a-test-key-change-in-production" \
       http://localhost:8000/v1/conversations \
       -w "\n%{http_code}\n"
done

# Expected:
# - First 100: 200 OK
# - Next 5: 429 Too Many Requests
```

### 6. Test Security Headers

```bash
# Check security headers
curl -I http://localhost:8000/health

# Expected headers:
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# X-XSS-Protection: 1; mode=block
# Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
# Content-Security-Policy: default-src 'self'; ...
# Referrer-Policy: strict-origin-when-cross-origin
```

### 7. Test CORS

```bash
# Preflight request
curl -X OPTIONS http://localhost:8000/v1/conversations \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type,X-API-Key" \
  -v

# Expected:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
# Access-Control-Allow-Credentials: true
```

### 8. Test Request Logging

```bash
# Make a request
curl -H "X-API-Key: a2a-test-key-change-in-production" \
     http://localhost:8000/v1/conversations

# Check logs for structured JSON
docker-compose logs backend | grep "API Request"

# Expected format:
# {
#   "timestamp": "2025-10-06T15:23:45.123456",
#   "request_id": "uuid",
#   "type": "request",
#   "method": "GET",
#   "path": "/v1/conversations"
# }
```

## Production Deployment Checklist

### Security

- [ ] Generate strong API keys (32+ characters)
- [ ] Rotate JWT secret key
- [ ] Enable HTTPS enforcement (`ENFORCE_HTTPS=true`)
- [ ] Configure Keycloak with production realm
- [ ] Set up SSL certificates for Kong
- [ ] Review and tighten CSP policy
- [ ] Enable TLS 1.3 minimum

### Configuration

- [ ] Set `ENVIRONMENT=production`
- [ ] Configure production CORS origins
- [ ] Set appropriate rate limits per service
- [ ] Configure Redis for rate limiting persistence
- [ ] Set up log aggregation (ELK, CloudWatch, etc.)
- [ ] Configure Prometheus for metrics
- [ ] Set up Grafana dashboards

### Monitoring

- [ ] Configure alerts for rate limit violations
- [ ] Set up alerts for authentication failures
- [ ] Monitor security event logs
- [ ] Track slow requests (>3s)
- [ ] Monitor error rates (4xx, 5xx)
- [ ] Set up uptime monitoring

### Compliance

- [ ] Verify PII is redacted from logs
- [ ] Test GDPR deletion workflow
- [ ] Verify audit trail completeness
- [ ] Review data retention policies
- [ ] Test consent management
- [ ] Perform security audit

## Troubleshooting

### Authentication Issues

**Problem**: 401 Unauthorized even with valid API key

**Solution**:
```bash
# Check if API key is in environment
docker exec backend env | grep VALID_API_KEYS

# Verify key format (no spaces, comma-separated)
VALID_API_KEYS=key1,key2,key3  # ✓ Correct
VALID_API_KEYS=key1, key2, key3  # ✗ Spaces break parsing
```

### CORS Issues

**Problem**: Browser shows CORS error

**Solution**:
```bash
# Verify CORS_ORIGINS includes your frontend URL
docker exec backend env | grep CORS_ORIGINS

# Check exact match (including protocol and port)
CORS_ORIGINS=http://localhost:3000  # ✓ Matches exactly
CORS_ORIGINS=http://localhost  # ✗ Port mismatch
```

### Rate Limiting Issues

**Problem**: Rate limits not working

**Solution**:
```bash
# Check Redis connection
docker exec backend redis-cli -h redis -a redis_password ping

# Verify Kong rate limiting plugin
curl http://localhost:8001/plugins | jq '.data[] | select(.name=="rate-limiting")'
```

### Logging Issues

**Problem**: Logs not appearing

**Solution**:
```bash
# Check log level
docker exec backend env | grep LOG_LEVEL

# Verify middleware is registered
docker exec backend python -c "from main import app; print(app.middleware)"

# Check if path is skipped
# Health checks are in skip_paths by default
```

## Advanced Configuration

### Custom Rate Limits per Endpoint

```python
from fastapi import Depends
from infrastructure.middleware.rate_limit import custom_rate_limit

# Expensive endpoint with stricter limit
@router.post(
    "/expensive-operation",
    dependencies=[
        Depends(verify_api_key),
        Depends(custom_rate_limit(limit=10, window_seconds=60))
    ]
)
async def expensive_operation():
    # Only 10 requests per minute for this endpoint
    pass
```

### Custom Security Headers per Route

```python
from fastapi import Response
from middleware import get_security_headers

@router.get("/embed-allowed")
async def embeddable_endpoint():
    """Endpoint that can be embedded in iframe."""
    headers = get_security_headers(
        frame_options="SAMEORIGIN",  # Allow same origin iframes
        include_hsts=True
    )
    return Response(content="...", headers=headers)
```

### Request-Specific Logging

```python
from middleware import log_business_event, log_security_event

@router.post("/high-value-offer")
async def create_high_value_offer(request: Request, data: OfferCreate):
    if data.value > 100000:
        # Log high-value transaction
        log_business_event(
            event_type="high_value_offer_created",
            request=request,
            data={"value": data.value, "currency": "EUR"},
            level="warning"  # Higher visibility
        )

        # Trigger approval workflow
        log_security_event(
            event_type="approval_required",
            request=request,
            details={"offer_value": data.value},
            severity="info"
        )
```

## References

- [FastAPI Middleware](https://fastapi.tiangolo.com/tutorial/middleware/)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [Kong Gateway Docs](https://docs.konghq.com/)
- [GDPR Compliance Guide](https://gdpr.eu/)
