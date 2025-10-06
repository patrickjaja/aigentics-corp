# Middleware Package

FastAPI middleware for the AI Offer Agent backend services.

## Overview

This package provides middleware components for:
- **Authentication**: API key and JWT validation
- **Logging**: Structured request/response logging with PII redaction
- **Security**: Security headers, CORS, TLS enforcement

## Middleware Components

### 1. Authentication Middleware (`auth.py`)

Handles API key and JWT authentication for different service types.

#### API Key Authentication

For external agents and A2A protocol:

```python
from fastapi import Depends
from middleware import verify_api_key

@router.post("/conversations")
async def create_conversation(
    api_key: str = Depends(verify_api_key),
    data: ConversationCreate
):
    # api_key is validated
    return {"status": "created"}
```

#### JWT Authentication

For admin portal and internal services:

```python
from fastapi import Depends
from middleware import verify_jwt_token, get_user_from_token

@router.get("/approvals")
async def list_approvals(
    token: dict = Depends(verify_jwt_token)
):
    user = get_user_from_token(token)
    # user contains: user_id, email, name, roles
    return approvals
```

#### Role-Based Access Control

```python
from fastapi import Depends
from middleware import require_role

@router.post("/approvals/{id}/approve", dependencies=[Depends(require_role("sales_manager"))])
async def approve_offer(id: str):
    # Only users with 'sales_manager' role can access
    return {"status": "approved"}
```

#### Configuration

Set environment variables:

```bash
# API Keys (comma-separated list)
VALID_API_KEYS=key1,key2,key3

# JWT Configuration
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
KEYCLOAK_ISSUER=https://keycloak.example.com/realms/offer-agent
```

### 2. Logging Middleware (`logging.py`)

Structured logging with automatic PII redaction for GDPR compliance.

#### Setup

Add to FastAPI application:

```python
from fastapi import FastAPI
from middleware import RequestLoggingMiddleware

app = FastAPI()

app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=False,      # Don't log bodies by default (PII safety)
    log_response_body=False,
    max_body_length=1000,
    skip_paths=["/health", "/metrics"]  # Skip health checks
)
```

#### Features

**Automatic PII Redaction**

The following fields are automatically redacted from logs:
- `email`, `phone`, `address`, `name`, `ssn`, `tax_id`
- `password`, `secret`, `token`, `api_key`
- `credit_card`, `card_number`, `cvv`, `iban`

Example:
```python
# Input
{"name": "John Doe", "email": "john@example.com", "project": "Website"}

# Logged as
{"name": "[REDACTED]", "email": "[REDACTED]", "project": "Website"}
```

**Request Correlation**

Each request gets a unique ID for tracing:

```python
from middleware import get_request_id

@router.post("/offers")
async def create_offer(request: Request):
    request_id = get_request_id(request)
    # Use in logs, pass to background tasks, etc.
```

**Business Event Logging**

Log important business events:

```python
from middleware import log_business_event

@router.post("/offers")
async def create_offer(request: Request, data: OfferCreate):
    offer = create_offer_service(data)

    log_business_event(
        event_type="offer_generated",
        request=request,
        data={
            "offer_id": offer.id,
            "value": offer.total_value,
            "customer_id": offer.customer_id
        }
    )
```

**Security Event Logging**

Track security-related events:

```python
from middleware import log_security_event

@router.post("/login")
async def login(request: Request, credentials: LoginRequest):
    if not validate_credentials(credentials):
        log_security_event(
            event_type="auth_failed",
            request=request,
            details={"username": credentials.username},
            severity="warning"
        )
        raise HTTPException(401)
```

#### Log Format

All logs are structured JSON:

```json
{
  "timestamp": "2025-10-06T15:23:45.123456",
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "type": "request",
  "method": "POST",
  "path": "/v1/offers/{id}",
  "status_code": 200,
  "duration_ms": 245.67,
  "client": {
    "host": "192.168.1.100",
    "port": 54321
  },
  "headers": {
    "user-agent": "Mozilla/5.0...",
    "x-api-key": "[REDACTED]"
  }
}
```

#### Performance Logging

Slow requests (>3s) are automatically logged as warnings:

```python
# Automatically logged if response takes >3s
logger.warning("API Response - Slow Request", extra={...})
```

### 3. Security Middleware (`security.py`)

Implements security headers, CORS, and TLS enforcement.

#### Security Headers

Add to FastAPI application:

```python
from fastapi import FastAPI
from middleware import SecurityHeadersMiddleware

app = FastAPI()

app.add_middleware(
    SecurityHeadersMiddleware,
    enforce_https=True,              # Redirect HTTP to HTTPS
    hsts_max_age=31536000,           # 1 year HSTS
    frame_options="DENY",            # Prevent clickjacking
    referrer_policy="strict-origin-when-cross-origin"
)
```

**Headers Applied**

All responses include:

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
Content-Security-Policy: default-src 'self'; script-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()...
```

**Custom CSP Policy**

```python
app.add_middleware(
    SecurityHeadersMiddleware,
    csp_policy=(
        "default-src 'self'; "
        "script-src 'self' https://cdn.example.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:;"
    )
)
```

#### CORS Configuration

```python
from middleware import setup_cors_middleware

