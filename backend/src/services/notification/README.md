# Notification Service

Multi-language email and webhook notification service with retry logic and circuit breaker pattern.

## Features

- **Email Notifications**: SMTP-based email delivery with HTML templates
- **Webhook Notifications**: HTTP webhook delivery to external integrations
- **Multi-language Support**: German and English email templates
- **Retry Logic**: Exponential backoff retry mechanism
- **Circuit Breaker**: Prevents cascading failures for external services
- **Health Checks**: Service health monitoring endpoint

## Notification Types

### Email Events

1. **OFFER_CREATED**: Customer receives offer creation confirmation
2. **APPROVAL_REQUIRED**: Manager receives approval request for high-value offers (>EUR 100k)
3. **OFFER_APPROVED**: Sales team notified when offer is approved
4. **OFFER_REJECTED**: Sales team notified when offer is rejected
5. **OFFER_SENT**: Customer receives final offer delivery notification

### Webhook Events

All offer lifecycle events can be sent to external systems via webhooks for integration purposes.

## API Endpoints

### POST /notifications/email

Send an email notification.

**Request Body:**
```json
{
  "to_email": "customer@example.com",
  "notification_type": "offer_created",
  "language": "de",
  "context": {
    "offer_id": "123e4567-e89b-12d3-a456-426614174000",
    "offer_number": "25-0001",
    "customer_name": "Max Mustermann",
    "total_value": "75000.00",
    "currency": "EUR",
    "download_link": "https://app.example.com/offers/123e4567/download",
    "valid_until": "2025-11-05"
  }
}
```

**Response:**
```json
{
  "notification_id": "uuid",
  "status": "sent",
  "message": "Email sent successfully",
  "sent_at": "2025-10-06T12:00:00Z",
  "retry_count": 0
}
```

### POST /notifications/webhook

Send a webhook notification.

**Request Body:**
```json
{
  "webhook_url": "https://api.example.com/webhooks/offers",
  "notification_type": "offer_created",
  "payload": {
    "offer_id": "123e4567-e89b-12d3-a456-426614174000",
    "offer_number": "25-0001",
    "customer_id": "customer-uuid",
    "total_value": 75000.00,
    "currency": "EUR"
  },
  "headers": {
    "X-API-Key": "your-secret-key"
  }
}
```

**Response:**
```json
{
  "notification_id": "uuid",
  "status": "sent",
  "message": "Webhook delivered successfully (HTTP 200)",
  "sent_at": "2025-10-06T12:00:00Z",
  "retry_count": 0
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "notification",
  "smtp_status": "healthy",
  "circuit_breaker_status": "SMTP: closed, Webhook: closed",
  "timestamp": "2025-10-06T12:00:00Z"
}
```

## Configuration

Environment variables (see `.env.example`):

### SMTP Configuration
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port (default: 587)
- `SMTP_USER`: SMTP authentication username
- `SMTP_PASSWORD`: SMTP authentication password
- `SMTP_FROM_EMAIL`: Sender email address
- `SMTP_FROM_NAME`: Sender display name

### Circuit Breaker Settings
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD`: Failures before opening circuit (default: 5)
- `CIRCUIT_BREAKER_TIMEOUT_SECONDS`: Circuit open timeout (default: 60)
- `CIRCUIT_BREAKER_RECOVERY_SECONDS`: Recovery attempt delay (default: 30)

### Retry Settings
- `MAX_RETRY_ATTEMPTS`: Maximum retry attempts (default: 3)
- `RETRY_BASE_DELAY_SECONDS`: Base delay between retries (default: 2)
- `RETRY_MAX_DELAY_SECONDS`: Maximum retry delay (default: 60)

## Email Templates

Templates are located in `backend/templates/email/` and follow the naming pattern:
```
{notification_type}_{language}.html
```

Example:
- `offer_created_de.html` - German offer creation template
- `offer_created_en.html` - English offer creation template

### Template Variables

Templates use Jinja2 syntax and support the following context variables:

**Offer Created:**
- `customer_name`: Customer name
- `offer_number`: Offer number (e.g., "25-0001")
- `total_value`: Formatted total value
- `currency`: Currency code (e.g., "EUR")
- `download_link`: Link to download PDF
- `valid_until`: Offer validity date

**Approval Required:**
- `offer_number`: Offer number
- `customer_name`: Customer name
- `total_value`: Formatted total value
- `currency`: Currency code
- `approval_link`: Link to approval dashboard

**Offer Approved/Rejected:**
- `offer_number`: Offer number
- `approver_name`: Name of approver
- `approval_comments`: Optional comments
- `rejection_reason`: Reason for rejection (if rejected)

## Circuit Breaker Pattern

The service implements circuit breaker pattern for both SMTP and webhook deliveries:

1. **CLOSED**: Normal operation, all requests go through
2. **OPEN**: Threshold exceeded, requests fail immediately
3. **HALF_OPEN**: Recovery attempt, single request allowed

Circuit opens after 5 consecutive failures (configurable) and automatically attempts recovery after 30 seconds.

## Retry Logic

Failed notifications are automatically retried with exponential backoff:

- Attempt 1: Immediate
- Attempt 2: 2 seconds delay
- Attempt 3: 4 seconds delay
- Attempt 4: 8 seconds delay (max: 60 seconds)

Maximum retry attempts: 3 (configurable)

## Usage Example

### Python Integration

```python
from services.notification import NotificationService, NotificationSettings
from services.notification import NotificationType, NotificationLanguage

