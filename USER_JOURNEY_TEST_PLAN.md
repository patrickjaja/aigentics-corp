# User Journey Test Plan - AI Offer Agent
**Task**: T101
**Date**: 2025-10-06
**Status**: Ready for Manual Testing

## Overview

This document outlines comprehensive manual testing scenarios for the AI Offer Agent system, covering all critical user journeys from initial conversation through offer download and admin approval workflows.

## Test Environment Setup

### Prerequisites Checklist
- [ ] All Docker services running (postgres, redis, qdrant, kong, keycloak)
- [ ] Backend microservices started
- [ ] Frontend application running on http://localhost:3000
- [ ] Admin account created in Keycloak
- [ ] Test API keys configured
- [ ] Database migrations applied
- [ ] Test data loaded

### Test Accounts

| Role | Username | Password | Purpose |
|------|----------|----------|---------|
| Customer | test@customer.com | test123 | Basic user flows |
| Sales Manager | sales@aigentics.com | manager123 | Approval workflows |
| Admin | admin@aigentics.com | admin123 | System administration |
| API Client | api-client-1 | [API Key] | A2A protocol testing |

## User Journey 1: Complete Conversation → Offer Generation

**Persona**: IT Manager at SME seeking software development
**Objective**: Complete conversation, receive offer, download PDF
**Duration**: 15-20 minutes
**Priority**: CRITICAL

### Test Steps

#### 1.1 Start Conversation
```
Action: Navigate to http://localhost:3000
Expected: Landing page with language selector and "Start Conversation" button

Action: Select language (German)
Expected: Interface switches to German, welcome message displayed

Action: Click "Gespräch beginnen" (Start Conversation)
Expected:
- Conversation ID generated
- First question displayed (max 5 questions)
- Chat interface active
```

**✅ Pass Criteria**:
- Page loads in < 2 seconds
- Language selection persists
- Conversation starts without errors
- UI elements properly localized

#### 1.2 Progressive Disclosure Conversation
```
Round 1 (Basic Information):
Q: "Was für ein Projekt planen Sie?"
A: "Wir brauchen eine neue E-Commerce-Plattform"

Expected:
- AI acknowledges answer
- Asks follow-up question
- Progress indicator shows 20% complete

Q: "Welche Features sind für Sie am wichtigsten?"
A: "Produktkatalog, Warenkorb, Zahlungsintegration, Kundenverwaltung"

Q: "Wie viele Nutzer erwarten Sie?"
A: "Ca. 10.000 monatlich"

Q: "Haben Sie technische Präferenzen?"
A: "React für Frontend, Node.js für Backend bevorzugt"

Q: "Was ist Ihr Budget-Rahmen?"
A: "50.000 - 80.000 Euro"
```

**✅ Pass Criteria**:
- Max 5 questions per round
- Each answer processed in < 3 seconds
- Conversation context maintained
- No duplicate questions
- Clear progress indication

#### 1.3 Requirement Gathering
```
Round 2 (Detailed Requirements):
AI Summary: "Ich verstehe, Sie benötigen eine E-Commerce-Plattform..."

Expected:
- Accurate summary of gathered requirements
- Option to correct misunderstandings
- Confidence indicators for unclear items

Action: Confirm requirements or provide corrections
Expected:
- Conversation completion percentage increases
- Option to generate offer appears when sufficient info gathered
```

**✅ Pass Criteria**:
- Requirements accurately captured
- Ability to edit/correct information
- Clear indication when ready for offer generation

#### 1.4 GDPR Consent
```
Action: Click "Angebot erstellen" (Create Offer)
Expected:
- GDPR consent form displayed
- Clear explanation of data usage
- Checkboxes for different consent purposes:
  ✓ Angebotserstellung (Offer generation)
  ✓ E-Mail-Kommunikation (Email communication)
  ☐ Marketing (optional)

Action: Fill in company details:
- Firma: Test GmbH
- Ansprechpartner: Max Mustermann
- E-Mail: max.mustermann@test-gmbh.de
- Telefon: +49 30 12345678

Action: Accept required consent, submit
```

