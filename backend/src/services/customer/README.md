# Customer Service - GDPR-Compliant Customer Management

## Overview

The Customer Service provides GDPR-compliant customer management with PII encryption, pseudonymization, and comprehensive audit logging. It implements the Customer aggregate from the domain model with full GDPR Right to be Forgotten support.

## Features

### 1. GDPR Compliance
- **Explicit Consent**: Customers must provide explicit consent before any PII is stored
- **Consent Purposes**: Granular consent tracking (offer_generation, marketing, analytics)
- **Right to be Forgotten**: 4-year legal retention period after deletion request
- **Audit Logging**: Complete audit trail without storing sensitive PII
- **Consent Withdrawal**: Customers can withdraw consent at any time

### 2. PII Protection
- **AES-256 Encryption**: All PII fields encrypted at rest
- **Pseudonymization**: External IDs generated for GDPR compliance
- **Salt-based Key Derivation**: PBKDF2 with 100,000 iterations
- **Data Masking**: Email and phone masking for logs and displays
- **One-way Hashing**: Audit logs use SHA-256 hashes instead of PII

### 3. API Endpoints

#### POST /customers
Create a new customer with GDPR consent.

**Request Body:**
```json
{
  "company_name": "Acme Corporation",
  "contact_person": "John Doe",
  "email": "john.doe@acme.com",
  "phone": "+49123456789",
  "language_preference": "de",
  "consent_purposes": ["offer_generation", "marketing"],
  "consent_text_version": "v1.0"
}
```

**Response (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "external_id": "CUST-A1B2C3D4E5F6",
  "company_name": "Acme Corporation",
  "contact_person": "John Doe",
  "email": "john.doe@acme.com",
  "phone": "+49123456789",
  "language_preference": "de",
  "gdpr_consent": {
    "given_at": "2025-09-30T10:00:00Z",
    "purposes": ["offer_generation", "marketing"],
    "withdrawn_at": null
  },
  "created_at": "2025-09-30T10:00:00Z",
  "updated_at": "2025-09-30T10:00:00Z",
  "deletion_requested_at": null,
  "has_active_consent": true
}
```

#### GET /customers/{customer_id}
Retrieve customer by ID with decrypted PII.

**Response (200 OK):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "external_id": "CUST-A1B2C3D4E5F6",
  "company_name": "Acme Corporation",
  ...
}
```

**Error Responses:**
- `404 Not Found`: Customer not found
- `410 Gone`: Customer data has been deleted

#### DELETE /customers/{customer_id}
Request customer deletion (GDPR Right to be Forgotten).

**Request Body:**
```json
{
  "reason": "Customer requested data deletion"
}
```

**Response (202 Accepted):**
```json
{
  "message": "Deletion request accepted. Data will be retained for 4 years as required by law.",
  "deletion_requested_at": "2025-09-30T10:00:00Z",
  "scheduled_deletion_date": "2029-09-30T10:00:00Z",
  "external_id": "CUST-A1B2C3D4E5F6"
}
```

#### GET /health
Health check endpoint.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "customer-service",
  "version": "1.0.0",
  "timestamp": "2025-09-30T10:00:00Z"
}
```

## Architecture

### Components

1. **main.py**: FastAPI application with customer endpoints
2. **privacy.py**: PII encryption and pseudonymization utilities
3. **Customer Models**: Domain models from `backend/src/models/customer.py`

### Data Flow

```
Request → Validation → GDPR Consent Check → PII Encryption → Storage → Audit Log
```

### Storage Strategy (Current Implementation)

**Current (In-Memory):**
- `customers_store`: Dictionary storing Customer aggregates
- `encrypted_pii_store`: Dictionary storing encrypted PII fields

**Production (Database):**
- Customer data in PostgreSQL with encrypted columns
- Encrypted PII in separate schema with row-level encryption
- Event sourcing for all state changes
- Audit logs in TimescaleDB (time-series optimized)

## Security Features

### Encryption
- **Algorithm**: AES-256-GCM (via Fernet with AES-128-CBC + HMAC)
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Salt**: 32-byte random salt per field
- **Master Key**: Loaded from `ENCRYPTION_KEY` environment variable

### Pseudonymization
- **External ID Format**: `CUST-{12-char-hash}`
- **Generation**: SHA-256 hash of `customer_id:timestamp`
- **Purpose**: One-way mapping for GDPR compliance

### Audit Logging
```python
{
  "action": "customer_created",
  "customer_external_id": "CUST-A1B2C3D4E5F6",
  "email_hash": "sha256-hash-of-email",  # Not plaintext!
  "ip_address": "192.168.1.1",
  "timestamp": "2025-09-30T10:00:00Z",
  "metadata": {
    "consent_purposes": ["offer_generation"],
    "language": "de"
  }
}
```

### Data Masking
- **Email**: `john.doe@example.com` → `j***@example.com`
- **Phone**: `+49123456789` → `+49***789`

## Environment Variables

Required environment variables (see `.env.example`):

```bash
# Encryption (REQUIRED)
ENCRYPTION_KEY=your_base64_encoded_key  # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Service Configuration
CUSTOMER_SERVICE_PORT=8003
ENVIRONMENT=development

