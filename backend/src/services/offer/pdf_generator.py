"""
PDF Generator for Offers - DIN 5008 Compliant

Generates professional PDF documents following German business standards (DIN 5008)
with multi-language support, company branding, and legal compliance.

DIN 5008 Key Standards:
- Paper: A4 (210mm x 297mm)
- Margins: Top 27mm, Left 24.1mm, Right 8.1mm, Bottom 20mm
- Address field: 45mm from top, 20mm height
- Fold marks: 87mm and 192mm from top
- Date format: DD.MM.YYYY (German), YYYY-MM-DD (ISO for other languages)
- Currency format: 1.234,56 € (German)
"""

from datetime import date, datetime
from decimal import Decimal
from io import BytesIO
from typing import Dict, List, Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from ...models.offer import Offer
from ...models.customer import Customer
from ...models.work_package import WorkPackage
from ...models.value_objects import Money


# DIN 5008 Measurements in mm
DIN5008_TOP_MARGIN = 27 * mm
DIN5008_LEFT_MARGIN = 24.1 * mm
DIN5008_RIGHT_MARGIN = 8.1 * mm
DIN5008_BOTTOM_MARGIN = 20 * mm
DIN5008_ADDRESS_TOP = 45 * mm
DIN5008_ADDRESS_HEIGHT = 20 * mm
DIN5008_FOLD_MARK_1 = 87 * mm
DIN5008_FOLD_MARK_2 = 192 * mm

# Company branding (can be configured from environment/settings)
COMPANY_NAME = "Aigentics Corporation"
COMPANY_ADDRESS = "Musterstraße 123\n12345 Musterstadt\nDeutschland"
COMPANY_PHONE = "+49 123 456789"
COMPANY_EMAIL = "info@aigentics.com"
COMPANY_WEB = "www.aigentics.com"
COMPANY_TAX_ID = "DE123456789"
COMPANY_BANK = "Musterbank\nIBAN: DE89 3704 0044 0532 0130 00\nBIC: COBADEFFXXX"

# Brand colors (can be customized)
BRAND_PRIMARY = colors.HexColor("#1E40AF")  # Blue
BRAND_SECONDARY = colors.HexColor("#64748B")  # Slate
BRAND_ACCENT = colors.HexColor("#0EA5E9")  # Sky blue


