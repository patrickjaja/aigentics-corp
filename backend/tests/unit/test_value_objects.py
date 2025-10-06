"""
Unit tests for value objects.

Tests all value object validations including EmailAddress, PhoneNumber, Money,
LanguageCode, and BudgetRange to ensure 100% coverage of business logic.
"""

import pytest
from decimal import Decimal
from pydantic import ValidationError

from src.models.value_objects import (
    EmailAddress,
    PhoneNumber,
    LanguageCode,
    Money,
    BudgetRange,
)


class TestEmailAddress:
    """Test cases for EmailAddress value object."""

    def test_valid_email(self):
        """Test creation of valid email addresses."""
        email = EmailAddress(value="test@example.com")
        assert email.value == "test@example.com"
        assert str(email) == "test@example.com"

    def test_email_lowercase_normalization(self):
        """Test that email addresses are normalized to lowercase."""
        email = EmailAddress(value="Test@Example.COM")
        assert email.value == "test@example.com"

    def test_valid_email_with_plus(self):
        """Test email with plus sign (common for aliases)."""
        email = EmailAddress(value="user+tag@example.com")
        assert email.value == "user+tag@example.com"

    def test_valid_email_with_subdomain(self):
        """Test email with subdomain."""
        email = EmailAddress(value="admin@mail.example.co.uk")
        assert email.value == "admin@mail.example.co.uk"

    def test_invalid_email_missing_at(self):
        """Test rejection of email without @ symbol."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAddress(value="invalid.email.com")
        assert "Invalid email address" in str(exc_info.value)

    def test_invalid_email_missing_domain(self):
        """Test rejection of email without domain."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAddress(value="test@")
        assert "Invalid email address" in str(exc_info.value)

    def test_invalid_email_missing_tld(self):
        """Test rejection of email without top-level domain."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAddress(value="test@example")
        assert "Invalid email address" in str(exc_info.value)

    def test_invalid_email_special_chars(self):
        """Test rejection of email with invalid special characters."""
        with pytest.raises(ValidationError) as exc_info:
            EmailAddress(value="test@exam ple.com")
        assert "Invalid email address" in str(exc_info.value)

    def test_email_immutability(self):
        """Test that EmailAddress is immutable."""
        email = EmailAddress(value="test@example.com")
        with pytest.raises(ValidationError):
            email.value = "new@example.com"


class TestPhoneNumber:
    """Test cases for PhoneNumber value object."""

    def test_valid_german_phone(self):
        """Test valid German phone number."""
        phone = PhoneNumber.from_string("+49 151 12345678")
        assert phone.country_code == "+49"
        assert phone.number == "15112345678"
        assert "+49" in str(phone)

    def test_valid_us_phone(self):
        """Test valid US phone number."""
        phone = PhoneNumber.from_string("+1 555 123 4567")
        assert phone.country_code == "+1"
        assert "555" in phone.number

    def test_valid_uk_phone(self):
        """Test valid UK phone number."""
        phone = PhoneNumber.from_string("+44 20 7946 0958")
        assert phone.country_code == "+44"

    def test_phone_without_plus(self):
        """Test phone number without leading plus (should work with country code)."""
        phone = PhoneNumber.from_string("0049 151 12345678")
        assert phone.country_code == "+49"

    def test_invalid_phone_too_short(self):
        """Test rejection of too short phone number."""
        with pytest.raises(ValueError) as exc_info:
            PhoneNumber.from_string("+49 123")
        assert "Invalid phone number" in str(exc_info.value)

    def test_invalid_phone_format(self):
        """Test rejection of invalid phone format."""
        with pytest.raises(ValueError) as exc_info:
            PhoneNumber.from_string("not-a-phone")
        assert "Invalid phone number" in str(exc_info.value)

    def test_invalid_phone_missing_country_code(self):
        """Test rejection of phone without country code."""
        with pytest.raises(ValueError) as exc_info:
            PhoneNumber.from_string("151 12345678")
        assert "Invalid phone number" in str(exc_info.value)

    def test_phone_immutability(self):
        """Test that PhoneNumber is immutable."""
        phone = PhoneNumber.from_string("+49 151 12345678")
        with pytest.raises(ValidationError):
            phone.country_code = "+1"


class TestLanguageCode:
    """Test cases for LanguageCode value object."""

    def test_valid_german(self):
        """Test valid German language code."""
        lang = LanguageCode(code="de")
        assert lang.code == "de"
        assert str(lang) == "de"

    def test_valid_english(self):
        """Test valid English language code."""
        lang = LanguageCode(code="en")
        assert lang.code == "en"

    def test_all_eu_languages(self):
        """Test all supported EU languages."""
        eu_languages = [
            "de", "en", "fr", "es", "it", "nl", "pl", "pt",
            "cs", "da", "el", "hu", "ro", "sv", "bg", "hr",
            "et", "fi", "ga", "lt", "lv", "mt", "sk", "sl"
        ]
        for lang_code in eu_languages:
            lang = LanguageCode(code=lang_code)
            assert lang.code == lang_code

    def test_uppercase_normalization(self):
        """Test that language codes are normalized to lowercase."""
        lang = LanguageCode(code="DE")
        assert lang.code == "de"

    def test_invalid_language_code(self):
        """Test rejection of unsupported language code."""
        with pytest.raises(ValidationError) as exc_info:
            LanguageCode(code="xx")
        assert "Unsupported language" in str(exc_info.value)

    def test_invalid_language_three_letter_code(self):
        """Test rejection of three-letter language code."""
        with pytest.raises(ValidationError) as exc_info:
            LanguageCode(code="eng")
        assert "Unsupported language" in str(exc_info.value)

    def test_language_immutability(self):
        """Test that LanguageCode is immutable."""
        lang = LanguageCode(code="de")
        with pytest.raises(ValidationError):
            lang.code = "en"


class TestMoney:
    """Test cases for Money value object."""

    def test_valid_money_creation(self):
        """Test creation of valid Money object."""
        money = Money(amount=Decimal("100.50"), currency="EUR")
        assert money.amount == Decimal("100.50")
        assert money.currency == "EUR"

    def test_money_default_currency(self):
        """Test that EUR is default currency."""
        money = Money(amount=Decimal("100"))
        assert money.currency == "EUR"

    def test_money_german_formatting(self):
        """Test German money formatting (1.234,56 €)."""
        money = Money(amount=Decimal("1234.56"), currency="EUR")
        formatted = money.format_german()
        assert formatted == "1.234,56 EUR"

    def test_money_string_representation(self):
        """Test string representation uses German format."""
        money = Money(amount=Decimal("999.99"), currency="EUR")
        assert "999,99" in str(money)

    def test_money_other_currencies(self):
        """Test money with different currencies."""
        usd = Money(amount=Decimal("100"), currency="USD")
        assert usd.currency == "USD"

        gbp = Money(amount=Decimal("100"), currency="GBP")
        assert gbp.currency == "GBP"

    def test_invalid_currency_code_lowercase(self):
        """Test rejection of lowercase currency code."""
        with pytest.raises(ValidationError) as exc_info:
            Money(amount=Decimal("100"), currency="eur")
        assert "Invalid currency code" in str(exc_info.value)

    def test_invalid_currency_code_length(self):
        """Test rejection of invalid currency code length."""
        with pytest.raises(ValidationError) as exc_info:
            Money(amount=Decimal("100"), currency="EU")
        assert "Invalid currency code" in str(exc_info.value)

    def test_invalid_decimal_places(self):
        """Test rejection of more than 4 decimal places."""
        with pytest.raises(ValidationError) as exc_info:
            Money(amount=Decimal("100.123456"), currency="EUR")
        assert "more than 4 decimal places" in str(exc_info.value)

    def test_money_addition_same_currency(self):
        """Test addition of money with same currency."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("50"), currency="EUR")
        result = m1 + m2
        assert result.amount == Decimal("150")
        assert result.currency == "EUR"

    def test_money_addition_different_currency(self):
        """Test rejection of addition with different currencies."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("50"), currency="USD")
        with pytest.raises(ValueError) as exc_info:
            m1 + m2
        assert "Cannot add different currencies" in str(exc_info.value)

    def test_money_subtraction_same_currency(self):
        """Test subtraction of money with same currency."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("30"), currency="EUR")
        result = m1 - m2
        assert result.amount == Decimal("70")
        assert result.currency == "EUR"

    def test_money_subtraction_different_currency(self):
        """Test rejection of subtraction with different currencies."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("50"), currency="GBP")
        with pytest.raises(ValueError) as exc_info:
            m1 - m2
        assert "Cannot subtract different currencies" in str(exc_info.value)

    def test_money_multiplication(self):
        """Test multiplication of money by scalar."""
        money = Money(amount=Decimal("100"), currency="EUR")
        result = money * Decimal("1.5")
        assert result.amount == Decimal("150")
        assert result.currency == "EUR"

    def test_money_comparison_less_than(self):
        """Test less than comparison."""
        m1 = Money(amount=Decimal("50"), currency="EUR")
        m2 = Money(amount=Decimal("100"), currency="EUR")
        assert m1 < m2
        assert not m2 < m1

    def test_money_comparison_less_equal(self):
        """Test less than or equal comparison."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("100"), currency="EUR")
        m3 = Money(amount=Decimal("150"), currency="EUR")
        assert m1 <= m2
        assert m1 <= m3

    def test_money_comparison_greater_than(self):
        """Test greater than comparison."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("50"), currency="EUR")
        assert m1 > m2
        assert not m2 > m1

    def test_money_comparison_greater_equal(self):
        """Test greater than or equal comparison."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("100"), currency="EUR")
        m3 = Money(amount=Decimal("50"), currency="EUR")
        assert m1 >= m2
        assert m1 >= m3

    def test_money_comparison_different_currency(self):
        """Test that comparing different currencies raises error."""
        m1 = Money(amount=Decimal("100"), currency="EUR")
        m2 = Money(amount=Decimal("100"), currency="USD")
        with pytest.raises(ValueError) as exc_info:
            m1 < m2
        assert "Cannot compare different currencies" in str(exc_info.value)

    def test_money_immutability(self):
        """Test that Money is immutable."""
        money = Money(amount=Decimal("100"), currency="EUR")
        with pytest.raises(ValidationError):
            money.amount = Decimal("200")


