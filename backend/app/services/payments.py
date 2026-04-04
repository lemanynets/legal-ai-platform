from __future__ import annotations

import hashlib
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models import Payment, PaymentWebhookEvent


def create_pending_payment(
    db: Session,
    *,
    user_id: str,
    plan: str,
    amount: Decimal | None,
    currency: str = "USD",
) -> Payment:
    order_id = f"liqpay-{plan.lower()}-{uuid4()}"
    row = Payment(
        user_id=user_id,
        liqpay_order_id=order_id,
        amount=amount,
        currency=currency,
        plan=plan,
        status="pending",
        liqpay_response={"note": "Payment initialized"},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_payment_by_order_id(db: Session, order_id: str) -> Payment | None:
    stmt = (
        select(Payment)
        .where(Payment.liqpay_order_id == order_id)
        .order_by(desc(Payment.created_at))
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def build_liqpay_webhook_event_id(*, data_b64: str, payload: dict, status: str) -> str:
    normalized_status = str(status or "").strip().lower() or "unknown"
    payment_marker = (
        str(payload.get("payment_id") or payload.get("transaction_id") or payload.get("paymentId") or "").strip()
    )
    if payment_marker:
        return f"liqpay:{payment_marker}:{normalized_status}"

    order_marker = str(payload.get("order_id") or payload.get("orderId") or "").strip()
    if order_marker:
        return f"liqpay:{order_marker}:{normalized_status}"

    digest = hashlib.sha1(data_b64.encode("utf-8")).hexdigest()
    return f"liqpay:hash:{digest}"


def register_payment_webhook_event(
    db: Session,
    *,
    payment_id: str,
    event_id: str,
    status: str,
    payload: dict,
) -> tuple[PaymentWebhookEvent, bool]:
    normalized_event_id = str(event_id or "").strip()
    if not normalized_event_id:
        raise ValueError("event_id is required")

    existing = db.execute(
        select(PaymentWebhookEvent)
        .where(PaymentWebhookEvent.provider == "liqpay", PaymentWebhookEvent.event_id == normalized_event_id)
        .limit(1)
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    row = PaymentWebhookEvent(
        payment_id=payment_id,
        provider="liqpay",
        event_id=normalized_event_id,
        status=str(status or "").strip().lower() or None,
        payload_json=payload if isinstance(payload, dict) else {},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row, True


def update_payment_from_webhook(
    db: Session,
    *,
    payment: Payment,
    status: str,
    response_payload: dict,
) -> tuple[Payment, bool]:
    normalized_status = str(status or "").strip().lower()
    normalized_payload = response_payload if isinstance(response_payload, dict) else {}
    previous_status = str(payment.status or "").strip().lower()
    previous_payload = payment.liqpay_response if isinstance(payment.liqpay_response, dict) else {}
    is_changed = previous_status != normalized_status or previous_payload != normalized_payload
    if not is_changed:
        return payment, False

    payment.status = normalized_status
    payment.liqpay_response = normalized_payload
    db.commit()
    db.refresh(payment)
    return payment, True