# Initialize service
settings = NotificationSettings()
notification_service = NotificationService(settings)

# Send email notification
response = await notification_service.send_email_notification(
    to_email="customer@example.com",
    notification_type=NotificationType.OFFER_CREATED,
    language=NotificationLanguage.GERMAN,
    context={
        "offer_number": "25-0001",
        "customer_name": "Max Mustermann",
        "total_value": "75.000,00",
        "currency": "EUR",
        "download_link": "https://app.example.com/offers/123/download",
        "valid_until": "05.11.2025"
    }
)

# Send webhook notification
webhook_response = await notification_service.send_webhook_notification(
    webhook_url="https://api.example.com/webhooks",
    notification_type=NotificationType.OFFER_CREATED,
    payload={"offer_id": "123", "status": "created"}
)
```

### cURL Examples

**Send Email:**
```bash
curl -X POST http://localhost:8005/notifications/email \
  -H "Content-Type: application/json" \
  -d '{
    "to_email": "customer@example.com",
    "notification_type": "offer_created",
    "language": "de",
    "context": {
      "offer_number": "25-0001",
      "customer_name": "Max Mustermann",
      "total_value": "75.000,00",
      "currency": "EUR",
      "download_link": "https://app.example.com/offers/123/download",
      "valid_until": "05.11.2025"
    }
  }'
```

**Send Webhook:**
```bash
curl -X POST http://localhost:8005/notifications/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://api.example.com/webhooks/offers",
    "notification_type": "offer_created",
    "payload": {
      "offer_id": "123",
      "status": "created"
    },
    "headers": {
      "X-API-Key": "secret"
    }
  }'
```

**Health Check:**
```bash
curl http://localhost:8005/health
```

## Running the Service

### Standalone

```bash
cd backend/src/services/notification
python -m main
```

Service will start on `http://0.0.0.0:8005`

### With Docker

```bash
docker-compose up notification-service
```

## Testing

Run unit tests:
```bash
pytest backend/tests/unit/test_notification_service.py -v
```

Run integration tests:
```bash
pytest backend/tests/integration/test_notification_integration.py -v
```

## Monitoring

The service exposes the following metrics for monitoring:

- Email delivery success/failure rates
- Webhook delivery success/failure rates
- Circuit breaker state changes
- Retry attempt counts
- Average delivery time

Monitor health at: `GET /health`

## Error Handling

The service handles the following error scenarios:

1. **SMTP Connection Failures**: Automatic retry with exponential backoff
2. **Template Rendering Errors**: Returns HTTP 500 with error details
3. **Webhook Timeout**: Configurable timeout with retry
4. **Circuit Breaker Open**: Returns failure immediately without attempting delivery
5. **Invalid Email Address**: Validation error returned

## Security Considerations

1. **Email Authentication**: SMTP credentials stored in environment variables
2. **Webhook Headers**: Support for custom authentication headers (API keys, tokens)
3. **TLS/SSL**: SMTP TLS enabled by default
4. **Input Validation**: Pydantic models validate all inputs
5. **Template Injection**: Jinja2 autoescape enabled

## License

Copyright 2025 AI Offer Agent. All rights reserved.
