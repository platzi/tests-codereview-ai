from decimal import Decimal
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from payments_svc.amounts import (
    AmountError,
    CurrencyError,
    calculate_fee,
    normalize_currency,
    parse_amount,
    round_money,
    total_with_fee,
    validate_amount,
)


class ParseAmountTests(unittest.TestCase):
    def test_numeric_inputs_preserve_precision(self):
        for raw, expected in [
            (" 12.340 ", "12.340"),
            (12, "12"),
            (0.1, "0.1"),
            (Decimal("1.23456789"), "1.23456789"),
            ("1e2", "100"),
            ("-1", "-1"),
            ("100000.01", "100000.01"),
        ]:
            with self.subTest(raw=raw):
                result = parse_amount(raw)
                self.assertIsInstance(result, Decimal)
                self.assertEqual(result, Decimal(expected))

    def test_missing_amount(self):
        with self.assertRaisesRegex(AmountError, "^amount is required$"):
            parse_amount(None)

    def test_invalid_numeric_inputs(self):
        for raw in ("", "  ", "abc", "1,000.00", True):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(AmountError, "^amount must be numeric$"):
                    parse_amount(raw)

    def test_non_finite_inputs(self):
        for raw in ("NaN", "sNaN", "Infinity", "-Infinity", float("inf"), Decimal("NaN")):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(AmountError, "^amount must be finite$"):
                    parse_amount(raw)


class NormalizeCurrencyTests(unittest.TestCase):
    def test_supported_currencies_are_normalized(self):
        for raw, expected in [(" usd ", "USD"), ("eUr", "EUR"), ("\tcop\n", "COP")]:
            with self.subTest(raw=raw):
                self.assertEqual(normalize_currency(raw), expected)

    def test_missing_currency(self):
        for raw in (None, "", " \t\n"):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(CurrencyError, "^currency is required$"):
                    normalize_currency(raw)

    def test_unsupported_currency(self):
        with self.assertRaisesRegex(CurrencyError, "^unsupported currency: GBP$"):
            normalize_currency(" gbp ")


class ValidateAmountTests(unittest.TestCase):
    def test_inclusive_boundaries(self):
        for amount in ("0", "-0.00", "0.01", "99999.99", "100000.00"):
            with self.subTest(amount=amount):
                self.assertIsNone(validate_amount(Decimal(amount)))

    def test_negative_amount(self):
        with self.assertRaisesRegex(AmountError, "^amount cannot be negative$"):
            validate_amount(Decimal("-0.001"))

    def test_amount_above_maximum(self):
        with self.assertRaisesRegex(AmountError, "^amount exceeds maximum allowed$"):
            validate_amount(Decimal("100000.001"))


class RoundMoneyTests(unittest.TestCase):
    def test_rounds_to_cents_using_half_even(self):
        for value, expected in [
            ("1", "1.00"),
            ("1.234", "1.23"),
            ("1.236", "1.24"),
            ("1.225", "1.22"),
            ("1.235", "1.24"),
            ("-1.225", "-1.22"),
            ("-1.235", "-1.24"),
        ]:
            with self.subTest(value=value):
                result = round_money(Decimal(value))
                self.assertEqual(result, Decimal(expected))
                self.assertEqual(result.as_tuple().exponent, -2)


class CalculateFeeTests(unittest.TestCase):
    def test_minimum_and_percentage_fees_for_each_currency(self):
        for amount, currency, expected in [
            ("1", "USD", "0.30"),
            ("1", "EUR", "0.25"),
            ("1", "COP", "900.00"),
            ("100", " usd ", "2.90"),
            ("100", "EUR", "2.50"),
            ("50000", "COP", "950.00"),
            ("10", "EUR", "0.25"),
            ("10.60", "USD", "0.31"),
            ("100000", "USD", "2900.00"),
            ("100000", "EUR", "2500.00"),
            ("100000", "COP", "1900.00"),
        ]:
            with self.subTest(amount=amount, currency=currency):
                self.assertEqual(calculate_fee(Decimal(amount), currency), Decimal(expected))

    def test_zero_has_no_fee_in_each_currency(self):
        for currency in ("USD", "EUR", "COP"):
            with self.subTest(currency=currency):
                result = calculate_fee(Decimal("0"), currency)
                self.assertEqual(result, Decimal("0.00"))
                self.assertEqual(result.as_tuple().exponent, -2)

    def test_percentage_fee_uses_half_even_rounding(self):
        for amount, expected in [("12.20", "0.30"), ("12.60", "0.32")]:
            with self.subTest(amount=amount):
                self.assertEqual(calculate_fee(Decimal(amount), "EUR"), Decimal(expected))


class TotalWithFeeTests(unittest.TestCase):
    def test_total_includes_fee_and_rounds_to_cents(self):
        for amount, currency, expected in [
            ("100", " usd ", "102.90"),
            ("100", "EUR", "102.50"),
            ("50000", "COP", "50950.00"),
            ("1", "USD", "1.30"),
            ("1.005", "USD", "1.30"),
            ("1.015", "USD", "1.32"),
            ("0", "COP", "0.00"),
            ("100000", "USD", "102900.00"),
        ]:
            with self.subTest(amount=amount, currency=currency):
                result = total_with_fee(Decimal(amount), currency)
                self.assertEqual(result, Decimal(expected))
                self.assertEqual(result.as_tuple().exponent, -2)


class PaymentValidationTests(unittest.TestCase):
    def test_fee_and_total_reject_invalid_amounts(self):
        for operation in (calculate_fee, total_with_fee):
            for amount, message in [
                ("-0.01", "amount cannot be negative"),
                ("100000.01", "amount exceeds maximum allowed"),
            ]:
                with self.subTest(operation=operation.__name__, amount=amount):
                    with self.assertRaisesRegex(AmountError, f"^{message}$"):
                        operation(Decimal(amount), "USD")

    def test_fee_and_total_validate_currency_even_for_zero(self):
        for operation in (calculate_fee, total_with_fee):
            for amount in ("0", "1"):
                for currency in (None, "", "GBP"):
                    with self.subTest(operation=operation.__name__, amount=amount, currency=currency):
                        with self.assertRaises(CurrencyError):
                            operation(Decimal(amount), currency)


if __name__ == "__main__":
    unittest.main()
