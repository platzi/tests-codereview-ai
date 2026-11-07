from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from collections.abc import Iterable
from typing import Protocol

from payments_svc.amounts import AmountError


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
    currency: str
    lines: tuple[SettlementLine, ...]
    total_gross: Decimal
    total_fees: Decimal
    total_refunds: Decimal
    total_adjustments: Decimal
    total_reserve: Decimal
    total_net: Decimal


class SettlementRepository(Protocol):
    def list_merchants_for_settlement(self, settlement_date: date) -> list[Merchant]:
        raise NotImplementedError

    def load_payment_batch(self, merchant_id: str, settlement_date: date) -> PaymentBatch:
        raise NotImplementedError

    def load_manual_adjustments(
        self,
        merchant_id: str,
        settlement_date: date,
    ) -> list[SettlementAdjustment]:
        raise NotImplementedError


class FxRates(Protocol):
    def convert(self, amount: Decimal, source: str, target: str) -> Decimal:
        raise NotImplementedError


def build_settlement_report(
    settlement_date: date,
    repository: SettlementRepository,
    fx_rates: FxRates,
    target_currency: str = "USD",
) -> SettlementReport:
    merchants = repository.list_merchants_for_settlement(settlement_date)
    lines: list[SettlementLine] = []

    for merchant in merchants:
        batch = repository.load_payment_batch(merchant.id, settlement_date)
        if batch.merchant_id != merchant.id:
            raise AmountError("payment batch belongs to another merchant")
        gross_amount = convert_money(
            fx_rates,
            batch.gross_amount,
            batch.currency,
            target_currency,
        )
        fee_amount = convert_money(
            fx_rates,
            batch.fee_amount,
            batch.currency,
            target_currency,
        )
        refund_amount = convert_money(
            fx_rates,
            batch.refund_amount,
            batch.currency,
            target_currency,
        )
        adjustment_amount = calculate_adjustment_total(
            repository,
            merchant.id,
            settlement_date,
            fx_rates,
            target_currency,
        )
        reserve_amount = calculate_reserve_amount(
            gross_amount=gross_amount,
            refund_amount=refund_amount,
            reserve_rate=merchant.reserve_rate,
        )
        net_amount = gross_amount - fee_amount - refund_amount + adjustment_amount
        net_amount = net_amount - reserve_amount

        lines.append(
            SettlementLine(
                merchant_id=merchant.id,
                gross_amount=round_money(gross_amount),
                fee_amount=round_money(fee_amount),
                refund_amount=round_money(refund_amount),
                adjustment_amount=round_money(adjustment_amount),
                reserve_amount=round_money(reserve_amount),
                net_amount=round_money(net_amount),
                currency=target_currency,
            )
        )

    return SettlementReport(
        settlement_date=settlement_date,
        currency=target_currency,
        lines=tuple(lines),
        total_gross=sum_money(line.gross_amount for line in lines),
        total_fees=sum_money(line.fee_amount for line in lines),
        total_refunds=sum_money(line.refund_amount for line in lines),
        total_adjustments=sum_money(line.adjustment_amount for line in lines),
        total_reserve=sum_money(line.reserve_amount for line in lines),
        total_net=sum_money(line.net_amount for line in lines),
    )


def calculate_adjustment_total(
    repository: SettlementRepository,
    merchant_id: str,
    settlement_date: date,
    fx_rates: FxRates,
    target_currency: str,
) -> Decimal:
    adjustments = repository.load_manual_adjustments(merchant_id, settlement_date)
    total = Decimal("0.00")
    for adjustment in adjustments:
        if adjustment.merchant_id != merchant_id:
            raise AmountError("adjustment belongs to another merchant")
        total += convert_money(
            fx_rates,
            adjustment.amount,
            source="USD",
            target=target_currency,
        )
    return round_money(total)


def calculate_reserve_amount(
    gross_amount: Decimal,
    refund_amount: Decimal,
    reserve_rate: Decimal,
) -> Decimal:
    for value in (gross_amount, refund_amount, reserve_rate):
        validate_finite(value)
    if reserve_rate < 0:
        raise AmountError("reserve rate cannot be negative")
    eligible_amount = max(gross_amount - refund_amount, Decimal("0.00"))
    return round_money(eligible_amount * reserve_rate)


def convert_money(
    fx_rates: FxRates,
    amount: Decimal,
    source: str,
    target: str,
) -> Decimal:
    validate_finite(amount)
    if source == target:
        return round_money(amount)
    return round_money(fx_rates.convert(amount, source, target))


def round_money(amount: Decimal) -> Decimal:
    validate_finite(amount)
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def validate_finite(value: Decimal) -> None:
    if not value.is_finite():
        raise AmountError("settlement values must be finite")


def sum_money(amounts: Iterable[Decimal]) -> Decimal:
    total = Decimal("0.00")
    for amount in amounts:
        validate_finite(amount)
        total += amount
    return round_money(total)
