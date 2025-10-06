"""Unit tests for PDF Generator - DIN 5008 compliance and formatting."""

import pytest
from datetime import datetime, timedelta, date
from decimal import Decimal
from uuid import uuid4

from src.services.offer.pdf_generator import PDFGenerator
from src.models.offer import Offer, OfferStatus
from src.models.work_package import WorkPackage, EstimatedHours, Deliverable
from src.models.value_objects import Money
from src.models.customer import Customer, GDPRConsent, ConsentPurpose
from src.models.value_objects import EmailAddress, LanguageCode


@pytest.fixture
def sample_work_package():
    """Create a sample work package for testing."""
    offer_id = uuid4()
    return WorkPackage(
        id=uuid4(),
        offer_id=offer_id,
        name="Backend Development",
        description="Complete REST API implementation with authentication",
        deliverables=[
            Deliverable(
                name="User Authentication API",
                description="JWT-based authentication endpoints",
                acceptance_criteria=[
                    "Login endpoint implemented",
                    "Token refresh implemented",
                    "User registration implemented",
                ],
            ),
            Deliverable(
                name="Database Schema",
                description="PostgreSQL database design and migrations",
                acceptance_criteria=["All tables created", "Indexes optimized"],
            ),
        ],
        estimated_hours=EstimatedHours(
            optimistic=Decimal("40.0"),
            likely=Decimal("50.0"),
            pessimistic=Decimal("65.0"),
            confidence=0.85,
        ),
        hourly_rate=Money(amount=Decimal("120.00"), currency="EUR"),
        total_cost=Money(amount=Decimal("6000.00"), currency="EUR"),
        order=1,
    )


@pytest.fixture
def sample_offer(sample_work_package):
    """Create a sample offer for testing."""
    customer_id = uuid4()
    project_id = uuid4()
    conversation_id = uuid4()

    return Offer(
        id=uuid4(),
        offer_number="25-0001",
        version=1,
        customer_id=customer_id,
        project_id=project_id,
        conversation_id=conversation_id,
        created_at=datetime.utcnow(),
        valid_until=date.today() + timedelta(days=30),
        status=OfferStatus.DRAFT,
        total_value=Money(amount=Decimal("6000.00"), currency="EUR"),
        work_packages=[sample_work_package],
        terms_and_conditions="""
Allgemeine Geschäftsbedingungen:

1. Zahlungsbedingungen: 30 Tage netto ab Rechnungsdatum
2. Gültigkeit des Angebots: 30 Tage ab Ausstellungsdatum
3. Alle Preise verstehen sich zuzüglich der gesetzlichen Mehrwertsteuer (19%)
4. Lieferung und Leistung erfolgen nach den vereinbarten Terminen
5. Es gelten unsere allgemeinen Geschäftsbedingungen in der aktuellen Fassung
""",
        approval_required=False,
    )


@pytest.fixture
def sample_customer():
    """Create a sample customer for testing."""
    return Customer(
        id=uuid4(),
        external_id="CUST-2025-001",
        company_name="Mustermann GmbH",
        contact_person="Max Mustermann",
        email=EmailAddress(value="max.mustermann@example.com"),
        language_preference=LanguageCode(code="de"),
        gdpr_consent=GDPRConsent(
            given_at=datetime.utcnow(),
            ip_address="192.168.1.1",
            consent_text_version="v1.0",
            purposes=[ConsentPurpose.OFFER_GENERATION],
        ),
    )


