# Data Model: AI Offer Agent

**Date**: 2025-09-24
**Feature**: AI Offer Agent for IT Consulting
**Branch**: 001-build-an-ai

## Overview

This document defines the domain model for the AI Offer Agent system, following Domain-Driven Design principles with clear bounded contexts and aggregates. All entities support event sourcing where required for audit trails.

## Bounded Contexts

### 1. Customer Context
Manages customer information, GDPR consent, and data privacy operations.

### 2. Conversation Context
Handles AI-powered conversations, context management, and requirement gathering.

### 3. Offer Context
Generates, versions, and manages offers with work packages and pricing.

### 4. Estimation Context
Calculates project estimates using COCOMO models and historical data.

### 5. Approval Context
Manages approval workflows for high-value offers.

## Core Entities

### Customer (Aggregate Root)

```python
class Customer:
    id: UUID
    external_id: str  # For GDPR pseudonymization
    company_name: str
    contact_person: str
    email: EmailAddress  # Value object with validation
    phone: Optional[PhoneNumber]  # Value object with validation
    language_preference: LanguageCode  # ISO 639-1
    gdpr_consent: GDPRConsent
    created_at: datetime
    updated_at: datetime
    deletion_requested_at: Optional[datetime]

class GDPRConsent:
    given_at: datetime
    ip_address: str
    consent_text_version: str
    purposes: List[ConsentPurpose]
    withdrawn_at: Optional[datetime]

class ConsentPurpose(Enum):
    OFFER_GENERATION = "offer_generation"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
```

**Invariants:**
- Email must be valid format
- GDPR consent required before storing PII
- Deletion request triggers 4-year legal retention

**State Transitions:**
- `Prospect → Lead → Customer → Deleted`

### Project (Entity)

```python
class Project:
    id: UUID
    customer_id: UUID
    name: str
    description: str
    category: ProjectCategory
    requirements: List[Requirement]
    constraints: ProjectConstraints
    timeline: Optional[Timeline]
    budget_indication: Optional[BudgetRange]
    created_at: datetime

class ProjectCategory(Enum):
    SOFTWARE_DEVELOPMENT = "software_development"
    IT_CONSULTING = "consulting"
    INFRASTRUCTURE = "infrastructure"
    MIXED = "mixed"

class Requirement:
    id: UUID
    description: str
    priority: Priority  # HIGH, MEDIUM, LOW
    type: RequirementType  # FUNCTIONAL, NON_FUNCTIONAL
    acceptance_criteria: List[str]

class ProjectConstraints:
    max_budget: Optional[Money]
    deadline: Optional[date]
    technology_preferences: List[str]
    team_size_limit: Optional[int]
```

**Invariants:**
- Project must have at least one requirement
- Budget and timeline constraints are optional but affect estimation

### Conversation (Aggregate Root)

```python
class Conversation:
    id: UUID
    session_id: str  # For anonymous tracking before customer creation
    customer_id: Optional[UUID]
    project_id: Optional[UUID]
    language: LanguageCode
    started_at: datetime
    last_interaction_at: datetime
    status: ConversationStatus
    interactions: List[Interaction]
    context: ConversationContext
    completion_percentage: int

class ConversationStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"

class Interaction:
    id: UUID
    timestamp: datetime
    type: InteractionType  # USER_MESSAGE, AI_MESSAGE, AI_QUESTION
    content: str
    language: LanguageCode
    metadata: Dict[str, Any]  # For tracking intents, entities

class ConversationContext:
    current_topic: str
    answered_questions: List[str]
    pending_questions: List[str]
    gathered_requirements: List[str]
    confidence_scores: Dict[str, float]
```

**Invariants:**
- Maximum 5 questions per interaction round
- Context must be maintained across interactions
- Escalation triggered after 5 clarification rounds

**State Machine:**
```
ACTIVE → PAUSED → ACTIVE
  ↓        ↓        ↓
COMPLETED  ABANDONED  ESCALATED
```

### Offer (Aggregate Root)

