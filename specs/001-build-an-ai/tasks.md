# Tasks: AI Offer Agent for IT Consulting

**Input**: Design documents from `/specs/001-build-an-ai/`
**Prerequisites**: plan.md (required), research.md, data-model.md, contracts/

## Execution Flow (main)
```
1. Load plan.md from feature directory
   → If not found: ERROR "No implementation plan found"
   → Extract: tech stack, libraries, structure
2. Load optional design documents:
   → data-model.md: Extract entities → model tasks
   → contracts/: Each file → contract test task
   → research.md: Extract decisions → setup tasks
3. Generate tasks by category:
   → Setup: project init, dependencies, linting
   → Tests: contract tests, integration tests
   → Core: models, services, CLI commands
   → Integration: DB, middleware, logging
   → Polish: unit tests, performance, docs
4. Apply task rules:
   → Different files = mark [P] for parallel
   → Same file = sequential (no [P])
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001, T002...)
6. Generate dependency graph
7. Create parallel execution examples
8. Validate task completeness:
   → All contracts have tests?
   → All entities have models?
   → All endpoints implemented?
9. Return: SUCCESS (tasks ready for execution)
```

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
- **Web app**: `backend/`, `frontend/` at repository root (per plan.md)
- Backend microservices in `backend/src/services/`
- Frontend components in `frontend/src/`

## Phase 3.1: Setup
- [ ] T001 Create project structure with backend/ and frontend/ directories per plan.md
- [ ] T002 Initialize Python 3.12 backend with FastAPI, LangGraph, pytest dependencies in backend/requirements.txt
- [ ] T003 Initialize Next.js 14 frontend with TypeScript and shadcn/ui in frontend/
- [ ] T004 [P] Configure Python linting (ruff, black) in backend/pyproject.toml
- [ ] T005 [P] Configure TypeScript linting (ESLint, Prettier) in frontend/.eslintrc
- [ ] T006 [P] Setup Docker Compose for PostgreSQL 16, Redis, Qdrant in docker-compose.yml
- [ ] T007 [P] Create .env.example with all configuration variables from quickstart.md
- [ ] T008 Setup Alembic for database migrations in backend/alembic/

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### Contract Tests
- [ ] T009 [P] Contract test POST /conversations in backend/tests/contract/test_conversation_api.py (4h)
- [ ] T010 [P] Contract test POST /conversations/{id}/messages in backend/tests/contract/test_conversation_messages_api.py (3h)
- [ ] T011 [P] Contract test POST /offers in backend/tests/contract/test_offer_generation_api.py (4h)
- [ ] T012 [P] Contract test GET /offers/{id} in backend/tests/contract/test_offer_retrieval_api.py (2h)
- [ ] T013 [P] Contract test POST /offers/{id}/download in backend/tests/contract/test_offer_download_api.py (3h)
- [ ] T014 [P] Contract test POST /customers in backend/tests/contract/test_customer_api.py (3h)
- [ ] T015 [P] Contract test GET /approvals/pending in backend/tests/contract/test_admin_approvals_api.py (3h)
- [ ] T016 [P] Contract test POST /approvals/{id}/review in backend/tests/contract/test_approval_workflow_api.py (4h)

### Integration Tests
- [ ] T017 [P] Integration test: Complete conversation flow in backend/tests/integration/test_conversation_flow.py (6h)
- [ ] T018 [P] Integration test: Offer generation <30s in backend/tests/integration/test_offer_performance.py (4h)
- [ ] T019 [P] Integration test: High-value approval workflow in backend/tests/integration/test_approval_workflow.py (5h)
- [ ] T020 [P] Integration test: GDPR consent and deletion in backend/tests/integration/test_gdpr_compliance.py (5h)
- [ ] T021 [P] Integration test: Multi-language support in backend/tests/integration/test_multilanguage.py (4h)
- [ ] T022 [P] Integration test: API rate limiting (100/min) in backend/tests/integration/test_rate_limiting.py (3h)

## Phase 3.3: Core Implementation (ONLY after tests are failing)

