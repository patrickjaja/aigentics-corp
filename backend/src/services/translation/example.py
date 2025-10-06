"""
Translation Service Examples

Demonstrates usage of the translation service for various scenarios.

Run this file to see the translation service in action:
    python -m src.services.translation.example
"""

import os
from datetime import datetime

from .main import (
    TranslationService,
    TranslationRequest,
    TranslationResponse,
    TranslationPriority,
    get_translation_service
)


def example_basic_translation():
    """Example 1: Basic text translation"""
    print("\n" + "="*80)
    print("Example 1: Basic Translation")
    print("="*80)

    service = get_translation_service()

    # English to German
    request = TranslationRequest(
        text="Thank you for your interest in our services. We will contact you shortly.",
        source_language="en",
        target_language="de",
        use_formal_form=True
    )

    response = service.translate(request)

    print(f"\nOriginal (EN): {request.text}")
    print(f"Translated (DE): {response.translated_text}")
    print(f"Confidence: {response.confidence_score:.2%}")
    print(f"Requires review: {response.requires_human_review}")
    print(f"Time: {response.translation_time_ms}ms")


def example_email_translation():
    """Example 2: Email translation with formal greeting"""
    print("\n" + "="*80)
    print("Example 2: Email Translation")
    print("="*80)

    service = get_translation_service()

    subject = "Your IT Consulting Offer - Ref: 25-0042"
    body = """We have prepared a comprehensive offer for your software development project.

The offer includes:
- Detailed project scope and requirements analysis
- Work package breakdown with hour estimates
- Timeline and milestone planning
- Terms and conditions

Please review the attached PDF document and let us know if you have any questions.

We look forward to working with you on this exciting project."""

    result = service.translate_email(
        subject=subject,
        body=body,
        target_language="de",
        recipient_name="Herr Schmidt"
    )

    print(f"\nOriginal Subject: {subject}")
    print(f"Translated Subject: {result['subject']}")
    print(f"\nOriginal Body:\n{body}")
    print(f"\nTranslated Body:\n{result['body']}")
    print(f"\nRequires review: {result['requires_review']}")


def example_pdf_content_translation():
    """Example 3: PDF document sections translation"""
    print("\n" + "="*80)
    print("Example 3: PDF Content Translation")
    print("="*80)

    service = get_translation_service()

    sections = [
        {
            "title": "Work Package 1: Requirements Analysis",
            "content": """We will conduct a comprehensive analysis of your business requirements:
- Stakeholder interviews
- Current system assessment
- Gap analysis
- Requirements documentation"""
        },
        {
            "title": "Work Package 2: System Design",
            "content": """Based on the requirements, we will create a detailed system design:
- Architecture diagrams
- Database schema design
- API specifications
- User interface mockups"""
        },
        {
            "title": "Work Package 3: Implementation",
            "content": """We will implement the system according to the approved design:
- Backend development (Python/FastAPI)
- Frontend development (React/Next.js)
- Database setup and migration
- Integration with third-party services"""
        }
    ]

    translated_sections = service.translate_pdf_content(
        sections=sections,
        target_language="de"
    )

    for i, section in enumerate(translated_sections, 1):
        print(f"\n--- Section {i} ---")
        print(f"Title: {section['title']}")
        print(f"Content: {section['content'][:100]}...")
        print(f"Requires review: {section['requires_review']}")


def example_language_detection():
    """Example 4: Language detection from Accept-Language header"""
    print("\n" + "="*80)
    print("Example 4: Language Detection")
    print("="*80)

    service = get_translation_service()

    test_headers = [
        "de-DE,de;q=0.9,en;q=0.8",
        "en-US,en;q=0.9",
        "fr-FR,fr;q=0.9,en;q=0.8",
        "es-ES,es;q=0.9,ca;q=0.8,en;q=0.7",
        "pl-PL,pl;q=0.9,en;q=0.8",
    ]

    for header in test_headers:
        detected = service.detect_language_from_header(header)
        print(f"\nAccept-Language: {header}")
        print(f"Detected: {detected}")


def example_multi_language_translation():
    """Example 5: Translate to multiple languages"""
    print("\n" + "="*80)
    print("Example 5: Multi-Language Translation")
    print("="*80)

    service = get_translation_service()

    original_text = "Your offer has been successfully generated and is ready for download."

    target_languages = ["de", "fr", "es", "it", "pl"]

    print(f"\nOriginal (EN): {original_text}\n")

    for lang in target_languages:
        request = TranslationRequest(
            text=original_text,
            source_language="en",
            target_language=lang,
            use_formal_form=True
        )

        response = service.translate(request)
        print(f"{lang.upper()}: {response.translated_text}")


