"""
Request/Response Logging Middleware

Structured logging for all API requests and responses.
Excludes PII data for GDPR compliance.
"""

import time
import json
import logging
from typing import Callable, Optional
from datetime import datetime
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# Configure structured logging
logger = logging.getLogger("api.requests")


# PII fields to exclude from logs (GDPR compliance)
PII_FIELDS = {
    "email",
    "phone",
    "phone_number",
    "address",
    "street",
    "city",
    "postal_code",
    "zip_code",
    "first_name",
    "last_name",
    "name",
    "ssn",
    "tax_id",
    "birth_date",
    "date_of_birth",
    "password",
    "secret",
    "token",
    "api_key",
    "credit_card",
    "card_number",
    "cvv",
    "iban",
    "swift"
}


def sanitize_data(data: dict, max_depth: int = 5) -> dict:
    """
    Remove PII fields from data for logging.

    Args:
        data: Dictionary to sanitize
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Sanitized dictionary with PII fields redacted
    """
    if max_depth <= 0:
        return {"__truncated__": "max_depth_reached"}

    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Check if key contains PII
        key_lower = str(key).lower()
        if any(pii_field in key_lower for pii_field in PII_FIELDS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_data(value, max_depth - 1)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_data(item, max_depth - 1) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def sanitize_path(path: str) -> str:
    """
    Sanitize URL path to remove potential PII.

    Redacts UUIDs and numeric IDs that could be customer identifiers.

    Args:
        path: URL path

    Returns:
        Sanitized path with IDs replaced
    """
    import re

    # Replace UUIDs with placeholder
    path = re.sub(
        r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
        '{uuid}',
        path,
        flags=re.IGNORECASE
    )

    # Replace numeric IDs with placeholder (but keep route names)
    path = re.sub(r'/\d+/', '/{id}/', path)
    path = re.sub(r'/\d+$', '/{id}', path)

    return path


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all HTTP requests and responses.

    Features:
    - Structured JSON logging
    - Request/response timing
    - Unique request ID correlation
    - PII redaction for GDPR compliance
    - Configurable log levels
    - Error tracking
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        log_request_body: bool = False,
        log_response_body: bool = False,
        max_body_length: int = 1000,
        skip_paths: Optional[list[str]] = None
    ):
        """
        Initialize logging middleware.

        Args:
            app: ASGI application
            log_request_body: Whether to log request body (default: False for PII safety)
            log_response_body: Whether to log response body (default: False for PII safety)
            max_body_length: Maximum length of body to log
            skip_paths: List of paths to skip logging (e.g., /health, /metrics)
        """
        super().__init__(app)
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.max_body_length = max_body_length
        self.skip_paths = skip_paths or ["/health", "/ready", "/metrics"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response from application
        """
        # Generate unique request ID for correlation
        request_id = str(uuid4())
        request.state.request_id = request_id

        # Check if we should skip logging for this path
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Start timing
        start_time = time.time()

        # Prepare request log data
        request_log = {
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": request_id,
            "type": "request",
            "method": request.method,
            "path": sanitize_path(request.url.path),
            "path_params": sanitize_data(dict(request.path_params)),
            "query_params": sanitize_data(dict(request.query_params)),
            "headers": {
                "user-agent": request.headers.get("user-agent", "unknown"),
                "content-type": request.headers.get("content-type"),
                "accept": request.headers.get("accept"),
                "x-api-key": "[REDACTED]" if request.headers.get("x-api-key") else None,
                "authorization": "[REDACTED]" if request.headers.get("authorization") else None,
            },
            "client": {
                "host": request.client.host if request.client else None,
                "port": request.client.port if request.client else None,
            }
        }

        # Optionally log request body (with PII redaction)
        if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    try:
                        body_data = json.loads(body)
                        sanitized_body = sanitize_data(body_data)
                        body_str = json.dumps(sanitized_body)[:self.max_body_length]
                        request_log["body"] = body_str
                    except json.JSONDecodeError:
                        request_log["body"] = "[non-json-body]"
            except Exception as e:
                request_log["body_error"] = str(e)

        # Log request
        logger.info("API Request", extra={"structured": request_log})

        # Process request
        try:
            response = await call_next(request)

            # Calculate request duration
            duration_ms = (time.time() - start_time) * 1000

            # Prepare response log data
            response_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "type": "response",
                "method": request.method,
                "path": sanitize_path(request.url.path),
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "headers": {
                    "content-type": response.headers.get("content-type"),
                    "content-length": response.headers.get("content-length"),
                    "x-ratelimit-limit": response.headers.get("x-ratelimit-limit"),
                    "x-ratelimit-remaining": response.headers.get("x-ratelimit-remaining"),
                }
            }

            # Add request ID to response headers for client-side correlation
            response.headers["X-Request-ID"] = request_id

            # Log response (different levels based on status code)
            if response.status_code >= 500:
                logger.error("API Response - Server Error", extra={"structured": response_log})
            elif response.status_code >= 400:
                logger.warning("API Response - Client Error", extra={"structured": response_log})
            elif duration_ms > 3000:  # Log slow requests (>3s)
                logger.warning("API Response - Slow Request", extra={"structured": response_log})
            else:
                logger.info("API Response", extra={"structured": response_log})

            return response

        except Exception as e:
            # Log exception
            duration_ms = (time.time() - start_time) * 1000

            error_log = {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
                "type": "error",
                "method": request.method,
                "path": sanitize_path(request.url.path),
                "duration_ms": round(duration_ms, 2),
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                }
            }

            logger.error("API Request Failed", extra={"structured": error_log}, exc_info=True)

            # Re-raise exception to be handled by FastAPI
            raise


def get_request_id(request: Request) -> str:
    """
    Get request ID from request state.

    Args:
        request: FastAPI request

    Returns:
        Request ID string
    """
    return getattr(request.state, "request_id", "unknown")


def log_business_event(
    event_type: str,
    request: Request,
    data: dict,
    level: str = "info"
) -> None:
    """
    Log business event with structured data.

    Useful for tracking important business operations beyond HTTP requests.

    Args:
        event_type: Type of business event (e.g., "offer_generated", "customer_created")
        request: Current request for correlation
        data: Event data (will be sanitized)
        level: Log level (debug, info, warning, error)
    """
    event_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": get_request_id(request),
        "type": "business_event",
        "event_type": event_type,
        "data": sanitize_data(data)
    }

    log_func = getattr(logger, level, logger.info)
    log_func(f"Business Event: {event_type}", extra={"structured": event_log})


def log_security_event(
    event_type: str,
    request: Request,
    details: dict,
    severity: str = "warning"
) -> None:
    """
    Log security-related event.

    Args:
        event_type: Type of security event (e.g., "auth_failed", "rate_limit_exceeded")
        request: Current request
        details: Event details
        severity: Severity level (info, warning, error, critical)
    """
    security_log = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": get_request_id(request),
        "type": "security_event",
        "event_type": event_type,
        "client_ip": request.client.host if request.client else "unknown",
        "path": sanitize_path(request.url.path),
        "details": details
    }

    log_func = getattr(logger, severity, logger.warning)
    log_func(f"Security Event: {event_type}", extra={"structured": security_log})
