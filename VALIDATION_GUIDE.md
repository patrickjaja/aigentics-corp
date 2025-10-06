# Final Validation Guide (T098-T101)

**Purpose**: Execute final validation tasks to ensure all E2E tests pass and the system meets all requirements.

---

## Prerequisites

### 1. Environment Setup

Create `.env` file from template:

```bash
cp .env.example .env
```

Required environment variables:
```bash
# OpenAI Configuration
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=offer_agent
POSTGRES_USER=offer_agent
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Encryption (for PII)
ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### 2. Start Infrastructure Services

```bash
# Start all services
docker-compose up -d postgres redis qdrant

# Wait for services to be ready
sleep 10

# Check status
docker-compose ps
```

### 3. Run Database Migrations

```bash
cd backend
source venv/bin/activate
python -m alembic upgrade head
```

### 4. Start Backend Services

In separate terminals:

```bash
# Terminal 1: Main FastAPI app
cd backend
python -m src.main  # Port 8000

# Terminal 2: Conversation Service
python -m src.services.conversation.main  # Port 8001

# Terminal 3: Offer Service
python -m src.services.offer.main  # Port 8002

# Terminal 4: Customer Service
python -m src.services.customer.main  # Port 8003

# Terminal 5: Estimation Service
python -m src.services.estimation.main  # Port 8004

# Terminal 6: Notification Service
python -m src.services.notification.main  # Port 8005
```

### 5. Start Frontend

```bash
cd frontend
npm install
npm run dev  # Port 3000
```

---

## T098: Run All Validation Scenarios (4h)

Execute all 5 scenarios from `specs/001-build-an-ai/quickstart.md`:

### Scenario 1: Basic Offer Generation

```bash
# 1. Create conversation
CONV_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"language": "en"}')

CONV_ID=$(echo $CONV_RESPONSE | jq -r '.conversation_id')
echo "Conversation ID: $CONV_ID"

# 2. Send project requirements
curl -X POST http://localhost:8000/v1/conversations/$CONV_ID/messages \
  -H "Content-Type: application/json" \
  -d '{
    "message": "We need a new e-commerce platform with React frontend and Node.js backend. We expect around 10,000 users. Budget is around 50,000 EUR. Timeline is 6 months."
  }'

# 3. Answer a few more questions (repeat 2-3 times)

# 4. Complete conversation
curl -X POST http://localhost:8000/v1/conversations/$CONV_ID/complete

# 5. Generate offer
OFFER_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/offers \
  -H "Content-Type: application/json" \
  -d "{
    \"project_id\": \"$PROJECT_ID\",
    \"conversation_id\": \"$CONV_ID\",
    \"customer_id\": \"$CUSTOMER_ID\"
  }")

OFFER_ID=$(echo $OFFER_RESPONSE | jq -r '.offer_id')
echo "Offer ID: $OFFER_ID"

# Expected: Offer generated within 30 seconds ✅
```

### Scenario 2: High-Value Offer Approval

```bash
# Create high-value project (>EUR 100k)
# Use frontend to enter large enterprise project requirements

# Check approval workflow created
curl -X GET http://localhost:8000/v1/admin/approvals/pending \
  -H "Authorization: Bearer $ADMIN_TOKEN" | jq

# Expected: Approval request in pending list ✅
```

### Scenario 3: Multi-Language Support

```bash
# Start German conversation
CONV_DE=$(curl -s -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"language": "de"}')

CONV_DE_ID=$(echo $CONV_DE | jq -r '.conversation_id')

# Expected: Questions in German ✅

# Generate offer preview in German
curl -X GET "http://localhost:8000/v1/offers/$OFFER_ID/preview?language=de"

# Expected: German formatted offer with DIN 5008 compliance ✅
```

### Scenario 4: GDPR Compliance

```bash
# Create customer with consent
CUSTOMER_RESPONSE=$(curl -s -X POST http://localhost:8000/v1/customers \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test GmbH",
    "contact_person": "Max Mustermann",
    "email": "max@test.de",
    "phone": "+4930123456",
    "language_preference": "de",
    "consent_purposes": ["offer_generation"],
    "consent_text_version": "v1.0"
  }')

CUSTOMER_ID=$(echo $CUSTOMER_RESPONSE | jq -r '.customer_id')