class TestPDFGenerator:
    """Test suite for PDF generation functionality."""

    def test_generator_initialization(self):
        """Test that PDFGenerator initializes correctly."""
        generator = PDFGenerator()
        assert generator is not None
        assert hasattr(generator, "TRANSLATIONS")
        assert "de" in generator.TRANSLATIONS
        assert "en" in generator.TRANSLATIONS

    @pytest.mark.asyncio
    async def test_generate_german_pdf(self, sample_offer, sample_customer):
        """Test PDF generation in German (DIN 5008)."""
        generator = PDFGenerator()
        pdf_bytes = await generator.generate_offer_pdf(
            sample_offer, language="de", customer=sample_customer
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")  # PDF magic number

    @pytest.mark.asyncio
    async def test_generate_english_pdf(self, sample_offer, sample_customer):
        """Test PDF generation in English."""
        generator = PDFGenerator()
        pdf_bytes = await generator.generate_offer_pdf(
            sample_offer, language="en", customer=sample_customer
        )

        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_unsupported_language_raises_error(self, sample_offer):
        """Test that unsupported language raises ValueError."""
        generator = PDFGenerator()

        with pytest.raises(ValueError, match="Unsupported language"):
            await generator.generate_offer_pdf(sample_offer, language="xx")

    def test_date_formatting_german(self):
        """Test German date format: DD.MM.YYYY."""
        generator = PDFGenerator()
        test_date = date(2025, 10, 6)

        formatted = generator._format_date(test_date, "de")

        assert formatted == "06.10.2025"

    def test_date_formatting_english(self):
        """Test English date format: YYYY-MM-DD."""
        generator = PDFGenerator()
        test_date = date(2025, 10, 6)

        formatted = generator._format_date(test_date, "en")

        assert formatted == "2025-10-06"

    def test_money_formatting_german(self):
        """Test German money format: 1.234,56 €."""
        generator = PDFGenerator()
        money = Money(amount=Decimal("1234.56"), currency="EUR")

        formatted = generator._format_money(money, "de")

        assert formatted == "1.234,56 EUR"

    def test_money_formatting_english(self):
        """Test English money format: EUR 1,234.56."""
        generator = PDFGenerator()
        money = Money(amount=Decimal("1234.56"), currency="EUR")

        formatted = generator._format_money(money, "en")

        assert formatted == "EUR 1,234.56"

    @pytest.mark.asyncio
    async def test_multiple_work_packages(self, sample_offer, sample_customer):
        """Test PDF generation with multiple work packages."""
        # Add more work packages
        for i in range(2, 5):
            wp = WorkPackage(
                id=uuid4(),
                offer_id=sample_offer.id,
                name=f"Work Package {i}",
                description=f"Description for package {i}",
                deliverables=[
                    Deliverable(
                        name=f"Deliverable {i}.1",
                        description="Test deliverable",
                        acceptance_criteria=["Criteria 1"],
                    )
                ],
                estimated_hours=EstimatedHours(
                    optimistic=Decimal("20.0"),
                    likely=Decimal("25.0"),
                    pessimistic=Decimal("30.0"),
                    confidence=0.8,
                ),
                hourly_rate=Money(amount=Decimal("120.00"), currency="EUR"),
                total_cost=Money(amount=Decimal("3000.00"), currency="EUR"),
                order=i,
            )
            sample_offer.work_packages.append(wp)

        generator = PDFGenerator()
        pdf_bytes = await generator.generate_offer_pdf(
            sample_offer, language="de", customer=sample_customer
        )

        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    @pytest.mark.asyncio
    async def test_high_value_offer_with_approval(self, sample_offer, sample_customer):
        """Test PDF generation for high-value offer requiring approval."""
        # Set high value requiring approval
        sample_offer.total_value = Money(amount=Decimal("150000.00"), currency="EUR")
        sample_offer.approval_required = True
        sample_offer.status = OfferStatus.APPROVED

        generator = PDFGenerator()
        pdf_bytes = await generator.generate_offer_pdf(
            sample_offer, language="de", customer=sample_customer
        )

        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    def test_text_wrapping(self):
        """Test text wrapping functionality."""
        generator = PDFGenerator()

        # Create a mock canvas with stringWidth method
        class MockCanvas:
            def stringWidth(self, text):
                # Approximate: 10 chars = 100 units
                return len(text) * 10

        canvas = MockCanvas()
        long_text = "This is a very long text that should be wrapped into multiple lines"
        max_width = 200  # ~20 characters

        wrapped = generator._wrap_text(long_text, max_width, canvas)

        assert len(wrapped) > 1  # Should be wrapped into multiple lines
        for line in wrapped:
            assert len(line) * 10 <= max_width + 50  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_pdf_without_customer_data(self, sample_offer):
        """Test PDF generation without customer data (still valid)."""
        generator = PDFGenerator()
        pdf_bytes = await generator.generate_offer_pdf(
            sample_offer, language="de", customer=None
        )

        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    def test_translation_completeness(self):
        """Test that all required translation keys are present."""
        generator = PDFGenerator()

        required_keys = [
            "offer",
            "offer_number",
            "date",
            "valid_until",
            "page",
            "work_packages",
            "description",
            "hours",
            "rate",
            "total",
            "terms",
            "footer_legal",
            "footer_contact",
        ]

        for lang in ["de", "en"]:
            trans = generator.TRANSLATIONS[lang]
            for key in required_keys:
                assert key in trans, f"Missing translation key '{key}' for language '{lang}'"

    @pytest.mark.asyncio
    async def test_long_terms_generate_additional_page(
        self, sample_offer, sample_customer
    ):
        """Test that long terms and conditions generate additional pages."""
        # Set very long terms
        sample_offer.terms_and_conditions = """
Allgemeine Geschäftsbedingungen:

1. Zahlungsbedingungen: {} Tage netto ab Rechnungsdatum
2. Gültigkeit des Angebots: 30 Tage ab Ausstellungsdatum
3. Alle Preise verstehen sich zuzüglich der gesetzlichen Mehrwertsteuer
4. Lieferung und Leistung erfolgen nach den vereinbarten Terminen

""" * 10  # Repeat to make it very long

        generator = PDFGenerator()
        needs_additional = generator._needs_additional_pages(sample_offer)

        assert needs_additional is True

    def test_din5008_measurements(self):
        """Test that DIN 5008 measurements are correctly defined."""
        from src.services.offer.pdf_generator import (
            DIN5008_TOP_MARGIN,
            DIN5008_LEFT_MARGIN,
            DIN5008_RIGHT_MARGIN,
            DIN5008_BOTTOM_MARGIN,
            DIN5008_ADDRESS_TOP,
            DIN5008_FOLD_MARK_1,
            DIN5008_FOLD_MARK_2,
        )
        from reportlab.lib.units import mm

        # Verify DIN 5008 standard measurements
        assert DIN5008_TOP_MARGIN == 27 * mm
        assert DIN5008_LEFT_MARGIN == 24.1 * mm
        assert DIN5008_RIGHT_MARGIN == 8.1 * mm
        assert DIN5008_BOTTOM_MARGIN == 20 * mm
        assert DIN5008_ADDRESS_TOP == 45 * mm
        assert DIN5008_FOLD_MARK_1 == 87 * mm
        assert DIN5008_FOLD_MARK_2 == 192 * mm
