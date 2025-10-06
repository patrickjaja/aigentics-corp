"""
Authentication Middleware

Handles API key validation for external agents and JWT validation for internal admin users.
"""

from typing import Optional
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt
import os


# Configuration
API_KEY_HEADER = "X-API-Key"
VALID_API_KEYS = os.getenv("VALID_API_KEYS", "").split(",")  # Comma-separated list
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
KEYCLOAK_ISSUER = os.getenv("KEYCLOAK_ISSUER", "https://keycloak.example.com/realms/offer-agent")


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Verify API key for external agent authentication.

    Used for conversation and offer APIs where external systems integrate.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        Validated API key

    Raises:
        HTTPException: 401 if API key is invalid
    """
    # TODO: In production, validate against database or cache
    # For now, check against environment variable list
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "API_KEY_MISSING",
                "message": "X-API-Key header is required"
            }
        )

    # Simple validation for now
    # TODO: Implement proper API key validation with database lookup
    # - Check if key exists and is active
    # - Check rate limits per key
    # - Log usage for billing/monitoring
    if x_api_key not in VALID_API_KEYS and len(VALID_API_KEYS) > 0 and VALID_API_KEYS[0]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_API_KEY",
                "message": "Invalid API key provided"
            }
        )

    return x_api_key


async def verify_jwt_token(authorization: str = Header(..., alias="Authorization")) -> dict:
    """
    Verify JWT token for internal admin authentication.

    Used for admin APIs where sales managers and administrators access the system.
    Integrates with Keycloak for identity management.

    Args:
        authorization: Bearer token from Authorization header

    Returns:
        Decoded JWT payload with user claims

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "TOKEN_MISSING",
                "message": "Authorization header is required"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Extract bearer token
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "INVALID_TOKEN_FORMAT",
                "message": "Authorization header must be in format: Bearer <token>"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = parts[1]

    try:
        # TODO: In production, integrate with Keycloak for token validation
        # - Verify signature using Keycloak public key
        # - Check token expiration
        # - Validate issuer and audience
        # - Check user roles and permissions

        # For now, decode without verification (DEV ONLY)
        payload = jwt.decode(
            token,
            JWT_SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"verify_signature": False}  # TODO: Enable in production
        )

        # Validate required claims
        if "sub" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": "INVALID_TOKEN_CLAIMS",
                    "message": "Token missing required claims"
                },
                headers={"WWW-Authenticate": "Bearer"}
            )

        return payload

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": "TOKEN_VALIDATION_FAILED",
                "message": f"Failed to validate token: {str(e)}"
            },
            headers={"WWW-Authenticate": "Bearer"}
        )


def get_user_from_token(payload: dict) -> dict:
    """
    Extract user information from JWT payload.

    Args:
        payload: Decoded JWT token payload

    Returns:
        User information dict with id, email, roles, etc.
    """
    return {
        "user_id": payload.get("sub"),
        "email": payload.get("email"),
        "name": payload.get("name"),
        "roles": payload.get("realm_access", {}).get("roles", []),
        "preferred_username": payload.get("preferred_username")
    }


def has_role(payload: dict, required_role: str) -> bool:
    """
    Check if user has a specific role.

    Args:
        payload: Decoded JWT token payload
        required_role: Role to check for (e.g., "sales_manager", "admin")

    Returns:
        True if user has the role
    """
    user_roles = payload.get("realm_access", {}).get("roles", [])
    return required_role in user_roles


def require_role(required_role: str):
    """
    Dependency that requires a specific role.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])

    Args:
        required_role: Role required to access the endpoint

    Returns:
        Dependency function
    """
    async def role_checker(payload: dict = Depends(verify_jwt_token)) -> dict:
        if not has_role(payload, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Role '{required_role}' is required"
                }
            )
        return payload

    return role_checker