# Download offer (requires consent)
curl -X POST http://localhost:8000/v1/offers/$OFFER_ID/download \
  -H "Content-Type: application/json" \
  -d "{
    \"customer_data\": {
      \"company_name\": \"Test GmbH\",
      \"contact_person\": \"Max Mustermann\",
      \"email\": \"max@test.de\",
      \"gdpr_consent\": {
        \"given\": true,
        \"purposes\": [\"offer_generation\"],
        \"consent_text_version\": \"v1.0\"
      }
    }
  }" --output offer.pdf

# Expected: PDF download with proper formatting ✅

# Test GDPR deletion
curl -X DELETE http://localhost:8000/v1/customers/$CUSTOMER_ID \
  -H "Content-Type: application/json" \
  -d '{"reason": "Customer request"}'

# Expected: 4-year retention period set ✅
```

### Scenario 5: API Integration (A2A)

```bash
# External agent integration
curl -X POST http://localhost:8000/v1/conversations \
  -H "X-API-Key: test_api_key_123" \
  -H "Content-Type: application/json" \
  -d '{"language": "en"}'

# Test rate limiting (100 req/min)
for i in {1..101}; do
  curl -s -X GET http://localhost:8000/v1/offers \
    -H "X-API-Key: test_api_key_123" \
    -w "%{http_code}\n" -o /dev/null
done

# Expected: 429 Too Many Requests after 100th request ✅
```

### Validation Checklist

- [ ] Scenario 1: Basic offer generation completes successfully
- [ ] Scenario 2: High-value offers trigger approval workflow
- [ ] Scenario 3: Multi-language support works (DE/EN)
- [ ] Scenario 4: GDPR consent required before download
- [ ] Scenario 5: Rate limiting enforced at 100 req/min
- [ ] All scenarios complete without errors
- [ ] Response times within SLAs

---

## T099: Security Audit with OWASP Top 10 (4h)

### 1. Injection Attacks

**SQL Injection**:
```bash
# Test with malicious input
curl -X POST http://localhost:8000/v1/conversations \
  -H "Content-Type: application/json" \
  -d '{"language": "en OR 1=1 --"}'

# Expected: Input validated, no SQL injection ✅
```

**Command Injection**:
```bash
# Test file upload or system commands
curl -X POST http://localhost:8000/v1/offers \
  -H "Content-Type: application/json" \
  -d '{"project_id": "; rm -rf /"}'

# Expected: Input sanitized, no command execution ✅
```

### 2. Broken Authentication

```bash
# Test without API key
curl -X GET http://localhost:8000/v1/offers

# Expected: 401 Unauthorized ✅

# Test with invalid JWT
curl -X GET http://localhost:8000/v1/admin/approvals/pending \
  -H "Authorization: Bearer invalid_token"

# Expected: 401 Unauthorized ✅
```

### 3. Sensitive Data Exposure

```bash
# Check logs don't contain PII
grep -r "email\|phone\|password" backend/logs/

# Expected: No sensitive data in logs ✅

# Verify encryption
python backend/tests/manual_security_audit.py

# Expected: All PII encrypted at rest ✅
```

### 4. XML External Entities (XXE)

Not applicable (no XML parsing in API)

### 5. Broken Access Control

```bash
# Try to access admin endpoint without admin role
curl -X GET http://localhost:8000/v1/admin/approvals/pending \
  -H "X-API-Key: regular_user_key"

# Expected: 403 Forbidden ✅

# Try to access another customer's data
curl -X GET http://localhost:8000/v1/customers/other_customer_id \
  -H "X-API-Key: customer_a_key"

# Expected: 403 Forbidden ✅
```

### 6. Security Misconfiguration

```bash
# Check security headers
curl -I http://localhost:8000/

# Expected headers:
# - X-Content-Type-Options: nosniff ✅
# - X-Frame-Options: DENY ✅
# - X-XSS-Protection: 1; mode=block ✅
# - Strict-Transport-Security: max-age=31536000 ✅
# - Content-Security-Policy: default-src 'self' ✅
```

### 7. Cross-Site Scripting (XSS)

```bash
# Test with XSS payload
curl -X POST http://localhost:8000/v1/conversations/$CONV_ID/messages \
  -H "Content-Type: application/json" \
  -d '{"message": "<script>alert(\"XSS\")</script>"}'

# Expected: Input sanitized, script tags escaped ✅
```

### 8. Insecure Deserialization

All data validated with Pydantic - not applicable

### 9. Using Components with Known Vulnerabilities

```bash
# Check for vulnerable dependencies
cd backend
pip list --outdated
safety check