app = FastAPI()
setup_cors_middleware(
    app,
    allowed_origins=[
        "http://localhost:3000",
        "https://app.aigentics.com",
        "https://*.aigentics.com"  # Wildcard subdomain
    ]
)
```

#### TLS Enforcement

```python
from middleware import TLSEnforcementMiddleware

app.add_middleware(
    TLSEnforcementMiddleware,
    min_tls_version="1.3",    # Require TLS 1.3
    require_tls=True          # Reject HTTP in production
)
```

#### Utility Functions

**Validate Origin**

```python
from middleware import validate_origin

if validate_origin(
    origin="https://app.aigentics.com",
    allowed_origins=["https://*.aigentics.com"]
):
    # Origin is allowed
    pass
```

**Get Security Headers**

```python
from middleware import get_security_headers

headers = get_security_headers(
    include_csp=True,
    include_hsts=True,
    frame_options="SAMEORIGIN"
)

# Use in response
return JSONResponse(content={...}, headers=headers)
```

**Sanitize Redirect URL**

Prevent open redirect vulnerabilities:

```python
from middleware import sanitize_redirect_url

redirect_url = sanitize_redirect_url(
    url=user_provided_url,
    allowed_domains=["aigentics.com", "app.aigentics.com"]
)

if redirect_url:
    return RedirectResponse(url=redirect_url)
else:
    raise HTTPException(400, "Invalid redirect URL")
```

## Complete Setup Example

```python
from fastapi import FastAPI
from middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    TLSEnforcementMiddleware,
    setup_cors_middleware
)

app = FastAPI()

# 1. Security headers (first, to wrap all responses)
app.add_middleware(
    SecurityHeadersMiddleware,
    enforce_https=True,
    hsts_max_age=31536000,
    frame_options="DENY"
)

# 2. TLS enforcement
app.add_middleware(
    TLSEnforcementMiddleware,
    min_tls_version="1.3",
    require_tls=True
)

# 3. Request logging (after security, to log secure requests)
app.add_middleware(
    RequestLoggingMiddleware,
    log_request_body=False,
    log_response_body=False,
    skip_paths=["/health", "/metrics"]
)

# 4. CORS (configured separately)
setup_cors_middleware(app, allowed_origins=[
    "http://localhost:3000",
    "https://app.aigentics.com"
])

# 5. Rate limiting (handled by Kong Gateway)
# No middleware needed - Kong handles this
```

## Environment Variables

```bash
# Authentication
VALID_API_KEYS=key1,key2,key3
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
KEYCLOAK_ISSUER=https://keycloak.example.com/realms/offer-agent

# Security
ENFORCE_HTTPS=true
CORS_ORIGINS=http://localhost:3000,https://app.aigentics.com
ENVIRONMENT=production

# Logging
LOG_LEVEL=INFO
```

## GDPR Compliance

All middleware components are designed with GDPR compliance:

### PII Redaction

Logging middleware automatically redacts PII:
- Email addresses
- Phone numbers
- Names
- Addresses
- Financial information
- Credentials

### Data Minimization

- Request/response bodies not logged by default
- Only essential headers logged
- API keys and tokens always redacted
- Path parameters sanitized (UUIDs/IDs replaced with placeholders)

### Audit Trail

Every request is logged with:
- Unique request ID
- Timestamp
- Method and path (sanitized)
- Status code
- Duration
- Client IP (for security, but can be anonymized)

### Right to Erasure

Security events and business events can be configured to exclude customer identifiers when needed.

## Performance Considerations

### Logging Overhead

- PII redaction adds ~1-5ms per request
- Skipping health checks reduces log volume
- Structured logging enables efficient log parsing

### Security Headers

- Minimal overhead (<1ms)
- Headers cached and reused
- No external service calls

### Authentication

- API key validation is in-memory (fast)
- JWT validation can cache decoded tokens
- Consider Redis caching for Keycloak public keys

## Testing

### Test Authentication

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Test without API key
response = client.post("/v1/conversations")
assert response.status_code == 401

# Test with API key
response = client.post(
    "/v1/conversations",
    headers={"X-API-Key": "test-key"}
)
assert response.status_code == 200
```

### Test Logging

```python
import logging
from middleware import sanitize_data

def test_pii_redaction():
    data = {
        "email": "test@example.com",
        "name": "John Doe",
        "project": "Website"
    }

    sanitized = sanitize_data(data)

    assert sanitized["email"] == "[REDACTED]"
    assert sanitized["name"] == "[REDACTED]"
    assert sanitized["project"] == "Website"
```

### Test Security Headers

```python
def test_security_headers():
    response = client.get("/health")

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in response.headers
```

## Troubleshooting

### Authentication Not Working

1. Check API key is in `VALID_API_KEYS` environment variable
2. Verify header name is `X-API-Key` (case-sensitive)
3. Check logs for authentication errors

### Logs Not Appearing

1. Check `LOG_LEVEL` environment variable
2. Verify path is not in `skip_paths`
3. Check logging configuration in main.py

### CORS Errors

1. Verify `CORS_ORIGINS` includes frontend URL
2. Check origin matches exactly (including protocol and port)
3. Test with wildcard `*` to isolate issue (not for production)

### Security Headers Missing

1. Ensure `SecurityHeadersMiddleware` is added to app
2. Check middleware order (security should be first)
3. Verify not overridden by downstream middleware

## References

- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [GDPR Requirements](https://gdpr.eu/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
