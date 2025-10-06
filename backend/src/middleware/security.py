"""
Security Middleware for API Gateway

Implements CORS, security headers, and TLS enforcement.
Follows OWASP security best practices and GDPR requirements.
"""

import os
from typing import Callable, Optional
from urllib.parse import urlparse

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp


# Security configuration from environment
ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
ENFORCE_HTTPS = os.getenv("ENFORCE_HTTPS", "false").lower() == "true"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware for adding security headers to all responses.

    Implements:
    - Content Security Policy (CSP)
    - HTTP Strict Transport Security (HSTS)
    - X-Frame-Options
    - X-Content-Type-Options
    - X-XSS-Protection
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        enforce_https: bool = ENFORCE_HTTPS,
        csp_policy: Optional[str] = None,
        hsts_max_age: int = 31536000,  # 1 year
        frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin"
    ):
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            enforce_https: Redirect HTTP to HTTPS
            csp_policy: Custom Content Security Policy (default: restrictive)
            hsts_max_age: HSTS max-age in seconds
            frame_options: X-Frame-Options value (DENY, SAMEORIGIN)
            referrer_policy: Referrer-Policy value
        """
        super().__init__(app)
        self.enforce_https = enforce_https
        self.hsts_max_age = hsts_max_age
        self.frame_options = frame_options
        self.referrer_policy = referrer_policy

        # Default CSP policy - very restrictive
        if csp_policy is None:
            self.csp_policy = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "  # unsafe-inline needed for some CSS frameworks
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self' https:; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "upgrade-insecure-requests;"
            )
        else:
            self.csp_policy = csp_policy

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with security headers
        """
        # HTTPS enforcement (redirect HTTP to HTTPS in production)
        if self.enforce_https and request.url.scheme == "http":
            # Don't redirect health checks and local development
            if not (
                request.url.path in ["/health", "/ready", "/metrics"]
                or request.client.host in ["127.0.0.1", "localhost"]
            ):
                https_url = request.url.replace(scheme="https")
                return Response(
                    status_code=301,
                    headers={"Location": str(https_url)}
                )

        # Process request
        response = await call_next(request)

        # Add security headers
        headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",

            # Prevent clickjacking
            "X-Frame-Options": self.frame_options,

            # XSS protection (legacy, but still useful for older browsers)
            "X-XSS-Protection": "1; mode=block",

            # Referrer policy
            "Referrer-Policy": self.referrer_policy,

            # Remove server information
            "X-Powered-By": "",  # Remove default framework header

            # Permissions policy (restrict browser features)
            "Permissions-Policy": (
                "geolocation=(), "
                "microphone=(), "
                "camera=(), "
                "payment=(), "
                "usb=(), "
                "magnetometer=(), "
                "gyroscope=(), "
                "accelerometer=()"
            ),
        }

        # Add HSTS only for HTTPS connections
        if request.url.scheme == "https":
            headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; "
                "includeSubDomains; "
                "preload"
            )

        # Add CSP
        headers["Content-Security-Policy"] = self.csp_policy

        # Apply headers to response
        for header, value in headers.items():
            if value:  # Only add non-empty values
                response.headers[header] = value

        # Remove potentially sensitive headers
        response.headers.pop("Server", None)
        response.headers.pop("X-AspNet-Version", None)
        response.headers.pop("X-AspNetMvc-Version", None)

        return response


class TLSEnforcementMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce TLS 1.3 and secure cipher suites.

    Note: This is primarily informational as TLS negotiation happens
    at the reverse proxy/load balancer level. This middleware ensures
    that the application is aware of TLS requirements.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        min_tls_version: str = "1.3",
        require_tls: bool = True
    ):
        """
        Initialize TLS enforcement middleware.

        Args:
            app: ASGI application
            min_tls_version: Minimum TLS version (1.2 or 1.3)
            require_tls: Whether to require TLS for all requests
        """
        super().__init__(app)
        self.min_tls_version = min_tls_version
        self.require_tls = require_tls

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Check TLS requirements.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or error if TLS requirements not met
        """
        # Skip for health checks and local development
        if request.url.path in ["/health", "/ready", "/metrics"]:
            return await call_next(request)

        if request.client and request.client.host in ["127.0.0.1", "localhost"]:
            return await call_next(request)

        # In production, verify TLS usage
        if self.require_tls and ENVIRONMENT == "production":
            # Check if request is over HTTPS
            # In production behind reverse proxy, check X-Forwarded-Proto
            forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
            scheme = forwarded_proto or request.url.scheme

            if scheme != "https":
                return Response(
                    status_code=426,  # Upgrade Required
                    content="HTTPS required. Please use https:// instead of http://",
                    headers={
                        "Upgrade": "TLS/1.3, HTTP/1.1",
                        "Connection": "Upgrade"
                    }
                )

        return await call_next(request)


def setup_cors_middleware(app, allowed_origins: Optional[list[str]] = None):
    """
    Configure CORS middleware with secure defaults.

    Args:
        app: FastAPI application
        allowed_origins: List of allowed origins (defaults to env CORS_ORIGINS)

    Returns:
        Configured CORS middleware
    """
    if allowed_origins is None:
        allowed_origins = ALLOWED_ORIGINS

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Type",
            "Authorization",
            "X-API-Key",
            "X-Request-ID",
            "X-Requested-With"
        ],
        expose_headers=[
            "X-Request-ID",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
            "Content-Disposition"  # For file downloads
        ],
        max_age=3600  # Cache preflight for 1 hour
    )

    return app


def validate_origin(origin: str, allowed_origins: list[str]) -> bool:
    """
    Validate if origin is allowed.

    Supports wildcards like https://*.example.com

    Args:
        origin: Origin to validate
        allowed_origins: List of allowed origins (may contain wildcards)

    Returns:
        True if origin is allowed
    """
    if "*" in allowed_origins:
        return True

    # Exact match
    if origin in allowed_origins:
        return True

    # Wildcard subdomain match
    for allowed in allowed_origins:
        if "*" in allowed:
            # Convert wildcard to regex pattern
            import re
            pattern = allowed.replace(".", r"\.").replace("*", r"[^.]+")
            if re.match(f"^{pattern}$", origin):
                return True

    return False


def get_security_headers(
    include_csp: bool = True,
    include_hsts: bool = True,
    frame_options: str = "DENY"
) -> dict[str, str]:
    """
    Get recommended security headers as a dictionary.

    Useful for adding headers to specific responses.

    Args:
        include_csp: Include Content-Security-Policy
        include_hsts: Include Strict-Transport-Security
        frame_options: X-Frame-Options value

    Returns:
        Dictionary of security headers
    """
    headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": frame_options,
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), "
            "gyroscope=(), accelerometer=()"
        )
    }

    if include_csp:
        headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

    if include_hsts:
        headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )

    return headers


def sanitize_redirect_url(url: str, allowed_domains: Optional[list[str]] = None) -> Optional[str]:
    """
    Sanitize redirect URL to prevent open redirect vulnerabilities.

    Args:
        url: URL to validate
        allowed_domains: List of allowed domains for redirect

    Returns:
        Sanitized URL or None if invalid
    """
    if not url:
        return None

    # Parse URL
    parsed = urlparse(url)

    # Relative URLs are safe
    if not parsed.netloc:
        return url

    # Check against allowed domains
    if allowed_domains is None:
        allowed_domains = [urlparse(origin).netloc for origin in ALLOWED_ORIGINS]

    if parsed.netloc in allowed_domains:
        return url

    # Invalid redirect target
    return None
