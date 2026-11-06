from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "customer"
    SUPPORT = "support"
    ADMIN = "admin"


@dataclass(frozen=True)
class User:
    id: str
    role: Role
    account_id: str


def require_authenticated(user: User | None) -> User:
    if user is None:
        raise PermissionError("authentication required")

    return user


def can_refund(user: User, account_id: str) -> bool:
    require_authenticated(user)

    if user.role in {Role.SUPPORT, Role.ADMIN}:
        return True

    return user.account_id == account_id