**✅ Pass Criteria**:
- Consent form complies with GDPR
- Cannot proceed without required consent
- Data validation works (email format, phone format)
- Consent timestamp recorded

#### 1.5 Offer Generation
```
Action: Submit offer generation request
Expected:
- Loading indicator with estimated time (< 30s)
- Progress updates:
  - "Anforderungen werden analysiert..."
  - "Arbeitspakete werden erstellt..."
  - "Stunden werden geschätzt (COCOMO)..."
  - "PDF wird generiert..."

Results after < 30 seconds:
- Offer preview displayed
- Offer number generated (format: YY-NNNN)
- Work packages listed with:
  - Description
  - Deliverables
  - Estimated hours
  - Cost in EUR
- Total project cost
- Validity period (30 days from today)
```

**✅ Pass Criteria**:
- Generation completes in < 30 seconds
- Offer number unique and correctly formatted
- All work packages include deliverables
- Total cost calculated correctly
- German number formatting (1.234,56 €)

#### 1.6 Offer Review & Download
```
Action: Review offer in preview mode
Expected:
- All sections visible:
  - Company details
  - Project description
  - Work packages with detailed breakdown
  - Terms and conditions
  - Valid until date
  - Signature section

Action: Click "PDF herunterladen" (Download PDF)
Expected:
- PDF generated in < 5 seconds
- DIN 5008 compliant formatting:
  - Correct address placement
  - Proper date format (DD.MM.YYYY)
  - German currency format (EUR)
  - Professional layout
  - Company branding (if configured)

Action: Open PDF
```

**✅ Pass Criteria**:
- PDF downloads successfully
- File size reasonable (< 5MB)
- All content readable and formatted correctly
- No rendering issues
- Sie-Form used throughout

### Journey 1 Completion Checklist
- [ ] Conversation started and completed
- [ ] GDPR consent properly handled
- [ ] Offer generated in < 30 seconds
- [ ] PDF downloaded with DIN 5008 formatting
- [ ] All German text properly localized
- [ ] No errors or crashes

---

## User Journey 2: High-Value Offer Approval Workflow

**Persona**: Sales Manager creates offer requiring approval
**Objective**: Test EUR 100k+ approval workflow
**Duration**: 10-15 minutes
**Priority**: CRITICAL

### Test Steps

#### 2.1 Generate High-Value Offer
```
Action: Complete conversation flow as in Journey 1
BUT: Answer budget question with "150.000 - 200.000 Euro"

Expected after offer generation:
- Warning displayed: "Dieses Angebot erfordert eine Genehmigung"
- Offer status: "PENDING_APPROVAL"
- Offer cannot be downloaded yet
- Notification sent to approver
```

**✅ Pass Criteria**:
- Approval workflow automatically triggered for > EUR 100,000
- User clearly informed about approval requirement
- Offer locked from download

#### 2.2 Approver Notification
```
Action: Check email of approval manager (sales@aigentics.com)
Expected:
- Email received with:
  - Offer number
  - Customer details
  - Project summary
  - Total value
  - Link to admin dashboard
```

**✅ Pass Criteria**:
- Email delivered within 1 minute
- All information accurate
- Link functional

#### 2.3 Admin Review
```
Action: Login to admin dashboard (http://localhost:3000/admin)
Credentials: sales@aigentics.com / manager123

Expected:
- Pending approvals list displayed
- Test offer visible with:
  - Offer number
  - Customer name
  - Total value
  - Request date
  - "Review" button

Action: Click "Review" on test offer
Expected:
- Full offer details displayed
- Work package breakdown
- Customer information
- Conversation transcript
- Approval actions:
  - Approve
  - Reject
  - Request Revision
- Comment field
```

**✅ Pass Criteria**:
- All pending approvals visible
- Offer details complete and accurate
- Action buttons functional

#### 2.4 Approval Decision
```
Scenario A: Approve
Action: Add comment "Approved - pricing is competitive"
Action: Click "Genehmigen" (Approve)

Expected:
- Offer status → "APPROVED"
- Customer notified via email
- Offer becomes downloadable
- Approval recorded in audit log with timestamp

Scenario B: Request Revision
Action: Add comment "Please reduce Frontend hours by 20"
Action: Click "Überarbeitung anfordern" (Request Revision)
Action: Modify work package hours

Expected:
- Offer status → "REVISION_REQUESTED"
- Sales rep notified
- Offer version incremented
- Change history tracked
```

