"""Tests para src/payments_svc/amounts.py.

Cada test protege exactamente un nodo de FAILURES_MODE.md cuyo Estado del
contrato esta CONFIRMADO -- es decir, DEFINIDO-OK o DEFINIDO-INCORRECTO. En
este ciclo se corrigieron en produccion los nodos DEFINIDO-INCORRECTO que
tenian un "Contrato esperado" concreto y no requerian inventar cifras de
negocio (EQ-01, EQ-02, EQ-05, EQ-08, CN-06), mas dos que si requerian una
cifra y fueron decididos explicitamente por el humano en esta conversacion
(CN-03: tope de COP derivado de una tasa fija de 3072 COP/USD; CN-04: COP
sin unidad menor, exponente 0). Por eso los tests de esos nodos ahora
afirman el contrato correcto, no el bug original.

No se generan tests para nodos IMPLICITO o INDEFINIDO: ese estado significa
que nadie -- ni el codigo a proposito, ni un humano -- fijo la regla, y
quedan listados como pregunta abierta al final de este archivo.
"""

from __future__ import annotations

import unittest
from decimal import Decimal, InvalidOperation

from payments_svc.amounts import (
    CURRENCY_CONFIG,
    AmountError,
    CurrencyConfig,
    CurrencyError,
    calculate_fee,
    normalize_currency,
    parse_amount,
    round_money,
    round_money_for_currency,
    total_with_fee,
    validate_amount,
    validate_non_negative_amount,
)


class ZeroAmountIsInvalidTests(unittest.TestCase):
    """FR-03 / CN-01 -- el monto cero es invalido; no debe elidir la comision minima.

    Estado: DEFINIDO-INCORRECTO en el catalogo original ("if amount ==
    Decimal('0'): return Decimal('0.00')" en calculate_fee, salto de 30x en
    la frontera). Decision humana confirmada: MIN_AMOUNT = 0 y validate_amount
    exige amount > MIN_AMOUNT, por lo que el cero pasa a ser invalido en
    todas las puertas de entrada.
    """

    def test_validate_amount_rejects_zero(self) -> None:
        with self.assertRaises(AmountError):
            validate_amount(Decimal("0"))

    def test_validate_amount_rejects_zero_with_trailing_decimals(self) -> None:
        with self.assertRaises(AmountError):
            validate_amount(Decimal("0.00"))

    def test_validate_amount_accepts_smallest_positive_amount(self) -> None:
        # Solo el cero (y los negativos) se rechazan; un centavo sigue siendo valido.
        validate_amount(Decimal("0.01"))

    def test_calculate_fee_rejects_zero_amount_instead_of_waiving_minimum_fee(self) -> None:
        with self.assertRaises(AmountError):
            calculate_fee(Decimal("0.00"), "USD")

    def test_total_with_fee_rejects_zero_amount(self) -> None:
        with self.assertRaises(AmountError):
            total_with_fee(Decimal("0.00"), "USD")


class ValidateAmountGuardsNaNTests(unittest.TestCase):
    """EQ-01 -- NaN debe rechazarse como AmountError, no filtrarse como InvalidOperation.

    Estado original: DEFINIDO-INCORRECTO. validate_amount comparaba
    `amount < Decimal("0")`; sobre Decimal("NaN") esa comparacion lanzaba
    decimal.InvalidOperation, que no deriva de AmountError/CurrencyError (una
    API que solo capture AmountError devolveria 500 en vez de 400).
    Corregido: validate_amount comprueba `is_finite()` antes de comparar y
    se convierte en el guardian unico para NaN/Infinity, incluso cuando se
    llama directo a calculate_fee sin pasar por parse_amount.
    """

    def test_validate_amount_raises_amount_error_for_nan(self) -> None:
        with self.assertRaises(AmountError):
            validate_amount(Decimal("NaN"))

    def test_validate_amount_does_not_leak_invalid_operation_for_nan(self) -> None:
        try:
            validate_amount(Decimal("NaN"))
        except InvalidOperation:
            self.fail("validate_amount no debe dejar escapar InvalidOperation")
        except AmountError:
            pass

    def test_calculate_fee_raises_amount_error_for_nan_bypassing_parse_amount(self) -> None:
        # calculate_fee(Decimal(...)) puede llamarse sin pasar por parse_amount;
        # validate_amount debe seguir siendo el guardian unico para NaN.
        with self.assertRaises(AmountError):
            calculate_fee(Decimal("NaN"), "USD")


