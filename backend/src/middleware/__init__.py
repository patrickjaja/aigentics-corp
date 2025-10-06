"""
Middleware Package for AI Offer Agent

Provides authentication, logging, security, and rate limiting middleware.
"""

from .auth import (
    verify_api_key,
    verify_jwt_token,
    get_user_from_token,
    has_role,
    require_role
)

from .logging import (
    RequestLoggingMiddleware,
    get_request_id,
    log_business_event,
    log_security_event,
    sanitize_data,
    sanitize_path
)

from .security import (
    SecurityHeadersMiddleware,
    TLSEnforcementMiddleware,
    setup_cors_middleware,
    validate_origin,
    get_security_headers,
    sanitize_redirect_url
)


__all__ = [
    # Authentication
    "verify_api_key",
    "verify_jwt_token",
    "get_user_from_token",
    "has_role",
    "require_role",

    # Logging
    "RequestLoggingMiddleware",
    "get_request_id",
    "log_business_event",
    "log_security_event",
    "sanitize_data",
    "sanitize_path",

    # Security
    "SecurityHeadersMiddleware",
    "TLSEnforcementMiddleware",
    "setup_cors_middleware",
    "validate_origin",
    "get_security_headers",
    "sanitize_redirect_url"
]
