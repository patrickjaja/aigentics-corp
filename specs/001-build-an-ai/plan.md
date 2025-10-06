
# Implementation Plan: AI Offer Agent for IT Consulting

**Branch**: `001-build-an-ai` | **Date**: 2025-09-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-build-an-ai/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARIFICATION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Fill the Constitution Check section based on the content of the constitution document.
4. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
5. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
6. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, `GEMINI.md` for Gemini CLI, `QWEN.md` for Qwen Code or `AGENTS.md` for opencode).
7. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
8. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
9. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Building an AI-powered offer generation system for IT consulting that engages customers through intelligent conversations, generates professional offers with accurate hour estimates using historical data and COCOMO models, and provides multi-language support for all EU languages. The system will use a microservices architecture with event-driven communication, implementing Domain-Driven Design with bounded contexts, CQRS with event sourcing for complete audit trail, and API Gateway pattern for external access.

## Technical Context
**Language/Version**: Python 3.12 (Backend), TypeScript/Node.js 20+ (Frontend)
**Primary Dependencies**: FastAPI, LangGraph, Next.js 14, shadcn/ui, PostgreSQL, Redis, Qdrant
**Storage**: PostgreSQL 16 with TimescaleDB for events, Redis for sessions, Qdrant for vector search
**Testing**: pytest (backend), Jest/Playwright (frontend), contract tests with Pact
**Target Platform**: Docker containers on Linux (Coolify/Hetzner deployment)
**Project Type**: web (frontend + backend microservices)
**Performance Goals**: <30s offer generation, 100 req/min API rate limit, <3s response time
**Constraints**: GDPR compliance, 10-year data retention, EUR 100k+ approval workflow
**Scale/Scope**: 1000 concurrent users, multi-language (all EU languages), A2A protocol support

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**I. GDPR Compliance & Data Privacy**
- [x] PII handling documented with legal basis (FR-005: explicit GDPR consent before download)
- [x] Encryption at rest/transit specified (FR-018: AES-256 for all customer PII)
- [x] Data retention and deletion policies defined (FR-013: 10 years, FR-021: 4 years for legal)
- [x] Right to erasure implementation planned (FR-021: GDPR-compliant deletion)

**II. German Business Standards**
- [x] DIN 5008 compliance for documents (FR-004: German business standards)
- [x] Proper date/currency formatting (DD.MM.YYYY, 1.234,56 €) (Constitution requirement)
- [x] Sie-Form in all communications (Constitution requirement)
- [x] Required legal footer elements included (FR-004: all required legal elements)

**III. Domain-Driven Design**
- [x] Bounded contexts identified (Architecture: microservices with bounded contexts)
- [x] Aggregates and value objects defined (Key Entities section defines aggregates)
- [x] Anti-corruption layers at boundaries (Architecture: API Gateway pattern)
- [x] Ubiquitous language documented (Entities match business terminology)

**IV. Event Sourcing**
- [x] Events defined for all state changes (Architecture: CQRS with event sourcing)
- [x] Event schema with required metadata (TimescaleDB for events)
- [x] CQRS read/write models separated (Architecture specification)
- [x] Audit trail retention (FR-013: 10 years exceeds 7-year requirement)

**V. Progressive Disclosure**
- [x] Max 5 decision points per interaction (FR-001: max 5 questions per round)
- [x] Essential info captured first (Primary User Story: basic info first)
- [x] Context-sensitive help planned (FR-016: coherent dialogue)
- [x] Save/resume capability designed (Edge case: 30-day save)

**VI. Test Coverage**
- [x] 100% coverage for business logic (Constitution requirement)
- [x] Test types defined (Testing: pytest, Jest/Playwright, Pact contracts)
- [x] CI/CD pipeline <5 min feedback (Constitution requirement)
- [x] Mutation testing planned (Constitution requirement)

**VII. A2A Protocol**
- [x] DIDs for agent identification (FR-009: A2A protocol standards)
- [x] DIDComm for secure messaging (A2A protocol implementation)
- [x] Verifiable credentials support (A2A protocol standards)
- [x] Protocol versioning strategy (FR-017: offer versioning)

**VIII. Circuit Breakers**
- [x] External service integrations identified (OpenAI GPT-4, DocuSign future)
- [x] Failure thresholds defined (Constitution: 5/60s)
- [x] Fallback strategies documented (Edge case: degraded functionality)
- [x] Timeout configurations (FR-011: 30s generation timeout)

**IX. LangGraph Orchestration**
- [x] Complex workflows use LangGraph (Tech stack: LangGraph orchestration)
- [x] Human checkpoints identified (FR-010: manager review for EUR 100k+)
- [x] State machines defined (Conversation entity: completion status)
- [x] Execution observability planned (LangGraph with PostgreSQL persistence)