### Domain Models
- [ ] T023 [P] Customer aggregate with GDPR consent in backend/src/models/customer.py (4h)
- [ ] T024 [P] Project entity with requirements in backend/src/models/project.py (3h)
- [ ] T025 [P] Conversation aggregate with interactions in backend/src/models/conversation.py (5h)
- [ ] T026 [P] Offer aggregate with work packages in backend/src/models/offer.py (5h)
- [ ] T027 [P] WorkPackage entity with deliverables in backend/src/models/work_package.py (3h)
- [ ] T028 [P] ApprovalWorkflow aggregate in backend/src/models/approval.py (4h)
- [ ] T029 [P] EstimationModel with COCOMO params in backend/src/models/estimation.py (4h)
- [ ] T030 [P] APIClient entity with rate limits in backend/src/models/api_client.py (2h)
- [ ] T031 [P] Value objects (EmailAddress, PhoneNumber, Money) in backend/src/models/value_objects.py (3h)

### Microservices
- [ ] T032 Conversation Service with LangGraph orchestration in backend/src/services/conversation/main.py (8h)
- [ ] T033 Conversation context management in backend/src/services/conversation/context_manager.py (5h)
- [ ] T034 AI question generation (max 5/round) in backend/src/services/conversation/ai_questions.py (6h)
- [ ] T035 Offer Service with versioning in backend/src/services/offer/main.py (8h)
- [ ] T036 Work package generation in backend/src/services/offer/work_packages.py (5h)
- [ ] T037 PDF generation with ReportLab (DIN 5008) in backend/src/services/offer/pdf_generator.py (6h)
- [ ] T038 Customer Service with GDPR operations in backend/src/services/customer/main.py (6h)
- [ ] T039 PII encryption/pseudonymization in backend/src/services/customer/privacy.py (5h)
- [ ] T040 Estimation Service with COCOMO in backend/src/services/estimation/main.py (6h)
- [ ] T041 Historical data calibration in backend/src/services/estimation/calibration.py (4h)
- [ ] T042 Notification Service for emails/webhooks in backend/src/services/notification/main.py (5h)

### API Endpoints
- [ ] T043 POST /conversations endpoint in backend/src/api/conversations.py (3h)
- [ ] T044 POST /conversations/{id}/messages endpoint in backend/src/api/conversations.py (3h)
- [ ] T045 GET /conversations/{id} endpoint in backend/src/api/conversations.py (2h)
- [ ] T046 POST /offers endpoint in backend/src/api/offers.py (4h)
- [ ] T047 GET /offers/{id} endpoint in backend/src/api/offers.py (2h)
- [ ] T048 POST /offers/{id}/download endpoint in backend/src/api/offers.py (3h)
- [ ] T049 POST /customers endpoint in backend/src/api/customers.py (3h)
- [ ] T050 DELETE /customers/{id} (GDPR) endpoint in backend/src/api/customers.py (3h)
- [ ] T051 GET /approvals/pending endpoint in backend/src/api/admin.py (3h)
- [ ] T052 POST /approvals/{id}/review endpoint in backend/src/api/admin.py (4h)

### Frontend Components
- [ ] T053 [P] Conversation chat interface in frontend/src/components/conversation/ChatInterface.tsx (6h)
- [ ] T054 [P] Progressive disclosure questions in frontend/src/components/conversation/QuestionFlow.tsx (5h)
- [ ] T055 [P] Offer preview component in frontend/src/components/offer/OfferPreview.tsx (4h)
- [ ] T056 [P] GDPR consent form in frontend/src/components/customer/ConsentForm.tsx (3h)
- [ ] T057 [P] Language selector (EU languages) in frontend/src/components/common/LanguageSelector.tsx (2h)
- [ ] T058 [P] Admin approval dashboard in frontend/src/components/admin/ApprovalDashboard.tsx (5h)
- [ ] T059 [P] Work package editor in frontend/src/components/admin/WorkPackageEditor.tsx (4h)

### Frontend Pages
- [ ] T060 Main conversation page in frontend/src/app/page.tsx (3h)
- [ ] T061 Offer review page in frontend/src/app/offer/[id]/page.tsx (3h)
- [ ] T062 Admin dashboard page in frontend/src/app/admin/page.tsx (3h)
- [ ] T063 Approval details page in frontend/src/app/admin/approvals/[id]/page.tsx (4h)

