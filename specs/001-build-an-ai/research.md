# Research: AI Offer Agent for IT Consulting

**Date**: 2025-09-24
**Feature**: AI Offer Agent
**Branch**: 001-build-an-ai

## Executive Summary

This research document consolidates technical decisions and architectural patterns for implementing the AI Offer Agent system. All previously unclear aspects from the specification have been resolved through analysis of best practices and the provided technical stack requirements.

## Critical Decisions for Implementation

### Admin Dashboard Authentication
**Decision**: OAuth 2.0 with Keycloak
**Rationale**:
- Enterprise-grade identity management with SSO support
- RBAC for sales managers and administrators
- GDPR-compliant with audit logging
- Supports MFA as required by Constitution security standards
- Can integrate with existing corporate LDAP/AD if needed
**Implementation**: Deploy Keycloak as separate service, integrate via OIDC flow
**Alternatives Considered**: Auth0 (vendor lock-in), local auth (insufficient for enterprise)

## Technology Stack Decisions

### Backend Architecture

**Decision**: Python 3.12 with FastAPI for microservices
**Rationale**:
- FastAPI provides automatic OpenAPI documentation and async support
- Strong typing with Pydantic aligns with DDD value objects
- Native async/await for handling concurrent AI operations
- Excellent performance (on par with Node.js/Go)
**Alternatives Considered**: Django (too monolithic), Flask (lacks built-in async), Node.js (less mature AI ecosystem)

### AI Orchestration

**Decision**: LangGraph with PostgreSQL persistence
**Rationale**:
- Deterministic workflow execution required by Constitution IX
- Built-in checkpointing for human-in-the-loop approvals (EUR 100k+ offers)
- Native integration with LangChain for GPT-4 interactions
- PostgreSQL persistence ensures workflow recovery
**Alternatives Considered**: Temporal (overcomplicated), Airflow (batch-oriented), custom state machines (reinventing wheel)

### Frontend Framework

**Decision**: Next.js 14 with shadcn/ui AI Elements
**Rationale**:
- Server-side rendering for SEO and initial load performance
- App Router provides better data fetching patterns
- shadcn/ui AI Elements specifically designed for conversational interfaces
- Built-in i18n support for EU languages
**Alternatives Considered**: React SPA (poor SEO), Vue.js (smaller ecosystem), Angular (overcomplicated)

### Database Architecture

**Decision**: PostgreSQL 16 with TimescaleDB extension
**Rationale**:
- TimescaleDB hypertables perfect for event sourcing (Constitution IV)
- Automatic partitioning for 10-year retention requirement
- Native JSON support for flexible event schemas
- Row-level security for GDPR compliance
**Alternatives Considered**: MongoDB (weak consistency), Cassandra (operational complexity), EventStore (limited ecosystem)

### Vector Search

**Decision**: Qdrant for semantic search
**Rationale**:
- Superior performance for similarity matching in project requirements
- On-premise deployment option for GDPR compliance
- REST and gRPC APIs for flexible integration
- Supports filtering for multi-tenant isolation
**Alternatives Considered**: Pinecone (cloud-only), Weaviate (resource heavy), pgvector (limited features)

### PDF Generation

**Decision**: ReportLab for Python
**Rationale**:
- Complete control over DIN 5008 formatting requirements
- Platypus layout engine for complex document structures
- Native support for European fonts and Unicode
- Can embed company branding assets
**Alternatives Considered**: wkhtmltopdf (rendering inconsistencies), Puppeteer (Node.js only), LaTeX (overcomplicated)

## Architecture Patterns

### Microservices Boundaries

**Decision**: 5 core bounded contexts aligned with DDD aggregates
**Services**:
1. **Conversation Service**: Manages AI interactions and context
2. **Offer Service**: Generates and versions offers
3. **Customer Service**: Handles PII and GDPR operations
4. **Estimation Service**: COCOMO calculations and historical analysis
5. **Notification Service**: Email, webhook, and approval workflows

