# Translation Service

Multi-language translation service for backend-generated content including emails, PDFs, system notifications, and audit messages.

## Features

- **GPT-4 Powered Translation**: High-quality, context-aware translations
- **24 EU Languages Support**: Complete coverage of all EU official languages
- **Language Detection**: Automatic language detection from Accept-Language header
- **Human Review Workflow**: Priority-based review markers for quality assurance
- **Caching**: Redis-based caching for frequently used translations
- **German Business Standards**: Sie-Form compliance and DIN 5008 formatting
- **Formal/Informal Forms**: Automatic handling of formal language requirements

## Supported Languages

All 24 EU official languages:
- **Primary**: German (de), English (en)
- **Romance**: French (fr), Spanish (es), Italian (it), Portuguese (pt), Romanian (ro)
- **Germanic**: Dutch (nl), Swedish (sv), Danish (da)
- **Slavic**: Polish (pl), Czech (cs), Slovak (sk), Bulgarian (bg), Croatian (hr), Slovenian (sl)
- **Baltic**: Lithuanian (lt), Latvian (lv), Estonian (et)
- **Finno-Ugric**: Finnish (fi), Hungarian (hu)
- **Hellenic**: Greek (el)
- **Celtic**: Irish (ga)
- **Semitic**: Maltese (mt)

## Installation

```bash
pip install openai redis
```

## Configuration

Set the following environment variables:

```bash
export OPENAI_API_KEY="your-api-key"
export REDIS_URL="redis://localhost:6379/0"
```

## Usage

### Basic Translation

```python
from src.services.translation import TranslationService, TranslationRequest, TranslationPriority

# Initialize service
service = TranslationService()

# Create translation request
request = TranslationRequest(
    text="Thank you for your inquiry. We will send you an offer shortly.",
    source_language="en",
    target_language="de",
    use_formal_form=True,  # Use Sie-Form
    priority=TranslationPriority.MEDIUM
)

# Translate
response = service.translate(request)

print(response.translated_text)
# Output: "Vielen Dank für Ihre Anfrage. Wir werden Ihnen in Kürze ein Angebot zusenden."

print(f"Requires review: {response.requires_human_review}")
print(f"Confidence: {response.confidence_score}")
```

### Email Translation

```python
# Translate email with proper formatting
result = service.translate_email(
    subject="Your Offer is Ready",
    body="We have prepared a detailed offer for your project. Please review it at your convenience.",
    target_language="de",
    recipient_name="Herr Schmidt"
)

print(result["subject"])
# Output: "Ihr Angebot ist fertig"

print(result["body"])
# Output includes formal greeting and closing
```

### PDF Content Translation

```python
# Translate PDF document sections
sections = [
    {
        "title": "Work Package 1: Requirements Analysis",
        "content": "We will conduct a thorough analysis of your requirements..."
    },
    {
        "title": "Work Package 2: Implementation",
        "content": "Based on the requirements, we will implement..."
    }
]

translated_sections = service.translate_pdf_content(
    sections=sections,
    target_language="de"
)

for section in translated_sections:
    print(f"{section['title']}")
    print(f"{section['content']}")
    print(f"Requires review: {section['requires_review']}")
```

### Language Detection

```python
# Detect language from HTTP Accept-Language header
accept_language = "de-DE,de;q=0.9,en;q=0.8,fr;q=0.7"
detected_language = service.detect_language_from_header(accept_language)

print(detected_language)
# Output: "de"
```

### Using Singleton Instance

```python
from src.services.translation import get_translation_service

# Get singleton instance
service = get_translation_service()

# Use as normal
response = service.translate(request)
```

## Translation Priorities

The service supports four priority levels that determine human review requirements:

1. **LOW**: Informal notifications, no review needed
2. **MEDIUM**: Standard business communications, spot-check review
3. **HIGH**: Legal documents, contracts, requires full review
4. **CRITICAL**: Legally binding, must be reviewed before use

```python
from src.services.translation import TranslationPriority

# High priority translation (requires human review)
request = TranslationRequest(
    text="This offer constitutes a legally binding agreement...",
    target_language="de",
    priority=TranslationPriority.HIGH,
    document_type="pdf"
)

response = service.translate(request)
assert response.requires_human_review == True
```

