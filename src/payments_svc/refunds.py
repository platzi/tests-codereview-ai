from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from payments_svc.amounts import AmountError, round_money, validate_amount


class RefundStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class RefundDecision:
    status: RefundStatus
    amount: Decimal
    reason: str | None = None


def validate_refunded_amount(amount: Decimal) -> None:
    if amount < Decimal("0"):
        raise AmountError("amount cannot be negative")


def calculate_remaining_refundable(
    original_amount: Decimal,
    already_refunded: Decimal,
) -> Decimal:
    validate_amount(original_amount)
    validate_refunded_amount(already_refunded)
    return round_money(original_amount - already_refunded)


def request_refund(
    original_amount: Decimal,
    refund_amount: Decimal,
    already_refunded: Decimal = Decimal("0.00"),
) -> RefundDecision:
    validate_amount(original_amount)
    validate_refunded_amount(already_refunded)

    if refund_amount == Decimal("0"):
        return RefundDecision(
            status=RefundStatus.REJECTED,
            amount=Decimal("0.00"),
            reason="refund amount must be greater than zero",
        )

    validate_amount(refund_amount)

    remaining = calculate_remaining_refundable(original_amount, already_refunded)

    if remaining <= Decimal("0"):
        return RefundDecision(
            status=RefundStatus.REJECTED,
            amount=Decimal("0.00"),
            reason="payment is already fully refunded",
        )

    return RefundDecision(
        status=RefundStatus.APPROVED,
        amount=round_money(refund_amount),
        reason=None,
    )


def assert_refundable(original_amount: Decimal, refund_amount: Decimal) -> None:
    decision = request_refund(original_amount, refund_amount)
    if decision.status is RefundStatus.REJECTED:
        raise AmountError(decision.reason or "refund rejected")

