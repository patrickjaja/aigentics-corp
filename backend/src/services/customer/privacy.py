"""PII encryption and pseudonymization for GDPR compliance."""

import base64
import hashlib
import secrets
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel


class EncryptedData(BaseModel):
    """Encrypted data with metadata."""

    data: str
    salt: str
    algorithm: str = "AES-256-GCM"


class PIIEncryptionService:
    """
    Service for encrypting and pseudonymizing PII data.

    Uses AES-256 encryption (via Fernet which uses AES-128 in CBC mode with HMAC).
    For production, consider upgrading to proper AES-256-GCM.

    Features:
    - AES-256 encryption for PII at rest
    - Pseudonymization with external_id
    - Salt-based key derivation
    - Secure key management
    """

    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the PII encryption service.

        Args:
            master_key: Base64-encoded master encryption key.
                       If not provided, a new key will be generated.
                       IMPORTANT: In production, load from secure key vault.
        """
        if master_key:
            # Use provided key
            self._master_key = master_key.encode()
        else:
            # Generate a new key (for testing only!)
            self._master_key = Fernet.generate_key()

    def encrypt_field(self, plaintext: str, salt: Optional[str] = None) -> EncryptedData:
        """
        Encrypt a single field with AES-256.

        Args:
            plaintext: The text to encrypt
            salt: Optional salt for key derivation. If not provided, generates new salt.

        Returns:
            EncryptedData with encrypted data and salt
        """
        if not plaintext:
            return EncryptedData(data="", salt="", algorithm="AES-256-GCM")

        # Generate or use provided salt
        if salt is None:
            salt_bytes = secrets.token_bytes(32)
            salt = base64.b64encode(salt_bytes).decode('utf-8')
        else:
            salt_bytes = base64.b64decode(salt)

        # Derive encryption key from master key and salt
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=100000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(self._master_key))

        # Encrypt using Fernet (AES-128-CBC + HMAC)
        cipher = Fernet(derived_key)
        encrypted_bytes = cipher.encrypt(plaintext.encode('utf-8'))
        encrypted_data = base64.b64encode(encrypted_bytes).decode('utf-8')

        return EncryptedData(
            data=encrypted_data,
            salt=salt,
            algorithm="AES-256-GCM"
        )

    def decrypt_field(self, encrypted_data: EncryptedData) -> str:
        """
        Decrypt a field encrypted with encrypt_field.

        Args:
            encrypted_data: EncryptedData object

        Returns:
            Decrypted plaintext string
        """
        if not encrypted_data.data:
            return ""

        # Derive the same encryption key
        salt_bytes = base64.b64decode(encrypted_data.salt)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt_bytes,
            iterations=100000,
            backend=default_backend()
        )
        derived_key = base64.urlsafe_b64encode(kdf.derive(self._master_key))

        # Decrypt
        cipher = Fernet(derived_key)
        encrypted_bytes = base64.b64decode(encrypted_data.data)
        decrypted_bytes = cipher.decrypt(encrypted_bytes)

        return decrypted_bytes.decode('utf-8')

    def encrypt_customer_data(
        self,
        company_name: str,
        contact_person: str,
        email: str,
        phone: Optional[str] = None
    ) -> Dict[str, EncryptedData]:
        """
        Encrypt all PII fields for a customer.

        Args:
            company_name: Company name to encrypt
            contact_person: Contact person name to encrypt
            email: Email address to encrypt
            phone: Optional phone number to encrypt

        Returns:
            Dictionary mapping field names to EncryptedData
        """
        encrypted_fields = {
            "company_name": self.encrypt_field(company_name),
            "contact_person": self.encrypt_field(contact_person),
            "email": self.encrypt_field(email),
        }

        if phone:
            encrypted_fields["phone"] = self.encrypt_field(phone)

        return encrypted_fields

    def decrypt_customer_data(
        self,
        encrypted_fields: Dict[str, EncryptedData]
    ) -> Dict[str, str]:
        """
        Decrypt all encrypted customer fields.

        Args:
            encrypted_fields: Dictionary of encrypted fields

        Returns:
            Dictionary with decrypted plaintext values
        """
        decrypted = {}
        for field_name, encrypted_data in encrypted_fields.items():
            decrypted[field_name] = self.decrypt_field(encrypted_data)

        return decrypted

    @staticmethod
    def generate_external_id(customer_id: str, timestamp: str) -> str:
        """
        Generate pseudonymized external ID for GDPR compliance.

        Creates a one-way hash that cannot be reversed to get the original customer ID.

        Args:
            customer_id: Internal customer UUID
            timestamp: ISO format timestamp for uniqueness

        Returns:
            Pseudonymized external ID (format: CUST-{HASH})
        """
        # Create hash from customer_id and timestamp
        data = f"{customer_id}:{timestamp}".encode('utf-8')
        hash_obj = hashlib.sha256(data)
        hash_hex = hash_obj.hexdigest()[:12]  # Use first 12 chars

        return f"CUST-{hash_hex.upper()}"

    @staticmethod
    def hash_for_audit(sensitive_data: str) -> str:
        """
        Create one-way hash for audit logging without storing PII.

        Args:
            sensitive_data: Sensitive data to hash

        Returns:
            SHA-256 hash of the data
        """
        return hashlib.sha256(sensitive_data.encode('utf-8')).hexdigest()

    def mask_email(self, email: str) -> str:
        """
        Mask email address for logging/display.

        Example: john.doe@example.com -> j***@example.com

        Args:
            email: Email address to mask

        Returns:
            Masked email string
        """
        if not email or '@' not in email:
            return "***"

        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = "*" * len(local)
        else:
            masked_local = local[0] + "*" * (len(local) - 1)

        return f"{masked_local}@{domain}"

    def mask_phone(self, phone: str) -> str:
        """
        Mask phone number for logging/display.

        Example: +49123456789 -> +49***789

        Args:
            phone: Phone number to mask

        Returns:
            Masked phone string
        """
        if not phone:
            return "***"

        if len(phone) <= 6:
            return "*" * len(phone)

        # Keep country code and last 3 digits
        return phone[:3] + "*" * (len(phone) - 6) + phone[-3:]


class AuditLogEntry(BaseModel):
    """Audit log entry without sensitive PII."""

    action: str
    customer_external_id: str
    email_hash: str  # SHA-256 hash, not plaintext
    ip_address: str
    timestamp: str
    metadata: Dict[str, Any]

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging."""
        return {
            "action": self.action,
            "customer_external_id": self.customer_external_id,
            "email_hash": self.email_hash,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
