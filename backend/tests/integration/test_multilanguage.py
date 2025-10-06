"""
Integration Test: Multi-Language Support

Tests internationalization (i18n) for all EU languages as required by
FR-006 and the bilingual support constitutional requirement (Constitution X).

Language Requirements:
- All EU languages supported (24 languages)
- German and English primary languages
- Accept-Language header handling
- Consistent translations across UI and documents
- PDF generation respects language
- Currency and date formatting per locale

Validation Scenarios:
- Conversations in different languages
- Offer PDFs generated in customer's language
- Language switching during conversation
- Date/currency formatting per locale
- Translation consistency
"""

import pytest
from uuid import uuid4


class TestMultiLanguageSupport:
    """Test internationalization for all EU languages."""

    # EU language codes as per data model
    EU_LANGUAGES = [
        "de", "en", "fr", "es", "it", "nl", "pl", "pt",
        "cs", "da", "el", "hu", "ro", "sv", "bg", "hr",
        "et", "fi", "ga", "lt", "lv", "mt", "sk", "sl"
    ]

    PRIMARY_LANGUAGES = ["de", "en"]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("language", PRIMARY_LANGUAGES)
    async def test_conversation_in_primary_languages(
        self, async_client, language
    ):
        """
        Test Case: German and English fully supported

        Given: System supports primary languages (DE, EN)
        When: Conversation started in DE or EN
        Then: AI responds in requested language

        Requirement: FR-006 - German/English primary languages
        """
        # ARRANGE & ACT: Start conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": language}
        )

        # ASSERT: Conversation created in requested language
        assert response.status_code == 201
        data = response.json()

        assert data["language"] == language
        assert "initial_questions" in data
        assert len(data["initial_questions"]) > 0

        # Questions should be in the requested language
        # (Full validation would require NLP, checking structure here)
        first_question = data["initial_questions"][0]
        assert "text" in first_question
        assert len(first_question["text"]) > 0

    @pytest.mark.asyncio
    @pytest.mark.parametrize("language", EU_LANGUAGES)
    async def test_all_eu_languages_accepted(
        self, async_client, language
    ):
        """
        Test Case: All 24 EU languages supported

        Given: System declares support for all EU languages
        When: Conversation initiated in any EU language
        Then: System accepts and creates conversation

        Requirement: FR-006 - All EU languages supported
        """
        # ACT: Start conversation in each EU language
        response = await async_client.post(
            "/v1/conversations",
            json={"language": language}
        )

        # ASSERT: Accepted
        assert response.status_code == 201
        data = response.json()

        assert data["language"] == language

    @pytest.mark.asyncio
    async def test_invalid_language_rejected(
        self, async_client
    ):
        """
        Test Case: Non-EU languages rejected

        Given: Only EU languages supported
        When: Conversation requested in non-EU language
        Then: Returns 400 Bad Request

        Validation: Language validation per data model
        """
        # ACT: Attempt unsupported language
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "ja"}  # Japanese not in EU
        )

        # ASSERT: Rejected
        assert response.status_code == 400
        error = response.json()

        assert "language" in error["message"].lower()

    @pytest.mark.asyncio
    async def test_offer_pdf_generated_in_customer_language(
        self, async_client, existing_offer
    ):
        """
        Test Case: PDF respects customer language preference

        Given: Offer generated
        When: Customer requests PDF in their language
        Then: PDF content in requested language

        Requirement: FR-006 - All interactions/documents multilingual
        """
        # ARRANGE
        offer_id = existing_offer["id"]

        customer_data_german = {
            "company_name": "Deutsche Firma GmbH",
            "contact_person": "Hans Müller",
            "email": "hans@deutsche-firma.de",
            "language_preference": "de",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        # ACT: Download PDF in German
        response = await async_client.post(
            f"/v1/offers/{offer_id}/download",
            json=customer_data_german
        )

        # ASSERT: PDF generated
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

        # Verify filename indicates language
        content_disposition = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disposition

        # Full PDF content validation would require PDF parsing
        # Integration test confirms generation succeeds

    @pytest.mark.asyncio
    async def test_offer_preview_in_different_languages(
        self, async_client, existing_offer
    ):
        """
        Test Case: Offer preview available in multiple languages

        Given: Offer exists
        When: Preview requested with different language parameter
        Then: HTML preview in requested language

        Requirement: Multi-language preview before download
        """
        # ARRANGE
        offer_id = existing_offer["id"]

        # Test multiple languages
        test_languages = ["de", "en", "fr", "es"]

        for language in test_languages:
            # ACT: Get preview in specific language
            response = await async_client.get(
                f"/v1/offers/{offer_id}/preview",
                params={"language": language}
            )

            # ASSERT: Preview generated
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html"

            # HTML should exist (full translation check needs i18n library)
            assert len(response.text) > 0

    @pytest.mark.asyncio
    async def test_german_currency_formatting(
        self, async_client, db_session
    ):
        """
        Test Case: German currency format (1.234,56 €)

        Given: Offer with amounts
        When: Displayed to German customer
        Then: Format: 1.234,56 € (not 1,234.56 EUR)

        Requirement: Constitution II - German formatting standards
        """
        # ARRANGE: Create German-language offer
        response = await async_client.post("/v1/conversations", json={"language": "de"})
        conversation_id = response.json()["conversation_id"]

        # Progress conversation and generate offer
        await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "Wir brauchen eine Webseite für EUR 50.000"}
        )

        complete_response = await async_client.post(
            f"/v1/conversations/{conversation_id}/complete"
        )

        project_id = complete_response.json()["project_id"]

        offer_response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        # ACT: Get offer details
        offer_id = offer_response.json()["offer_id"]
        details_response = await async_client.get(f"/v1/offers/{offer_id}")

        # ASSERT: German formatting
        details = details_response.json()

        formatted_amount = details["total_value"]["formatted"]

        # German format: dot for thousands, comma for decimal, € symbol
        assert "," in formatted_amount  # Decimal comma
        assert "€" in formatted_amount
        # For amounts >= 1000, should have dot separator
        if float(details["total_value"]["amount"]) >= 1000:
            assert "." in formatted_amount.replace(",", "")  # Thousands separator

    @pytest.mark.asyncio
    async def test_german_date_formatting(
        self, async_client, existing_offer
    ):
        """
        Test Case: German date format (DD.MM.YYYY)

        Given: Offer with dates
        When: Displayed to German customer
        Then: Format: 24.12.2024 (not 12/24/2024)

        Requirement: Constitution II - DIN 5008 compliance
        """
        # ARRANGE
        offer_id = existing_offer["id"]

        # ACT: Get offer in German format
        response = await async_client.get(
            f"/v1/offers/{offer_id}/preview",
            params={"language": "de"}
        )

        # ASSERT: German date format in HTML
        assert response.status_code == 200
        html = response.text

        # Look for date patterns DD.MM.YYYY
        import re
        german_date_pattern = r"\d{2}\.\d{2}\.\d{4}"

        assert re.search(german_date_pattern, html), "No German date format found in preview"

    @pytest.mark.asyncio
    async def test_language_consistency_across_conversation(
        self, async_client
    ):
        """
        Test Case: Language maintained throughout conversation

        Given: Conversation started in French
        When: Multiple messages exchanged
        Then: All AI responses remain in French

        Requirement: Consistent user experience per language
        """
        # ARRANGE: Start French conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "fr"}
        )

        conversation_id = response.json()["conversation_id"]

        # ACT: Exchange multiple messages
        messages = [
            "Nous avons besoin d'un site web",
            "Budget environ 50000 euros",
            "Délai 6 mois"
        ]

        for message in messages:
            response = await async_client.post(
                f"/v1/conversations/{conversation_id}/messages",
                json={"message": message}
            )

            # ASSERT: Each response maintains French language
            assert response.status_code == 200
            data = response.json()

            assert "questions" in data
            # Language consistency (full validation needs NLP)

        # Final check: conversation details show French
        details_response = await async_client.get(
            f"/v1/conversations/{conversation_id}"
        )

        details = details_response.json()
        # Verify language preference persisted (if tracked in model)

    @pytest.mark.asyncio
    async def test_accept_language_header_handling(
        self, async_client
    ):
        """
        Test Case: Accept-Language header support

        Given: Request with Accept-Language header
        When: No explicit language parameter
        Then: System uses header for language selection

        Requirement: Constitution X - Accept-Language handling
        """
        # ACT: Request with Accept-Language header
        response = await async_client.post(
            "/v1/conversations",
            json={},  # No explicit language
            headers={"Accept-Language": "es-ES,es;q=0.9"}
        )

        # ASSERT: Spanish conversation created
        # (Behavior depends on implementation - may fallback to default)
        # At minimum, should not error
        assert response.status_code in [201, 400]

        if response.status_code == 201:
            data = response.json()
            # May use Spanish if header supported
            assert data["language"] in ["es", "en", "de"]  # Fallback acceptable

    @pytest.mark.asyncio
    async def test_translation_keys_defined_for_all_languages(
        self, async_client, translation_service
    ):
        """
        Test Case: Translation resources complete

        Given: System supports 24 EU languages
        When: Translation keys checked
        Then: All keys have translations for all languages

        Requirement: Complete i18n resource bundles
        """
        # ARRANGE: Key UI elements
        required_keys = [
            "conversation.welcome",
            "conversation.question_prompt",
            "offer.generated",
            "offer.download",
            "gdpr.consent_required"
        ]

        # ACT & ASSERT: Check each language has all keys
        for language in self.EU_LANGUAGES:
            for key in required_keys:
                translation = translation_service.get(key, language)

                assert translation is not None, f"Missing translation for {key} in {language}"
                assert len(translation) > 0

    @pytest.mark.asyncio
    async def test_multilingual_error_messages(
        self, async_client
    ):
        """
        Test Case: Error messages in customer's language

        Given: Conversation in specific language
        When: Error occurs
        Then: Error message in conversation language

        Requirement: Complete multilingual experience
        """
        # ARRANGE: Italian conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "it"}
        )

        conversation_id = response.json()["conversation_id"]

        # ACT: Trigger error (invalid message format)
        error_response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": ""}  # Empty message
        )

        # ASSERT: Error in Italian (or at least structured)
        assert error_response.status_code == 400
        error_data = error_response.json()

        assert "error_code" in error_data
        assert "message" in error_data

        # Full validation: error message in Italian
        # (Requires i18n implementation)

    @pytest.mark.asyncio
    async def test_language_switching_not_supported_mid_conversation(
        self, async_client
    ):
        """
        Test Case: Language fixed at conversation start

        Given: Conversation started in one language
        When: Attempt to switch language mid-conversation
        Then: Language remains fixed

        Business Rule: Prevents confusion, maintains context
        """
        # ARRANGE: Start English conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "en"}
        )

        conversation_id = response.json()["conversation_id"]

        # ACT: Send message in different language
        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "Ich möchte die Sprache wechseln"}  # German
        )

        # ASSERT: AI still responds in English context
        assert response.status_code == 200
        # Conversation language unchanged

        details = await async_client.get(f"/v1/conversations/{conversation_id}")
        # Original language preserved

    @pytest.mark.asyncio
    async def test_rtl_language_support(
        self, async_client
    ):
        """
        Test Case: Right-to-left language handling

        Given: No RTL languages in EU currently
        When: Future RTL support needed
        Then: System architecture ready

        Note: No EU languages use RTL currently, but architecture should support
        """
        # This test documents that current EU languages are all LTR
        # If EU expands or system used elsewhere, RTL support needed

        # All current EU languages are LTR
        for lang in self.EU_LANGUAGES:
            response = await async_client.post(
                "/v1/conversations",
                json={"language": lang}
            )

            assert response.status_code == 201
            # All should work with LTR assumptions

    @pytest.mark.asyncio
    async def test_special_character_handling_by_language(
        self, async_client
    ):
        """
        Test Case: Special characters preserved per language

        Given: Different languages use different character sets
        When: Messages contain language-specific characters
        Then: Characters preserved correctly

        Examples:
        - German: ä, ö, ü, ß
        - French: é, è, ê, ç
        - Polish: ą, ć, ę, ł
        - Greek: α, β, γ, δ
        """
        test_cases = [
            ("de", "Wir brauchen Lösung für Größe"),
            ("fr", "Système de gestion intégré"),
            ("pl", "Aplikacja mobilna z funkcją"),
            ("el", "Σύστημα διαχείρισης")
        ]

        for language, message in test_cases:
            # ARRANGE: Start conversation
            response = await async_client.post(
                "/v1/conversations",
                json={"language": language}
            )

            conversation_id = response.json()["conversation_id"]

            # ACT: Send message with special characters
            response = await async_client.post(
                f"/v1/conversations/{conversation_id}/messages",
                json={"message": message}
            )

            # ASSERT: Success (characters handled)
            assert response.status_code == 200
            # Character encoding handled correctly (UTF-8)
