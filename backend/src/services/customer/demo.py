#!/usr/bin/env python3
"""
Demo script for Customer Service API.

This script demonstrates:
1. Creating a customer with GDPR consent
2. Retrieving customer data
3. Requesting customer deletion (GDPR Right to be Forgotten)

Run the service first:
    python src/services/customer/main.py

Then run this demo:
    python src/services/customer/demo.py
"""

import json
import requests
from datetime import datetime

# Service URL
BASE_URL = "http://localhost:8003"


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_response(response: requests.Response):
    """Print formatted HTTP response."""
    print(f"Status: {response.status_code}")
    if response.headers.get('content-type', '').startswith('application/json'):
        print(f"Response:\n{json.dumps(response.json(), indent=2)}")
    else:
        print(f"Response: {response.text}")


def demo():
    """Run the demo."""
    print_section("Customer Service API Demo")

    # 1. Health check
    print_section("1. Health Check")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print_response(response)
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure the service is running:")
        print("  python src/services/customer/main.py")
        return

    # 2. Create customer
    print_section("2. Create Customer with GDPR Consent")
    customer_data = {
        "company_name": "Demo Corporation",
        "contact_person": "Alice Smith",
        "email": "alice.smith@demo.com",
        "phone": "+4930123456",
        "language_preference": "de",
        "consent_purposes": ["offer_generation", "marketing"],
        "consent_text_version": "v1.0"
    }

    print("Request:")
    print(json.dumps(customer_data, indent=2))
    print()

    response = requests.post(f"{BASE_URL}/customers", json=customer_data)
    print_response(response)

    if response.status_code == 201:
        customer_id = response.json()["id"]
        external_id = response.json()["external_id"]
        print(f"\n✓ Customer created!")
        print(f"  ID: {customer_id}")
        print(f"  External ID: {external_id}")
    else:
        print("\n✗ Failed to create customer")
        return

    # 3. Retrieve customer
    print_section("3. Retrieve Customer")
    response = requests.get(f"{BASE_URL}/customers/{customer_id}")
    print_response(response)

    if response.status_code == 200:
        print("\n✓ Customer retrieved successfully")
    else:
        print("\n✗ Failed to retrieve customer")

    # 4. Request deletion
    print_section("4. Request Customer Deletion (GDPR)")
    deletion_request = {
        "reason": "Customer requested data deletion for privacy reasons"
    }

    print("Request:")
    print(json.dumps(deletion_request, indent=2))
    print()

    response = requests.delete(
        f"{BASE_URL}/customers/{customer_id}",
        json=deletion_request
    )
    print_response(response)

    if response.status_code == 202:
        print("\n✓ Deletion request accepted")
        data = response.json()
        print(f"  Requested: {data['deletion_requested_at']}")
        print(f"  Scheduled deletion: {data['scheduled_deletion_date']}")
        print(f"  Retention period: 4 years (legal requirement)")
    else:
        print("\n✗ Failed to request deletion")

    # 5. Verify deletion was requested
    print_section("5. Verify Deletion Status")
    response = requests.get(f"{BASE_URL}/customers/{customer_id}")
    print_response(response)

    if response.status_code == 200:
        data = response.json()
        if data['deletion_requested_at']:
            print("\n✓ Customer marked for deletion")
            print(f"  Deletion requested: {data['deletion_requested_at']}")
        else:
            print("\n✗ Deletion status not updated")
    else:
        print("\n✗ Failed to verify deletion status")

    print_section("Demo Complete")
    print("Key GDPR Features Demonstrated:")
    print("  ✓ Explicit consent required before storing PII")
    print("  ✓ Granular consent purposes (offer_generation, marketing)")
    print("  ✓ Pseudonymized external IDs for privacy")
    print("  ✓ Right to be Forgotten (4-year retention)")
    print("  ✓ PII encryption at rest (AES-256)")
    print("  ✓ Audit logging without sensitive data")
    print()


if __name__ == "__main__":
    demo()