cd ../frontend
npm audit

# Expected: No critical vulnerabilities ✅
```

### 10. Insufficient Logging & Monitoring

```bash
# Verify all actions logged
curl -X POST http://localhost:8000/v1/offers \
  -H "Content-Type: application/json" \
  -d '{"project_id": "test"}'

# Check logs
tail -f backend/logs/app.log

# Expected: Request logged with correlation ID ✅
```

### Security Audit Checklist

- [ ] No SQL injection vulnerabilities
- [ ] No command injection vulnerabilities
- [ ] Authentication required for all protected endpoints
- [ ] PII properly encrypted and not in logs
- [ ] Access control enforced (RBAC)
- [ ] Security headers present
- [ ] XSS protection enabled
- [ ] No known vulnerable dependencies
- [ ] Comprehensive logging without sensitive data
- [ ] Rate limiting prevents brute force
- [ ] HTTPS enforced in production

---

## T100: Performance Validation (3h)

### 1. Offer Generation Time (<30s)

```bash
# Create test script
cat > test_offer_performance.sh <<'EOF'
#!/bin/bash
for i in {1..10}; do
  START=$(date +%s)

  # Create conversation, answer questions, generate offer
  CONV_ID=$(curl -s -X POST http://localhost:8000/v1/conversations \
    -H "Content-Type: application/json" \
    -d '{"language": "en"}' | jq -r '.conversation_id')

  # Send requirements
  curl -s -X POST http://localhost:8000/v1/conversations/$CONV_ID/messages \
    -H "Content-Type: application/json" \
    -d '{"message": "E-commerce platform, 10k users, 6 months"}' > /dev/null

  # Generate offer
  curl -s -X POST http://localhost:8000/v1/offers \
    -H "Content-Type: application/json" \
    -d "{\"conversation_id\": \"$CONV_ID\"}" > /dev/null

  END=$(date +%s)
  DURATION=$((END - START))
  echo "Test $i: ${DURATION}s"

  if [ $DURATION -gt 30 ]; then
    echo "❌ FAILED: Offer generation took ${DURATION}s (>30s)"
    exit 1
  fi
done
echo "✅ All tests passed: Offer generation <30s"
EOF

chmod +x test_offer_performance.sh
./test_offer_performance.sh
```

### 2. API Response Time (<3s p95)

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test each endpoint
ab -n 1000 -c 10 http://localhost:8000/health
ab -n 1000 -c 10 http://localhost:8000/v1/conversations

# Check p95 latency
# Expected: <3000ms for p95 ✅
```

### 3. Load Test (1000 Concurrent Users)

```bash
cd backend/tests/load

# Run load test
locust -f locustfile.py \
  --host=http://localhost:8000 \
  --users=1000 \
  --spawn-rate=100 \
  --run-time=5m \
  --html=load_test_report.html

# Check results
open load_test_report.html

# Expected:
# - 0% failure rate ✅
# - p95 response time <3s ✅
# - Throughput >100 req/s ✅
```

### 4. Database Performance

```bash
# Check slow queries
psql -U offer_agent -d offer_agent -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  WHERE mean_exec_time > 1000
  ORDER BY mean_exec_time DESC
  LIMIT 10;
"

# Expected: No queries >1s average ✅
```

### Performance Validation Checklist

- [ ] Offer generation <30s (10/10 tests pass)
- [ ] API response time <3s p95 (all endpoints)
- [ ] 1000 concurrent users supported
- [ ] No slow database queries (>1s)
- [ ] Circuit breakers functioning under load
- [ ] Rate limiting prevents overload
- [ ] No memory leaks during extended run

---

## T101: Manual Testing of Complete User Journey (4h)

### Complete User Journey Test

1. **Open Application**
   ```
   Navigate to: http://localhost:3000
   ```
   - [ ] Main page loads
   - [ ] Language selector shows 24 EU languages
   - [ ] Default language is German

2. **Start Conversation (German)**
   - [ ] Click "Neue Konversation starten"
   - [ ] AI asks initial questions in German
   - [ ] Maximum 5 questions visible
   - [ ] Progress bar shows 0%

3. **Answer Questions (3-5 rounds)**
   - [ ] Type project description
   - [ ] Submit answers
   - [ ] New questions appear
   - [ ] Progress bar increases
   - [ ] Completion percentage updates