```python
class Offer:
    id: UUID
    offer_number: str  # Format: YY-NNNN
    version: int
    customer_id: UUID
    project_id: UUID
    conversation_id: UUID
    created_at: datetime
    valid_until: date
    status: OfferStatus
    total_value: Money
    work_packages: List[WorkPackage]
    terms_and_conditions: str
    approval_required: bool
    approval_workflow_id: Optional[UUID]
    events: List[OfferEvent]  # Event sourcing

class OfferStatus(Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class Money:
    amount: Decimal
    currency: str  # ISO 4217

    def __str__(self):
        # German formatting: 1.234,56 €
        return format_german_currency(self.amount, self.currency)
```

**Invariants:**
- Offer number must be unique
- Approval required if total_value > EUR 100,000
- Version increments on any modification
- Valid for 30 days from creation

**Event Sourcing:**
All state changes recorded as events:
- `OfferCreated`
- `OfferModified`
- `OfferApproved`
- `OfferSent`
- `OfferViewed`
- `OfferAccepted`
- `OfferRejected`

### WorkPackage (Entity)

```python
class WorkPackage:
    id: UUID
    offer_id: UUID
    name: str
    description: str
    deliverables: List[Deliverable]
    estimated_hours: EstimatedHours
    hourly_rate: Money
    total_cost: Money
    dependencies: List[UUID]  # Other work package IDs
    order: int  # Display order

class Deliverable:
    name: str
    description: str
    acceptance_criteria: List[str]

class EstimatedHours:
    optimistic: Decimal
    likely: Decimal
    pessimistic: Decimal
    confidence: float  # 0.0 to 1.0

    @property
    def expected(self) -> Decimal:
        # PERT formula: (O + 4L + P) / 6
        return (self.optimistic + 4 * self.likely + self.pessimistic) / 6
```

**Invariants:**
- Total cost = estimated_hours.expected × hourly_rate
- Dependencies must form a DAG (no cycles)
- At least one deliverable per package

### ApprovalWorkflow (Aggregate Root)

```python
class ApprovalWorkflow:
    id: UUID
    offer_id: UUID
    requested_by: UUID
    requested_at: datetime
    approver_id: UUID
    status: ApprovalStatus
    decision: Optional[ApprovalDecision]
    decided_at: Optional[datetime]
    comments: List[Comment]
    modifications: List[OfferModification]

class ApprovalStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"

class ApprovalDecision:
    outcome: ApprovalStatus
    reason: str
    conditions: List[str]

class Comment:
    id: UUID
    author_id: UUID
    timestamp: datetime
    content: str

class OfferModification:
    field_path: str  # JSONPath to modified field
    old_value: Any
    new_value: Any
    modified_by: UUID
    modified_at: datetime
    reason: str
```

**Invariants:**
- Only one active workflow per offer
- Approver cannot be the requester
- Modifications trigger new offer version

### EstimationModel (Entity)

```python
class EstimationModel:
    id: UUID
    name: str
    project_category: ProjectCategory
    cocomo_parameters: COCOMOParameters
    calibration_data: List[CalibrationPoint]
    accuracy_metrics: AccuracyMetrics
    last_updated: datetime

class COCOMOParameters:
    # Intermediate COCOMO II
    effort_multipliers: Dict[str, float]
    scale_factors: Dict[str, float]
    cost_drivers: Dict[str, float]

class CalibrationPoint:
    project_id: UUID
    estimated_hours: float
    actual_hours: float
    variance: float
    factors: Dict[str, Any]

class AccuracyMetrics:
    mean_absolute_error: float
    mean_squared_error: float
    r_squared: float
    within_25_percent: float  # Percentage within ±25%
```

**Invariants:**
- Must maintain ±25% variance target
- Calibration data retained for continuous learning
- Model updated after each completed project

### APIClient (Entity)

```python
class APIClient:
    id: UUID
    name: str
    api_key: str  # Hashed
    organization: str
    rate_limit: RateLimit
    usage_statistics: UsageStats
    enabled: bool
    created_at: datetime
    last_used_at: Optional[datetime]

class RateLimit:
    requests_per_minute: int = 100
    burst_size: int = 200
    current_tokens: int
    last_refill: datetime

class UsageStats:
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_offers_generated: int
    last_30_days_requests: int
```

