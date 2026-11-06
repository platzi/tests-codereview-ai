import os
import sys
import unittest
from decimal import Decimal

# Add 'src' directory to python path for importing payments_svc
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from payments_svc.amounts import (
    parse_amount,
    normalize_currency,
    validate_amount,
    round_money,
    calculate_fee,
    total_with_fee,
    AmountError,
    CurrencyError,
    MAX_AMOUNT
)

class TestAmounts(unittest.TestCase):
    # --- 1. Null / Vacío ---

    def test_fm_null_01_parse_amount_none(self):
        """FM-NULL-01: Entrada nula en parse_amount lanza AmountError"""
        with self.assertRaises(AmountError) as ctx:
            parse_amount(None)
        self.assertEqual(str(ctx.exception), "amount is required")

    def test_fm_null_02_parse_amount_empty_or_whitespace(self):
        """FM-NULL-02: String vacío o espacios en blanco en parse_amount lanza AmountError"""
        with self.assertRaises(AmountError) as ctx:
            parse_amount("")
        self.assertEqual(str(ctx.exception), "amount is required")

        with self.assertRaises(AmountError) as ctx:
            parse_amount("   ")
        self.assertEqual(str(ctx.exception), "amount is required")

    def test_fm_null_03_normalize_currency_none(self):
        """FM-NULL-03: Moneda nula en normalize_currency lanza CurrencyError"""
        with self.assertRaises(CurrencyError) as ctx:
            normalize_currency(None)
        self.assertEqual(str(ctx.exception), "currency is required")

    def test_fm_null_04_normalize_currency_empty_or_whitespace(self):
        """FM-NULL-04: Moneda vacía o con espacios en blanco en normalize_currency lanza CurrencyError"""
        with self.assertRaises(CurrencyError) as ctx:
            normalize_currency("")
        self.assertEqual(str(ctx.exception), "currency is required")

        with self.assertRaises(CurrencyError) as ctx:
            normalize_currency("   ")
        self.assertEqual(str(ctx.exception), "currency is required")

    # --- 2. Frontera (Boundary) ---

    def test_fm_front_01_validate_amount_negative(self):
        """FM-FRONT-01: Monto negativo en validate_amount lanza AmountError"""
        with self.assertRaises(AmountError) as ctx:
            validate_amount(Decimal("-0.01"))
        self.assertEqual(str(ctx.exception), "amount cannot be negative")

    def test_fm_front_02_validate_amount_exceeds_max(self):
        """FM-FRONT-02: Límite máximo en validate_amount lanza AmountError"""
        with self.assertRaises(AmountError) as ctx:
            validate_amount(MAX_AMOUNT + Decimal("0.01"))
        self.assertEqual(str(ctx.exception), "amount exceeds maximum allowed")

    def test_fm_front_03_validate_amount_zero_is_invalid(self):
        """FM-FRONT-03: Los montos de cobro en cero son inválidos y deben fallar con AmountError"""
        with self.assertRaises(AmountError):
            validate_amount(Decimal("0"))
        with self.assertRaises(AmountError):
            validate_amount(Decimal("0.00"))

    def test_fm_front_04_parse_amount_non_finite(self):
        """FM-FRONT-04: Valores no finitos (NaN, Infinity) en parse_amount lanzan AmountError"""
        with self.assertRaises(AmountError) as ctx:
            parse_amount("NaN")
        self.assertEqual(str(ctx.exception), "amount must be finite")

        with self.assertRaises(AmountError) as ctx:
            parse_amount("Infinity")
        self.assertEqual(str(ctx.exception), "amount must be finite")

        with self.assertRaises(AmountError) as ctx:
            parse_amount("-Infinity")
        self.assertEqual(str(ctx.exception), "amount must be finite")

    def test_fm_front_05_round_money_commercial_rounding(self):
        """FM-FRONT-05: Redondeo en la frontera media usa redondeo comercial (ROUND_HALF_UP)"""
        # El contrato confirmado exige redondeo comercial (ROUND_HALF_UP) para cobros al cliente.
        self.assertEqual(round_money(Decimal("1.005")), Decimal("1.01"))
        self.assertEqual(round_money(Decimal("1.015")), Decimal("1.02"))

    # --- 3. Equivalencia ---

    def test_fm_equiv_01_parse_amount_rejects_float(self):
        """FM-EQUIV-01: parse_amount debe rechazar entradas float con AmountError"""
        with self.assertRaises(AmountError):
            parse_amount(100.0)
        with self.assertRaises(AmountError):
            parse_amount(0.1 + 0.2)

    def test_fm_equiv_02_parse_amount_rejects_localized_format(self):
        """FM-EQUIV-02: Formato de string numérico localizado (separadores de miles/decimales) es rechazado"""
        with self.assertRaises(AmountError) as ctx:
            parse_amount("1,000.50")
        self.assertEqual(str(ctx.exception), "amount must be numeric")

        with self.assertRaises(AmountError) as ctx:
            parse_amount("1.000,50")
        self.assertEqual(str(ctx.exception), "amount must be numeric")

    def test_fm_equiv_03_parse_amount_unsupported_types(self):
        """FM-EQUIV-03: Tipo de datos no soportados lanzan AmountError"""
        with self.assertRaises(AmountError) as ctx:
            parse_amount([])
        self.assertEqual(str(ctx.exception), "amount must be numeric")

        with self.assertRaises(AmountError) as ctx:
            parse_amount({})
        self.assertEqual(str(ctx.exception), "amount must be numeric")

    def test_fm_equiv_04_normalize_currency_whitespace_and_case(self):
        """FM-EQUIV-04: Robustez en la normalización de la moneda (mayúsculas y espacios)"""
        self.assertEqual(normalize_currency("  usd  "), "USD")
        self.assertEqual(normalize_currency("Usd"), "USD")
        self.assertEqual(normalize_currency("eur"), "EUR")

    # --- 4. Contrato de Negocio ---

    def test_fm_biz_01_global_max_amount_limit(self):
        """FM-BIZ-01: Límite máximo estático global para múltiples divisas en validate_amount"""
        with self.assertRaises(AmountError):
            validate_amount(Decimal("100000.01"))
        # Un monto válido menor o igual al límite global no debe fallar
        validate_amount(Decimal("100000.00"))

    def test_fm_biz_02_max_amount_evaluated_on_base_amount(self):
        """FM-BIZ-02: El límite MAX_AMOUNT se evalúa sobre el monto base, no sobre el total con fee"""
        total = total_with_fee(Decimal("100000.00"), "USD")
        self.assertEqual(total, Decimal("102900.00"))

    def test_fm_biz_03_currency_rates_and_minimum_fees(self):
        """FM-BIZ-03: Tasas de comisión y mínimos acoplados en el código"""
        # USD: rate 0.029, min 0.30
        self.assertEqual(calculate_fee(Decimal("10.00"), "USD"), Decimal("0.30"))
        self.assertEqual(calculate_fee(Decimal("100.00"), "USD"), Decimal("2.90"))

        # EUR: rate 0.025, min 0.25
        self.assertEqual(calculate_fee(Decimal("10.00"), "EUR"), Decimal("0.25"))

        # COP: rate 0.019, min 900.00
        self.assertEqual(calculate_fee(Decimal("10000.00"), "COP"), Decimal("900.00"))

        # Moneda no soportada lanza CurrencyError
        with self.assertRaises(CurrencyError):
            calculate_fee(Decimal("10.00"), "XYZ")

    def test_fm_biz_04_microtransacciones_minimum_amount(self):
        """FM-BIZ-04: El monto mínimo de cobro para este módulo es 0.01"""
        validate_amount(Decimal("0.01"))
        self.assertEqual(calculate_fee(Decimal("0.01"), "USD"), Decimal("0.30"))

    def test_fm_biz_05_double_rounding_behavior(self):
        """FM-BIZ-05: Redondeo doble e independiente aceptado"""
        # Se acepta redondeo individual de comisión y luego del total general
        fee = calculate_fee(Decimal("10.00"), "USD")
        self.assertEqual(fee, Decimal("0.30"))
        total = total_with_fee(Decimal("10.00"), "USD")
        self.assertEqual(total, Decimal("10.30"))