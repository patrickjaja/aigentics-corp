"""
Notification Service - Email and Webhook Notifications

Provides async notification capabilities for offer-related events with:
- Email notifications (SMTP with multi-language support)
- Webhook notifications for external integrations
- Retry logic with exponential backoff
- Circuit breaker pattern for resilience
- Health check endpoint

Events:
- Offer created
- Approval required (high-value offers)
- Offer approved/rejected
- Offer sent to customer
"""

import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import aiosmtplib
import httpx
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from jinja2 import Environment, FileSystemLoader, Template
from pydantic import BaseModel, EmailStr, Field, HttpUrl
from pydantic_settings import BaseSettings

from ...models.value_objects import EmailAddress, Money


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NotificationSettings(BaseSettings):
    """Configuration for notification service."""

    # SMTP Configuration
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@example.com"
    smtp_from_name: str = "AI Offer Agent"
    smtp_use_tls: bool = True

    # Circuit Breaker Configuration
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout_seconds: int = 60
    circuit_breaker_recovery_seconds: int = 30

    # Retry Configuration
    max_retry_attempts: int = 3
    retry_base_delay_seconds: int = 2
    retry_max_delay_seconds: int = 60

    # Webhook Configuration
    webhook_timeout_seconds: int = 10

    # Template Configuration
    template_dir: str = "./templates/email"

    class Config:
        env_file = ".env"
        case_sensitive = False


class NotificationType(str, Enum):
    """Types of notifications."""
    OFFER_CREATED = "offer_created"
    APPROVAL_REQUIRED = "approval_required"
    OFFER_APPROVED = "offer_approved"
    OFFER_REJECTED = "offer_rejected"
    OFFER_SENT = "offer_sent"


class NotificationLanguage(str, Enum):
    """Supported notification languages."""
    GERMAN = "de"
    ENGLISH = "en"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# Pydantic models for API
class EmailNotificationRequest(BaseModel):
    """Request model for email notifications."""
    to_email: EmailStr
    notification_type: NotificationType
    language: NotificationLanguage = NotificationLanguage.ENGLISH
    context: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "to_email": "customer@example.com",
                "notification_type": "offer_created",
                "language": "de",
                "context": {
                    "offer_id": "123e4567-e89b-12d3-a456-426614174000",
                    "offer_number": "25-0001",
                    "customer_name": "Max Mustermann",
                    "total_value": "75000.00",
                    "currency": "EUR"
                }
            }
        }


class WebhookNotificationRequest(BaseModel):
    """Request model for webhook notifications."""
    webhook_url: HttpUrl
    notification_type: NotificationType
    payload: Dict[str, Any]
    headers: Optional[Dict[str, str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "webhook_url": "https://api.example.com/webhooks/offers",
                "notification_type": "offer_created",
                "payload": {
                    "event": "offer.created",
                    "offer_id": "123e4567-e89b-12d3-a456-426614174000",
                    "timestamp": "2025-10-06T12:00:00Z"
                },
                "headers": {
                    "X-API-Key": "secret_key"
                }
            }
        }


