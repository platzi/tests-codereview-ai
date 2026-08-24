from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Final


CENT: Final = Decimal("0.01")
MIN_AMOUNT: Final = Decimal("0")
MAX_AMOUNT: Final = Decimal("100000.00")


@dataclass(frozen=True)
class CurrencyConfig:
    """Una sola fuente de verdad por moneda (resuelve EQ-08: antes rate y
    min_fee vivian en dos dicts sin acoplar y podian desincronizarse)."""

    rate: Decimal
    min_fee: Decimal
    max_amount: Decimal
    exponent: int


CURRENCY_CONFIG: Final[dict[str, CurrencyConfig]] = {
    "USD": CurrencyConfig(
        rate=Decimal("0.029"),
        min_fee=Decimal("0.30"),
        max_amount=Decimal("100000"),
        exponent=2,
    ),
    "EUR": CurrencyConfig(
        rate=Decimal("0.025"),
        min_fee=Decimal("0.25"),
        max_amount=Decimal("100000"),
        exponent=2,
    ),
    "COP": CurrencyConfig(
        rate=Decimal("0.019"),
        min_fee=Decimal("900"),
        # ~USD 100000 convertidos a una tasa fija de 3072 COP/USD (aproximacion
        # documentada, no una tasa de mercado en vivo). Resuelve CN-03: el
        # tope global de 100000 era ~25 USD en COP, absurdamente restrictivo.
        max_amount=Decimal("307200000"),
        # COP no usa unidad menor en la practica de pagos (CN-04). Distinto
        # del digito ISO 4217 "de jure"; es una decision de negocio explicita.
        exponent=0,
    ),
}


class AmountError(ValueError):
    """Raised when an amount cannot be used in a payment operation."""


class CurrencyError(ValueError):
    """Raised when a currency is missing or unsupported."""


def parse_amount(raw: str | int | Decimal) -> Decimal:
    if raw is None:
        raise AmountError("amount is required")

    # EQ-02: float queda fuera del contrato de dinero (perdida de precision
    # binaria); solo se acepta str | int | Decimal.
    if isinstance(raw, float):
        raise AmountError("amount must not be a float; use str, int, or Decimal")

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

    # EQ-05: cualquier no-str distinto de None debe rechazarse como
    # CurrencyError, no reventar en .strip() con AttributeError.
    if not isinstance(currency, str):
        raise CurrencyError("currency must be a string")

    normalized = currency.strip().upper()
    if not normalized:
        raise CurrencyError("currency is required")

    if normalized not in CURRENCY_CONFIG:
        raise CurrencyError(f"unsupported currency: {normalized}")

    return normalized


def _validate_amount_shape(amount: Decimal) -> None:
    # EQ-01: is_finite() no lanza sobre NaN/Infinity (a diferencia de los
    # operadores de comparacion), por lo que validate_amount pasa a ser el
    # guardian unico que traduce esos casos a AmountError.
    if not amount.is_finite():
        raise AmountError("amount must be finite")

    if amount < Decimal("0"):
        raise AmountError("amount cannot be negative")

    if amount <= MIN_AMOUNT:
        raise AmountError("amount must be greater than the minimum allowed")


def validate_amount(amount: Decimal) -> None:
    """Guardian generico sin contexto de moneda (usado por callers como
    refunds que no conocen la moneda del pago original)."""
    _validate_amount_shape(amount)

    if amount > MAX_AMOUNT:
        raise AmountError("amount exceeds maximum allowed")


def validate_amount_for_currency(amount: Decimal, currency: str) -> None:
    """Guardian usado por calculate_fee/total_with_fee: aplica el tope
    propio de cada moneda (CN-03) en vez del tope global unico."""
    _validate_amount_shape(amount)

    max_amount = CURRENCY_CONFIG[currency].max_amount
    if amount > max_amount:
        raise AmountError("amount exceeds maximum allowed for currency")


def validate_non_negative_amount(amount: Decimal) -> None:
    """Guardian para acumuladores como `already_refunded`, que a diferencia
    de un monto de transaccion nuevo si pueden ser 0 (decision confirmada:
    'separar la validacion' entre monto de transaccion y acumulador)."""
    if not amount.is_finite():
        raise AmountError("amount must be finite")

    if amount < Decimal("0"):
        raise AmountError("amount cannot be negative")

    if amount > MAX_AMOUNT:
        raise AmountError("amount exceeds maximum allowed")


def round_money(value: Decimal) -> Decimal:
    """Cuantizador generico a centavos (2 decimales), para callers sin
    contexto de moneda."""
    return value.quantize(CENT, rounding=ROUND_HALF_EVEN)


def round_money_for_currency(value: Decimal, currency: str) -> Decimal:
    """CN-04: cuantiza segun el exponente propio de cada moneda en vez de
    asumir siempre 2 decimales (COP no usa unidad menor en la practica)."""
    exponent = CURRENCY_CONFIG[currency].exponent
    quantum = Decimal(1).scaleb(-exponent)
    return value.quantize(quantum, rounding=ROUND_HALF_EVEN)


def calculate_fee(amount: Decimal, currency: str) -> Decimal:
    # CN-06: normalizar la moneda antes de validar el monto, en el mismo
    # orden que total_with_fee, para que ambas puertas de entrada fallen con
    # el mismo tipo de error ante la misma entrada invalida.
    currency = normalize_currency(currency)
    validate_amount_for_currency(amount, currency)

    config = CURRENCY_CONFIG[currency]
    percentage_fee = amount * config.rate
    fee = max(percentage_fee, config.min_fee)
    return round_money_for_currency(fee, currency)


def total_with_fee(amount: Decimal, currency: str) -> Decimal:
    currency = normalize_currency(currency)
    validate_amount_for_currency(amount, currency)

    fee = calculate_fee(amount, currency)
    return round_money_for_currency(amount + fee, currency)
