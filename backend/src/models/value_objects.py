"""Value objects for domain models."""

import re
from decimal import Decimal
from typing import ClassVar, Optional
from pydantic import BaseModel, field_validator
import phonenumbers


class EmailAddress(BaseModel):
    """Email address value object with validation."""

    value: str

    @field_validator('value')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError(f"Invalid email address: {v}")
        return v.lower()

    def __str__(self) -> str:
        return self.value

    class Config:
        frozen = True


class PhoneNumber(BaseModel):
    """Phone number value object with international format validation."""

    country_code: str
    number: str

    @classmethod
    def from_string(cls, full_number: str) -> "PhoneNumber":
        """Parse and validate phone number."""
        try:
            parsed = phonenumbers.parse(full_number)
            if not phonenumbers.is_valid_number(parsed):
                raise ValueError(f"Invalid phone number: {full_number}")
            return cls(
                country_code=f"+{parsed.country_code}",
                number=str(parsed.national_number)
            )
        except phonenumbers.NumberParseException as e:
            raise ValueError(f"Invalid phone number format: {full_number}") from e

    def __str__(self) -> str:
        return f"{self.country_code} {self.number}"

    class Config:
        frozen = True


class LanguageCode(BaseModel):
    """ISO 639-1 language code with EU language support."""

    code: str

    SUPPORTED_LANGUAGES: ClassVar[list[str]] = [
        "de", "en", "fr", "es", "it", "nl", "pl", "pt",
        "cs", "da", "el", "hu", "ro", "sv", "bg", "hr",
        "et", "fi", "ga", "lt", "lv", "mt", "sk", "sl"
    ]

    @field_validator('code')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code is supported."""
        if v not in cls.SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {v}. Supported: {', '.join(cls.SUPPORTED_LANGUAGES)}")
        return v.lower()

    def __str__(self) -> str:
        return self.code

    class Config:
        frozen = True


class Money(BaseModel):
    """Money value object with German formatting support."""

    amount: Decimal
    currency: str = "EUR"

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount has max 4 decimal places."""
        if v.as_tuple().exponent < -4:
            raise ValueError("Amount cannot have more than 4 decimal places")
        return v

    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate ISO 4217 currency code."""
        if len(v) != 3 or not v.isupper():
            raise ValueError(f"Invalid currency code: {v}. Must be ISO 4217 format")
        return v

    def format_german(self) -> str:
        """Format money in German style: 1.234,56 €"""
        # Round to 2 decimal places for display
        amount_str = f"{self.amount:,.2f}"
        # Replace separators (1,234.56 -> 1.234,56)
        amount_str = amount_str.replace(',', '_').replace('.', ',').replace('_', '.')
        return f"{amount_str} {self.currency}"

    def __str__(self) -> str:
        return self.format_german()

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")
        return Money(amount=self.amount - other.amount, currency=self.currency)

    def __mul__(self, multiplier: Decimal) -> "Money":
        return Money(amount=self.amount * multiplier, currency=self.currency)

    def __lt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")
        return self.amount >= other.amount

    class Config:
        frozen = True


class BudgetRange(BaseModel):
    """Budget range value object."""

    min_amount: Optional[Money] = None
    max_amount: Optional[Money] = None

    @field_validator('max_amount')
    @classmethod
    def validate_range(cls, v: Optional[Money], info) -> Optional[Money]:
        """Ensure min <= max."""
        min_amount = info.data.get('min_amount')
        if min_amount and v and min_amount.amount > v.amount:
            raise ValueError("Min amount cannot exceed max amount")
        return v

    def contains(self, amount: Money) -> bool:
        """Check if amount is within range."""
        if self.min_amount and amount < self.min_amount:
            return False
        if self.max_amount and amount > self.max_amount:
            return False
        return True

    class Config:
        frozen = True
