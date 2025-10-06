# API Gateway & Middleware Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Clients                                │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │  Frontend    │  │  A2A Agent   │  │  Admin Web   │  │  Monitoring │ │
│  │  (Browser)   │  │  (API Key)   │  │  (JWT)       │  │  (API Key)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬──────┘ │
│         │                 │                 │                 │         │
└─────────┼─────────────────┼─────────────────┼─────────────────┼─────────┘
          │                 │                 │                 │
          │                 │                 │                 │
          ▼                 ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        Kong API Gateway (Port 8000)                      │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                      Plugin Chain (per request)                     │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  1. IP Restriction       → Block/Allow by IP                       │ │
│  │  2. Request Size Limit   → Max 10MB payload                        │ │
│  │  3. Bot Detection        → Identify/block bots                     │ │
│  │  4. Rate Limiting        → 100 req/min (Redis)                     │ │
│  │  5. Authentication       → API Key or JWT validation               │ │
│  │  6. Request Transform    → Add gateway headers                     │ │
│  │  7. CORS                 → Handle preflight & headers              │ │
│  │  8. Response Transform   → Add security headers                    │ │
│  │  9. Prometheus           → Collect metrics                         │ │
│  │ 10. File Log             → Log access                              │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  Service Routes:                                                         │
│  ┌─────────────────────┬─────────────────────────────────────────────┐ │
│  │ /v1/conversations   │ → Backend:8000  (API Key, 100/min)          │ │
│  │ /v1/offers          │ → Backend:8000  (API Key, 100/min)          │ │
│  │ /v1/customers       │ → Backend:8000  (API Key, 50/min, HTTPS)    │ │
│  │ /v1/approvals       │ → Backend:8000  (JWT, 100/min, HTTPS)       │ │
│  │ /health             │ → Backend:8000  (No Auth, 1000/min)         │ │
│  └─────────────────────┴─────────────────────────────────────────────┘ │
│                                                                           │
│  State Stores:                                                           │
│  ┌──────────────────┐  ┌───────────────────┐                            │
│  │  Kong Database   │  │  Redis (Limits)   │                            │
│  │  (PostgreSQL)    │  │  (Shared State)   │                            │
│  └──────────────────┘  └───────────────────┘                            │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │
                                │ Upstream Request
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Port 8000)                          │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Middleware Stack (order matters)                 │ │
│  ├────────────────────────────────────────────────────────────────────┤ │
│  │  1. SecurityHeadersMiddleware                                       │ │
│  │     • Add CSP, HSTS, X-Frame-Options, etc.                         │ │
│  │     • Remove server headers                                         │ │
│  │     • Enforce HTTPS redirect (production)                           │ │
│  │                                                                      │ │
│  │  2. TLSEnforcementMiddleware                                        │ │
│  │     • Verify TLS 1.3 minimum                                        │ │
│  │     • Check X-Forwarded-Proto header                                │ │
│  │     • Return 426 if HTTP in production                              │ │
│  │                                                                      │ │
│  │  3. RequestLoggingMiddleware                                        │ │
│  │     • Generate unique request ID                                    │ │
│  │     • Log request (sanitize PII)                                    │ │
│  │     • Time request duration                                         │ │
│  │     • Log response with metrics                                     │ │
│  │     • Detect slow requests (>3s)                                    │ │
│  │                                                                      │ │
│  │  4. CORSMiddleware (FastAPI built-in)                               │ │
│  │     • Validate origin                                               │ │
│  │     • Handle preflight OPTIONS                                      │ │
│  │     • Add CORS headers                                              │ │
│  │                                                                      │ │
│  │  5. GZipMiddleware (FastAPI built-in)                               │ │
│  │     • Compress responses >1000 bytes                                │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  Route Handlers (with dependencies):                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  @router.post("/conversations")                                  │   │
│  │  async def create_conversation(                                  │   │
│  │      api_key: str = Depends(verify_api_key),  ← Auth dependency │   │
│  │      request: Request,                                           │   │
│  │      data: ConversationCreate                                    │   │
│  │  ):                                                               │   │
│  │      # Log business event                                        │   │
│  │      log_business_event("conversation_created", request, {...})  │   │
│  │      return conversation                                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  Services:                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────────┐  │
│  │  Conversation    │  │  Offer           │  │  Customer           │  │
│  │  Service         │  │  Service         │  │  Service (GDPR)     │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          External Services                               │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │  PostgreSQL  │  │  Redis       │  │  Qdrant      │  │  OpenAI    │ │
│  │  (Data+Events│  │  (Sessions)  │  │  (Vectors)   │  │  (GPT-4)   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  Keycloak    │  │  Prometheus  │  │  Grafana     │                  │
│  │  (Auth)      │  │  (Metrics)   │  │  (Dashboards)│                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Request Flow

### 1. API Key Authentication Flow

```
Client Request
    │
    │  POST /v1/conversations
    │  X-API-Key: abc123
    │
    ▼
┌─────────────────┐
│  Kong Gateway   │
│                 │
│  1. Rate Limit  │─────→ Redis: Check rate_limit:api_key:abc123
│     ✓ 45/100    │       ZCOUNT key (timestamp range)
│                 │
│  2. Key Auth    │─────→ Database: SELECT * FROM consumers
│     ✓ Valid     │       WHERE keyauth_credentials = 'abc123'
│                 │
│  3. Add Headers │       X-Gateway-Version: 1.0.0
│                 │       X-Forwarded-Proto: https
│                 │
│  4. CORS        │       Access-Control-Allow-Origin: *
│                 │       Access-Control-Allow-Credentials: true
│                 │
│  5. Security    │       X-Content-Type-Options: nosniff
│     Headers     │       X-Frame-Options: DENY
│                 │       Strict-Transport-Security: ...
└────────┬────────┘
         │
         │  Forward to Backend:8000
         │
         ▼
┌─────────────────┐
│  FastAPI        │
│                 │
│  1. Security    │       Add/verify security headers
│     Middleware  │
│                 │
│  2. TLS Check   │       Verify HTTPS (prod only)
│                 │
│  3. Logging     │       Generate request_id: uuid
│     Middleware  │       Log: {method: POST, path: /v1/conversations, ...}
│                 │       PII redaction active
│                 │
│  4. CORS        │       Already handled by Kong, but can add more
│     Middleware  │
│                 │
│  5. Route       │       Match: /v1/conversations
│     Handler     │
│                 │
│  6. Dependency  │       verify_api_key(x_api_key="abc123")
│     Injection   │       ✓ Already validated by Kong
│                 │
│  7. Business    │       create_conversation(data)
│     Logic       │
│                 │
│  8. Response    │       {id: "...", status: "created"}
│                 │
│  9. Log         │       Log: {status: 200, duration_ms: 245}
│     Response    │
└────────┬────────┘
         │
         │  Response
         │
         ▼
┌─────────────────┐
│  Kong Gateway   │
│                 │
│  1. Security    │       Headers already present
│     Headers     │
│                 │
│  2. Prometheus  │       Increment: kong_http_requests_total{service="conversation"}
│     Metrics     │       Observe: kong_latency{service="conversation"} = 250ms
│                 │
│  3. File Log    │       127.0.0.1 - [06/Oct/2025:15:23:45] "POST /v1/conversations"
│                 │       200 245ms
└────────┬────────┘
         │
         │  200 OK
         │  X-Request-ID: uuid
         │  X-RateLimit-Remaining: 44
         │
         ▼
     Client
```

### 2. JWT Authentication Flow (Admin)

```
Client Request
    │
    │  GET /v1/approvals/pending
    │  Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbG...
    │
    ▼
┌─────────────────┐
│  Kong Gateway   │
│                 │
│  1. Rate Limit  │─────→ Redis: Check rate_limit:ip:192.168.1.100
│     ✓ 12/100    │
│                 │
│  2. JWT Auth    │─────→ Keycloak: GET /realms/offer-agent/protocol/openid-connect/certs
│     Plugin      │       Verify signature with public key
│                 │       Check exp, nbf claims
│                 │       ✓ Valid, exp: 2025-10-07
│                 │
│  3. Security    │       (Same as API Key flow)
│     Headers     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │
│                 │
│  1. Middleware  │       (Same stack as above)
│     Stack       │
│                 │
│  2. Route       │       Match: /v1/approvals/pending
│     Handler     │
│                 │
│  3. Dependency  │       verify_jwt_token(token)
│     Injection   │       Decode: {sub: "user123", roles: ["sales_manager"]}
│                 │       get_user_from_token() → {user_id, email, roles}
│                 │
│  4. Role Check  │       require_role("sales_manager")
│     (if needed) │       ✓ User has required role
│                 │
│  5. Business    │       list_pending_approvals(user_id)
│     Logic       │
└─────────────────┘
```

### 3. Rate Limit Exceeded Flow

```
Client Request (101st in 1 minute)
    │
    ▼
┌─────────────────┐
│  Kong Gateway   │
│                 │
│  1. Rate Limit  │─────→ Redis: ZCOUNT rate_limit:api_key:abc123
│     ✗ 100/100   │       Result: 100 (limit reached)
│                 │
│  2. Reject      │       429 Too Many Requests
│     Request     │       X-RateLimit-Limit: 100
│                 │       X-RateLimit-Remaining: 0
│                 │       X-RateLimit-Reset: 1728229500
│                 │       Retry-After: 60
│                 │
│  3. Prometheus  │       Increment: kong_http_requests_total{status="429"}
│     Metrics     │
└────────┬────────┘
         │
         │  429 Too Many Requests
         │  {error_code: "RATE_LIMIT_EXCEEDED", ...}
         │
         ▼
     Client
```

### 4. PII Logging Protection

```
Backend Receives Request
    │
    │  POST /v1/customers
    │  Body: {
    │    "email": "john@example.com",
    │    "name": "John Doe",
    │    "phone": "+1234567890",
    │    "project": "Website Redesign"
    │  }
    │
    ▼
┌─────────────────────────┐
│  RequestLoggingMiddleware│
│                         │
│  1. Sanitize Data       │
│     - Detect PII fields │
│     - Replace with      │
│       [REDACTED]        │
│                         │
│  2. Sanitize Path       │
│     - Replace UUIDs     │
│     - Replace IDs       │
│                         │
│  3. Log Request         │
│     {                   │
│       "path": "/v1/customers/{id}",
│       "body": {         │
│         "email": "[REDACTED]",
│         "name": "[REDACTED]",
│         "phone": "[REDACTED]",
│         "project": "Website Redesign"
│       }                 │
│     }                   │
│                         │
│  ✓ GDPR Compliant      │
└─────────────────────────┘
```

## Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     Defense in Depth                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Network                                            │
│    • Firewall rules                                          │
│    • DDoS protection                                         │
│    • IP whitelisting (optional)                              │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Kong Gateway                                       │
│    • Rate limiting (prevent abuse)                           │
│    • Request size limits (prevent DoS)                       │
│    • Bot detection                                           │
│    • API key validation                                      │
│    • JWT signature verification                              │
│    • CORS enforcement                                        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: TLS                                                │
│    • TLS 1.3 minimum                                         │
│    • Strong cipher suites                                    │
│    • Certificate validation                                  │
│    • HSTS headers                                            │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Application Middleware                             │
│    • Security headers (CSP, X-Frame-Options)                 │
│    • TLS enforcement                                         │
│    • Request logging (audit trail)                           │
│    • PII redaction                                           │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Route Dependencies                                 │
│    • API key re-verification                                 │
│    • JWT claims validation                                   │
│    • Role-based access control                               │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: Business Logic                                     │
│    • Input validation                                        │
│    • Authorization checks                                    │
│    • Data encryption                                         │
│    • GDPR compliance                                         │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

```
┌──────────────────────────────────────────────────────────────┐
│                      Metrics Flow                             │
└──────────────────────────────────────────────────────────────┘

Kong Gateway ──────┐
                   │
Backend App ───────┼───→  Prometheus ───→  Grafana
                   │        (Port 9090)      (Port 3001)
Redis ─────────────┘
PostgreSQL ────────┘

Metrics Collected:
• Request rate (req/s)
• Response latency (p50, p95, p99)
• Error rate (4xx, 5xx)
• Rate limit hits
• Authentication failures
• Slow requests (>3s)
• Database query time
• Cache hit rate

┌──────────────────────────────────────────────────────────────┐
│                        Logs Flow                              │
└──────────────────────────────────────────────────────────────┘

Kong Access Logs ──┐
                   │
Backend App Logs ──┼───→  Aggregator ───→  Search/Analysis
                   │      (Loki/ELK)        (Kibana/Grafana)
Service Logs ──────┘

Log Types:
• Access logs (all HTTP requests)
• Application logs (business events)
• Security logs (auth failures, suspicious activity)
• Error logs (exceptions, stack traces)
• Audit logs (GDPR operations, data changes)

All logs structured JSON with:
• timestamp
• request_id (correlation)
• level (info, warning, error)
• message
• context (sanitized)
```

## Deployment Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                      Production Setup                           │
└────────────────────────────────────────────────────────────────┘

                          Load Balancer
                          (nginx/HAProxy)
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │ Kong 1  │ │ Kong 2  │ │ Kong 3  │
              └────┬────┘ └────┬────┘ └────┬────┘
                   │           │           │
                   └───────────┼───────────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
                    ▼          ▼          ▼
              ┌─────────┐ ┌─────────┐ ┌─────────┐
              │Backend 1│ │Backend 2│ │Backend 3│
              └────┬────┘ └────┬────┘ └────┬────┘
                   │           │           │
                   └───────────┼───────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ PostgreSQL   │    │ Redis Cluster│    │   Keycloak   │
  │ (Primary +   │    │ (Master +    │    │   (HA)       │
  │  Replicas)   │    │  Replicas)   │    │              │
  └──────────────┘    └──────────────┘    └──────────────┘

Benefits:
• High availability (no single point of failure)
• Horizontal scaling (add more instances)
• Load distribution
• Rolling updates (zero downtime)
• Fault isolation
```

## Configuration Management

```
Development          Staging             Production
    │                   │                     │
    │                   │                     │
    ▼                   ▼                     ▼
.env (local)       .env.staging        .env.production
    │                   │                     │
    ├─→ ENFORCE_HTTPS=false            ENFORCE_HTTPS=true
    ├─→ LOG_LEVEL=DEBUG                LOG_LEVEL=INFO
    ├─→ CORS_ORIGINS=*                 CORS_ORIGINS=https://app.aigentics.com
    ├─→ API_KEYS=test-keys             API_KEYS=prod-secrets (from Vault)
    └─→ RATE_LIMIT=1000                RATE_LIMIT=100

Environment-Specific Behavior:
• Dev: Relaxed security, verbose logging, wildcard CORS
• Staging: Production-like config, test data
• Production: Strict security, minimal logging, specific CORS
```
