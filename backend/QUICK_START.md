# Quick Start Guide - API Endpoints

## Testing the API Endpoints

### Prerequisites
```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Set environment variables
export VALID_API_KEYS="test-api-key-123"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET_KEY="dev-secret-key"
```

### Start the API Server
```bash
# From backend directory
python -m src.main

# Or with uvicorn directly
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: http://localhost:8000

### Access API Documentation
- **Swagger UI**: http://localhost:8000/docs (interactive testing)
- **ReDoc**: http://localhost:8000/redoc (beautiful docs)
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## Example API Calls

### 1. Start a Conversation (T043)
```bash
curl -X POST "http://localhost:8000/v1/conversations" \
  -H "X-API-Key: test-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "en",
    "session_id": "session-123"
  }'
```

**Response:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "initial_questions": [
    {
      "id": "q_0",
      "text": "What is the main purpose of your project?",
      "type": "text",
      "required": false
    }
  ],
  "language": "en"
}
```

### 2. Send a Message (T044)
```bash
curl -X POST "http://localhost:8000/v1/conversations/{conversation_id}/messages" \
  -H "X-API-Key: test-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We need a web application for managing customer orders",
    "context": {}
  }'
```

**Response:**
```json
{
  "message": "Thank you for that information. I'd like to understand more...",
  "questions": [
    {
      "id": "q_0",
      "text": "How many users do you expect?",
      "type": "number",
      "required": true
    }
  ],
  "completion_percentage": 20,
  "suggested_category": "software_development",
  "confidence_score": 0.85
}
```

### 3. Get Conversation Details (T045)
```bash
curl -X GET "http://localhost:8000/v1/conversations/{conversation_id}" \
  -H "X-API-Key: test-api-key-123"
```

**Response:**
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "started_at": "2025-10-06T10:00:00Z",
  "last_interaction_at": "2025-10-06T10:05:00Z",
  "completion_percentage": 60,
  "interactions_count": 12,
  "gathered_requirements": [
    "Web application",
    "Customer order management",
    "50-100 concurrent users"
  ]
}
```

### 4. Generate an Offer (T046)
```bash
curl -X POST "http://localhost:8000/v1/offers" \
  -H "X-API-Key: test-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "660e8400-e29b-41d4-a716-446655440001",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
    "customer_id": "770e8400-e29b-41d4-a716-446655440002"
  }'
```

**Response:**
```json
{
  "offer_id": "880e8400-e29b-41d4-a716-446655440003",
  "offer_number": "25-0001",
  "status": "draft",
  "total_value": {
    "amount": "45000.00",
    "currency": "EUR",
    "formatted": "45.000,00 €"
  },
  "approval_required": false,
  "created_at": "2025-10-06T10:15:00Z",
  "valid_until": "2025-11-05"
}
```

### 5. Create Customer (T049)
```bash
curl -X POST "http://localhost:8000/v1/customers" \
  -H "X-API-Key: test-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corporation",
    "contact_person": "John Doe",
    "email": "john.doe@acme.com",
    "phone": "+491234567890",
    "language_preference": "de",
    "gdpr_consent": {
      "given": true,
      "purposes": ["offer_generation", "marketing"],
      "consent_text_version": "v1.0",
      "ip_address": "192.168.1.1"
    }
  }'
```

**Response:**
```json
{
  "customer_id": "770e8400-e29b-41d4-a716-446655440002",
  "gdpr_consent_recorded": true
}
```

### 6. Download Offer PDF (T048)
```bash
curl -X POST "http://localhost:8000/v1/offers/{offer_id}/download" \
  -H "X-API-Key: test-api-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Acme Corporation",
    "contact_person": "John Doe",
    "email": "john.doe@acme.com",
    "language_preference": "de",
    "gdpr_consent": {
      "given": true,
      "purposes": ["offer_generation"],
      "consent_text_version": "v1.0",
      "ip_address": "192.168.1.1"
    }
  }' \
  --output offer.pdf
```

### 7. Get Pending Approvals - Admin (T051)
```bash
curl -X GET "http://localhost:8000/v1/approvals/pending?limit=10" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Response:**
```json
{
  "total": 3,
  "items": [
    {
      "workflow_id": "990e8400-e29b-41d4-a716-446655440004",
      "offer_id": "880e8400-e29b-41d4-a716-446655440003",
      "offer_number": "25-0001",
      "requested_at": "2025-10-06T10:15:00Z",
      "status": "pending",
      "offer_value": {
        "amount": "125000.00",
        "currency": "EUR",
        "formatted": "125.000,00 €"
      },
      "customer_name": "Big Corp GmbH"
    }
  ]
}
```

### 8. Review and Decide on Approval (T052)
```bash
# Start review
curl -X POST "http://localhost:8000/v1/approvals/{workflow_id}/review" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Make decision
curl -X POST "http://localhost:8000/v1/approvals/{workflow_id}/decide" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "outcome": "approved",
    "reason": "Offer is well-structured and pricing is competitive",
    "conditions": ["Include 3 months of support"],
    "notify_customer": true
  }'
```

**Response:**
```json
{
  "workflow_id": "990e8400-e29b-41d4-a716-446655440004",
  "outcome": "approved",
  "offer_status": "approved",
  "customer_notified": true
}
```

### 9. Delete Customer (GDPR) (T050)
```bash
curl -X DELETE "http://localhost:8000/v1/customers/{customer_id}" \
  -H "X-API-Key: test-api-key-123"
```

**Response:**
```json
{
  "status": "deletion_requested",
  "customer_id": "770e8400-e29b-41d4-a716-446655440002",
  "deletion_requested_at": "2025-10-06T10:30:00Z",
  "retention_period_years": 4,
  "final_deletion_date": "2029-10-06T10:30:00Z",
  "message": "Customer deletion request recorded. Data will be pseudonymized immediately and deleted after 4-year legal retention period."
}
```

## Rate Limiting

All endpoints include rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1696595460
```

If you exceed the limit, you'll get a 429 response:
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "message": "Rate limit of 100 requests per 60 seconds exceeded",
  "details": {
    "limit": 100,
    "reset_at": 1696595460
  }
}
```

## Error Handling

All errors follow the standard format:
```json
{
  "error_code": "CONVERSATION_NOT_FOUND",
  "message": "Conversation {id} not found",
  "details": {
    "additional": "context"
  }
}
```

Common error codes:
- `INVALID_UUID` - Malformed UUID in path
- `API_KEY_MISSING` - X-API-Key header not provided
- `INVALID_API_KEY` - API key is not valid
- `TOKEN_MISSING` - Authorization header not provided
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `GDPR_CONSENT_REQUIRED` - GDPR consent not provided or invalid

## Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Kubernetes readiness probe
curl http://localhost:8000/ready
```

## Interactive Testing with Swagger UI

The easiest way to test all endpoints is through Swagger UI:

1. Open http://localhost:8000/docs
2. Click "Authorize" button
3. Enter your API key: `test-api-key-123`
4. Try out any endpoint with interactive forms
5. View request/response examples

## Next Steps

1. **Connect to PostgreSQL** - Implement actual database persistence
2. **Connect to Redis** - Enable distributed rate limiting
3. **Test LangGraph workflows** - Ensure conversation AI works
4. **Add event publishing** - Integrate with event bus
5. **Frontend integration** - Connect React components to API
