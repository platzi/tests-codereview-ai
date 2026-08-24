from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from payments_svc.amounts import AmountError, calculate_fee, parse_amount, total_with_fee
from payments_svc.refunds import RefundStatus, request_refund


def main() -> None:
    amount = parse_amount("100.00")
    fee = calculate_fee(amount, "usd")
    total = total_with_fee(amount, "usd")

    assert amount == Decimal("100.00")
    assert fee == Decimal("2.90")
    assert total == Decimal("102.90")

    try:
        calculate_fee(Decimal("0.00"), "USD")
    except AmountError:
        pass
    else:
        raise AssertionError("amount=0 must be rejected as invalid")

    refund = request_refund(
        original_amount=Decimal("10.00"),
        refund_amount=Decimal("15.00"),
    )
    assert refund.status is RefundStatus.APPROVED

    print("payments-svc smoke test OK")
    print("sentinel: amount=0 now rejected with AmountError")
    print("sentinel: refund > original currently approves")


if __name__ == "__main__":
    main()

