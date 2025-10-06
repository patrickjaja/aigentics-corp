"""
Translation Service for Backend Messages

Handles translation of backend-generated content including:
- Email messages
- PDF documents
- System notifications
- Audit trail messages

Features:
- GPT-4 powered translation with context awareness
- Language detection from Accept-Language header
- Human review workflow markers for critical translations
- Caching for frequently used translations
- German business standards compliance (Sie-Form, DIN 5008)

Author: AI Offer Agent Team
Date: 2025-10-06
"""

import os
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

# External dependencies
try:
    import openai
    from openai import OpenAI
except ImportError:
    openai = None
    OpenAI = None

# Internal dependencies
import redis
from redis import Redis


class TranslationPriority(Enum):
    """Translation priority levels for human review workflow"""
    LOW = "low"  # Informal notifications, no review needed
    MEDIUM = "medium"  # Standard business communications, spot-check review
    HIGH = "high"  # Legal documents, contracts, requires full review
    CRITICAL = "critical"  # Legally binding, must be reviewed before use


class SupportedLanguage(Enum):
    """All 24 EU official languages"""
    DE = "de"  # German (primary)
    EN = "en"  # English (primary)
    FR = "fr"  # French
    ES = "es"  # Spanish
    IT = "it"  # Italian
    NL = "nl"  # Dutch
    PL = "pl"  # Polish
    PT = "pt"  # Portuguese
    CS = "cs"  # Czech
    DA = "da"  # Danish
    EL = "el"  # Greek
    HU = "hu"  # Hungarian
    RO = "ro"  # Romanian
    SV = "sv"  # Swedish
    BG = "bg"  # Bulgarian
    HR = "hr"  # Croatian
    ET = "et"  # Estonian
    FI = "fi"  # Finnish
    GA = "ga"  # Irish
    LT = "lt"  # Lithuanian
    LV = "lv"  # Latvian
    MT = "mt"  # Maltese
    SK = "sk"  # Slovak
    SL = "sl"  # Slovenian