class NotificationResponse(BaseModel):
    """Response model for notification requests."""
    notification_id: str
    status: str
    message: str
    sent_at: datetime
    retry_count: int = 0


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    service: str
    smtp_status: str
    circuit_breaker_status: str
    timestamp: datetime


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external services.

    Prevents cascading failures by temporarily blocking requests
    when failure threshold is exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        recovery_seconds: int = 30
    ):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.recovery_seconds = recovery_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None

    def record_success(self) -> None:
        """Record a successful operation."""
        self.failure_count = 0
        self.last_success_time = datetime.utcnow()

        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovered, state: CLOSED")
            self.state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Record a failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"Circuit breaker threshold exceeded ({self.failure_count}), state: OPEN"
            )
            self.state = CircuitState.OPEN

    def can_attempt(self) -> bool:
        """Check if an operation can be attempted."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                time_since_failure = (datetime.utcnow() - self.last_failure_time).total_seconds()

                if time_since_failure >= self.recovery_seconds:
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = CircuitState.HALF_OPEN
                    return True

            return False

        # HALF_OPEN state - allow single attempt
        return True

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state


class NotificationService:
    """Service for managing email and webhook notifications."""

    def __init__(self, settings: NotificationSettings):
        self.settings = settings
        self.smtp_circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            timeout_seconds=settings.circuit_breaker_timeout_seconds,
            recovery_seconds=settings.circuit_breaker_recovery_seconds
        )
        self.webhook_circuit_breaker = CircuitBreaker(
            failure_threshold=settings.circuit_breaker_failure_threshold,
            timeout_seconds=settings.circuit_breaker_timeout_seconds,
            recovery_seconds=settings.circuit_breaker_recovery_seconds
        )

        # Initialize Jinja2 template environment
        try:
            self.template_env = Environment(
                loader=FileSystemLoader(settings.template_dir),
                autoescape=True
            )
        except Exception as e:
            logger.warning(f"Could not load templates from {settings.template_dir}: {e}")
            self.template_env = None

    def _get_email_template(
        self,
        notification_type: NotificationType,
        language: NotificationLanguage
    ) -> tuple[str, str]:
        """
        Get email subject and body template for notification type and language.

        Returns:
            Tuple of (subject, html_body)
        """
        # Template filenames follow pattern: {type}_{lang}.html
        template_name = f"{notification_type.value}_{language.value}.html"

        # Default templates if file loading fails
        templates = {
            NotificationType.OFFER_CREATED: {
                NotificationLanguage.GERMAN: (
                    "Ihr Angebot wurde erstellt",
                    """
                    <html>
                    <body>
                        <h2>Sehr geehrte/r {{ customer_name }},</h2>
                        <p>Ihr Angebot <strong>{{ offer_number }}</strong> wurde erfolgreich erstellt.</p>
                        <p><strong>Gesamtwert:</strong> {{ total_value }} {{ currency }}</p>
                        <p>Sie können das Angebot über folgenden Link herunterladen:</p>
                        <p><a href="{{ download_link }}">Angebot herunterladen</a></p>
                        <p>Das Angebot ist gültig bis zum {{ valid_until }}.</p>
                        <p>Mit freundlichen Grüßen,<br>Ihr AI Offer Agent Team</p>
                    </body>
                    </html>
                    """
                ),
                NotificationLanguage.ENGLISH: (
                    "Your offer has been created",
                    """
                    <html>
                    <body>
                        <h2>Dear {{ customer_name }},</h2>
                        <p>Your offer <strong>{{ offer_number }}</strong> has been successfully created.</p>
                        <p><strong>Total value:</strong> {{ total_value }} {{ currency }}</p>
                        <p>You can download your offer using the following link:</p>
                        <p><a href="{{ download_link }}">Download Offer</a></p>
                        <p>The offer is valid until {{ valid_until }}.</p>
                        <p>Best regards,<br>Your AI Offer Agent Team</p>
                    </body>
                    </html>
                    """
                )
            },
            NotificationType.APPROVAL_REQUIRED: {
                NotificationLanguage.GERMAN: (
                    "Genehmigung erforderlich - Angebot {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Genehmigung erforderlich</h2>
                        <p>Das Angebot <strong>{{ offer_number }}</strong> für {{ customer_name }} benötigt Ihre Genehmigung.</p>
                        <p><strong>Gesamtwert:</strong> {{ total_value }} {{ currency }}</p>
                        <p><strong>Grund:</strong> Angebotswert überschreitet EUR 100.000</p>
                        <p><a href="{{ approval_link }}">Angebot prüfen und genehmigen</a></p>
                        <p>Mit freundlichen Grüßen,<br>AI Offer Agent System</p>
                    </body>
                    </html>
                    """
                ),
                NotificationLanguage.ENGLISH: (
                    "Approval Required - Offer {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Approval Required</h2>
                        <p>The offer <strong>{{ offer_number }}</strong> for {{ customer_name }} requires your approval.</p>
                        <p><strong>Total value:</strong> {{ total_value }} {{ currency }}</p>
                        <p><strong>Reason:</strong> Offer value exceeds EUR 100,000</p>
                        <p><a href="{{ approval_link }}">Review and approve offer</a></p>
                        <p>Best regards,<br>AI Offer Agent System</p>
                    </body>
                    </html>
                    """
                )
            },
            NotificationType.OFFER_APPROVED: {
                NotificationLanguage.GERMAN: (
                    "Angebot genehmigt - {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Angebot genehmigt</h2>
                        <p>Das Angebot <strong>{{ offer_number }}</strong> wurde von {{ approver_name }} genehmigt.</p>
                        <p><strong>Kommentar:</strong> {{ approval_comments }}</p>
                        <p>Das Angebot kann nun an den Kunden versendet werden.</p>
                        <p>Mit freundlichen Grüßen,<br>AI Offer Agent System</p>
                    </body>
                    </html>
                    """
                ),
                NotificationLanguage.ENGLISH: (
                    "Offer Approved - {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Offer Approved</h2>
                        <p>The offer <strong>{{ offer_number }}</strong> has been approved by {{ approver_name }}.</p>
                        <p><strong>Comment:</strong> {{ approval_comments }}</p>
                        <p>The offer can now be sent to the customer.</p>
                        <p>Best regards,<br>AI Offer Agent System</p>
                    </body>
                    </html>
                    """
                )
            },
            NotificationType.OFFER_REJECTED: {
                NotificationLanguage.GERMAN: (
                    "Angebot abgelehnt - {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Angebot abgelehnt</h2>
                        <p>Das Angebot <strong>{{ offer_number }}</strong> wurde von {{ approver_name }} abgelehnt.</p>
                        <p><strong>Begründung:</strong> {{ rejection_reason }}</p>
                        <p>Bitte überarbeiten Sie das Angebot entsprechend.</p>
                        <p>Mit freundlichen Grüßen,<br>AI Offer Agent System</p>
                    </body>
                    </html>
                    """
                ),
                NotificationLanguage.ENGLISH: (
                    "Offer Rejected - {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Offer Rejected</h2>
                        <p>The offer <strong>{{ offer_number }}</strong> has been rejected by {{ approver_name }}.</p>
                        <p><strong>Reason:</strong> {{ rejection_reason }}</p>
                        <p>Please revise the offer accordingly.</p>
                        <p>Best regards,<br>AI Offer Agent System</p>
                    </body>
                    </html>
                    """
                )
            },
            NotificationType.OFFER_SENT: {
                NotificationLanguage.GERMAN: (
                    "Angebot versendet - {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Sehr geehrte/r {{ customer_name }},</h2>
                        <p>Ihr angefordertes Angebot <strong>{{ offer_number }}</strong> wurde versendet.</p>
                        <p><strong>Gesamtwert:</strong> {{ total_value }} {{ currency }}</p>
                        <p><a href="{{ download_link }}">Angebot herunterladen</a></p>
                        <p>Bei Fragen stehen wir Ihnen gerne zur Verfügung.</p>
                        <p>Mit freundlichen Grüßen,<br>Ihr AI Offer Agent Team</p>
                    </body>
                    </html>
                    """
                ),
                NotificationLanguage.ENGLISH: (
                    "Offer Sent - {{ offer_number }}",
                    """
                    <html>
                    <body>
                        <h2>Dear {{ customer_name }},</h2>
                        <p>Your requested offer <strong>{{ offer_number }}</strong> has been sent.</p>
                        <p><strong>Total value:</strong> {{ total_value }} {{ currency }}</p>
                        <p><a href="{{ download_link }}">Download Offer</a></p>
                        <p>Please feel free to contact us if you have any questions.</p>
                        <p>Best regards,<br>Your AI Offer Agent Team</p>
                    </body>
                    </html>
                    """
                )
            }
        }

        # Try to load from file template
        if self.template_env:
            try:
                template = self.template_env.get_template(template_name)
                subject = template.module.SUBJECT if hasattr(template.module, 'SUBJECT') else ""
                if not subject:
                    subject = templates[notification_type][language][0]
                body = template.render()
                return (subject, body)
            except Exception as e:
                logger.warning(f"Could not load template {template_name}: {e}, using default")

        # Use default templates
        return templates.get(notification_type, {}).get(
            language,
            templates[NotificationType.OFFER_CREATED][NotificationLanguage.ENGLISH]
        )

    async def _send_email_with_retry(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        retry_count: int = 0
    ) -> tuple[bool, str]:
        """
        Send email with retry logic and exponential backoff.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            retry_count: Current retry attempt

        Returns:
            Tuple of (success: bool, message: str)
        """
        # Check circuit breaker
        if not self.smtp_circuit_breaker.can_attempt():
            return (False, "SMTP circuit breaker is OPEN, service temporarily unavailable")

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
            message["To"] = to_email
            message["Subject"] = subject

            # Attach HTML body
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)

            # Send via SMTP
            async with aiosmtplib.SMTP(
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                use_tls=self.settings.smtp_use_tls
            ) as smtp:
                if self.settings.smtp_user and self.settings.smtp_password:
                    await smtp.login(self.settings.smtp_user, self.settings.smtp_password)

                await smtp.send_message(message)

            # Record success
            self.smtp_circuit_breaker.record_success()
            logger.info(f"Email sent successfully to {to_email}")

            return (True, "Email sent successfully")

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")

            # Record failure
            self.smtp_circuit_breaker.record_failure()

            # Retry logic with exponential backoff
            if retry_count < self.settings.max_retry_attempts:
                delay = min(
                    self.settings.retry_base_delay_seconds * (2 ** retry_count),
                    self.settings.retry_max_delay_seconds
                )
                logger.info(f"Retrying email send in {delay}s (attempt {retry_count + 1})")

                await asyncio.sleep(delay)
                return await self._send_email_with_retry(
                    to_email, subject, html_body, retry_count + 1
                )

            return (False, f"Failed to send email after {retry_count + 1} attempts: {str(e)}")

    async def send_email_notification(
        self,
        to_email: str,
        notification_type: NotificationType,
        language: NotificationLanguage,
        context: Dict[str, Any]
    ) -> NotificationResponse:
        """
        Send an email notification.

        Args:
            to_email: Recipient email address
            notification_type: Type of notification
            language: Language for email template
            context: Template context variables

        Returns:
            NotificationResponse with status
        """
        notification_id = str(uuid4())

        # Get email template
        subject, html_body = self._get_email_template(notification_type, language)

        # Render template with context
        try:
            subject_template = Template(subject)
            body_template = Template(html_body)

            rendered_subject = subject_template.render(**context)
            rendered_body = body_template.render(**context)
        except Exception as e:
            logger.error(f"Template rendering failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to render email template: {str(e)}"
            )

        # Send email with retry
        success, message = await self._send_email_with_retry(
            to_email, rendered_subject, rendered_body
        )

        return NotificationResponse(
            notification_id=notification_id,
            status="sent" if success else "failed",
            message=message,
            sent_at=datetime.utcnow(),
            retry_count=0
        )

    async def send_webhook_notification(
        self,
        webhook_url: str,
        notification_type: NotificationType,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> NotificationResponse:
        """
        Send a webhook notification with retry logic.

        Args:
            webhook_url: Webhook endpoint URL
            notification_type: Type of notification
            payload: JSON payload to send
            headers: Optional HTTP headers

        Returns:
            NotificationResponse with status
        """
        notification_id = str(uuid4())

        # Check circuit breaker
        if not self.webhook_circuit_breaker.can_attempt():
            return NotificationResponse(
                notification_id=notification_id,
                status="failed",
                message="Webhook circuit breaker is OPEN, service temporarily unavailable",
                sent_at=datetime.utcnow()
            )

        # Add metadata to payload
        enriched_payload = {
            "event_type": notification_type.value,
            "event_id": notification_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": payload
        }

        # Prepare headers
        webhook_headers = {
            "Content-Type": "application/json",
            "User-Agent": "AI-Offer-Agent-Webhook/1.0"
        }
        if headers:
            webhook_headers.update(headers)

        retry_count = 0
        last_error = None

        # Retry loop
        while retry_count <= self.settings.max_retry_attempts:
            try:
                async with httpx.AsyncClient(
                    timeout=self.settings.webhook_timeout_seconds
                ) as client:
                    response = await client.post(
                        webhook_url,
                        json=enriched_payload,
                        headers=webhook_headers
                    )

                    response.raise_for_status()

                # Record success
                self.webhook_circuit_breaker.record_success()
                logger.info(f"Webhook sent successfully to {webhook_url}")

                return NotificationResponse(
                    notification_id=notification_id,
                    status="sent",
                    message=f"Webhook delivered successfully (HTTP {response.status_code})",
                    sent_at=datetime.utcnow(),
                    retry_count=retry_count
                )

            except Exception as e:
                last_error = str(e)
                logger.error(f"Webhook delivery failed (attempt {retry_count + 1}): {last_error}")

                # Record failure
                self.webhook_circuit_breaker.record_failure()

                if retry_count < self.settings.max_retry_attempts:
                    delay = min(
                        self.settings.retry_base_delay_seconds * (2 ** retry_count),
                        self.settings.retry_max_delay_seconds
                    )
                    logger.info(f"Retrying webhook in {delay}s")
                    await asyncio.sleep(delay)

                retry_count += 1

        return NotificationResponse(
            notification_id=notification_id,
            status="failed",
            message=f"Failed to deliver webhook after {retry_count} attempts: {last_error}",
            sent_at=datetime.utcnow(),
            retry_count=retry_count
        )

    async def check_health(self) -> HealthCheckResponse:
        """
        Health check for notification service.

        Returns:
            HealthCheckResponse with service status
        """
        # Test SMTP connectivity
        smtp_status = "unknown"
        try:
            async with aiosmtplib.SMTP(
                hostname=self.settings.smtp_host,
                port=self.settings.smtp_port,
                timeout=5
            ) as smtp:
                smtp_status = "healthy"
        except Exception as e:
            smtp_status = f"unhealthy: {str(e)}"
            logger.error(f"SMTP health check failed: {str(e)}")

        overall_status = (
            "healthy" if smtp_status == "healthy" else "degraded"
        )

        return HealthCheckResponse(
            status=overall_status,
            service="notification",
            smtp_status=smtp_status,
            circuit_breaker_status=f"SMTP: {self.smtp_circuit_breaker.get_state().value}, "
                                   f"Webhook: {self.webhook_circuit_breaker.get_state().value}",
            timestamp=datetime.utcnow()
        )


# FastAPI application
app = FastAPI(
    title="Notification Service",
    version="1.0.0",
    description="Email and webhook notification service with retry logic and circuit breaker"
)

# Dependency injection
settings = NotificationSettings()
notification_service = NotificationService(settings)


async def get_notification_service() -> NotificationService:
    """Dependency for getting notification service."""
    return notification_service


# API Endpoints
@app.post("/notifications/email", response_model=NotificationResponse)
async def send_email(
    request: EmailNotificationRequest,
    background_tasks: BackgroundTasks,
    service: NotificationService = Depends(get_notification_service)
):
    """
    Send an email notification.

    Supports multi-language templates (German/English) for:
    - Offer created
    - Approval required
    - Offer approved/rejected
    - Offer sent to customer
    """
    try:
        response = await service.send_email_notification(
            to_email=request.to_email,
            notification_type=request.notification_type,
            language=request.language,
            context=request.context
        )
        return response
    except Exception as e:
        logger.error(f"Email notification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/notifications/webhook", response_model=NotificationResponse)
async def send_webhook(
    request: WebhookNotificationRequest,
    background_tasks: BackgroundTasks,
    service: NotificationService = Depends(get_notification_service)
):
    """
    Send a webhook notification to external integration.

    Includes retry logic with exponential backoff and circuit breaker pattern.
    """
    try:
        response = await service.send_webhook_notification(
            webhook_url=str(request.webhook_url),
            notification_type=request.notification_type,
            payload=request.payload,
            headers=request.headers
        )
        return response
    except Exception as e:
        logger.error(f"Webhook notification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthCheckResponse)
async def health_check(
    service: NotificationService = Depends(get_notification_service)
):
    """
    Health check endpoint.

    Verifies SMTP connectivity and circuit breaker status.
    """
    return await service.check_health()


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "notification",
        "version": "1.0.0",
        "endpoints": {
            "email": "/notifications/email",
            "webhook": "/notifications/webhook",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