**Invariants:**
- API key must be unique
- Rate limiting enforced at gateway level
- Usage tracked for billing and analytics

## Value Objects

### EmailAddress
```python
class EmailAddress:
    value: str

    def __init__(self, value: str):
        if not self._is_valid_email(value):
            raise ValueError(f"Invalid email address: {value}")
        self.value = value.lower()
```

### PhoneNumber
```python
class PhoneNumber:
    country_code: str
    number: str

    def __init__(self, full_number: str):
        # Parse and validate using phonenumbers library
        parsed = phonenumbers.parse(full_number)
        if not phonenumbers.is_valid_number(parsed):
            raise ValueError(f"Invalid phone number: {full_number}")
        self.country_code = f"+{parsed.country_code}"
        self.number = str(parsed.national_number)
```

### LanguageCode
```python
class LanguageCode:
    code: str  # ISO 639-1

    SUPPORTED_LANGUAGES = [
        "de", "en", "fr", "es", "it", "nl", "pl", "pt",
        "cs", "da", "el", "hu", "ro", "sv", "bg", "hr",
        "et", "fi", "ga", "lt", "lv", "mt", "sk", "sl"
    ]

    def __init__(self, code: str):
        if code not in self.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {code}")
        self.code = code
```

### BudgetRange
```python
class BudgetRange:
    min_amount: Optional[Money]
    max_amount: Optional[Money]

    def __init__(self, min_amount: Optional[Money], max_amount: Optional[Money]):
        if min_amount and max_amount and min_amount.amount > max_amount.amount:
            raise ValueError("Min amount cannot exceed max amount")
        self.min_amount = min_amount
        self.max_amount = max_amount
```

## Domain Events

Event sourcing for audit trail (stored in TimescaleDB):

```python
class DomainEvent:
    event_id: UUID
    aggregate_id: UUID
    aggregate_type: str
    event_type: str
    event_version: int
    occurred_at: datetime
    correlation_id: UUID
    causation_id: UUID
    actor_id: Optional[UUID]
    metadata: Dict[str, Any]
    payload: Dict[str, Any]
```

### Key Events

1. **Customer Events**
   - CustomerCreated
   - ConsentGiven
   - ConsentWithdrawn
   - DeletionRequested

2. **Conversation Events**
   - ConversationStarted
   - QuestionAsked
   - AnswerReceived
   - RequirementIdentified
   - ConversationCompleted

3. **Offer Events**
   - OfferGenerated
   - OfferModified
   - ApprovalRequested
   - OfferApproved
   - OfferSent
   - OfferViewed
   - OfferAccepted

4. **Workflow Events**
   - WorkflowInitiated
   - ReviewStarted
   - RevisionRequested
   - DecisionMade

## Database Schema Considerations

### Write Model (Event Store)
- Single `events` table in TimescaleDB
- Hypertable partitioned by time
- Indexes on aggregate_id, event_type, occurred_at

### Read Models (Projections)
- Separate tables for each aggregate
- Optimized for query patterns
- Eventually consistent with event store

### GDPR Compliance
- PII in separate schema with encryption
- Audit logs exclude sensitive data
- Soft deletes with retention policy

## Validation Rules

### Business Rules
1. Offers expire after 30 days
2. High-value offers (>EUR 100k) need approval
3. Maximum 5 questions per conversation round
4. Work packages must have deliverables
5. Customer must consent before data storage

### Technical Constraints
1. UUID v4 for all identifiers
2. Timestamps in UTC
3. Money calculations use Decimal (4 decimal places)
4. All strings UTF-8 encoded
5. Enums stored as strings for clarity

## Migration Considerations

### Event Schema Evolution
- New fields are optional
- Never remove fields
- Use event version for branching logic
- Provide upgrade/downgrade paths

### Data Retention
- Customer data: 4 years after deletion request
- Offers: 10 years (legal requirement)
- Conversations: 30 days if incomplete
- Events: Indefinite (append-only)

---
*Data model defined: 2025-09-24*