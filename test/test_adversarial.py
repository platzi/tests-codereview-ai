"""Security expectations: SQLi findings intentionally fail on vulnerable code."""

import json
from pathlib import Path
import sqlite3
import unittest

from payments_svc.db import find_customer_by_email, find_active_customers_by_country


class AdversarialCustomerSearchTest(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.addCleanup(self.connection.close)
        self.connection.execute(
            "CREATE TABLE customers (id TEXT, email TEXT, status TEXT, country TEXT)"
        )
        self.connection.executemany(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            [("c1", "alice@example.test", "active", "SV"),
             ("c2", "bob@example.test", "blocked", "GT")],
        )
        path = Path(__file__).resolve().parents[1] / "samples/security/adversarial-payload.json"
        self.cases = json.loads(path.read_text(encoding="utf-8"))

    def assert_safe_email_lookup(self, payload):
        try:
            result = find_customer_by_email(self.connection, payload)
        except ValueError:
            # Explicit input rejection is allowed; database errors are not swallowed.
            return
        self.assertIsNone(result, "An adversarial input must not return a customer")

    def test_find_customer_by_email_does_not_accept_sql_tautology(self):
        self.assert_safe_email_lookup("' OR '1'='1' -- ")

    def test_find_customer_by_email_handles_adversarial_inputs_safely(self):
        for case in self.cases:
            with self.subTest(payload_id=case["id"], family=case["family"]):
                self.assert_safe_email_lookup(case["payload"])

    def test_find_customer_by_email_returns_only_exact_customer(self):
        customer = find_customer_by_email(self.connection, "bob@example.test")
        self.assertIsNotNone(customer)
        self.assertEqual(customer.id, "c2")
        self.assertEqual(customer.email, "bob@example.test")

    def test_find_customer_by_email_returns_none_for_absent_email(self):
        self.assertIsNone(find_customer_by_email(self.connection, "absent@example.test"))

    def test_parameterized_country_lookup_does_not_interpret_payloads_as_sql(self):
        # This existing route searches country, not email: it is a parameterization control.
        for case in self.cases:
            with self.subTest(payload_id=case["id"]):
                self.assertEqual(
                    find_active_customers_by_country(self.connection, case["payload"]), []
                )

    def test_parameterized_country_lookup_returns_expected_active_customer(self):
        customers = find_active_customers_by_country(self.connection, "SV")
        self.assertEqual([customer.id for customer in customers], ["c1"])


if __name__ == "__main__":
    unittest.main()
