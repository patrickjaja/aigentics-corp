"""
Authentication Middleware for API Gateway

Handles API key validation for external agents and JWT validation for internal admin users.
This is a convenience wrapper that imports from infrastructure middleware.
"""

# Import from infrastructure middleware (single source of truth)
from ..infrastructure.middleware.auth import (
    verify_api_key,
    verify_jwt_token,
    get_user_from_token,
    has_role,
    require_role,
    API_KEY_HEADER,
    VALID_API_KEYS,
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    KEYCLOAK_ISSUER
)

__all__ = [
    "verify_api_key",
    "verify_jwt_token",
    "get_user_from_token",
    "has_role",
    "require_role",
    "API_KEY_HEADER",
    "VALID_API_KEYS",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "KEYCLOAK_ISSUER"
]