class PDFGenerator:
    """
    PDF Generator for professional offers following DIN 5008 standards.

    Features:
    - DIN 5008 compliant layout with proper margins and fold marks
    - Multi-language support (German/English primary)
    - Company branding with logo, colors, headers/footers
    - Professional work package tables with pricing breakdown
    - Legal terms and conditions section
    - Multi-page support with page numbering
    """

    # Translations for supported languages
    TRANSLATIONS = {
        "de": {
            "offer": "Angebot",
            "offer_number": "Angebotsnummer",
            "date": "Datum",
            "customer_number": "Kundennummer",
            "valid_until": "Gültig bis",
            "page": "Seite",
            "of": "von",
            "dear": "Sehr geehrte Damen und Herren",
            "intro": "vielen Dank für Ihr Interesse an unseren Dienstleistungen. Gerne unterbreiten wir Ihnen folgendes Angebot:",
            "work_packages": "Leistungspakete",
            "package": "Paket",
            "description": "Beschreibung",
            "deliverables": "Liefergegenstände",
            "hours": "Stunden",
            "rate": "Stundensatz",
            "total": "Gesamt",
            "subtotal": "Zwischensumme",
            "vat": "MwSt. (19%)",
            "grand_total": "Gesamtsumme",
            "net": "Netto",
            "terms": "Allgemeine Geschäftsbedingungen",
            "payment_terms": "Zahlungsbedingungen",
            "validity": "Gültigkeit",
            "acceptance": "Annahme",
            "closing": "Mit freundlichen Grüßen",
            "signature": "Aigentics Corporation",
            "footer_legal": "Geschäftsführer: Max Mustermann | Handelsregister: AG Musterstadt HRB 12345",
            "footer_contact": f"Tel: {COMPANY_PHONE} | E-Mail: {COMPANY_EMAIL} | Web: {COMPANY_WEB}",
            "footer_tax": f"USt-IdNr: {COMPANY_TAX_ID}",
        },
        "en": {
            "offer": "Offer",
            "offer_number": "Offer Number",
            "date": "Date",
            "customer_number": "Customer Number",
            "valid_until": "Valid Until",
            "page": "Page",
            "of": "of",
            "dear": "Dear Sir or Madam",
            "intro": "Thank you for your interest in our services. We are pleased to submit the following offer:",
            "work_packages": "Work Packages",
            "package": "Package",
            "description": "Description",
            "deliverables": "Deliverables",
            "hours": "Hours",
            "rate": "Hourly Rate",
            "total": "Total",
            "subtotal": "Subtotal",
            "vat": "VAT (19%)",
            "grand_total": "Grand Total",
            "net": "Net",
            "terms": "Terms and Conditions",
            "payment_terms": "Payment Terms",
            "validity": "Validity",
            "acceptance": "Acceptance",
            "closing": "Sincerely",
            "signature": "Aigentics Corporation",
            "footer_legal": "Managing Director: Max Mustermann | Commercial Register: AG Musterstadt HRB 12345",
            "footer_contact": f"Tel: {COMPANY_PHONE} | Email: {COMPANY_EMAIL} | Web: {COMPANY_WEB}",
            "footer_tax": f"VAT ID: {COMPANY_TAX_ID}",
        },
    }

    def __init__(self):
        """Initialize PDF generator with default settings."""
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Set up custom paragraph styles for consistent formatting."""
        # Heading style
        self.styles.add(
            ParagraphStyle(
                name="CustomHeading1",
                parent=self.styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=16,
                textColor=BRAND_PRIMARY,
                spaceAfter=12,
                spaceBefore=12,
            )
        )

        # Subheading style
        self.styles.add(
            ParagraphStyle(
                name="CustomHeading2",
                parent=self.styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                textColor=BRAND_PRIMARY,
                spaceAfter=8,
                spaceBefore=10,
            )
        )

        # Body text style
        self.styles.add(
            ParagraphStyle(
                name="CustomBody",
                parent=self.styles["Normal"],
                fontName="Helvetica",
                fontSize=10,
                leading=14,
                spaceAfter=6,
            )
        )

        # Small text for footer
        self.styles.add(
            ParagraphStyle(
                name="Footer",
                parent=self.styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                textColor=BRAND_SECONDARY,
                alignment=1,  # Center
            )
        )

    async def generate_offer_pdf(
        self, offer: Offer, language: str = "de", customer: Optional[Customer] = None
    ) -> bytes:
        """
        Generate a professional PDF document for an offer.

        Args:
            offer: Offer aggregate containing all offer details
            language: Language code (de, en, etc.)
            customer: Optional customer entity for address details

        Returns:
            PDF document as bytes

        Raises:
            ValueError: If language is not supported
        """
        if language not in self.TRANSLATIONS:
            raise ValueError(
                f"Unsupported language: {language}. "
                f"Supported: {', '.join(self.TRANSLATIONS.keys())}"
            )

        # Create PDF buffer
        buffer = BytesIO()

        # Create PDF with DIN 5008 layout
        pdf = canvas.Canvas(buffer, pagesize=A4)

        # Generate all pages
        self._create_first_page(pdf, offer, language, customer)

        # Add additional pages if needed
        if len(offer.work_packages) > 3 or self._needs_additional_pages(offer):
            self._create_additional_pages(pdf, offer, language)

        # Finalize PDF
        pdf.save()

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def _create_first_page(
        self, pdf: canvas.Canvas, offer: Offer, language: str, customer: Optional[Customer]
    ):
        """Create the first page with header, address, and main content."""
        trans = self.TRANSLATIONS[language]

        # Draw fold marks (DIN 5008)
        self._draw_fold_marks(pdf)

        # Draw header with company branding
        self._draw_header(pdf, language)

        # Draw address field (DIN 5008 position)
        if customer:
            self._draw_address_field(pdf, customer)

        # Draw offer metadata (offer number, date, etc.)
        self._draw_metadata(pdf, offer, language)

        # Draw salutation and introduction
        y_pos = self._draw_introduction(pdf, language)

        # Draw work packages table
        y_pos = self._draw_work_packages(pdf, offer, language, y_pos)

        # Draw pricing summary
        y_pos = self._draw_pricing_summary(pdf, offer, language, y_pos)

        # Draw terms and conditions if space permits
        if y_pos > 150:
            self._draw_terms_preview(pdf, language, y_pos)

        # Draw footer
        self._draw_footer(pdf, language, 1, 1)

        pdf.showPage()

    def _create_additional_pages(
        self, pdf: canvas.Canvas, offer: Offer, language: str
    ):
        """Create additional pages for terms and conditions."""
        trans = self.TRANSLATIONS[language]
        page_num = 2

        # Draw header
        self._draw_header(pdf, language)

        # Draw terms and conditions
        y_pos = self.page_height - DIN5008_TOP_MARGIN - 20
        self._draw_full_terms(pdf, offer, language, y_pos)

        # Draw footer
        self._draw_footer(pdf, language, page_num, 2)

        pdf.showPage()

    def _draw_fold_marks(self, pdf: canvas.Canvas):
        """Draw DIN 5008 fold marks at 87mm and 192mm from top."""
        pdf.setStrokeColor(BRAND_SECONDARY)
        pdf.setLineWidth(0.5)

        # Upper fold mark at 87mm
        pdf.line(0, self.page_height - DIN5008_FOLD_MARK_1, 5 * mm, self.page_height - DIN5008_FOLD_MARK_1)

        # Lower fold mark at 192mm
        pdf.line(0, self.page_height - DIN5008_FOLD_MARK_2, 5 * mm, self.page_height - DIN5008_FOLD_MARK_2)

    def _draw_header(self, pdf: canvas.Canvas, language: str):
        """Draw company header with branding."""
        pdf.setFont("Helvetica-Bold", 18)
        pdf.setFillColor(BRAND_PRIMARY)
        pdf.drawString(DIN5008_LEFT_MARGIN, self.page_height - 20 * mm, COMPANY_NAME)

        # Company tagline or logo placeholder
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(BRAND_SECONDARY)
        pdf.drawString(DIN5008_LEFT_MARGIN, self.page_height - 25 * mm, "Professional IT Consulting Services")

    def _draw_address_field(self, pdf: canvas.Canvas, customer: Customer):
        """Draw recipient address in DIN 5008 address window."""
        x = DIN5008_LEFT_MARGIN
        y = self.page_height - DIN5008_ADDRESS_TOP

        pdf.setFont("Helvetica", 8)
        pdf.setFillColor(colors.grey)

        # Return address (small, above main address)
        return_address = f"{COMPANY_NAME} • {COMPANY_ADDRESS.split()[0]} • Musterstadt"
        pdf.drawString(x, y, return_address.replace('\n', ' '))

        # Main recipient address
        y -= 5 * mm
        pdf.setFont("Helvetica", 11)
        pdf.setFillColor(colors.black)

        pdf.drawString(x, y, customer.company_name)
        y -= 5 * mm
        pdf.drawString(x, y, customer.contact_person)
        y -= 5 * mm
        pdf.drawString(x, y, str(customer.email))

    def _draw_metadata(self, pdf: canvas.Canvas, offer: Offer, language: str):
        """Draw offer metadata (number, date, validity)."""
        trans = self.TRANSLATIONS[language]

        x = self.page_width - DIN5008_RIGHT_MARGIN - 80 * mm
        y = self.page_height - DIN5008_ADDRESS_TOP - 10 * mm

        pdf.setFont("Helvetica-Bold", 9)
        pdf.setFillColor(colors.black)

        # Offer number
        pdf.drawString(x, y, trans["offer_number"] + ":")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 50 * mm, y, offer.offer_number)

        # Date
        y -= 5 * mm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x, y, trans["date"] + ":")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 50 * mm, y, self._format_date(offer.created_at, language))

        # Valid until
        y -= 5 * mm
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(x, y, trans["valid_until"] + ":")
        pdf.setFont("Helvetica", 9)
        pdf.drawString(x + 50 * mm, y, self._format_date(offer.valid_until, language))

    def _draw_introduction(self, pdf: canvas.Canvas, language: str) -> float:
        """Draw salutation and introduction text. Returns y position."""
        trans = self.TRANSLATIONS[language]

        x = DIN5008_LEFT_MARGIN
        y = self.page_height - DIN5008_ADDRESS_TOP - 45 * mm

        pdf.setFont("Helvetica-Bold", 14)
        pdf.setFillColor(BRAND_PRIMARY)
        pdf.drawString(x, y, trans["offer"])

        y -= 10 * mm
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(colors.black)
        pdf.drawString(x, y, trans["dear"] + ",")

        y -= 8 * mm
        # Word wrap for introduction text
        text_width = self.page_width - DIN5008_LEFT_MARGIN - DIN5008_RIGHT_MARGIN - 20 * mm
        lines = self._wrap_text(trans["intro"], text_width, pdf)
        for line in lines:
            pdf.drawString(x, y, line)
            y -= 5 * mm

        return y - 5 * mm

    def _draw_work_packages(
        self, pdf: canvas.Canvas, offer: Offer, language: str, y_pos: float
    ) -> float:
        """Draw work packages as a professional table. Returns y position."""
        trans = self.TRANSLATIONS[language]

        x = DIN5008_LEFT_MARGIN
        y_pos -= 5 * mm

        # Section heading
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(BRAND_PRIMARY)
        pdf.drawString(x, y_pos, trans["work_packages"])
        y_pos -= 8 * mm

        # Table data
        table_data = []

        # Header row
        header = [
            trans["package"],
            trans["description"],
            trans["hours"],
            trans["rate"],
            trans["total"],
        ]
        table_data.append(header)

        # Work package rows
        for i, wp in enumerate(offer.work_packages, 1):
            # Format deliverables as bullet list
            deliverables_text = "\n".join(
                f"• {d.name}" for d in wp.deliverables[:3]  # Limit to 3 for space
            )

            row = [
                str(i),
                f"{wp.name}\n{deliverables_text}",
                f"{wp.estimated_hours.expected:.1f}",
                self._format_money(wp.hourly_rate, language),
                self._format_money(wp.total_cost, language),
            ]
            table_data.append(row)

        # Calculate table dimensions
        col_widths = [20 * mm, 80 * mm, 25 * mm, 30 * mm, 30 * mm]
        table_width = sum(col_widths)

        # Draw table
        table_height = self._draw_table(
            pdf,
            table_data,
            x,
            y_pos,
            col_widths,
            language,
        )

        return y_pos - table_height - 5 * mm

    def _draw_table(
        self,
        pdf: canvas.Canvas,
        data: List[List[str]],
        x: float,
        y: float,
        col_widths: List[float],
        language: str,
    ) -> float:
        """Draw a formatted table and return its height."""
        # Header styling
        pdf.setFillColor(BRAND_PRIMARY)
        pdf.setStrokeColor(BRAND_PRIMARY)
        row_height = 8 * mm

        # Draw header background
        pdf.rect(x, y - row_height, sum(col_widths), row_height, fill=1)

        # Draw header text
        pdf.setFillColor(colors.white)
        pdf.setFont("Helvetica-Bold", 9)

        x_pos = x + 2 * mm
        for i, header_text in enumerate(data[0]):
            pdf.drawString(x_pos, y - row_height + 2.5 * mm, header_text)
            x_pos += col_widths[i]

        # Draw data rows
        y -= row_height
        pdf.setFillColor(colors.black)
        pdf.setFont("Helvetica", 9)

        for row_idx, row in enumerate(data[1:], 1):
            # Alternate row colors
            if row_idx % 2 == 0:
                pdf.setFillColor(colors.HexColor("#F8FAFC"))
                pdf.rect(x, y - row_height * 1.5, sum(col_widths), row_height * 1.5, fill=1, stroke=0)
                pdf.setFillColor(colors.black)

            x_pos = x + 2 * mm
            for i, cell_text in enumerate(row):
                # Handle multi-line cells
                if "\n" in cell_text:
                    lines = cell_text.split("\n")
                    y_offset = y - 4 * mm
                    for line in lines:
                        pdf.drawString(x_pos, y_offset, line)
                        y_offset -= 3.5 * mm
                else:
                    pdf.drawString(x_pos, y - 5 * mm, cell_text)
                x_pos += col_widths[i]

            y -= row_height * 1.5

        # Draw table border
        pdf.setStrokeColor(BRAND_SECONDARY)
        pdf.setLineWidth(0.5)
        pdf.rect(x, y, sum(col_widths), len(data) * row_height)

        total_height = len(data) * row_height * 1.2
        return total_height

    def _draw_pricing_summary(
        self, pdf: canvas.Canvas, offer: Offer, language: str, y_pos: float
    ) -> float:
        """Draw pricing summary with VAT calculation. Returns y position."""
        trans = self.TRANSLATIONS[language]

        x = self.page_width - DIN5008_RIGHT_MARGIN - 70 * mm
        y_pos -= 10 * mm

        # Net total
        pdf.setFont("Helvetica", 10)
        pdf.drawString(x, y_pos, trans["subtotal"] + " " + trans["net"] + ":")
        pdf.drawRightString(x + 60 * mm, y_pos, self._format_money(offer.total_value, language))

        # VAT (19%)
        y_pos -= 5 * mm
        vat_amount = Money(
            amount=offer.total_value.amount * Decimal("0.19"),
            currency=offer.total_value.currency,
        )
        pdf.drawString(x, y_pos, trans["vat"] + ":")
        pdf.drawRightString(x + 60 * mm, y_pos, self._format_money(vat_amount, language))

        # Grand total
        y_pos -= 8 * mm
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(BRAND_PRIMARY)
        grand_total = offer.total_value + vat_amount
        pdf.drawString(x, y_pos, trans["grand_total"] + ":")
        pdf.drawRightString(x + 60 * mm, y_pos, self._format_money(grand_total, language))

        pdf.setFillColor(colors.black)
        return y_pos - 10 * mm

    def _draw_terms_preview(self, pdf: canvas.Canvas, language: str, y_pos: float):
        """Draw a preview of terms and conditions."""
        trans = self.TRANSLATIONS[language]

        x = DIN5008_LEFT_MARGIN

        pdf.setFont("Helvetica-Bold", 10)
        pdf.setFillColor(BRAND_PRIMARY)
        pdf.drawString(x, y_pos, trans["terms"])

        y_pos -= 6 * mm
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.black)

        # Short terms preview
        terms_preview = [
            f"• {trans['payment_terms']}: 30 Tage netto" if language == "de" else "• Payment Terms: 30 days net",
            f"• {trans['validity']}: 30 Tage ab Angebotsdatum" if language == "de" else "• Validity: 30 days from offer date",
        ]

        for term in terms_preview:
            pdf.drawString(x, y_pos, term)
            y_pos -= 4 * mm

    def _draw_full_terms(
        self, pdf: canvas.Canvas, offer: Offer, language: str, y_pos: float
    ):
        """Draw complete terms and conditions on separate page."""
        trans = self.TRANSLATIONS[language]

        x = DIN5008_LEFT_MARGIN

        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColor(BRAND_PRIMARY)
        pdf.drawString(x, y_pos, trans["terms"])

        y_pos -= 10 * mm
        pdf.setFont("Helvetica", 9)
        pdf.setFillColor(colors.black)

        # Use terms from offer or default
        terms_text = offer.terms_and_conditions

        # Word wrap and draw
        text_width = self.page_width - DIN5008_LEFT_MARGIN - DIN5008_RIGHT_MARGIN - 20 * mm
        lines = self._wrap_text(terms_text, text_width, pdf)

        for line in lines:
            if y_pos < 50 * mm:  # Don't overlap footer
                break
            pdf.drawString(x, y_pos, line)
            y_pos -= 4.5 * mm

    def _draw_footer(self, pdf: canvas.Canvas, language: str, page_num: int, total_pages: int):
        """Draw footer with legal information and page numbers."""
        trans = self.TRANSLATIONS[language]

        y = DIN5008_BOTTOM_MARGIN - 5 * mm

        # Legal information
        pdf.setFont("Helvetica", 7)
        pdf.setFillColor(BRAND_SECONDARY)

        # Line 1: Legal
        pdf.drawCentredString(self.page_width / 2, y, trans["footer_legal"])

        # Line 2: Contact
        y -= 3 * mm
        pdf.drawCentredString(self.page_width / 2, y, trans["footer_contact"])

        # Line 3: Tax
        y -= 3 * mm
        pdf.drawCentredString(self.page_width / 2, y, trans["footer_tax"])

        # Page number
        y -= 3 * mm
        pdf.drawCentredString(
            self.page_width / 2,
            y,
            f"{trans['page']} {page_num} {trans['of']} {total_pages}",
        )

    def _format_date(self, date_obj, language: str) -> str:
        """Format date according to language conventions."""
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()

        if language == "de":
            # German format: DD.MM.YYYY
            return date_obj.strftime("%d.%m.%Y")
        else:
            # ISO format for other languages: YYYY-MM-DD
            return date_obj.strftime("%Y-%m-%d")

    def _format_money(self, money: Money, language: str) -> str:
        """Format money according to language conventions."""
        if language == "de":
            # German format: 1.234,56 €
            return money.format_german()
        else:
            # English format: €1,234.56
            amount_str = f"{money.amount:,.2f}"
            return f"{money.currency} {amount_str}"

    def _wrap_text(self, text: str, max_width: float, pdf: canvas.Canvas) -> List[str]:
        """Wrap text to fit within max_width."""
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            test_line = " ".join(current_line + [word])
            if pdf.stringWidth(test_line) <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _needs_additional_pages(self, offer: Offer) -> bool:
        """Determine if additional pages are needed for terms."""
        # If terms are long or many work packages, need additional page
        return len(offer.terms_and_conditions) > 500 or len(offer.work_packages) > 5