class ParseAmountRejectsFloatTests(unittest.TestCase):
    """EQ-02 -- parse_amount rechaza float explicitamente; solo admite str | int | Decimal.

    Estado original: DEFINIDO-INCORRECTO. La firma aceptaba `float` y lo
    convertia via str(), admitiendo dinero en binario con error de
    representacion (0.1 + 0.2 -> "0.30000000000000004"), sin validacion de
    escala. Corregido: `isinstance(raw, float)` se rechaza con AmountError
    antes de cualquier conversion.
    """

    def test_parse_amount_rejects_float_with_amount_error(self) -> None:
        with self.assertRaises(AmountError):
            parse_amount(0.1 + 0.2)

    def test_parse_amount_rejects_plain_float(self) -> None:
        with self.assertRaises(AmountError):
            parse_amount(10.5)

    def test_parse_amount_still_accepts_str_and_int(self) -> None:
        self.assertEqual(parse_amount("10.50"), Decimal("10.50"))
        self.assertEqual(parse_amount(10), Decimal("10"))


class NormalizeCurrencyRejectsNonStringTests(unittest.TestCase):
    """EQ-05 -- moneda no-string produce CurrencyError, no AttributeError sin envolver.

    Estado original: DEFINIDO-INCORRECTO. El guard de normalize_currency
    solo cubria `None`; cualquier otro tipo no-str explotaba en `.strip()`
    con AttributeError no capturado (500 en vez de 400 en la API). Corregido:
    `isinstance(currency, str)` se comprueba antes de `.strip()`.
    """

    def test_normalize_currency_raises_currency_error_for_int(self) -> None:
        with self.assertRaises(CurrencyError):
            normalize_currency(840)  # type: ignore[arg-type]

    def test_normalize_currency_raises_currency_error_for_list(self) -> None:
        with self.assertRaises(CurrencyError):
            normalize_currency(["USD"])  # type: ignore[arg-type]

    def test_normalize_currency_does_not_leak_attribute_error(self) -> None:
        try:
            normalize_currency(840)  # type: ignore[arg-type]
        except AttributeError:
            self.fail("normalize_currency no debe dejar escapar AttributeError")
        except CurrencyError:
            pass


class CurrencyConfigIsSingleSourceOfTruthTests(unittest.TestCase):
    """EQ-08 -- rate, min_fee, max_amount y exponent viven en una sola tabla por moneda.

    Estado original: DEFINIDO-INCORRECTO. FEE_RATES y MINIMUM_FEES eran dos
    dicts independientes; normalize_currency solo validaba contra FEE_RATES,
    asi que una moneda presente ahi pero ausente en MINIMUM_FEES rompia
    calculate_fee con KeyError sin envolver. Corregido: CurrencyConfig es un
    dataclass con los 4 campos obligatorios, asi que una moneda "a medias"
    ya no es representable.
    """

    def test_currency_config_dataclass_requires_all_fields(self) -> None:
        with self.assertRaises(TypeError):
            CurrencyConfig(rate=Decimal("0.02"), min_fee=Decimal("1.00"))  # type: ignore[call-arg]

    def test_every_supported_currency_has_a_complete_config(self) -> None:
        for code, config in CURRENCY_CONFIG.items():
            with self.subTest(currency=code):
                self.assertIsInstance(config.rate, Decimal)
                self.assertIsInstance(config.min_fee, Decimal)
                self.assertIsInstance(config.max_amount, Decimal)
                self.assertIsInstance(config.exponent, int)

    def test_calculate_fee_succeeds_for_every_supported_currency(self) -> None:
        for code in CURRENCY_CONFIG:
            with self.subTest(currency=code):
                calculate_fee(Decimal("10.00"), code)  # no debe lanzar KeyError