**X. Bilingual Support**
- [x] i18n keys for all UI text (FR-006: full multi-language support)
- [x] German/English resource bundles (FR-006: German/English primary)
- [x] Accept-Language header handling (FR-006: all EU languages)
- [x] Translation consistency strategy (FR-006: all interactions/documents)

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository root)
```
# Option 1: Single project (DEFAULT)
src/
├── models/
├── services/
├── cli/
└── lib/

tests/
├── contract/
├── integration/
└── unit/

# Option 2: Web application (when "frontend" + "backend" detected)
backend/
├── src/
│   ├── models/
│   ├── services/
│   └── api/
└── tests/

frontend/
├── src/
│   ├── components/
│   ├── pages/
│   └── services/
└── tests/

# Option 3: Mobile + API (when "iOS/Android" detected)
api/
└── [same as backend above]

ios/ or android/
└── [platform-specific structure]
```

**Structure Decision**: Option 2 - Web application (frontend + backend microservices)

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1: Design & Contracts
*Prerequisites: research.md complete*

1. **Extract entities from feature spec** → `data-model.md`:
   - Entity name, fields, relationships
   - Validation rules from requirements
   - State transitions if applicable

2. **Generate API contracts** from functional requirements:
   - For each user action → endpoint
   - Use standard REST/GraphQL patterns
   - Output OpenAPI/GraphQL schema to `/contracts/`

3. **Generate contract tests** from contracts:
   - One test file per endpoint
   - Assert request/response schemas
   - Tests must fail (no implementation yet)

4. **Extract test scenarios** from user stories:
   - Each story → integration test scenario
   - Quickstart test = story validation steps

5. **Update agent file incrementally** (O(1) operation):
   - Run `.specify/scripts/bash/update-agent-context.sh claude`
     **IMPORTANT**: Execute it exactly as specified above. Do not add or remove any arguments.
   - If exists: Add only NEW tech from current plan
   - Preserve manual additions between markers
   - Update recent changes (keep last 3)
   - Keep under 150 lines for token efficiency
   - Output to repository root

**Output**: data-model.md, /contracts/*, failing tests, quickstart.md, agent-specific file

## Phase 2: Task Planning Approach
*This section describes what the /tasks command will do - DO NOT execute during /plan*

**Task Generation Strategy**:
- Load `.specify/templates/tasks-template.md` as base
- Generate tasks from Phase 1 design docs (contracts, data model, quickstart)
- Each contract endpoint → contract test task [P]
- Each domain entity → model + repository task [P]
- Each bounded context → service implementation task
- Each user scenario → E2E test task
- Infrastructure setup tasks for Docker, databases, caching

**Task Categories**:
1. **Infrastructure Setup** (Tasks 1-5)
   - Docker Compose configuration
   - Database schema and migrations
   - Redis and Qdrant setup
   - API Gateway configuration
   - Monitoring setup

2. **Domain Models** (Tasks 6-15) [P]
   - Customer entity and value objects
   - Conversation aggregate
   - Offer aggregate with work packages
   - Estimation models
   - Approval workflow
   - Event sourcing infrastructure

3. **Service Implementation** (Tasks 16-25)
   - Conversation service with LangGraph
   - Offer generation service
   - Customer service with GDPR
   - Estimation service with COCOMO
   - Notification service

4. **API Implementation** (Tasks 26-35) [P]
   - Conversation API endpoints
   - Offer API endpoints
   - Admin API endpoints
   - API Gateway routing
   - Rate limiting middleware

5. **Frontend Components** (Tasks 36-45) [P]
   - Conversation UI with shadcn/ui
   - Offer preview component
   - PDF download flow
   - Admin dashboard
   - Multi-language support

6. **Testing & Validation** (Tasks 46-55)
   - Contract tests for all APIs
   - Integration tests for services
   - E2E tests for user scenarios
   - Performance tests with Locust
   - GDPR compliance tests

**Ordering Strategy**:
- TDD approach: Tests before implementation
- Bottom-up: Infrastructure → Models → Services → APIs → UI
- Parallel tasks marked with [P] for independent work
- Critical path: Infrastructure must complete first

**Estimated Output**: 50-60 numbered, dependency-ordered tasks in tasks.md

**Task Format Example**:
```
1. Setup Docker Compose with PostgreSQL, Redis, Qdrant
2. [P] Create Customer domain model with GDPR support
3. [P] Create Conversation aggregate with state machine
4. [P] Create Offer aggregate with event sourcing
...
```

**IMPORTANT**: This phase is executed by the /tasks command, NOT by /plan

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)  
**Phase 4**: Implementation (execute tasks.md following constitutional principles)  
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (/plan command)
- [x] Phase 1: Design complete (/plan command)
- [x] Phase 2: Task planning complete (/plan command - describe approach only)
- [ ] Phase 3: Tasks generated (/tasks command)
- [ ] Phase 4: Implementation complete
- [ ] Phase 5: Validation passed

**Gate Status**:
- [x] Initial Constitution Check: PASS
- [x] Post-Design Constitution Check: PASS
- [x] All NEEDS CLARIFICATION resolved
- [x] Complexity deviations documented (none needed)

---
*Based on Constitution v1.0.0 - See `.specify/memory/constitution.md`*