## Phase 3.4: Integration

### Event Sourcing & Database
- [ ] T064 Event store schema with TimescaleDB in backend/src/infrastructure/events/schema.py (4h)
- [ ] T065 Event publisher/subscriber in backend/src/infrastructure/events/bus.py (5h)
- [ ] T066 CQRS projections for read models in backend/src/infrastructure/projections/handlers.py (6h)
- [ ] T067 Database repositories for aggregates in backend/src/infrastructure/repositories/ (6h)

### External Integrations
- [ ] T068 OpenAI GPT-4 integration with streaming in backend/src/integrations/openai_service.py (5h)
- [ ] T069 Circuit breaker for external services in backend/src/infrastructure/circuit_breaker.py (3h)
- [ ] T070 Qdrant vector search integration in backend/src/integrations/qdrant_service.py (4h)
- [ ] T071 Redis session management in backend/src/infrastructure/sessions.py (3h)

### API Gateway & Middleware
- [ ] T072 Kong Gateway setup with rate limiting in infrastructure/kong/kong.yml (4h)
- [ ] T073 API key authentication middleware in backend/src/middleware/auth.py (3h)
- [ ] T074 Request/response logging middleware in backend/src/middleware/logging.py (2h)
- [ ] T075 CORS and security headers in backend/src/middleware/security.py (2h)

### Internationalization
- [ ] T076 [P] i18next setup with EU languages in frontend/src/i18n/config.ts (3h)
- [ ] T077 [P] Translation resource bundles in frontend/src/i18n/locales/ (4h)
- [ ] T078 [P] Backend message translation service in backend/src/services/translation/main.py (4h)

## Phase 3.5: Polish

### Unit Tests
- [ ] T079 [P] Unit tests for value objects in backend/tests/unit/test_value_objects.py (2h)
- [ ] T080 [P] Unit tests for COCOMO calculations in backend/tests/unit/test_estimation.py (3h)
- [ ] T081 [P] Unit tests for PDF generation in backend/tests/unit/test_pdf_generator.py (3h)
- [ ] T082 [P] Unit tests for conversation context in backend/tests/unit/test_context_manager.py (3h)
- [ ] T083 [P] Frontend component tests in frontend/src/__tests__/components/ (4h)

### Performance & Monitoring
- [ ] T084 Load testing with Locust (1000 users) in backend/tests/load/locustfile.py (4h)
- [ ] T085 Database query optimization in backend/src/infrastructure/optimization.py (4h)
- [ ] T086 Prometheus metrics integration in backend/src/monitoring/metrics.py (3h)
- [ ] T087 Health check endpoints in backend/src/api/health.py (2h)

### Documentation
- [ ] T088 [P] API documentation with OpenAPI in backend/docs/api.md (3h)
- [ ] T089 [P] Deployment guide in docs/deployment.md (2h)
- [ ] T090 [P] Admin user guide in docs/admin-guide.md (2h)
- [ ] T091 [P] GDPR compliance documentation in docs/gdpr-compliance.md (3h)

### Analytics Implementation
- [ ] T092 [P] Analytics data model for metrics in backend/src/models/analytics.py (3h)
- [ ] T093 [P] Metrics collection service in backend/src/services/analytics/main.py (5h)
- [ ] T094 [P] Analytics API endpoints (GET /analytics/offers, /analytics/conversion) in backend/src/api/analytics.py (4h)
- [ ] T095 [P] Analytics dashboard component in frontend/src/components/analytics/Dashboard.tsx (6h)
- [ ] T096 [P] Conversion funnel visualization in frontend/src/components/analytics/ConversionFunnel.tsx (4h)
- [ ] T097 Analytics data aggregation jobs in backend/src/jobs/analytics_aggregator.py (4h)

### Final Validation
- [ ] T098 Run all validation scenarios from quickstart.md (4h)
- [ ] T099 Security audit with OWASP Top 10 checks (4h)
- [ ] T100 Performance validation (<30s generation, <3s API) (3h)
- [ ] T101 Manual testing of complete user journey (4h)

