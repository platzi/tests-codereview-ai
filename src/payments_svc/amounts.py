from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Final


CENT: Final = Decimal("0.01")
MAX_AMOUNT: Final = Decimal("100000.00")

FEE_RATES: Final[dict[str, Decimal]] = {
    "USD": Decimal("0.029"),
    "EUR": Decimal("0.025"),
    "COP": Decimal("0.019"),
}

MINIMUM_FEES: Final[dict[str, Decimal]] = {
    "USD": Decimal("0.30"),
    "EUR": Decimal("0.25"),
    "COP": Decimal("900.00"),
}


class AmountError(ValueError):
    """Raised when an amount cannot be used in a payment operation."""


class CurrencyError(ValueError):
    """Raised when a currency is missing or unsupported."""


def parse_amount(raw: str | int | Decimal) -> Decimal:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        raise AmountError("amount is required")

    if isinstance(raw, float):
        raise AmountError("amount cannot be a float")

    try:
        amount = Decimal(str(raw).strip())
    except (AttributeError, InvalidOperation) as exc:
        raise AmountError("amount must be numeric") from exc

    if not amount.is_finite():
        raise AmountError("amount must be finite")

    return amount


def normalize_currency(currency: str) -> str:
    if currency is None:
        raise CurrencyError("currency is required")

    normalized = currency.strip().upper()
    if not normalized:
        raise CurrencyError("currency is required")

    if normalized not in FEE_RATES:
        raise CurrencyError(f"unsupported currency: {normalized}")

    return normalized


def validate_amount(amount: Decimal) -> None:
    if amount < Decimal("0"):
        raise AmountError("amount cannot be negative")

    if amount < CENT:
        raise AmountError("amount must be at least 0.01")

    if amount > MAX_AMOUNT:
        raise AmountError("amount exceeds maximum allowed")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_fee(amount: Decimal, currency: str) -> Decimal:
    currency = normalize_currency(currency)
    validate_amount(amount)

    if amount == Decimal("0"):
        return Decimal("0.00")

    percentage_fee = amount * FEE_RATES[currency]
    fee = max(percentage_fee, MINIMUM_FEES[currency])
    return round_money(fee)


def total_with_fee(amount: Decimal, currency: str) -> Decimal:
    validate_amount(amount)
    return round_money(amount + calculate_fee(amount, currency))