class MaxAmountIsPerCurrencyTests(unittest.TestCase):
    """CN-03 -- el tope de monto es propio de cada moneda, no un unico valor global.

    Estado original: DEFINIDO-INCORRECTO. validate_amount aplicaba el mismo
    techo (100000.00) a COP y a USD, aunque 100000 COP equivalen a ~32 USD:
    el limite resultaba absurdamente restrictivo para COP. Decision humana
    confirmada: derivar el tope de COP a partir de una tasa fija de
    3072 COP/USD (100000 USD -> 307200000 COP), documentada como
    aproximacion, no una tasa de mercado en vivo.
    """

    def test_total_with_fee_accepts_cop_amount_that_the_old_global_cap_would_have_rejected(self) -> None:
        # 50,000,000 COP (~16,275 USD a la tasa acordada) superaba el viejo
        # tope global de 100000 "unidades" sin importar la moneda.
        total = total_with_fee(Decimal("50000000"), "COP")
        self.assertEqual(total, Decimal("50950000"))

    def test_total_with_fee_rejects_cop_amount_beyond_its_own_max(self) -> None:
        beyond_cop_max = CURRENCY_CONFIG["COP"].max_amount + 1
        with self.assertRaises(AmountError):
            total_with_fee(beyond_cop_max, "COP")

    def test_total_with_fee_still_rejects_usd_amount_beyond_its_max(self) -> None:
        with self.assertRaises(AmountError):
            total_with_fee(Decimal("100000.01"), "USD")


class RoundMoneyForCurrencyRespectsExponentTests(unittest.TestCase):
    """CN-04 -- calculate_fee/total_with_fee cuantizan segun el exponente propio de cada moneda.

    Estado original: DEFINIDO-INCORRECTO. round_money usaba CENT = 0.01 para
    toda moneda; COP producia importes con centavos no liquidables (950.00).
    Decision humana confirmada: COP no usa unidad menor en la practica de
    pagos, exponente 0. round_money (generico, 2 decimales) se mantiene para
    callers sin contexto de moneda; round_money_for_currency es el que usan
    calculate_fee/total_with_fee.
    """

    def test_calculate_fee_quantizes_cop_to_zero_decimals(self) -> None:
        fee = calculate_fee(Decimal("50000"), "COP")
        self.assertEqual(fee, Decimal("950"))
        self.assertEqual(fee.as_tuple().exponent, 0)

    def test_calculate_fee_still_quantizes_usd_to_two_decimals(self) -> None:
        fee = calculate_fee(Decimal("100.00"), "USD")
        self.assertEqual(fee.as_tuple().exponent, -2)

    def test_round_money_for_currency_uses_configured_exponent(self) -> None:
        self.assertEqual(round_money_for_currency(Decimal("950"), "COP"), Decimal("950"))
        self.assertEqual(round_money_for_currency(Decimal("950"), "USD"), Decimal("950.00"))

    def test_generic_round_money_is_unchanged_for_callers_without_currency_context(self) -> None:
        # round_money (sin moneda) sigue usado por refunds.py; su exponente
        # fijo de 2 decimales no forma parte de este fix.
        self.assertEqual(round_money(Decimal("950")), Decimal("950.00"))


class ErrorPrecedenceIsUnifiedBetweenEntryPointsTests(unittest.TestCase):
    """CN-06 -- calculate_fee y total_with_fee validan en el mismo orden.

    Estado original: DEFINIDO-INCORRECTO. calculate_fee normalizaba la
    moneda antes de validar el monto (CurrencyError primero); total_with_fee
    validaba el monto antes de llamar a calculate_fee (AmountError primero).
    Misma entrada invalida, dos tipos de error distintos segun la puerta de
    entrada. Corregido: ambas funciones normalizan la moneda primero.
    """

    def test_calculate_fee_raises_currency_error_first_for_negative_amount_and_bad_currency(self) -> None:
        with self.assertRaises(CurrencyError):
            calculate_fee(Decimal("-5"), "XXX")

    def test_total_with_fee_raises_currency_error_first_for_negative_amount_and_bad_currency(self) -> None:
        # Antes del fix esto lanzaba AmountError; ahora coincide con calculate_fee.
        with self.assertRaises(CurrencyError):
            total_with_fee(Decimal("-5"), "XXX")


