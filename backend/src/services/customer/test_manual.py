#!/usr/bin/env python3
"""Manual test script for Customer Service."""

import asyncio
import sys
from datetime import datetime
from uuid import uuid4

# Add parent directory to path for imports
sys.path.insert(0, '/home/patrickjaja/development/aigentics-corp/aigentics-corp/backend')

from src.models.customer import ConsentPurpose, Customer, GDPRConsent
from src.models.value_objects import EmailAddress, LanguageCode, PhoneNumber
from src.services.customer.privacy import PIIEncryptionService


def test_encryption_service():
    """Test PII encryption and decryption."""
    print("\n=== Testing PII Encryption Service ===\n")

    # Initialize service
    service = PIIEncryptionService()

    # Test single field encryption
    print("1. Testing single field encryption:")
    plaintext = "john.doe@example.com"
    encrypted = service.encrypt_field(plaintext)
    print(f"   Original: {plaintext}")
    print(f"   Encrypted: {encrypted.data[:50]}...")
    print(f"   Salt: {encrypted.salt[:20]}...")

    # Test decryption
    decrypted = service.decrypt_field(encrypted)
    print(f"   Decrypted: {decrypted}")
    assert decrypted == plaintext, "Decryption failed!"
    print("   ✓ Encryption/Decryption successful\n")

    # Test customer data encryption
    print("2. Testing customer data encryption:")
    encrypted_fields = service.encrypt_customer_data(
        company_name="Acme Corporation",
        contact_person="Jane Doe",
        email="jane.doe@acme.com",
        phone="+49123456789"
    )
    print(f"   Encrypted fields: {list(encrypted_fields.keys())}")

    # Test decryption
    decrypted_fields = service.decrypt_customer_data(encrypted_fields)
    print(f"   Decrypted company_name: {decrypted_fields['company_name']}")
    print(f"   Decrypted email: {decrypted_fields['email']}")
    assert decrypted_fields['company_name'] == "Acme Corporation"
    assert decrypted_fields['email'] == "jane.doe@acme.com"
    print("   ✓ Customer data encryption/decryption successful\n")

    # Test external ID generation
    print("3. Testing external ID generation:")
    customer_id = str(uuid4())
    timestamp = datetime.utcnow().isoformat()
    external_id = service.generate_external_id(customer_id, timestamp)
    print(f"   Customer ID: {customer_id}")
    print(f"   External ID: {external_id}")
    assert external_id.startswith("CUST-"), "External ID format incorrect!"
    print("   ✓ External ID generation successful\n")

    # Test data masking
    print("4. Testing data masking:")
    email = "john.doe@example.com"
    masked_email = service.mask_email(email)
    print(f"   Original email: {email}")
    print(f"   Masked email: {masked_email}")
    assert masked_email.startswith("j*"), "Email masking incorrect!"
    assert "@example.com" in masked_email, "Email domain should be visible!"

    phone = "+49123456789"
    masked_phone = service.mask_phone(phone)
    print(f"   Original phone: {phone}")
    print(f"   Masked phone: {masked_phone}")
    print("   ✓ Data masking successful\n")

    # Test audit hashing
    print("5. Testing audit hashing:")
    sensitive_data = "john.doe@example.com"
    hash1 = service.hash_for_audit(sensitive_data)
    hash2 = service.hash_for_audit(sensitive_data)
    print(f"   Data: {sensitive_data}")
    print(f"   Hash: {hash1[:20]}...")
    assert hash1 == hash2, "Hashing not deterministic!"
    print("   ✓ Audit hashing successful\n")


def test_customer_model():
    """Test Customer domain model."""
    print("\n=== Testing Customer Domain Model ===\n")

    # Create GDPR consent
    consent = GDPRConsent(
        given_at=datetime.utcnow(),
        ip_address="192.168.1.1",
        consent_text_version="v1.0",
        purposes=[ConsentPurpose.OFFER_GENERATION, ConsentPurpose.MARKETING],
        withdrawn_at=None
    )
    print(f"1. GDPR Consent created with purposes: {[p.value for p in consent.purposes]}")

    # Create customer
    customer = Customer(
        id=uuid4(),
        external_id="CUST-TEST123",
        company_name="Test Corporation",
        contact_person="John Doe",
        email=EmailAddress(value="john.doe@test.com"),
        phone=PhoneNumber.from_string("+4930123456"),
        language_preference=LanguageCode(code="de"),
        gdpr_consent=consent,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deletion_requested_at=None
    )
    print(f"2. Customer created: {customer.external_id}")
    print(f"   Email: {customer.email.value}")
    print(f"   Language: {customer.language_preference.code}")
    print(f"   Has active consent: {customer.has_active_consent()}")

    # Test consent checking
    assert customer.has_active_consent(), "Should have active consent"
    assert customer.has_consent_for_purpose(ConsentPurpose.OFFER_GENERATION)
    assert customer.has_consent_for_purpose(ConsentPurpose.MARKETING)
    assert not customer.has_consent_for_purpose(ConsentPurpose.ANALYTICS)
    print("   ✓ Consent checking successful\n")

    # Test consent withdrawal
    print("3. Testing consent withdrawal:")
    customer.withdraw_consent()
    print(f"   Consent withdrawn: {customer.gdpr_consent.withdrawn_at is not None}")
    assert not customer.has_active_consent(), "Should not have active consent after withdrawal"
    print("   ✓ Consent withdrawal successful\n")

    # Test deletion request
    print("4. Testing deletion request:")
    customer.request_deletion()
    print(f"   Deletion requested: {customer.deletion_requested_at is not None}")
    assert customer.deletion_requested_at is not None, "Deletion should be requested"
    print("   ✓ Deletion request successful\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Customer Service Manual Tests")
    print("=" * 60)

    try:
        test_encryption_service()
        test_customer_model()

        print("=" * 60)
        print("✓ All tests passed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