4. **Generate Offer**
   - [ ] Conversation reaches 80%+ completion
   - [ ] "Angebot generieren" button enabled
   - [ ] Click to generate offer
   - [ ] Loading indicator shows
   - [ ] Offer generated within 30s

5. **Trigger Approval Workflow (>EUR 100k)**
   - [ ] Enter high-value project (>100,000 EUR)
   - [ ] Offer marked "Genehmigung erforderlich"
   - [ ] Approval workflow created
   - [ ] Notification sent to admin

6. **Review and Approve Offer (Admin)**
   - [ ] Login to admin panel
   - [ ] Navigate to approvals
   - [ ] See pending approval
   - [ ] View offer details
   - [ ] Add review comment
   - [ ] Approve offer
   - [ ] Status changes to "Genehmigt"

7. **Download PDF with GDPR Consent**
   - [ ] Click "PDF herunterladen"
   - [ ] GDPR consent form appears
   - [ ] Fill company name, contact person, email
   - [ ] Check required consents
   - [ ] Acknowledge privacy policy
   - [ ] Submit form
   - [ ] PDF downloads

8. **Verify PDF DIN 5008 Compliance**
   - [ ] Open downloaded PDF
   - [ ] Check margins (27mm top, 24.1mm left)
   - [ ] Check fold marks (87mm, 192mm)
   - [ ] Check address field position (45mm from top)
   - [ ] Check date format (DD.MM.YYYY)
   - [ ] Check currency format (1.234,56 €)
   - [ ] Check all legal footer elements present

9. **Test Multi-Language Switching**
   - [ ] Change language to English
   - [ ] UI updates to English
   - [ ] Start new conversation
   - [ ] Questions in English
   - [ ] Generate offer in English
   - [ ] Date format changes (YYYY-MM-DD)
   - [ ] Currency format changes (EUR 1,234.56)

10. **Test GDPR Deletion Request**
    - [ ] Navigate to customer profile
    - [ ] Click "Daten löschen"
    - [ ] Confirm deletion request
    - [ ] 4-year retention period set
    - [ ] Customer data pseudonymized
    - [ ] Audit log entry created

11. **Verify Event Sourcing Audit Trail**
    - [ ] Check event store in database
    - [ ] All actions recorded as events
    - [ ] Event metadata complete (correlation_id, actor_id)
    - [ ] Events immutable (append-only)
    - [ ] No PII in event payloads

### Manual Testing Checklist

- [ ] All 11 steps completed successfully
- [ ] No errors in browser console
- [ ] No errors in backend logs
- [ ] UI responsive on desktop
- [ ] UI responsive on mobile
- [ ] Accessibility: keyboard navigation works
- [ ] Accessibility: screen reader compatible
- [ ] All GDPR requirements met
- [ ] All performance targets met
- [ ] Complete audit trail captured

---

## Final Validation Summary

After completing T098-T101, verify:

### Functional Requirements
- [ ] All 5 quickstart scenarios pass
- [ ] Complete user journey works end-to-end
- [ ] All APIs functional
- [ ] Frontend fully integrated
- [ ] Multi-language support working

### Non-Functional Requirements
- [ ] Performance: <30s offer generation
- [ ] Performance: <3s API response (p95)
- [ ] Scalability: 1000 concurrent users
- [ ] Security: OWASP Top 10 audit clean
- [ ] GDPR: All compliance requirements met

### Quality Assurance
- [ ] Contract tests: 8/8 passing
- [ ] Integration tests: 6/6 passing
- [ ] Unit tests: >80% coverage
- [ ] Load tests: No failures
- [ ] Manual tests: All scenarios passing

---

## Success Criteria

✅ **All validation tasks complete (T098-T101)**
✅ **All E2E tests passing**
✅ **All performance targets met**
✅ **All security checks passed**
✅ **Complete user journey validated**

**Result**: System ready for production deployment 🚀

---

## Troubleshooting

### Services won't start
```bash
# Check ports in use
lsof -i :8000 :8001 :8002 :8003 :8004 :8005 :3000

# Kill conflicting processes
kill -9 $(lsof -t -i:8000)
```

### Database connection errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection
psql -h localhost -U offer_agent -d offer_agent

# Recreate database
docker-compose down -v
docker-compose up -d postgres
```

### Tests failing
```bash
# Clear cache and reinstall
cd backend
rm -rf __pycache__ .pytest_cache
pip install -r requirements.txt

cd ../frontend
rm -rf node_modules .next
npm install
```

---

**Ready to execute final validation!** 🎯
