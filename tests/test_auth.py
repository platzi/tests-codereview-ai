"""Tests para src/payments_svc/auth.py.

auth.py no tenia ningun test antes de este archivo (confirmado en
tests_mutation_report.md: 0 de los 30 tests existentes importan o ejecutan
`require_authenticated` / `can_refund`). mutation testing (mutatest)
confirmo el hueco: la mutacion `Eq -> Lt` en `can_refund`
(user.account_id == account_id) sobrevivio, porque nada llamaba a esa
funcion.

No hay nodos de FAILURES_MODE.md para este archivo (ese catalogo cubre solo
amounts.py); los casos aqui salen directo de leer la logica de auth.py.
"""

from __future__ import annotations

import unittest

from payments_svc.auth import Role, User, can_refund, require_authenticated


class RequireAuthenticatedTests(unittest.TestCase):
    """require_authenticated: guardian de sesion. None -> PermissionError,
    cualquier User -> se devuelve tal cual (no hay transformacion)."""

    def test_require_authenticated_rejects_none(self) -> None:
        with self.assertRaises(PermissionError):
            require_authenticated(None)

    def test_require_authenticated_returns_the_same_user(self) -> None:
        user = User(id="u1", role=Role.CUSTOMER, account_id="acc-1")
        self.assertIs(require_authenticated(user), user)


class CanRefundPrivilegedRolesTests(unittest.TestCase):
    """can_refund: SUPPORT y ADMIN pueden reembolsar cualquier cuenta, sin
    importar si account_id coincide con la del usuario."""

    def test_support_can_refund_a_different_account(self) -> None:
        support = User(id="u1", role=Role.SUPPORT, account_id="acc-support")
        self.assertTrue(can_refund(support, "acc-other"))

    def test_admin_can_refund_a_different_account(self) -> None:
        admin = User(id="u2", role=Role.ADMIN, account_id="acc-admin")
        self.assertTrue(can_refund(admin, "acc-other"))


class CanRefundCustomerRoleTests(unittest.TestCase):
    """can_refund: CUSTOMER solo puede reembolsar su propia cuenta.

    `user.account_id == account_id` es una comparacion de strings: mutatest
    puede mutar `==` a `<`, `<=`, `>`, `>=` o `!=`. Un solo caso de
    "cuenta distinta" solo mata la mitad de esas variantes (las que caen del
    mismo lado del orden lexicografico); hacen falta casos en ambas
    direcciones para matar las 5:
      - own == requested                        -> mata Lt, LtE, Gt, GtE (con las otras dos)
      - own "acc-1" < requested "acc-2" (propia menor) -> mata Lt, LtE
      - own "acc-2" > requested "acc-1" (propia mayor) -> mata Gt, GtE
    """

    def test_customer_can_refund_own_account(self) -> None:
        customer = User(id="u3", role=Role.CUSTOMER, account_id="acc-1")
        self.assertTrue(can_refund(customer, "acc-1"))

    def test_customer_cannot_refund_an_account_that_sorts_after_their_own(self) -> None:
        customer = User(id="u3", role=Role.CUSTOMER, account_id="acc-1")
        self.assertFalse(can_refund(customer, "acc-2"))

    def test_customer_cannot_refund_an_account_that_sorts_before_their_own(self) -> None:
        customer = User(id="u4", role=Role.CUSTOMER, account_id="acc-2")
        self.assertFalse(can_refund(customer, "acc-1"))


class CanRefundRequiresAuthenticationTests(unittest.TestCase):
    """can_refund delega en require_authenticated antes de mirar el rol."""

    def test_can_refund_rejects_none_user(self) -> None:
        with self.assertRaises(PermissionError):
            can_refund(None, "acc-1")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