def example_context_aware_translation():
    """Example 6: Context-aware translation"""
    print("\n" + "="*80)
    print("Example 6: Context-Aware Translation")
    print("="*80)

    service = get_translation_service()

    # Same word, different contexts
    text = "Package delivered"

    # Context 1: Software work package
    request1 = TranslationRequest(
        text=text,
        target_language="de",
        context="software_work_package",
        document_type="pdf"
    )
    response1 = service.translate(request1)

    # Context 2: Physical delivery
    request2 = TranslationRequest(
        text=text,
        target_language="de",
        context="shipping_notification",
        document_type="email"
    )
    response2 = service.translate(request2)

    print(f"\nOriginal: {text}")
    print(f"\nWith context 'software_work_package': {response1.translated_text}")
    print(f"With context 'shipping_notification': {response2.translated_text}")


def example_priority_based_review():
    """Example 7: Priority-based human review"""
    print("\n" + "="*80)
    print("Example 7: Priority-Based Human Review")
    print("="*80)

    service = get_translation_service()

    test_cases = [
        (
            "Welcome to our platform!",
            TranslationPriority.LOW,
            "notification"
        ),
        (
            "Your project offer includes detailed work packages and pricing.",
            TranslationPriority.MEDIUM,
            "email"
        ),
        (
            "This agreement constitutes a legally binding contract between the parties.",
            TranslationPriority.HIGH,
            "pdf"
        ),
        (
            "By signing below, you agree to all terms and conditions stated herein.",
            TranslationPriority.CRITICAL,
            "contract"
        )
    ]

    for text, priority, doc_type in test_cases:
        request = TranslationRequest(
            text=text,
            target_language="de",
            priority=priority,
            document_type=doc_type
        )

        response = service.translate(request)

        print(f"\nText: {text[:60]}...")
        print(f"Priority: {priority.value}")
        print(f"Requires review: {response.requires_human_review}")
        print(f"Confidence: {response.confidence_score:.2%}")


def example_caching():
    """Example 8: Caching demonstration"""
    print("\n" + "="*80)
    print("Example 8: Caching Performance")
    print("="*80)

    service = get_translation_service()

    request = TranslationRequest(
        text="This is a test of the caching system.",
        target_language="de"
    )

    # First call - no cache
    print("\nFirst translation (cold start):")
    response1 = service.translate(request)
    print(f"Cached: {response1.cached}")
    print(f"Time: {response1.translation_time_ms}ms")

    # Second call - should use cache
    print("\nSecond translation (cache hit):")
    response2 = service.translate(request)
    print(f"Cached: {response2.cached}")
    print(f"Time: {response2.translation_time_ms}ms")

    if response2.cached:
        speedup = response1.translation_time_ms / max(response2.translation_time_ms, 1)
        print(f"\nSpeed improvement: {speedup:.1f}x faster")


def example_formal_vs_informal():
    """Example 9: Formal vs informal translation"""
    print("\n" + "="*80)
    print("Example 9: Formal vs Informal Forms")
    print("="*80)

    service = get_translation_service()

    text = "Please send us your requirements and we will prepare an offer for you."

    # Formal (Sie-Form)
    formal_request = TranslationRequest(
        text=text,
        target_language="de",
        use_formal_form=True
    )
    formal_response = service.translate(formal_request)

    # Note: For informal, we would need to adjust the prompt
    # This is just to show the structure
    print(f"\nOriginal: {text}")
    print(f"\nFormal (Sie-Form): {formal_response.translated_text}")
    print("\nNote: The service uses formal form by default for business contexts")


def run_all_examples():
    """Run all examples"""
    print("\n" + "="*80)
    print("TRANSLATION SERVICE EXAMPLES")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"OpenAI API Key configured: {bool(os.getenv('OPENAI_API_KEY'))}")
    print(f"Redis configured: {bool(os.getenv('REDIS_URL'))}")

    try:
        example_basic_translation()
        example_email_translation()
        example_pdf_content_translation()
        example_language_detection()
        example_multi_language_translation()
        example_context_aware_translation()
        example_priority_based_review()
        example_caching()
        example_formal_vs_informal()

        print("\n" + "="*80)
        print("All examples completed successfully!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"\n\nError running examples: {e}")
        print("\nNote: Make sure OPENAI_API_KEY is set in your environment")
        print("      export OPENAI_API_KEY='your-key-here'")


if __name__ == "__main__":
    run_all_examples()