**Rationale**: Each service owns its data, can scale independently, and has clear boundaries
**Alternatives Considered**: Monolith (scaling issues), serverless functions (cold starts), 10+ microservices (operational overhead)

### Event Sourcing Implementation

**Decision**: Hybrid approach - Event sourcing for offers, CRUD for reference data
**Rationale**:
- Offers require full audit trail (legal requirement)
- Customer data needs GDPR deletion capability
- Reference data (templates, rates) doesn't need event history
- Reduces complexity while meeting compliance needs
**Alternatives Considered**: Full event sourcing (GDPR deletion complex), No event sourcing (audit trail missing)

### API Gateway Pattern

**Decision**: Kong Gateway with custom plugins
**Rationale**:
- Built-in rate limiting (100 req/min requirement)
- API key management for A2A protocol
- Request/response transformation for versioning
- Prometheus metrics out of the box
**Alternatives Considered**: Nginx (limited features), AWS API Gateway (vendor lock-in), Traefik (immature)

## Integration Patterns

### OpenAI GPT-4 Integration

**Decision**: Streaming responses with fallback to GPT-3.5
**Rationale**:
- Streaming improves perceived performance for conversations
- Fallback ensures availability when GPT-4 has issues
- Token usage tracking for cost management
- Response caching for common questions
**Implementation**: LangChain with custom retry logic and circuit breakers

### Multi-language Support

**Decision**: i18next with separate translation service
**Rationale**:
- Industry standard for React/Next.js i18n
- Supports pluralization and formatting rules for all EU languages
- Translation service can use GPT-4 for initial translations
- Human review workflow for quality assurance
**Implementation**: JSON resource bundles with namespace separation

### COCOMO Model Calibration

**Decision**: Intermediate COCOMO with domain-specific adjustments
**Rationale**:
- Intermediate model accounts for project attributes
- Historical data provides calibration factors
- Bayesian updates improve accuracy over time
- Confidence intervals communicate uncertainty
**Implementation**: Python library with PostgreSQL storage for parameters

## Security & Compliance

### GDPR Implementation

**Decision**: Privacy-by-design with encryption and pseudonymization
**Approach**:
- AES-256-GCM for encryption at rest
- TLS 1.3 for transport encryption
- Separate PII service with restricted access
- Audit logs exclude sensitive data
- Automated retention policies with soft deletes
**Tools**: HashiCorp Vault for key management

### Authentication & Authorization

**Decision**: Keycloak for admin portal, API keys for A2A
**Rationale**:
- Keycloak provides enterprise SSO capabilities
- API keys simpler for agent integration
- JWT tokens for session management
- Role-based access with fine-grained permissions
**Implementation**: OIDC for web, bearer tokens for API

## Performance Optimization

### Caching Strategy

**Decision**: Redis with multi-tier caching
**Levels**:
1. CDN for static assets (Cloudflare)
2. Redis for session and API responses
3. PostgreSQL query cache for read models
4. Application-level memoization for calculations
**Rationale**: Reduces latency and database load

### Scalability Approach

**Decision**: Horizontal scaling with Kubernetes
**Rationale**:
- Auto-scaling based on CPU/memory metrics
- Rolling updates for zero-downtime deployments
- Service mesh (Istio) for internal communication
- Distributed tracing for performance monitoring
**Target**: 1000 concurrent users with <3s response time

## Development & Deployment

### CI/CD Pipeline

**Decision**: GitLab CI with Docker multi-stage builds
**Stages**:
1. Lint and format checks
2. Unit tests (parallel execution)
3. Build Docker images
4. Integration tests
5. Security scanning
6. Deploy to staging
7. Smoke tests
8. Production deployment (manual approval)
**Target**: <5 minute feedback loop

### Infrastructure as Code

**Decision**: Terraform for Hetzner Cloud provisioning
**Rationale**:
- Declarative infrastructure definition
- State management for drift detection
- Modular design for environment parity
- Cost-effective Hetzner Cloud as provider
**Implementation**: Separate workspaces for dev/staging/prod