**✅ Pass Criteria**:
- Approval decisions properly recorded
- Notifications sent correctly
- Offer status updated
- Audit trail complete

### Journey 2 Completion Checklist
- [ ] High-value offer triggers approval
- [ ] Notification sent to approver
- [ ] Admin can review details
- [ ] Approval/rejection works correctly
- [ ] Version control for revisions
- [ ] Audit trail maintained

---

## User Journey 3: Multi-Language Support

**Persona**: French customer seeking IT consulting
**Objective**: Test full multi-language capability
**Duration**: 10 minutes
**Priority**: HIGH

### Test Steps

#### 3.1 French Conversation
```
Action: Start new conversation
Action: Select language: Français

Expected:
- Interface switches to French
- First question in French
- Conversation flows naturally in French

Sample Interaction:
Q: "Quel type de projet planifiez-vous ?"
A: "Nous avons besoin d'une application mobile"

Q: "Quelles plateformes ciblez-vous ?"
A: "iOS et Android"
```

**✅ Pass Criteria**:
- All UI elements translated
- AI responses in selected language
- No language mixing
- Natural, professional French

#### 3.2 Offer in Multiple Languages
```
Action: Generate offer in French
Expected:
- Offer preview in French
- Work packages in French
- Terms and conditions in French

Action: Switch language to English
Expected:
- Same offer content, translated to English
- All numbers/dates formatted per locale
  - French: 1 234,56 €
  - English: €1,234.56
```

**✅ Pass Criteria**:
- Translations accurate and professional
- Locale-specific formatting correct
- Content consistency across languages

### Journey 3 Completion Checklist
- [ ] UI translation complete
- [ ] AI conversations in target language
- [ ] Offer generation in multiple languages
- [ ] Locale-specific formatting correct
- [ ] Language switching works seamlessly

---

## User Journey 4: GDPR Data Rights

**Persona**: Customer exercising GDPR rights
**Objective**: Test data deletion and access requests
**Duration**: 15 minutes
**Priority**: CRITICAL (Legal compliance)

### Test Steps

#### 4.1 Data Access Request
```
Action: Login with customer account
Action: Navigate to "Meine Daten" (My Data)

Expected:
- All stored personal data displayed:
  - Company details
  - Contact information
  - Conversation history
  - Generated offers
  - Consent history
- Download data option (machine-readable format)

Action: Click "Daten herunterladen" (Download Data)
Expected:
- JSON file with all customer data
- File encrypted or password-protected
- Downloaded in < 5 seconds
```

**✅ Pass Criteria**:
- All PII visible to customer
- Data export comprehensive
- Export format machine-readable (JSON)
- Secure download

#### 4.2 Data Deletion Request
```
Action: Click "Konto löschen" (Delete Account)
Expected:
- Warning about consequences
- Confirmation required
- Legal retention notice (4 years for legal data, offer documents retained 10 years)

Action: Confirm deletion
Expected:
- Account marked for deletion
- PII immediately pseudonymized
- Deletion date recorded (4 years from request)
- Customer cannot login
- Offers anonymized but retained for legal purposes
```

**✅ Pass Criteria**:
- Clear deletion warning
- Immediate PII pseudonymization
- Legal data retained as required
- Deletion logged in audit trail

#### 4.3 Consent Withdrawal
```
Action: Before deletion, test consent withdrawal
Action: Navigate to consent management
Action: Withdraw marketing consent

Expected:
- Consent status updated
- No more marketing emails
- Offer generation consent cannot be withdrawn (active offers)
- Withdrawal timestamp recorded
```

**✅ Pass Criteria**:
- Granular consent management
- Withdrawals immediately effective
- Cannot withdraw required consents
- Audit trail complete

### Journey 4 Completion Checklist
- [ ] Data access request works
- [ ] Data export complete and secure
- [ ] Deletion request properly handled
- [ ] PII pseudonymization works
- [ ] Legal retention periods enforced
- [ ] Consent management functional

