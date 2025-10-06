# AI Offer Agent API Documentation

Version: 1.0.0
Base URL: `https://api.aigentics-corp.com/v1`
OpenAPI Spec: Available at `/openapi.json`

## Overview

The AI Offer Agent API provides endpoints for automated offer generation through conversational AI. The system uses a progressive disclosure approach to gather project requirements and generate detailed IT consulting offers with pricing, work packages, and deliverables.

## Authentication

All API requests require authentication using API keys.

```http
X-API-Key: your_api_key_here
```

API keys can be requested through the admin portal and support both development and production environments.

## Rate Limiting

- **Default Limit**: 100 requests per minute per API key
- **Conversation endpoints**: 50 requests per minute
- **Offer generation**: 10 requests per minute

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
```

## Error Responses

All errors follow this structure:

```json
{
  "error_code": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "additional": "context"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request body or parameters |
| `UNAUTHORIZED` | 401 | Missing or invalid API key |
| `RATE_LIMIT_EXCEEDED` | 429 | Rate limit exceeded |
| `NOT_FOUND` | 404 | Resource not found |
| `INSUFFICIENT_INFORMATION` | 422 | Not enough data to complete operation |
| `SERVICE_TIMEOUT` | 503 | Request timeout (30s exceeded) |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

## OpenAPI 3.1 Specification

### Conversations API

#### Start New Conversation

```yaml
POST /conversations
Content-Type: application/json
X-API-Key: {api_key}

Request Body:
{
  "customer_id": "optional-uuid",
  "language": "de",
  "initial_message": "We need a custom CRM system"
}

Response: 201 Created
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "language": "de",
  "completion_percentage": 10,
  "next_question": {
    "question_id": "q1",
    "text": "Wie viele Benutzer soll das CRM-System unterstützen?",
    "type": "number",
    "options": null,
    "is_required": true
  },
  "created_at": "2025-10-06T15:30:00Z"
}
```

**Example cURL:**
```bash
curl -X POST https://api.aigentics-corp.com/v1/conversations \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "de",
    "initial_message": "We need a custom CRM system"
  }'
```

#### Send Message in Conversation

```yaml
POST /conversations/{conversationId}/messages
Content-Type: application/json
X-API-Key: {api_key}

Request Body:
{
  "content": "About 50 users initially",
  "answer_to_question_id": "q1"
}

Response: 200 OK
{
  "message_id": "msg-123",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "completion_percentage": 25,
  "next_question": {
    "question_id": "q2",
    "text": "Welche Hauptfunktionen benötigen Sie?",
    "type": "multi_select",
    "options": [
      "Lead Management",
      "Contact Management",
      "Sales Pipeline",
      "Reporting"
    ],
    "is_required": true
  },
  "is_complete": false,
  "timestamp": "2025-10-06T15:31:00Z"
}
```

**Example cURL:**
```bash
curl -X POST https://api.aigentics-corp.com/v1/conversations/550e8400-e29b-41d4-a716-446655440000/messages \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "About 50 users initially",
    "answer_to_question_id": "q1"
  }'
```

#### Get Conversation Status

```yaml
GET /conversations/{conversationId}
X-API-Key: {api_key}

Response: 200 OK
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "language": "de",
  "completion_percentage": 85,
  "message_count": 12,
  "can_generate_offer": true,
  "created_at": "2025-10-06T15:30:00Z",
  "updated_at": "2025-10-06T15:45:00Z"
}
```

### Offers API

#### Generate Offer

```yaml
POST /offers
Content-Type: application/json
X-API-Key: {api_key}

Request Body:
{
  "project_id": "proj-uuid",
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "customer_id": "optional-customer-uuid"
}

Response: 201 Created
{
  "offer_id": "off-uuid",
  "offer_number": "25-0042",
  "status": "draft",
  "total_value": {
    "amount": "125000.00",
    "currency": "EUR",
    "formatted": "125.000,00 €"
  },
  "approval_required": true,
  "approval_workflow_id": "wf-uuid",
  "created_at": "2025-10-06T15:50:00Z",
  "valid_until": "2025-11-05"
}
```

**Performance SLA**: Maximum 30 seconds processing time.

**Example cURL:**
```bash
curl -X POST https://api.aigentics-corp.com/v1/offers \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj-uuid",
    "conversation_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

#### Get Offer Details

```yaml
GET /offers/{offerId}
X-API-Key: {api_key}

Response: 200 OK
{
  "offer_id": "off-uuid",
  "offer_number": "25-0042",
  "status": "approved",
  "total_value": {
    "amount": "125000.00",
    "currency": "EUR",
    "formatted": "125.000,00 €"
  },
  "approval_required": true,
  "approval_workflow_id": "wf-uuid",
  "created_at": "2025-10-06T15:50:00Z",
  "valid_until": "2025-11-05",
  "version": 1,
  "work_packages": [
    {
      "id": "wp-1",
      "name": "Requirements Analysis & Design",
      "description": "Detailed analysis of CRM requirements...",
      "deliverables": [
        {
          "name": "Requirements Document",
          "description": "Comprehensive requirements specification",
          "acceptance_criteria": [
            "All stakeholders signed off",
            "Technical feasibility confirmed"
          ]
        }
      ],
      "estimated_hours": {
        "optimistic": 80,
        "likely": 120,
        "pessimistic": 160,
        "expected": 120,
        "confidence": 0.85
      },
      "hourly_rate": {
        "amount": "150.00",
        "currency": "EUR",
        "formatted": "150,00 €"
      },
      "total_cost": {
        "amount": "18000.00",
        "currency": "EUR",
        "formatted": "18.000,00 €"
      },
      "dependencies": null
    }
  ],
  "terms_and_conditions": "Standard T&C apply...",
  "project_details": {
    "name": "Custom CRM System",
    "category": "software_development",
    "requirements_count": 25,
    "timeline": "6 months",
    "budget_range": "100k-150k EUR"
  }
}
```

#### Download Offer as PDF

```yaml
POST /offers/{offerId}/download
Content-Type: application/json
X-API-Key: {api_key}

Request Body:
{
  "customer_data": {
    "gdpr_consent": {
      "given": true,
      "timestamp": "2025-10-06T15:55:00Z",
      "version": "1.0"
    },
    "language_preference": "de"
  }
}

Response: 200 OK
Content-Type: application/pdf
Content-Disposition: attachment; filename="offer-25-0042.pdf"

[PDF binary data]
```

**GDPR Note**: Requires explicit consent to include customer data in PDF.

### Customers API

#### Create Customer

```yaml
POST /customers
Content-Type: application/json
X-API-Key: {api_key}

Request Body:
{
  "company_name": "Acme Corp",
  "contact_person": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@acme.com",
    "phone": "+49 30 12345678"
  },
  "address": {
    "street": "Hauptstraße 123",
    "city": "Berlin",
    "postal_code": "10115",
    "country": "DE"
  },
  "gdpr_consent": {
    "given": true,
    "timestamp": "2025-10-06T16:00:00Z",
    "version": "1.0",
    "purposes": ["offer_generation", "communication"]
  }
}

