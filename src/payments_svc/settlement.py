from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from collections.abc import Iterable
from typing import Protocol


# ---------------------------------------------------------------------------
# Domain entities
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Merchant:
    id: str
    country: str
    settlement_currency: str
    reserve_rate: Decimal


@dataclass(frozen=True)
class PaymentBatch:
    merchant_id: str
    gross_amount: Decimal
    fee_amount: Decimal
    refund_amount: Decimal
    currency: str


@dataclass(frozen=True)
class SettlementAdjustment:
    merchant_id: str
    amount: Decimal
    reason: str


@dataclass(frozen=True)
class SettlementLine:
    merchant_id: str
    gross_amount: Decimal
    fee_amount: Decimal
    refund_amount: Decimal
    adjustment_amount: Decimal
    reserve_amount: Decimal
    net_amount: Decimal
    currency: str


@dataclass(frozen=True)
class SettlementReport:
    settlement_date: date
    lines: tuple[SettlementLine, ...]
    total_gross: Decimal
    total_fees: Decimal
    total_refunds: Decimal
    total_adjustments: Decimal
    total_reserve: Decimal
    total_net: Decimal


# ---------------------------------------------------------------------------
# Injected dependencies (kept as protocols so this module stays free of I/O)
# ---------------------------------------------------------------------------

class FxRateProvider(Protocol):
    """Supplies FX rates. Implementations may hit a DB, cache, or an API."""

    def get_rate(self, from_currency: str, to_currency: str) -> Decimal:
        ...


class MerchantRepository(Protocol):
    """Resolves merchant metadata needed to compute a settlement."""

    def get_merchant(self, merchant_id: str) -> Merchant:
        ...


# ---------------------------------------------------------------------------
# Money utilities
# ---------------------------------------------------------------------------

CENTS = Decimal("0.01")


def round_money(amount: Decimal) -> Decimal:
    """Round to the nearest cent using standard half-up rounding."""
    return amount.quantize(CENTS, rounding=ROUND_HALF_UP)


def sum_money(amounts: Iterable[Decimal]) -> Decimal:
    """Sum an iterable of amounts and round the result to the nearest cent."""
    total = sum(amounts, Decimal("0"))
    return round_money(total)


def convert_money(
    amount: Decimal,
    from_currency: str,
    to_currency: str,
    fx_rates: FxRateProvider,
) -> Decimal:
    """Convert an amount between currencies.

    Skips the FX lookup entirely when the source and destination
    currencies match, avoiding an unnecessary dependency call.
    """
    if from_currency == to_currency:
        return round_money(amount)

    rate = fx_rates.get_rate(from_currency, to_currency)
    return round_money(amount * rate)


# ---------------------------------------------------------------------------
# Settlement calculation
# ---------------------------------------------------------------------------

def _adjustment_total(
    merchant_id: str,
    adjustments: Iterable[SettlementAdjustment],
) -> Decimal:
    relevant = (adj.amount for adj in adjustments if adj.merchant_id == merchant_id)
    return sum_money(relevant)


def build_settlement_line(
    batch: PaymentBatch,
    merchant: Merchant,
    adjustments: Iterable[SettlementAdjustment],
    fx_rates: FxRateProvider,
) -> SettlementLine:
    """Build a single settlement line for one merchant's payment batch.

    Amounts are converted into the merchant's settlement currency,
    a reserve is withheld based on the merchant's reserve rate, and
    any matching adjustments are folded into the net amount.
    """
    to_currency = merchant.settlement_currency

    gross = convert_money(batch.gross_amount, batch.currency, to_currency, fx_rates)
    fees = convert_money(batch.fee_amount, batch.currency, to_currency, fx_rates)
    refunds = convert_money(batch.refund_amount, batch.currency, to_currency, fx_rates)
    adjustment_total = _adjustment_total(batch.merchant_id, adjustments)

    payable = gross - fees - refunds + adjustment_total
    reserve = round_money(payable * merchant.reserve_rate)
    net = round_money(payable - reserve)

    return SettlementLine(
        merchant_id=batch.merchant_id,
        gross_amount=gross,
        fee_amount=fees,
        refund_amount=refunds,
        adjustment_amount=adjustment_total,
        reserve_amount=reserve,
        net_amount=net,
        currency=to_currency,
    )


def build_settlement_report(
    settlement_date: date,
    batches: Iterable[PaymentBatch],
    adjustments: Iterable[SettlementAdjustment],
    merchants: MerchantRepository,
    fx_rates: FxRateProvider,
) -> SettlementReport:
    """Build the full settlement report for a set of payment batches.

    Pure domain logic: no I/O happens here directly. The repository
    and FX rates are injected, so this is easy to test with fakes.
    """
    adjustments = list(adjustments)

    lines = tuple(
        build_settlement_line(
            batch,
            merchants.get_merchant(batch.merchant_id),
            adjustments,
            fx_rates,
        )
        for batch in batches
    )

    return SettlementReport(
        settlement_date=settlement_date,
        lines=lines,
        total_gross=sum_money(line.gross_amount for line in lines),
        total_fees=sum_money(line.fee_amount for line in lines),
        total_refunds=sum_money(line.refund_amount for line in lines),
        total_adjustments=sum_money(line.adjustment_amount for line in lines),
        total_reserve=sum_money(line.reserve_amount for line in lines),
        total_net=sum_money(line.net_amount for line in lines),
    )