---

## User Journey 5: API Integration (A2A Protocol)

**Persona**: External AI agent integrating via API
**Objective**: Test agent-to-agent communication
**Duration**: 10 minutes
**Priority**: HIGH

### Test Steps

#### 5.1 API Authentication
```bash
# Test API key authentication
curl -X POST http://localhost:8000/v1/conversations \
  -H "X-API-Key: test_api_key_123" \
  -H "Content-Type: application/json" \
  -d '{
    "language": "en",
    "client_metadata": {
      "agent_name": "TestAgent",
      "version": "1.0"
    }
  }'

Expected:
- HTTP 200 OK
- Conversation ID returned
- DID (Decentralized Identifier) assigned
```

**✅ Pass Criteria**:
- API key authentication works
- DID properly generated
- Response includes conversation context

#### 5.2 Rate Limiting
```bash
# Test rate limiting (100 req/min)
for i in {1..105}; do
  curl -X GET http://localhost:8000/v1/offers \
    -H "X-API-Key: test_api_key_123"
done

Expected:
- First 100 requests: HTTP 200 OK
- Requests 101-105: HTTP 429 Too Many Requests
- Response headers:
  X-RateLimit-Limit: 100
  X-RateLimit-Remaining: 0
  X-RateLimit-Reset: <timestamp>
```

**✅ Pass Criteria**:
- Rate limiting enforced correctly
- Proper HTTP status codes
- Rate limit headers included

#### 5.3 DIDComm Messaging
```json
// Test secure agent messaging
POST /v1/conversations/{id}/messages
{
  "from": "did:key:test-agent",
  "to": "did:key:offer-agent",
  "type": "https://didcomm.org/question/1.0/ask",
  "body": {
    "question": "What is your pricing model?",
    "context": "enterprise_licensing"
  }
}

Expected:
- Message validated
- Response in DIDComm format
- Verifiable credentials included
```

**✅ Pass Criteria**:
- DIDComm protocol supported
- Messages properly signed
- Verifiable credentials work

### Journey 5 Completion Checklist
- [ ] API key authentication functional
- [ ] Rate limiting works correctly
- [ ] DIDComm messaging supported
- [ ] Verifiable credentials validated
- [ ] API documentation accurate

---

## User Journey 6: Error Handling & Edge Cases

**Persona**: User encountering various error scenarios
**Objective**: Validate graceful error handling
**Duration**: 15 minutes
**Priority**: HIGH

### Test Scenarios

#### 6.1 Conversation Timeout
```
Action: Start conversation
Action: Wait 35 minutes without interaction

Expected:
- Warning at 25 minutes: "Ihre Sitzung läuft bald ab"
- Timeout at 30 minutes
- Conversation saved (can resume)
- Data not lost
```

**✅ Pass Criteria**:
- Session timeout warnings clear
- Data persisted correctly
- Resume option available

#### 6.2 Invalid Input
```
Action: Enter malformed data:
- Email: "not-an-email"
- Phone: "abcd1234"
- Budget: "negative amount"

Expected:
- Real-time validation errors
- Clear error messages
- Field highlighting
- Cannot submit invalid data
```

**✅ Pass Criteria**:
- All validation works
- Error messages helpful
- No server errors from client validation

#### 6.3 OpenAI API Failure
```
Simulation: Stop OpenAI API or use invalid key

Action: Try to continue conversation

Expected:
- Circuit breaker activates
- Fallback to GPT-3.5 (if configured)
- Or: Graceful error message
- "Service temporarily unavailable. Please try again in 30 seconds."
- Conversation state preserved
```

**✅ Pass Criteria**:
- Circuit breaker works
- Fallback mechanism functional
- No data loss
- Clear user communication

#### 6.4 Database Connection Loss
```
Simulation: Stop PostgreSQL container

Action: Try to generate offer

Expected:
- HTTP 503 Service Unavailable
- Error logged
- User-friendly message (no stack trace)
- Automatic retry after database recovery
```

**✅ Pass Criteria**:
- Graceful degradation
- No sensitive info leaked
- Service recovers automatically

