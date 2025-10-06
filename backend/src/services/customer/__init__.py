"""Customer service package with GDPR compliance."""

from .main import app, create_customer, delete_customer, get_customer, health_check
from .privacy import (
    AuditLogEntry,
    EncryptedData,
    PIIEncryptionService,
)

__all__ = [
    # FastAPI app and endpoints
    "app",
    "create_customer",
    "get_customer",
    "delete_customer",
    "health_check",
    # Privacy utilities
    "PIIEncryptionService",
    "EncryptedData",
    "AuditLogEntry",
]
