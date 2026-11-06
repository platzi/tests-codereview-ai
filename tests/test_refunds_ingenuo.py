import unittest
from decimal import Decimal

from payments_svc.amounts import AmountError
from payments_svc.refunds import (
    RefundStatus,
    assert_refundable,
    calculate_remaining_refundable,
    request_refund,
)


class TestRefundsBefore(unittest.TestCase):
    def test_calculate_remaining_refundable_subtracts_refunded_amount(self):
        remaining = calculate_remaining_refundable(
            original_amount=Decimal("100.00"),
            already_refunded=Decimal("25.00"),
        )

        self.assertEqual(remaining, Decimal("75.00"))

    def test_request_refund_approves_valid_refund(self):
        decision = request_refund(
            original_amount=Decimal("100.00"),
            refund_amount=Decimal("25.00"),
        )

        self.assertEqual(decision.status, RefundStatus.APPROVED)
        self.assertEqual(decision.amount, Decimal("25.00"))
        self.assertIsNone(decision.reason)

    def test_request_refund_rejects_zero_refund(self):
        decision = request_refund(
            original_amount=Decimal("100.00"),
            refund_amount=Decimal("0.00"),
        )

        self.assertEqual(decision.status, RefundStatus.REJECTED)
        self.assertEqual(decision.amount, Decimal("0.00"))
        self.assertEqual(decision.reason, "refund amount must be greater than zero")

    def test_request_refund_rejects_fully_refunded_payment(self):
        decision = request_refund(
            original_amount=Decimal("100.00"),
            refund_amount=Decimal("10.00"),
            already_refunded=Decimal("100.00"),
        )

        self.assertEqual(decision.status, RefundStatus.REJECTED)
        self.assertEqual(decision.amount, Decimal("0.00"))
        self.assertEqual(decision.reason, "payment is already fully refunded")

    def test_assert_refundable_raises_for_rejected_refund(self):
        with self.assertRaises(AmountError):
            assert_refundable(Decimal("100.00"), Decimal("0.00"))