Response: 201 Created
{
  "customer_id": "cust-uuid",
  "company_name": "Acme Corp",
  "contact_person": {
    "first_name": "John",
    "last_name": "Doe",
    "email": "john.doe@acme.com",
    "phone": "+49 30 12345678"
  },
  "gdpr_consent_status": "active",
  "created_at": "2025-10-06T16:00:00Z"
}
```

#### Delete Customer Data (GDPR Right to Erasure)

```yaml
DELETE /customers/{customerId}
X-API-Key: {api_key}

Response: 204 No Content
```

**GDPR Compliance**:
- Pseudonymizes all personal data
- Retains minimal business data for accounting
- Completes within 30 days of request

### Approvals API (Admin Only)

#### List Pending Approvals

```yaml
GET /approvals/pending
X-API-Key: {admin_api_key}
X-Admin-Role: approver

Query Parameters:
  - min_value: number (optional, filter by minimum offer value)
  - sort: string (default: "created_at_desc")
  - limit: number (default: 20, max: 100)
  - offset: number (default: 0)

Response: 200 OK
{
  "approvals": [
    {
      "workflow_id": "wf-uuid",
      "offer_id": "off-uuid",
      "offer_number": "25-0042",
      "total_value": {
        "amount": "125000.00",
        "currency": "EUR",
        "formatted": "125.000,00 €"
      },
      "customer_name": "Acme Corp",
      "submitted_at": "2025-10-06T15:50:00Z",
      "submitted_by": "agent-uuid",
      "urgency": "medium",
      "age_hours": 2
    }
  ],
  "total_count": 1,
  "has_more": false
}
```

#### Review Approval

```yaml
POST /approvals/{workflowId}/review
Content-Type: application/json
X-API-Key: {admin_api_key}
X-Admin-Role: approver

Request Body:
{
  "decision": "approved",
  "comments": "Approved with minor adjustments to timeline",
  "modifications": {
    "work_package_adjustments": [
      {
        "package_id": "wp-1",
        "new_hours": 100
      }
    ]
  }
}

Response: 200 OK
{
  "workflow_id": "wf-uuid",
  "offer_id": "off-uuid",
  "status": "approved",
  "approved_by": "approver-uuid",
  "approved_at": "2025-10-06T16:30:00Z",
  "comments": "Approved with minor adjustments to timeline",
  "notifications_sent": ["email", "webhook"]
}
```

**Decision Values**: `approved`, `rejected`, `needs_revision`

### Analytics API (Admin Only)

#### Get Offer Generation Metrics

```yaml
GET /analytics/offers
X-API-Key: {admin_api_key}

Query Parameters:
  - start_date: date (ISO 8601, required)
  - end_date: date (ISO 8601, required)
  - granularity: string (hour|day|week|month, default: day)

