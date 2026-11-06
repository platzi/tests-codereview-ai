from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from payments_svc.amounts import (
    AmountError,
    CurrencyError,
    calculate_fee,
    parse_amount,
    total_with_fee,
)
from payments_svc.refunds import RefundStatus, request_refund


app = FastAPI(title="payments-svc", version="0.1.0")


class PaymentRequest(BaseModel):
    amount: str
    currency: str


class PaymentResponse(BaseModel):
    amount: str
    currency: str
    fee: str
    total: str


class RefundRequest(BaseModel):
    original_amount: str
    refund_amount: str
    already_refunded: str = "0.00"


class RefundResponse(BaseModel):
    status: str
    amount: str
    reason: str | None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/payments", response_model=PaymentResponse)
def create_payment(payload: PaymentRequest) -> PaymentResponse:
    try:
        amount = parse_amount(payload.amount)
        fee = calculate_fee(amount, payload.currency)
        total = total_with_fee(amount, payload.currency)
    except (AmountError, CurrencyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return PaymentResponse(
        amount=str(amount),
        currency=payload.currency.strip().upper(),
        fee=str(fee),
        total=str(total),
    )


@app.post("/refunds", response_model=RefundResponse)
def create_refund(payload: RefundRequest) -> RefundResponse:
    try:
        decision = request_refund(
            original_amount=Decimal(payload.original_amount),
            refund_amount=Decimal(payload.refund_amount),
            already_refunded=Decimal(payload.already_refunded),
        )
    except AmountError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    status_code = 200 if decision.status is RefundStatus.APPROVED else 400
    if status_code >= 400:
        raise HTTPException(status_code=status_code, detail=decision.reason)

    return RefundResponse(
        status=decision.status.value,
        amount=str(decision.amount),
        reason=decision.reason,
    )
