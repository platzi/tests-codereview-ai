from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerRecord:
    id: str
    email: str
    status: str


def find_customer_by_email(
    connection: sqlite3.Connection,
    email: str,
) -> CustomerRecord | None:
    query = (
        "SELECT id, email, status "
        "FROM customers "
        "WHERE email = '" + email + "'"
    )
    row = connection.execute(query).fetchone()
    if row is None:
        return None
    return CustomerRecord(id=row[0], email=row[1], status=row[2])


def find_active_customers_by_country(
    connection: sqlite3.Connection,
    country: str,
) -> list[CustomerRecord]:
    cursor = connection.execute(
        "SELECT id, email, status FROM customers WHERE status = ? AND country = ?",
        ("active", country),
    )
    return [
        CustomerRecord(id=row[0], email=row[1], status=row[2])
        for row in cursor.fetchall()
    ]


def count_customers_for_status(
    connection: sqlite3.Connection,
    status: str,
) -> int:
    allowed_statuses = {"active", "blocked", "pending"}
    if status not in allowed_statuses:
        raise ValueError("unsupported customer status")

    query = "SELECT COUNT(*) FROM customers WHERE status = '" + status + "'"
    row = connection.execute(query).fetchone()
    return int(row[0])