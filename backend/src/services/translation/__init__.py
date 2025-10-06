"""
Translation Service Package

Provides multi-language translation support for backend operations including:
- Email message translation
- PDF document translation
- System notifications translation
- Audit trail message translation

Uses GPT-4 for initial translations with human review workflow markers.
"""

from .main import TranslationService, TranslationRequest, TranslationResponse

__all__ = ['TranslationService', 'TranslationRequest', 'TranslationResponse']