class TestBudgetRange:
    """Test cases for BudgetRange value object."""

    def test_valid_budget_range(self):
        """Test creation of valid budget range."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money, max_amount=max_money)
        assert budget_range.min_amount == min_money
        assert budget_range.max_amount == max_money

    def test_budget_range_only_min(self):
        """Test budget range with only minimum."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money)
        assert budget_range.min_amount == min_money
        assert budget_range.max_amount is None

    def test_budget_range_only_max(self):
        """Test budget range with only maximum."""
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(max_amount=max_money)
        assert budget_range.min_amount is None
        assert budget_range.max_amount == max_money

    def test_budget_range_no_limits(self):
        """Test budget range with no limits."""
        budget_range = BudgetRange()
        assert budget_range.min_amount is None
        assert budget_range.max_amount is None

    def test_invalid_budget_range_min_greater_max(self):
        """Test rejection when min > max."""
        min_money = Money(amount=Decimal("5000"), currency="EUR")
        max_money = Money(amount=Decimal("1000"), currency="EUR")
        with pytest.raises(ValidationError) as exc_info:
            BudgetRange(min_amount=min_money, max_amount=max_money)
        assert "Min amount cannot exceed max amount" in str(exc_info.value)

    def test_budget_range_contains_within_range(self):
        """Test that amount within range returns True."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money, max_amount=max_money)

        test_money = Money(amount=Decimal("3000"), currency="EUR")
        assert budget_range.contains(test_money)

    def test_budget_range_contains_at_min(self):
        """Test that amount at minimum boundary returns True."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money, max_amount=max_money)
        assert budget_range.contains(min_money)

    def test_budget_range_contains_at_max(self):
        """Test that amount at maximum boundary returns True."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money, max_amount=max_money)
        assert budget_range.contains(max_money)

    def test_budget_range_contains_below_min(self):
        """Test that amount below minimum returns False."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money)

        test_money = Money(amount=Decimal("500"), currency="EUR")
        assert not budget_range.contains(test_money)

    def test_budget_range_contains_above_max(self):
        """Test that amount above maximum returns False."""
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(max_amount=max_money)

        test_money = Money(amount=Decimal("6000"), currency="EUR")
        assert not budget_range.contains(test_money)

    def test_budget_range_contains_no_limits(self):
        """Test that any amount is contained when no limits set."""
        budget_range = BudgetRange()
        test_money = Money(amount=Decimal("99999"), currency="EUR")
        assert budget_range.contains(test_money)

    def test_budget_range_immutability(self):
        """Test that BudgetRange is immutable."""
        min_money = Money(amount=Decimal("1000"), currency="EUR")
        max_money = Money(amount=Decimal("5000"), currency="EUR")
        budget_range = BudgetRange(min_amount=min_money, max_amount=max_money)
        with pytest.raises(ValidationError):
            budget_range.min_amount = Money(amount=Decimal("2000"), currency="EUR")