## Dependencies
- Setup (T001-T008) must complete first
- All tests (T009-T022) before any implementation (T023+)
- Domain models (T023-T031) before services (T032-T042)
- Services before API endpoints (T043-T052)
- Backend APIs before frontend components
- Core implementation before integration (T064-T078)
- Everything before polish phase (T079-T095)

## Parallel Execution Examples

### Test Phase (can run all together):
```bash
# Launch contract tests T009-T016 in parallel:
Task: "Contract test POST /conversations in backend/tests/contract/test_conversation_api.py"
Task: "Contract test POST /conversations/{id}/messages in backend/tests/contract/test_conversation_messages_api.py"
Task: "Contract test POST /offers in backend/tests/contract/test_offer_generation_api.py"
Task: "Contract test GET /offers/{id} in backend/tests/contract/test_offer_retrieval_api.py"
Task: "Contract test POST /offers/{id}/download in backend/tests/contract/test_offer_download_api.py"
Task: "Contract test POST /customers in backend/tests/contract/test_customer_api.py"
Task: "Contract test GET /approvals/pending in backend/tests/contract/test_admin_approvals_api.py"
Task: "Contract test POST /approvals/{id}/review in backend/tests/contract/test_approval_workflow_api.py"

# Launch integration tests T017-T022 in parallel:
Task: "Integration test: Complete conversation flow in backend/tests/integration/test_conversation_flow.py"
Task: "Integration test: Offer generation <30s in backend/tests/integration/test_offer_performance.py"
Task: "Integration test: High-value approval workflow in backend/tests/integration/test_approval_workflow.py"
Task: "Integration test: GDPR consent and deletion in backend/tests/integration/test_gdpr_compliance.py"
Task: "Integration test: Multi-language support in backend/tests/integration/test_multilanguage.py"
Task: "Integration test: API rate limiting (100/min) in backend/tests/integration/test_rate_limiting.py"
```

### Domain Models Phase (can run all together):
```bash
# Launch T023-T031 in parallel:
Task: "Customer aggregate with GDPR consent in backend/src/models/customer.py"
Task: "Project entity with requirements in backend/src/models/project.py"
Task: "Conversation aggregate with interactions in backend/src/models/conversation.py"
Task: "Offer aggregate with work packages in backend/src/models/offer.py"
Task: "WorkPackage entity with deliverables in backend/src/models/work_package.py"
Task: "ApprovalWorkflow aggregate in backend/src/models/approval.py"
Task: "EstimationModel with COCOMO params in backend/src/models/estimation.py"
Task: "APIClient entity with rate limits in backend/src/models/api_client.py"
Task: "Value objects (EmailAddress, PhoneNumber, Money) in backend/src/models/value_objects.py"
```

### Frontend Components Phase (can run all together):
```bash
# Launch T053-T059 in parallel:
Task: "Conversation chat interface in frontend/src/components/conversation/ChatInterface.tsx"
Task: "Progressive disclosure questions in frontend/src/components/conversation/QuestionFlow.tsx"
Task: "Offer preview component in frontend/src/components/offer/OfferPreview.tsx"
Task: "GDPR consent form in frontend/src/components/customer/ConsentForm.tsx"
Task: "Language selector (EU languages) in frontend/src/components/common/LanguageSelector.tsx"
Task: "Admin approval dashboard in frontend/src/components/admin/ApprovalDashboard.tsx"
Task: "Work package editor in frontend/src/components/admin/WorkPackageEditor.tsx"
```

## Notes
- [P] tasks = different files, no shared dependencies
- Verify all tests fail before implementing (TDD discipline)
- Commit after each completed task for rollback capability
- Use feature flags for gradual rollout
- Monitor performance metrics from day 1
- Ensure GDPR compliance in every data-handling task

## Estimated Total Time
- Setup: 20 hours
- Tests: 71 hours
- Core Implementation: 188 hours
- Integration: 54 hours
- Polish: 46 hours
- Analytics: 26 hours
- Validation: 14 hours
- **Total: 419 hours (~11 weeks for 1 developer, ~3.5 weeks for team of 3)**

---
*Generated: 2025-09-24*