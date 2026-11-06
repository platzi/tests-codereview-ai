import unittest
from decimal import Decimal

from payments_svc.amounts import (
    AmountError, CurrencyError, MAX_AMOUNT, calculate_fee,
    normalize_currency, parse_amount, round_money, total_with_fee,
    validate_amount,
)


class AmountsTest(unittest.TestCase):
    def test_parse_amount_rejects_missing_amount(self):
        # FM-NULL-01
        # Arrange
        raw = None
        # Act
        with self.assertRaises(AmountError) as error:
            parse_amount(raw)
        # Assert
        self.assertIn("required", str(error.exception))

    def test_parse_amount_reports_blank_input_as_missing(self):
        # FM-NULL-02
        # Arrange
        inputs = ("", "   ", "\t\n")
        for raw in inputs:
            with self.subTest(raw=raw):
                # Act
                with self.assertRaises(AmountError) as error:
                    parse_amount(raw)
                # Assert
                self.assertEqual(str(error.exception), "amount is required")

    def test_normalize_currency_rejects_missing_currency(self):
        # FM-NULL-03
        # Arrange
        currency = None
        # Act
        with self.assertRaises(CurrencyError) as error:
            normalize_currency(currency)
        # Assert
        self.assertIn("required", str(error.exception))

    def test_normalize_currency_reports_blank_currency_as_missing(self):
        # FM-NULL-04
        # Arrange
        inputs = ("", "   ", "\t\n")
        for currency in inputs:
            with self.subTest(currency=currency):
                # Act
                with self.assertRaises(CurrencyError) as error:
                    normalize_currency(currency)
                # Assert
                self.assertEqual(str(error.exception), "currency is required")

    def test_validate_amount_rejects_negative_amounts(self):
        # FM-FRONT-01
        # Arrange
        amounts = (Decimal("-0.01"), Decimal("-100"))
        for amount in amounts:
            with self.subTest(amount=amount):
                # Act / Assert
                with self.assertRaises(AmountError):
                    validate_amount(amount)

    def test_validate_amount_accepts_maximum_and_rejects_excess(self):
        # FM-FRONT-02
        # Arrange
        maximum = MAX_AMOUNT
        excess = maximum + Decimal("0.01")
        # Act
        result = validate_amount(maximum)
        # Assert
        self.assertIsNone(result)
        # Act / Assert
        with self.assertRaises(AmountError):
            validate_amount(excess)

    def test_validate_amount_rejects_zero_regardless_of_representation(self):
        # FM-FRONT-03
        # Arrange
        amounts = (Decimal("0"), Decimal("0.00"), Decimal("-0.00"))
        for amount in amounts:
            with self.subTest(amount=repr(amount)):
                # Act / Assert
                with self.assertRaises(AmountError):
                    validate_amount(amount)

    def test_parse_amount_rejects_non_finite_values(self):
        # FM-FRONT-04
        # Arrange
        inputs = ("NaN", "Infinity", "-Infinity")
        for raw in inputs:
            with self.subTest(raw=raw):
                # Act / Assert
                with self.assertRaises(AmountError):
                    parse_amount(raw)

    def test_round_money_uses_commercial_rounding_at_half_cent(self):
        # FM-FRONT-05
        # Arrange
        cases = ((Decimal("1.005"), Decimal("1.01")), (Decimal("1.015"), Decimal("1.02")))
        for amount, expected in cases:
            with self.subTest(amount=amount):
                # Act
                result = round_money(amount)
                # Assert
                self.assertEqual(result, expected)

    def test_parse_amount_rejects_float_inputs(self):
        # FM-EQUIV-01
        # Arrange
        inputs = (100.0, 100.03, 0.1 + 0.2, 0.0)
        for raw in inputs:
            with self.subTest(raw=raw):
                # Act / Assert
                with self.assertRaises(AmountError):
                    parse_amount(raw)

    def test_parse_amount_rejects_localized_numeric_formats(self):
        # FM-EQUIV-02
        # Arrange
        inputs = ("1,000.50", "1.000,50", "1 000.50")
        for raw in inputs:
            with self.subTest(raw=raw):
                # Act / Assert
                with self.assertRaises(AmountError):
                    parse_amount(raw)

    def test_parse_amount_accepts_canonical_decimal_format(self):
        # FM-EQUIV-02
        # Arrange
        raw = "1000.50"
        # Act
        result = parse_amount(raw)
        # Assert
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("1000.50"))

    def test_parse_amount_rejects_unsupported_types(self):
        # FM-EQUIV-03
        # Arrange
        inputs = ([], {}, (), object())
        for raw in inputs:
            with self.subTest(raw=raw):
                # Act / Assert
                with self.assertRaises(AmountError):
                    parse_amount(raw)

    def test_parse_amount_accepts_supported_numeric_input_types(self):
        # FM-EQUIV-03
        # Arrange
        inputs = ("12", 12, Decimal("12"))
        for raw in inputs:
            with self.subTest(raw=raw, input_type=type(raw).__name__):
                # Act
                result = parse_amount(raw)
                # Assert
                self.assertIsInstance(result, Decimal)
                self.assertEqual(result, Decimal("12"))

    def test_normalize_currency_trims_spaces_and_uppercases(self):
        # FM-EQUIV-04
        # Arrange
        cases = (("  usd  ", "USD"), ("Usd", "USD"), (" eur ", "EUR"), ("cop", "COP"))
        for currency, expected in cases:
            with self.subTest(currency=currency):
                # Act
                result = normalize_currency(currency)
                # Assert
                self.assertEqual(result, expected)

    def test_calculate_fee_applies_global_base_limit_to_all_currencies(self):
        # FM-BIZ-01
        # Arrange
        currencies = ("USD", "EUR", "COP")
        for currency in currencies:
            with self.subTest(currency=currency):
                # Act
                fee = calculate_fee(MAX_AMOUNT, currency)
                # Assert
                self.assertIsInstance(fee, Decimal)
                # Act / Assert
                with self.assertRaises(AmountError):
                    calculate_fee(MAX_AMOUNT + Decimal("0.01"), currency)

    def test_total_with_fee_applies_maximum_to_base_amount_only(self):
        # FM-BIZ-02
        # Arrange
        amount = MAX_AMOUNT
        excess = MAX_AMOUNT + Decimal("0.01")
        # Act
        result = total_with_fee(amount, "USD")
        # Assert
        self.assertEqual(result, Decimal("102900.00"))
        self.assertGreater(result, MAX_AMOUNT)
        # Act / Assert
        with self.assertRaises(AmountError):
            total_with_fee(excess, "USD")

    def test_calculate_fee_preserves_configured_rates_and_minimums(self):
        # FM-BIZ-03
        # Arrange
        cases = (
            ("USD", Decimal("1.00"), Decimal("0.30")),
            ("USD", Decimal("100.00"), Decimal("2.90")),
            ("EUR", Decimal("1.00"), Decimal("0.25")),
            ("EUR", Decimal("100.00"), Decimal("2.50")),
            ("COP", Decimal("1.00"), Decimal("900.00")),
            ("COP", Decimal("100000.00"), Decimal("1900.00")),
        )
        for currency, amount, expected in cases:
            with self.subTest(currency=currency, amount=amount):
                # Act
                result = calculate_fee(amount, currency)
                # Assert
                self.assertEqual(result, expected)

    def test_calculate_fee_rejects_currency_without_configuration(self):
        # FM-BIZ-03
        # Arrange
        amount = Decimal("10.00")
        currencies = ("MXN", "BRL")
        for currency in currencies:
            with self.subTest(currency=currency):
                # Act / Assert
                with self.assertRaises(CurrencyError):
                    calculate_fee(amount, currency)

    def test_validate_amount_accepts_minimum_charge(self):
        # FM-BIZ-04
        # Arrange
        amount = Decimal("0.01")
        # Act
        result = validate_amount(amount)
        # Assert
        self.assertIsNone(result)

    def test_validate_amount_rejects_positive_amount_below_minimum_charge(self):
        # FM-BIZ-04
        # Arrange
        amount = Decimal("0.009")
        # Act / Assert
        with self.assertRaises(AmountError):
            validate_amount(amount)

    def test_total_with_fee_rounds_fee_before_rounding_total(self):
        # FM-BIZ-05
        # Arrange
        amount = Decimal("10.344")
        currency = "USD"
        # Act
        fee = calculate_fee(amount, currency)
        total = total_with_fee(amount, currency)
        # Assert
        self.assertEqual(fee, Decimal("0.30"))
        self.assertEqual(total, Decimal("10.64"))


if __name__ == "__main__":
    unittest.main()