@dataclass
class TranslationRequest:
    """Translation request structure"""
    text: str
    source_language: str = "en"
    target_language: str = "de"
    context: Optional[str] = None
    priority: TranslationPriority = TranslationPriority.MEDIUM
    use_formal_form: bool = True  # Sie-Form for German
    document_type: Optional[str] = None  # email, pdf, notification, audit
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranslationResponse:
    """Translation response structure"""
    translated_text: str
    source_language: str
    target_language: str
    confidence_score: float
    requires_human_review: bool
    review_priority: TranslationPriority
    cached: bool
    translation_time_ms: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class TranslationService:
    """
    Multi-language translation service for backend operations

    Uses GPT-4 for high-quality translations with context awareness.
    Implements caching and human review workflow markers.
    """

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        redis_client: Optional[Redis] = None,
        cache_ttl_seconds: int = 86400 * 7,  # 7 days
        model: str = "gpt-4"
    ):
        """
        Initialize translation service

        Args:
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            redis_client: Redis client for caching (optional)
            cache_ttl_seconds: Cache TTL in seconds (default 7 days)
            model: OpenAI model to use (default gpt-4)
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key and OpenAI:
            raise ValueError("OpenAI API key is required")

        self.client = OpenAI(api_key=self.api_key) if OpenAI and self.api_key else None
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl_seconds
        self.model = model

        # Language-specific settings
        self.formal_languages = {"de", "fr", "es", "it", "nl", "pl", "pt"}

    def translate(self, request: TranslationRequest) -> TranslationResponse:
        """
        Translate text from source to target language

        Args:
            request: TranslationRequest with text and parameters

        Returns:
            TranslationResponse with translated text and metadata
        """
        start_time = datetime.now()

        # Check cache first
        cache_key = self._generate_cache_key(request)
        cached_translation = self._get_cached_translation(cache_key)
        if cached_translation:
            translation_time = (datetime.now() - start_time).microseconds // 1000
            cached_translation.translation_time_ms = translation_time
            cached_translation.cached = True
            return cached_translation

        # Perform translation using GPT-4
        translated_text = self._translate_with_gpt4(request)

        # Determine if human review is required
        requires_review = self._requires_human_review(request)

        # Calculate confidence score (simplified - in production use more sophisticated method)
        confidence = self._calculate_confidence(request, translated_text)

        # Build response
        translation_time = (datetime.now() - start_time).microseconds // 1000
        response = TranslationResponse(
            translated_text=translated_text,
            source_language=request.source_language,
            target_language=request.target_language,
            confidence_score=confidence,
            requires_human_review=requires_review,
            review_priority=request.priority,
            cached=False,
            translation_time_ms=translation_time,
            metadata={
                "model": self.model,
                "timestamp": datetime.now().isoformat(),
                "document_type": request.document_type,
                "formal_form": request.use_formal_form,
            }
        )

        # Cache the translation
        self._cache_translation(cache_key, response)

        return response

    def translate_email(
        self,
        subject: str,
        body: str,
        target_language: str = "de",
        recipient_name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Translate email with proper formatting

        Args:
            subject: Email subject
            body: Email body
            target_language: Target language code
            recipient_name: Recipient name for personalization

        Returns:
            Dict with translated subject and body
        """
        # Translate subject
        subject_request = TranslationRequest(
            text=subject,
            target_language=target_language,
            context="email_subject",
            priority=TranslationPriority.MEDIUM,
            document_type="email"
        )
        subject_response = self.translate(subject_request)

        # Translate body with formal greeting
        body_with_greeting = self._add_formal_greeting(body, target_language, recipient_name)
        body_request = TranslationRequest(
            text=body_with_greeting,
            target_language=target_language,
            context="email_body",
            priority=TranslationPriority.MEDIUM,
            document_type="email",
            use_formal_form=True
        )
        body_response = self.translate(body_request)

        return {
            "subject": subject_response.translated_text,
            "body": body_response.translated_text,
            "requires_review": subject_response.requires_human_review or body_response.requires_human_review
        }

    def translate_pdf_content(
        self,
        sections: List[Dict[str, str]],
        target_language: str = "de"
    ) -> List[Dict[str, str]]:
        """
        Translate PDF document sections

        Args:
            sections: List of sections with title and content
            target_language: Target language code

        Returns:
            List of translated sections
        """
        translated_sections = []

        for section in sections:
            title_request = TranslationRequest(
                text=section.get("title", ""),
                target_language=target_language,
                context="pdf_section_title",
                priority=TranslationPriority.HIGH,
                document_type="pdf"
            )
            title_response = self.translate(title_request)

            content_request = TranslationRequest(
                text=section.get("content", ""),
                target_language=target_language,
                context=f"pdf_section_content: {section.get('title', '')}",
                priority=TranslationPriority.HIGH,
                document_type="pdf"
            )
            content_response = self.translate(content_request)

            translated_sections.append({
                "title": title_response.translated_text,
                "content": content_response.translated_text,
                "requires_review": title_response.requires_human_review or content_response.requires_human_review
            })

        return translated_sections

    def detect_language_from_header(self, accept_language_header: str) -> str:
        """
        Detect preferred language from Accept-Language header

        Args:
            accept_language_header: Accept-Language header value

        Returns:
            Detected language code (defaults to 'de')
        """
        if not accept_language_header:
            return "de"

        # Parse Accept-Language header (e.g., "de-DE,de;q=0.9,en;q=0.8")
        languages = []
        for lang_spec in accept_language_header.split(","):
            parts = lang_spec.strip().split(";")
            lang = parts[0].split("-")[0].lower()
            quality = 1.0
            if len(parts) > 1 and parts[1].startswith("q="):
                try:
                    quality = float(parts[1][2:])
                except ValueError:
                    quality = 1.0
            languages.append((lang, quality))

        # Sort by quality and find first supported language
        languages.sort(key=lambda x: x[1], reverse=True)
        for lang, _ in languages:
            if lang in [l.value for l in SupportedLanguage]:
                return lang

        # Default to German
        return "de"

    def _translate_with_gpt4(self, request: TranslationRequest) -> str:
        """
        Perform translation using GPT-4

        Args:
            request: Translation request

        Returns:
            Translated text
        """
        if not self.client:
            # Fallback for testing without API key
            return f"[TRANSLATED to {request.target_language}] {request.text}"

        # Build context-aware prompt
        formal_instruction = ""
        if request.use_formal_form and request.target_language in self.formal_languages:
            if request.target_language == "de":
                formal_instruction = "\nIMPORTANT: Use formal German (Sie-Form), NOT informal (du-Form). This is for business communication."
            else:
                formal_instruction = f"\nIMPORTANT: Use formal/polite form in {request.target_language}."

        context_instruction = ""
        if request.context:
            context_instruction = f"\nContext: {request.context}"

        document_type_instruction = ""
        if request.document_type:
            document_type_instruction = f"\nThis is a {request.document_type} document."

        system_prompt = f"""You are a professional translator specializing in business and legal translations.
Translate the following text from {request.source_language} to {request.target_language}.
{formal_instruction}{context_instruction}{document_type_instruction}

Requirements:
- Maintain the original meaning and tone
- Use appropriate business language
- Preserve formatting (line breaks, bullet points, etc.)
- Do not add or remove content
- For German: Follow DIN 5008 standards for business communication

Only respond with the translated text, nothing else."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request.text}
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=4000
            )

            translated_text = response.choices[0].message.content.strip()
            return translated_text

        except Exception as e:
            # Log error and return fallback
            print(f"Translation error: {e}")
            return f"[TRANSLATION ERROR] {request.text}"

    def _requires_human_review(self, request: TranslationRequest) -> bool:
        """
        Determine if translation requires human review

        Args:
            request: Translation request

        Returns:
            True if human review is required
        """
        # Always require review for high priority and critical translations
        if request.priority in [TranslationPriority.HIGH, TranslationPriority.CRITICAL]:
            return True

        # Require review for PDF documents
        if request.document_type == "pdf":
            return True

        # Require review for long texts (>500 words)
        word_count = len(request.text.split())
        if word_count > 500:
            return True

        return False

    def _calculate_confidence(self, request: TranslationRequest, translated_text: str) -> float:
        """
        Calculate translation confidence score

        Args:
            request: Translation request
            translated_text: Translated text

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Simplified confidence calculation
        # In production, use more sophisticated metrics

        base_confidence = 0.85

        # Reduce confidence for long texts
        word_count = len(request.text.split())
        if word_count > 1000:
            base_confidence -= 0.15
        elif word_count > 500:
            base_confidence -= 0.10

        # Reduce confidence for less common languages
        uncommon_languages = {"ga", "mt"}  # Irish, Maltese
        if request.target_language in uncommon_languages:
            base_confidence -= 0.10

        # Increase confidence if context is provided
        if request.context:
            base_confidence += 0.05

        return max(0.0, min(1.0, base_confidence))

    def _generate_cache_key(self, request: TranslationRequest) -> str:
        """
        Generate cache key for translation request

        Args:
            request: Translation request

        Returns:
            Cache key string
        """
        key_parts = [
            request.text,
            request.source_language,
            request.target_language,
            str(request.use_formal_form),
            request.context or "",
            request.document_type or ""
        ]
        key_string = "|".join(key_parts)
        key_hash = hashlib.sha256(key_string.encode()).hexdigest()
        return f"translation:{key_hash}"

    def _get_cached_translation(self, cache_key: str) -> Optional[TranslationResponse]:
        """
        Get cached translation if available

        Args:
            cache_key: Cache key

        Returns:
            Cached TranslationResponse or None
        """
        if not self.redis_client:
            return None

        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                return TranslationResponse(
                    translated_text=data["translated_text"],
                    source_language=data["source_language"],
                    target_language=data["target_language"],
                    confidence_score=data["confidence_score"],
                    requires_human_review=data["requires_human_review"],
                    review_priority=TranslationPriority(data["review_priority"]),
                    cached=True,
                    translation_time_ms=0,
                    metadata=data.get("metadata", {})
                )
        except Exception as e:
            print(f"Cache retrieval error: {e}")

        return None

    def _cache_translation(self, cache_key: str, response: TranslationResponse) -> None:
        """
        Cache translation response

        Args:
            cache_key: Cache key
            response: Translation response to cache
        """
        if not self.redis_client:
            return

        try:
            cache_data = {
                "translated_text": response.translated_text,
                "source_language": response.source_language,
                "target_language": response.target_language,
                "confidence_score": response.confidence_score,
                "requires_human_review": response.requires_human_review,
                "review_priority": response.review_priority.value,
                "metadata": response.metadata
            }
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(cache_data)
            )
        except Exception as e:
            print(f"Cache storage error: {e}")

    def _add_formal_greeting(
        self,
        body: str,
        language: str,
        recipient_name: Optional[str] = None
    ) -> str:
        """
        Add formal greeting to email body based on language

        Args:
            body: Email body
            language: Target language
            recipient_name: Recipient name

        Returns:
            Email body with formal greeting
        """
        greetings = {
            "de": "Sehr geehrte Damen und Herren," if not recipient_name else f"Sehr geehrte/r {recipient_name},",
            "en": "Dear Sir/Madam," if not recipient_name else f"Dear {recipient_name},",
            "fr": "Madame, Monsieur," if not recipient_name else f"Madame/Monsieur {recipient_name},",
            "es": "Estimado/a Señor/a," if not recipient_name else f"Estimado/a {recipient_name},",
            "it": "Gentile Signore/Signora," if not recipient_name else f"Gentile {recipient_name},",
        }

        greeting = greetings.get(language, "Dear Sir/Madam,")

        closings = {
            "de": "\n\nMit freundlichen Grüßen",
            "en": "\n\nKind regards",
            "fr": "\n\nCordialement",
            "es": "\n\nAtentamente",
            "it": "\n\nCordiali saluti",
        }

        closing = closings.get(language, "\n\nKind regards")

        return f"{greeting}\n\n{body}{closing}"


# Singleton instance for easy access
_translation_service: Optional[TranslationService] = None


def get_translation_service() -> TranslationService:
    """
    Get or create singleton translation service instance

    Returns:
        TranslationService instance
    """
    global _translation_service
    if _translation_service is None:
        # Initialize with environment variables
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            redis_client = Redis.from_url(redis_url)
        except Exception as e:
            print(f"Redis connection failed: {e}")
            redis_client = None

        _translation_service = TranslationService(
            redis_client=redis_client
        )

    return _translation_service
