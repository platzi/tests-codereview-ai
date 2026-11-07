import unittest
from datetime import date
from decimal import Decimal as D
from unittest.mock import Mock

from payments_svc.amounts import AmountError
from payments_svc.legacy.settlement import (
    Merchant, PaymentBatch, SettlementAdjustment, build_settlement_report,
    calculate_reserve_amount, convert_money, round_money, sum_money,
)


class SettlementTest(unittest.TestCase):
    def setUp(self):
        self.day = date(2026, 1, 1)
        self.repository = Mock()
        self.repository.list_merchants_for_settlement.return_value = [
            Merchant("merchant-1", "SV", "USD", D("0.05"))
        ]
        self.repository.load_payment_batch.return_value = PaymentBatch(
            "merchant-1", D("1000"), D("30"), D("100"), "USD"
        )
        self.repository.load_manual_adjustments.return_value = [
            SettlementAdjustment("merchant-1", D("10"), "correction")
        ]
        self.fx = Mock()

    def report(self):
        return build_settlement_report(self.day, self.repository, self.fx)

    def test_valid_report_preserves_formula_and_totals(self):
        report = self.report()
        line = report.lines[0]
        self.assertEqual(line.reserve_amount, D("45.00"))
        self.assertEqual(line.net_amount, D("835.00"))
        self.assertEqual(
            (report.total_gross, report.total_fees, report.total_refunds,
             report.total_adjustments, report.total_reserve, report.total_net),
            (D("1000"), D("30"), D("100"), D("10"), D("45"), D("835")),
        )
        self.assertEqual(report.currency, "USD")
        self.fx.convert.assert_not_called()

    def test_negative_reserve_rate_is_rejected(self):
        with self.assertRaises(AmountError):
            calculate_reserve_amount(D("100"), D("0"), D("-0.10"))

    def test_zero_and_rates_above_one_are_not_rejected(self):
        for rate, expected in (("0", "0.00"), ("1.5", "150.00")):
            with self.subTest(rate=rate):
                self.assertEqual(
                    calculate_reserve_amount(D("100"), D("0"), D(rate)),
                    D(expected),
                )

    def test_non_finite_reserve_inputs_are_rejected(self):
        for raw in ("NaN", "Infinity", "-Infinity"):
            for position in range(3):
                with self.subTest(raw=raw, position=position):
                    values = [D("100"), D("0"), D("0.05")]
                    values[position] = D(raw)
                    with self.assertRaises(AmountError):
                        calculate_reserve_amount(*values)

    def test_non_finite_money_is_rejected_before_conversion_or_summing(self):
        for raw in ("NaN", "Infinity", "-Infinity"):
            value = D(raw)
            for operation in (
                lambda: round_money(value),
                lambda: sum_money([D("1"), value]),
                lambda: convert_money(self.fx, value, "USD", "EUR"),
                lambda: convert_money(self.fx, value, "USD", "USD"),
            ):
                with self.subTest(raw=raw, operation=operation):
                    with self.assertRaises(AmountError):
                        operation()
        self.fx.convert.assert_not_called()

    def test_non_finite_fx_results_are_rejected(self):
        for raw in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(raw=raw):
                self.fx.convert.return_value = D(raw)
                with self.assertRaises(AmountError):
                    convert_money(self.fx, D("10"), "EUR", "USD")

    def test_valid_conversion_preserves_commercial_rounding(self):
        self.fx.convert.return_value = D("1.005")
        self.assertEqual(convert_money(self.fx, D("1"), "EUR", "USD"), D("1.01"))
        self.fx.convert.assert_called_once_with(D("1"), "EUR", "USD")

    def test_batch_from_another_merchant_is_rejected(self):
        self.repository.load_payment_batch.return_value = PaymentBatch(
            "merchant-2", D("1000"), D("30"), D("100"), "USD"
        )
        with self.assertRaises(AmountError):
            self.report()

    def test_adjustment_from_another_merchant_is_rejected(self):
        self.repository.load_manual_adjustments.return_value = [
            SettlementAdjustment("merchant-2", D("10"), "correction")
        ]
        with self.assertRaises(AmountError):
            self.report()

    def test_non_finite_batch_and_adjustment_amounts_are_rejected(self):
        for raw in ("NaN", "Infinity", "-Infinity"):
            for position in range(3):
                with self.subTest(raw=raw, position=position):
                    values = [D("1000"), D("30"), D("100")]
                    values[position] = D(raw)
                    self.repository.load_payment_batch.return_value = PaymentBatch(
                        "merchant-1", *values, "USD"
                    )
                    with self.assertRaises(AmountError):
                        self.report()
            self.repository.load_payment_batch.return_value = PaymentBatch(
                "merchant-1", D("1000"), D("30"), D("100"), "USD"
            )
            self.repository.load_manual_adjustments.return_value = [
                SettlementAdjustment("merchant-1", D(raw), "correction")
            ]
            with self.subTest(raw=raw, field="adjustment"):
                with self.assertRaises(AmountError):
                    self.report()
            self.repository.load_manual_adjustments.return_value = []