#### 6.5 Extremely Large Request
```
Action: Provide extremely detailed requirements (5000+ words)

Expected:
- Request accepted up to limit
- Validation on size limit
- "Please summarize your requirements" if too large
- Or: Ability to handle large inputs efficiently
```

**✅ Pass Criteria**:
- Input limits enforced
- Large inputs handled gracefully
- Performance not degraded

### Journey 6 Completion Checklist
- [ ] Timeout handling works
- [ ] Input validation comprehensive
- [ ] Circuit breakers functional
- [ ] Database failures handled
- [ ] Large requests managed
- [ ] Error messages user-friendly

---

## Cross-Functional Test Cases

### CFT-1: Performance Under Load
```
Action: Run 10 concurrent conversations
Expected:
- All conversations complete successfully
- Response times < 3s per interaction
- No resource exhaustion
- Database connections managed
```

### CFT-2: Security Headers
```
Action: Inspect HTTP response headers
Expected headers:
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Strict-Transport-Security: max-age=31536000
- X-XSS-Protection: 1; mode=block
- Referrer-Policy: strict-origin-when-cross-origin
```

### CFT-3: Accessibility
```
Action: Test with screen reader
Action: Test keyboard-only navigation
Action: Check color contrast ratios

Expected:
- WCAG 2.1 AA compliance
- Keyboard navigation works
- Screen reader friendly
- Sufficient contrast (4.5:1)
```

### CFT-4: Mobile Responsiveness
```
Action: Test on mobile devices (iOS, Android)
Expected:
- Responsive design works
- Touch interactions smooth
- Text readable without zooming
- Forms usable on small screens
```

---

## Test Execution Tracking

### Test Session Template

```markdown
**Test Date**: YYYY-MM-DD
**Tester**: [Name]
**Environment**: [Development/Staging/Production]
**Browser**: [Chrome/Firefox/Safari]

| Journey | Status | Issues Found | Notes |
|---------|--------|--------------|-------|
| Journey 1 | ✅/⚠️/❌ | [List] | [Notes] |
| Journey 2 | ✅/⚠️/❌ | [List] | [Notes] |
| Journey 3 | ✅/⚠️/❌ | [List] | [Notes] |
| Journey 4 | ✅/⚠️/❌ | [List] | [Notes] |
| Journey 5 | ✅/⚠️/❌ | [List] | [Notes] |
| Journey 6 | ✅/⚠️/❌ | [List] | [Notes] |

**Overall Assessment**: [PASS / FAIL / CONDITIONAL PASS]
**Production Ready**: [YES / NO]
```

---

## Issue Tracking Template

```markdown
**Issue ID**: UAT-XXX
**Journey**: [Journey Number]
**Severity**: [Critical/High/Medium/Low]
**Description**: [Clear description]
**Steps to Reproduce**:
1. [Step 1]
2. [Step 2]
3. [Step 3]

**Expected**: [What should happen]
**Actual**: [What actually happened]
**Screenshots**: [If applicable]
**Browser/Device**: [Details]
**Assigned To**: [Developer]
**Status**: [Open/In Progress/Fixed/Closed]
```

---

## Sign-Off Criteria

### Must Pass (Blocking)
- [ ] Journey 1: Complete offer generation works end-to-end
- [ ] Journey 2: Approval workflow functions correctly
- [ ] Journey 4: GDPR compliance fully functional
- [ ] No critical bugs
- [ ] No data loss scenarios
- [ ] All security measures operational

### Should Pass (Non-Blocking but important)
- [ ] Journey 3: Multi-language support complete
- [ ] Journey 5: A2A protocol functional
- [ ] Journey 6: Error handling comprehensive
- [ ] Performance acceptable
- [ ] Accessibility standards met

### Final Sign-Off

```
I hereby certify that manual testing has been completed for the AI Offer Agent system.

Testing Results:
- Total Test Cases: XX
- Passed: XX
- Failed: XX
- Blocked: XX

Critical Issues: [None / List]
Production Readiness: [YES / NO]

Signed: ___________________
Date: ___________________
Role: ___________________
```

---

**Test Plan Status**: Ready for Execution
**Last Updated**: 2025-10-06
**Document Version**: 1.0

*User Journey Test Plan - Task T101*