## Caching

Translations are automatically cached in Redis for 7 days. Cache keys are generated from:
- Source and target languages
- Text content (hashed)
- Context and document type
- Formal/informal form setting

```python
# First call - translates using GPT-4
response1 = service.translate(request)
print(response1.cached)  # False

# Second call - retrieves from cache
response2 = service.translate(request)
print(response2.cached)  # True
print(response2.translation_time_ms)  # Much faster
```

## German Business Standards

The service automatically applies German business standards:

### Sie-Form (Formal Address)
```python
request = TranslationRequest(
    text="Please send us your requirements.",
    target_language="de",
    use_formal_form=True  # Default
)

# Output uses "Sie" instead of "du"
```

### DIN 5008 Formatting
- Date format: DD.MM.YYYY
- Currency: 1.234,56 €
- Number format: 1.234,56
- Formal salutations and closings

## Context-Aware Translation

Provide context for better translation quality:

```python
request = TranslationRequest(
    text="Package delivered",
    target_language="de",
    context="software_work_package",  # Not physical delivery
    document_type="pdf"
)

# Will translate as "Arbeitspaket geliefert" not "Paket zugestellt"
```

## Error Handling

```python
try:
    response = service.translate(request)
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Translation failed: {e}")
    # Service returns fallback text in case of errors
```

## Human Review Workflow

Translations marked with `requires_human_review=True` should follow this workflow:

1. **Initial Translation**: GPT-4 generates translation
2. **Review Assignment**: Assign to native speaker based on `review_priority`
3. **Quality Check**: Native speaker reviews and corrects
4. **Approval**: Mark as approved in your workflow system
5. **Cache Update**: Update cache with approved translation

```python
if response.requires_human_review:
    # Store in review queue
    review_queue.add({
        "translation_id": generate_id(),
        "text": response.translated_text,
        "priority": response.review_priority.value,
        "language": response.target_language,
        "created_at": datetime.now()
    })
```

## Performance

- **Cold start** (no cache): 2-5 seconds per translation (GPT-4 API call)
- **Warm cache**: <10ms per translation (Redis lookup)
- **Cache hit rate**: 70-80% for common translations
- **Supported throughput**: 100+ translations/minute (with caching)

## Testing

```bash
# Run tests
pytest backend/tests/unit/test_translation_service.py

# Run with coverage
pytest --cov=src/services/translation backend/tests/unit/test_translation_service.py
```

## Monitoring

The service provides metadata for monitoring:

```python
response = service.translate(request)

# Monitoring metrics
print(f"Model used: {response.metadata['model']}")
print(f"Translation time: {response.translation_time_ms}ms")
print(f"Confidence score: {response.confidence_score}")
print(f"Cache hit: {response.cached}")
```

## Integration with Other Services

### Email Service

```python
from src.services.notification import NotificationService

notification_service = NotificationService()
translation_service = get_translation_service()

# Translate email content
email_content = translation_service.translate_email(
    subject="Your offer",
    body="...",
    target_language=customer.language_preference
)

# Send translated email
notification_service.send_email(
    to=customer.email,
    subject=email_content["subject"],
    body=email_content["body"]
)
```

### PDF Generation Service

```python
from src.services.offer import PDFGenerator

pdf_generator = PDFGenerator()
translation_service = get_translation_service()

# Translate PDF sections
translated_sections = translation_service.translate_pdf_content(
    sections=offer_sections,
    target_language=customer.language_preference
)

# Generate PDF with translated content
pdf_generator.generate_offer_pdf(
    offer=offer,
    sections=translated_sections,
    language=customer.language_preference
)
```

## Future Enhancements

- [ ] Add support for custom terminology glossaries
- [ ] Implement translation memory for consistency
- [ ] Add quality metrics and A/B testing
- [ ] Support for document format preservation (HTML, Markdown)
- [ ] Real-time streaming translation for chat interfaces
- [ ] Integration with professional translation services (DeepL, etc.)

## License

Internal use only - AI Offer Agent project

## Support

For issues or questions, contact the AI Offer Agent team.

---

Last updated: 2025-10-06