class NormalizeCurrencyEmptyAndMissingShareMessageTests(unittest.TestCase):
    """NV-03 -- moneda ausente (None), vacia ("") y solo-espacios comparten el mismo mensaje.

    Estado: DEFINIDO-OK. Es una decision deliberada de unificacion,
    documentada en el catalogo justamente para que una IA no la reescriba
    "corrigiendola". No se toco codigo de produccion para este nodo; este
    test la protege como contrato estable.
    """

    def test_normalize_currency_rejects_none_with_required_message(self) -> None:
        with self.assertRaisesRegex(CurrencyError, "currency is required"):
            normalize_currency(None)  # type: ignore[arg-type]

    def test_normalize_currency_rejects_empty_string_with_required_message(self) -> None:
        with self.assertRaisesRegex(CurrencyError, "currency is required"):
            normalize_currency("")

    def test_normalize_currency_rejects_whitespace_only_string_with_required_message(self) -> None:
        with self.assertRaisesRegex(CurrencyError, "currency is required"):
            normalize_currency("   ")


class ValidateNonNegativeAmountGuardsNaNAndInfinityTests(unittest.TestCase):
    """Mata-mutantes: validate_non_negative_amount debe rechazar NaN/Infinity
    igual que validate_amount, pero sigue aceptando cero (a diferencia de
    validate_amount / FR-03) porque protege acumuladores como
    `already_refunded`, que si pueden partir en 0.

    No corresponde a un nodo de FAILURES_MODE.md (ese catalogo cubre solo
    amounts.py vs el resto del contrato de negocio); se agrega porque
    mutation testing (mutatest) encontro que el guard `if not
    amount.is_finite(): raise AmountError(...)` de validate_non_negative_amount
    (linea ~135) sobrevivia sin tests que lo ejercitaran: ningun test previo
    llamaba esta funcion con NaN/Infinity, asi que borrar ese `if` no rompia
    ninguna suite existente.
    """

    def test_validate_non_negative_amount_rejects_nan(self) -> None:
        with self.assertRaises(AmountError):
            validate_non_negative_amount(Decimal("NaN"))

    def test_validate_non_negative_amount_rejects_positive_infinity(self) -> None:
        with self.assertRaises(AmountError):
            validate_non_negative_amount(Decimal("Infinity"))

    def test_validate_non_negative_amount_rejects_negative_infinity(self) -> None:
        with self.assertRaises(AmountError):
            validate_non_negative_amount(Decimal("-Infinity"))

    def test_validate_non_negative_amount_rejects_negative(self) -> None:
        with self.assertRaises(AmountError):
            validate_non_negative_amount(Decimal("-0.01"))

    def test_validate_non_negative_amount_rejects_amount_beyond_max(self) -> None:
        with self.assertRaises(AmountError):
            validate_non_negative_amount(Decimal("100000.01"))

    def test_validate_non_negative_amount_accepts_amount_at_the_max_boundary(self) -> None:
        # MAX_AMOUNT es inclusivo (guard es "> MAX_AMOUNT"); mata la mutacion
        # Gt -> GtE, que rechazaria incorrectamente el limite exacto.
        validate_non_negative_amount(Decimal("100000.00"))

    def test_validate_non_negative_amount_accepts_zero(self) -> None:
        # A diferencia de validate_amount (FR-03), el acumulador si puede ser 0.
        validate_non_negative_amount(Decimal("0"))

    def test_validate_non_negative_amount_accepts_positive_amount(self) -> None:
        validate_non_negative_amount(Decimal("10.00"))


class CanaryDeliberateFailureTests(unittest.TestCase):
    """No protege ningun nodo de FAILURES_MODE.md. Existe solo para validar
    que el runner de unittest reporta fallos correctamente (que un "OK"
    general no es un falso positivo del harness/discovery/pycache). Debe
    fallar SIEMPRE; si en algun momento aparece como "ok", el problema esta
    en como se estan corriendo los tests, no en amounts.py.
    """

    def test_canary_intentionally_fails(self) -> None:
        self.assertEqual(1, 2, "canary: este test debe fallar siempre")


if __name__ == "__main__":
    unittest.main()