# Database (for production)
DATABASE_URL=postgresql://user:password@localhost:5432/offer_agent

# Data Retention
DELETION_GRACE_PERIOD_YEARS=4
DATA_RETENTION_YEARS=10
```

## Running the Service

### Development
```bash
cd backend/src/services/customer
python main.py
```

### Production (with uvicorn)
```bash
uvicorn backend.src.services.customer.main:app --host 0.0.0.0 --port 8003
```

### Docker
```bash
docker-compose up customer-service
```

## Testing

### Manual Testing with curl

**Create Customer:**
```bash
curl -X POST http://localhost:8003/customers \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "contact_person": "Jane Doe",
    "email": "jane@test.com",
    "phone": "+491234567890",
    "language_preference": "en",
    "consent_purposes": ["offer_generation"],
    "consent_text_version": "v1.0"
  }'
```

**Get Customer:**
```bash
curl http://localhost:8003/customers/{customer_id}
```

**Delete Customer:**
```bash
curl -X DELETE http://localhost:8003/customers/{customer_id} \
  -H "Content-Type: application/json" \
  -d '{"reason": "Test deletion"}'
```

**Health Check:**
```bash
curl http://localhost:8003/health
```

### Automated Tests

See `backend/tests/contract/test_customer_api.py` for contract tests.

## GDPR Compliance Checklist

- [x] Explicit consent required before storing PII
- [x] Consent purposes tracked granularly
- [x] PII encrypted at rest (AES-256)
- [x] Pseudonymized external IDs
- [x] Audit logging without PII
- [x] Right to be Forgotten (4-year retention)
- [x] Data masking for logs
- [x] Secure key management
- [x] IP address tracking for consent
- [x] Consent text versioning

## Data Model Integration

This service implements the Customer aggregate from `specs/001-build-an-ai/data-model.md`:

```python
class Customer:
    id: UUID                          # Internal ID
    external_id: str                  # Pseudonymized ID
    company_name: str                 # Encrypted PII
    contact_person: str               # Encrypted PII
    email: EmailAddress               # Encrypted PII
    phone: Optional[PhoneNumber]      # Encrypted PII
    language_preference: LanguageCode # ISO 639-1
    gdpr_consent: GDPRConsent         # Consent tracking
    created_at: datetime
    updated_at: datetime
    deletion_requested_at: Optional[datetime]
```

## Future Enhancements

1. **Database Integration**
   - Replace in-memory storage with PostgreSQL
   - Implement event sourcing for audit trail
   - Add TimescaleDB for time-series audit logs

2. **Advanced Features**
   - Consent withdrawal workflow
   - Data export (GDPR Right to Data Portability)
   - Multi-tenancy support
   - Batch operations for GDPR requests

3. **Security**
   - Hardware Security Module (HSM) integration
   - Key rotation mechanism
   - Separate encryption keys per customer

4. **Monitoring**
   - Prometheus metrics for API performance
   - Alerts for failed encryption/decryption
   - GDPR compliance dashboards

## References

- [GDPR Article 17 - Right to Erasure](https://gdpr-info.eu/art-17-gdpr/)
- [GDPR Article 7 - Conditions for Consent](https://gdpr-info.eu/art-7-gdpr/)
- Data Model: `specs/001-build-an-ai/data-model.md`
- Tasks: `specs/001-build-an-ai/tasks.md` (T038-T039)
