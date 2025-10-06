# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Removed incorrect nested `frontend/frontend` directory structure

## [0.1.0] - 2025-10-06

### Added

#### Backend Infrastructure
- Complete FastAPI application with event-driven architecture
- LangGraph-powered conversational AI system for customer interactions
- Domain models: Offer, Customer, Conversation, WorkPackage, Analytics, Estimation, Approval
- Repository pattern with PostgreSQL integration and Alembic migrations
- Event bus system with projections for read models
- OpenAI GPT-4 integration service with circuit breaker pattern
- Qdrant vector database integration for context retrieval
- Redis session management and caching
- PDF generation service for offer documents
- Email notification service with multi-language templates (German/English)
- Analytics aggregation job with time-series data
- Comprehensive middleware: JWT authentication, rate limiting, security headers, structured logging
- Circuit breaker and optimization patterns for resilience
- Prometheus metrics integration for monitoring

#### Frontend Application
- Next.js 14 application with App Router and TypeScript
- shadcn/ui component library with Tailwind CSS
- Multi-language support for all 27 EU official languages
- Customer-facing conversational interface with AI chat
- GDPR-compliant consent management system
- Admin approval dashboard with work package editing
- Analytics dashboards with conversion funnel visualization
- Offer preview and PDF download functionality
- Language selector component with flag icons
- Responsive design for mobile and desktop

#### Testing Suite
- Unit tests for core business logic (value objects, estimation, PDF generation, context manager)
- Integration tests for workflows (approval, conversation, GDPR, multi-language, rate limiting)
- Contract tests for all API endpoints (admin, analytics, conversations, customers, offers)
- Load tests with Locust for performance benchmarking
- Jest tests for React components (ConsentForm, LanguageSelector)
- Test coverage monitoring

#### Infrastructure & DevOps
- Docker Compose setup for local development
- PostgreSQL with initialization scripts
- Kong API Gateway configuration with rate limiting and CORS
- Prometheus monitoring setup
- Grafana dashboard configurations
- Multi-service orchestration (backend, frontend, databases, monitoring)

#### Documentation
- Comprehensive API documentation (698 lines)
- Admin guide with approval workflows
- GDPR compliance documentation (1193 lines)
- Deployment guide with production considerations
- Quick start guides for backend and monitoring
- Implementation status reports and validation guides
- Security audit report
- Performance monitoring documentation

#### Configuration & Tooling
- Comprehensive .gitignore for Python and Node.js ecosystems
- Environment configuration with .env.example template
- ESLint, Prettier, and TypeScript configurations
- Python packaging with pyproject.toml and requirements.txt
- Project constitution and memory configuration
- Plan template for feature development
- CLAUDE.md configuration files for development guidelines

### Changed
- Updated plan template with AI offer agent specific requirements
- Enhanced Spec-Kit templates with project-specific configurations

### Security
- JWT-based authentication middleware
- Rate limiting per IP and per API key
- GDPR-compliant data handling with consent tracking
- Security headers (HSTS, CSP, X-Frame-Options)
- API key redaction in logs
- Structured logging with correlation IDs
- Circuit breaker pattern for external service failures
- Input validation and sanitization
- Added .env files to .gitignore to prevent accidental commit of secrets
- Redacted sensitive API keys from documentation

### Fixed
- Redacted exposed OpenAI API key in SECURITY_AUDIT_REPORT.md before push