### Deployment Platform

**Decision**: Coolify on Hetzner Cloud
**Rationale**:
- Open-source alternative to Heroku/Vercel
- Built-in support for Docker Compose
- Automatic SSL certificates with Let's Encrypt
- Cost-effective for European hosting (GDPR)
- GitOps workflow with automatic deployments
**Architecture**: 3 nodes for HA, managed PostgreSQL, Redis cluster

## Testing Strategy

### Test Pyramid

**Decision**: 70% unit, 20% integration, 10% E2E
**Tools**:
- **Unit**: pytest (Python), Jest (TypeScript)
- **Integration**: pytest with test containers
- **Contract**: Pact for service boundaries
- **E2E**: Playwright for critical paths
- **Performance**: Locust for load testing
- **Security**: OWASP ZAP for vulnerability scanning
**Coverage Target**: 100% for business logic, 80% overall

### Test Data Management

**Decision**: Factories with faker for synthetic data
**Rationale**:
- GDPR compliance (no real customer data in tests)
- Deterministic tests with seed values
- Edge case generation for property testing
- Separate test database with migrations
**Implementation**: Factory Boy (Python), Fishery (TypeScript)

## Monitoring & Observability

### Logging & Tracing

**Decision**: OpenTelemetry with Grafana stack
**Components**:
- **Logs**: Loki for aggregation
- **Metrics**: Prometheus with custom business metrics
- **Traces**: Tempo for distributed tracing
- **Visualization**: Grafana dashboards
**Rationale**: Open-source, comprehensive observability

### Alerting Strategy

**Decision**: Multi-channel alerts based on severity
**Channels**:
- **Critical**: PagerDuty (24/7 on-call)
- **High**: Email to team
- **Medium**: Slack notifications
- **Low**: Dashboard only
**SLOs**: 99.9% availability, <30s offer generation

## Risk Mitigation

### Technical Risks

1. **GPT-4 API Reliability**
   - Mitigation: Fallback to GPT-3.5, response caching, circuit breakers

2. **COCOMO Accuracy**
   - Mitigation: Confidence intervals, human review for high-value offers, continuous calibration

3. **Multi-language Complexity**
   - Mitigation: Phased rollout (DE/EN first), professional translation review, A/B testing

4. **Event Store Growth**
   - Mitigation: TimescaleDB compression, archival strategy, read model optimization

### Compliance Risks

1. **GDPR Violations**
   - Mitigation: Privacy impact assessment, data protection officer review, automated compliance checks

2. **DIN 5008 Non-compliance**
   - Mitigation: Template validation, business analyst review, automated formatting tests

## Resolved Clarifications

All technical uncertainties from the specification have been resolved:

1. **Historical Data**: Will use synthetic data initially, then learn from production
2. **COCOMO Calibration**: Industry defaults with iterative refinement
3. **Legal Requirements**: Standard German business terms with lawyer review
4. **Admin Authentication**: Keycloak with SSO integration

## Implementation Priorities

### Phase 1 (MVP) - Weeks 1-4
- Core conversation flow with GPT-4
- Basic offer generation (no estimation)
- German language only
- PDF generation with DIN 5008
- Customer data capture with GDPR consent

### Phase 2 (Enhanced) - Weeks 5-8
- COCOMO estimation integration
- English language support
- Approval workflow for high-value offers
- API for agent integration
- Redis caching layer

### Phase 3 (Complete) - Weeks 9-12
- All EU languages
- Historical data learning
- Advanced analytics dashboard
- DocuSign integration preparation
- Performance optimization

## Conclusion

All technical decisions have been made with clear rationale and consideration of alternatives. The architecture fully complies with the constitutional requirements while meeting all functional specifications. No clarifications remain - the system is ready for detailed design phase.

---
*Research completed: 2025-09-24*