Response: 200 OK
{
  "metrics": {
    "total_offers": 142,
    "avg_generation_time_ms": 18500,
    "approval_rate": 0.87,
    "avg_value": {
      "amount": "85000.00",
      "currency": "EUR"
    },
    "time_series": [
      {
        "timestamp": "2025-10-01T00:00:00Z",
        "offers_generated": 12,
        "avg_value": "82000.00",
        "approval_rate": 0.83
      }
    ]
  }
}
```

#### Get Conversion Funnel

```yaml
GET /analytics/conversion
X-API-Key: {admin_api_key}

Query Parameters:
  - start_date: date (ISO 8601, required)
  - end_date: date (ISO 8601, required)

Response: 200 OK
{
  "funnel": {
    "conversations_started": 500,
    "conversations_completed": 385,
    "offers_generated": 320,
    "offers_sent": 280,
    "offers_accepted": 156,
    "conversion_rates": {
      "completion": 0.77,
      "generation": 0.83,
      "acceptance": 0.56
    }
  },
  "avg_time_to_conversion": {
    "conversation_to_offer": "45 minutes",
    "offer_to_acceptance": "4.2 days"
  }
}
```

## Webhooks

Configure webhooks in the admin portal to receive real-time notifications.

### Events

- `conversation.completed` - Conversation reached 80%+ completion
- `offer.generated` - New offer created
- `offer.approval_required` - Offer requires approval
- `offer.approved` - Offer approved
- `offer.sent` - Offer sent to customer
- `offer.accepted` - Customer accepted offer
- `offer.rejected` - Customer rejected offer

### Webhook Payload Example

```json
{
  "event_type": "offer.generated",
  "event_id": "evt-uuid",
  "timestamp": "2025-10-06T15:50:00Z",
  "data": {
    "offer_id": "off-uuid",
    "offer_number": "25-0042",
    "total_value": {
      "amount": "125000.00",
      "currency": "EUR"
    },
    "approval_required": true
  }
}
```

## SDK Examples

### Python

```python
import requests

API_BASE = "https://api.aigentics-corp.com/v1"
API_KEY = "your_api_key"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Start conversation
response = requests.post(
    f"{API_BASE}/conversations",
    headers=headers,
    json={
        "language": "de",
        "initial_message": "We need a custom CRM system"
    }
)
conversation = response.json()
conversation_id = conversation["conversation_id"]

# Send message
response = requests.post(
    f"{API_BASE}/conversations/{conversation_id}/messages",
    headers=headers,
    json={
        "content": "About 50 users",
        "answer_to_question_id": conversation["next_question"]["question_id"]
    }
)

# Generate offer (when complete)
response = requests.post(
    f"{API_BASE}/offers",
    headers=headers,
    json={
        "project_id": "proj-uuid",
        "conversation_id": conversation_id
    }
)
offer = response.json()
```

### TypeScript/Node.js

```typescript
import axios from 'axios';

const API_BASE = 'https://api.aigentics-corp.com/v1';
const API_KEY = 'your_api_key';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json'
  }
});

// Start conversation
const conversation = await client.post('/conversations', {
  language: 'de',
  initial_message: 'We need a custom CRM system'
});

const conversationId = conversation.data.conversation_id;

// Send message
const response = await client.post(
  `/conversations/${conversationId}/messages`,
  {
    content: 'About 50 users',
    answer_to_question_id: conversation.data.next_question.question_id
  }
);

// Generate offer
const offer = await client.post('/offers', {
  project_id: 'proj-uuid',
  conversation_id: conversationId
});
```

## Performance & SLA

| Endpoint | Target Response Time | Max Response Time |
|----------|---------------------|-------------------|
| POST /conversations | < 500ms | 2s |
| POST /conversations/{id}/messages | < 1s | 3s |
| POST /offers | < 20s | 30s |
| GET /offers/{id} | < 200ms | 1s |
| POST /offers/{id}/download | < 3s | 10s |

## Internationalization

Supported languages for conversations and offer generation:
- German (de)
- English (en)
- French (fr)
- Spanish (es)
- Italian (it)
- Dutch (nl)

Language is set per conversation and affects:
- AI-generated questions
- Offer document language
- Email notifications
- Terms and conditions

## Security

### HTTPS Only
All API requests must use HTTPS. HTTP requests are rejected.

### API Key Management
- Keys can be rotated via admin portal
- Separate keys for dev/staging/production
- Keys can be revoked immediately

### Data Encryption
- All PII encrypted at rest using AES-256
- TLS 1.3 for data in transit
- Keys managed via AWS KMS/HashiCorp Vault

### GDPR Compliance
- Right to access: GET /customers/{id}
- Right to erasure: DELETE /customers/{id}
- Data portability: GET /customers/{id}/export
- Consent management: tracked per customer

## Support

- **Documentation**: https://docs.aigentics-corp.com
- **Status Page**: https://status.aigentics-corp.com
- **Support Email**: api-support@aigentics-corp.com
- **Emergency Hotline**: +49 30 1234-5678 (24/7)

## Changelog

### Version 1.0.0 (2025-10-06)
- Initial release
- Conversation management
- AI-powered offer generation
- Approval workflows
- GDPR compliance
- Analytics dashboard
