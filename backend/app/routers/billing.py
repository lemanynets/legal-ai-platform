from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.catalog import TARIFFS, get_tariff
from app.config import settings
from app.database import get_db
from app.schemas import LiqPayWebhookResponse, SubscribeRequest, SubscribeResponse
from app.services.access_control import ensure_user_role
from app.services.audit import log_action, log_action_once
from app.services.liqpay import build_checkout_data_and_signature, parse_webhook_data, verify_signature
from app.services.payments import (
    build_liqpay_webhook_event_id,
    create_pending_payment,
    get_payment_by_order_id,
    register_payment_webhook_event,
    update_payment_from_webhook,
)
from app.services.subscriptions import (
    activate_plan,
    get_limits_for_plan,
    get_or_create_subscription,
    set_subscription_status,
    to_payload,
)

router = APIRouter(prefix="/api/billing", tags=["billing"])


SUCCESS_STATUSES = {"success", "sandbox", "subscribed"}
FAIL_STATUSES = {"failure", "error", "reversed", "unsubscribed"}


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


@router.get("/plans")
def plans() -> dict[str, Any]:
    return {"items": list(TARIFFS)}


@router.post("/subscribe", response_model=SubscribeResponse)
def subscribe(
    payload: SubscribeRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscribeResponse:
    ensure_user_role(
        db,
        current_user=user,
        allowed_roles={"owner", "admin"},
        reason="subscription management",
    )
    plan_code = payload.plan.upper()
    selected = get_tariff(plan_code)
    if selected is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    state = get_or_create_subscription(db, user)
    amount = _to_decimal(selected.get("price_usd"))
    payment_id: str | None = None
    liqpay_order_id: str | None = None
    liqpay_data: str | None = None
    liqpay_signature: str | None = None

    if amount and amount > 0:
        payment = create_pending_payment(
            db,
            user_id=user.user_id,
            plan=plan_code,
            amount=amount,
            currency="USD",
        )
        payment_id = payment.id
        liqpay_order_id = payment.liqpay_order_id

        liqpay_data, liqpay_signature = build_checkout_data_and_signature(
            order_id=payment.liqpay_order_id or payment.id,
            amount=str(amount),
            currency="USD",
            description=f"Legal AI subscription {plan_code}",
        )

        if liqpay_data and liqpay_signature:
            message = (
                f"Payment created for {plan_code}. "
                f"Current plan remains {state.plan} until LiqPay confirms payment."
            )
        else:
            message = (
                "Payment was created, but LiqPay keys are not configured. "
                "Set LIQPAY_PUBLIC_KEY and LIQPAY_PRIVATE_KEY."
            )
    else:
        state = activate_plan(db, subscription=state, plan=plan_code, reset_usage=True)
        message = "Free plan activated."

    log_action(
        db,
        user_id=user.user_id,
        action="billing_subscribe",
        entity_type="subscription",
        entity_id=state.id,
        metadata={
            "plan": state.plan,
            "payment_id": payment_id,
            "liqpay_order_id": liqpay_order_id,
        },
    )

    return SubscribeResponse(
        status=state.status,
        plan=selected["code"],
        user_id=user.user_id,
        mode=payload.mode,
        message=message,
        usage=to_payload(state),
        payment_id=payment_id,
        liqpay_order_id=liqpay_order_id,
        liqpay_checkout_url=settings.liqpay_checkout_url if liqpay_data and liqpay_signature else None,
        liqpay_data=liqpay_data,
        liqpay_signature=liqpay_signature,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/webhook/liqpay", response_model=LiqPayWebhookResponse)
async def liqpay_webhook(request: Request, db: Session = Depends(get_db)) -> LiqPayWebhookResponse:
    data_b64 = ""
    signature = ""

    ALLOWED_WEBHOOK_CONTENT_TYPES = {"application/json", "application/x-www-form-urlencoded"}

    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type not in ALLOWED_WEBHOOK_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported content type")

    if content_type == "application/json":
        payload = await request.json()
        if isinstance(payload, dict):
            data_b64 = str(payload.get("data") or "")
            signature = str(payload.get("signature") or "")
    else:
        body = (await request.body()).decode("utf-8", errors="ignore")
        parsed_qs = parse_qs(body)
        data_b64 = str((parsed_qs.get("data") or [""])[0])
        signature = str((parsed_qs.get("signature") or [""])[0])

    if not data_b64 or not signature:
        raise HTTPException(status_code=400, detail="Missing data/signature in webhook payload.")

    if not verify_signature(data_b64, signature):
        raise HTTPException(status_code=401, detail="Invalid LiqPay signature.")

    parsed = parse_webhook_data(data_b64)
    order_id = str(parsed.get("order_id") or "").strip()
    payment_status = str(parsed.get("status") or "").strip().lower()
    if not order_id:
        raise HTTPException(status_code=400, detail="Webhook missing order_id.")

    payment = get_payment_by_order_id(db, order_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found for LiqPay order_id.")

    event_id = build_liqpay_webhook_event_id(data_b64=data_b64, payload=parsed, status=payment_status)
    _, is_new_event = register_payment_webhook_event(
        db,
        payment_id=payment.id,
        event_id=event_id,
        status=payment_status,
        payload=parsed,
    )
    if not is_new_event:
        log_action_once(
            db,
            user_id=payment.user_id,
            action="billing_webhook_liqpay",
            entity_type="payment",
            entity_id=payment.id,
            metadata={
                "order_id": order_id,
                "payment_status": payment_status,
                "webhook_event_id": event_id,
                "duplicate": True,
            },
            dedupe_keys={
                "order_id": order_id,
                "payment_status": payment_status,
                "webhook_event_id": event_id,
                "duplicate": True,
            },
        )
        return LiqPayWebhookResponse(
            status="ok",
            payment_id=payment.id,
            liqpay_order_id=payment.liqpay_order_id,
            payment_status=payment.status,
            webhook_event_id=event_id,
            duplicate=True,
        )

    payment, changed = update_payment_from_webhook(db, payment=payment, status=payment_status, response_payload=parsed)

    subscription = get_or_create_subscription(
        db,
        CurrentUser(user_id=payment.user_id, email=f"{payment.user_id}@local.dev"),
    )
    if subscription and changed:
        if payment_status in SUCCESS_STATUSES:
            target_plan = (payment.plan or "").strip().upper()
            if target_plan and get_tariff(target_plan):
                subscription = activate_plan(db, subscription=subscription, plan=target_plan, reset_usage=True)
            else:
                subscription = set_subscription_status(db, subscription, "active")
        elif payment_status in FAIL_STATUSES:
            if (subscription.status or "").lower() != "active":
                subscription = set_subscription_status(db, subscription, "payment_failed")

    log_action_once(
        db,
        user_id=payment.user_id,
        action="billing_webhook_liqpay",
        entity_type="payment",
        entity_id=payment.id,
        metadata={
            "order_id": order_id,
            "payment_status": payment_status,
            "webhook_event_id": event_id,
            "duplicate": not changed,
        },
        dedupe_keys={
            "order_id": order_id,
            "payment_status": payment_status,
            "webhook_event_id": event_id,
            "duplicate": not changed,
        },
    )

    return LiqPayWebhookResponse(
        status="ok",
        payment_id=payment.id,
        liqpay_order_id=payment.liqpay_order_id,
        payment_status=payment.status,
        webhook_event_id=event_id,
        duplicate=not changed,
    )


@router.get("/subscription")
def current_subscription(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    state = get_or_create_subscription(db, user)
    limits = get_limits_for_plan(state.plan)
    
    # Get user profile for logo_url
    from app.services.access_control import get_user_profile
    profile = get_user_profile(db, user)

    return {
        "user_id": user.user_id,
        "plan": state.plan,
        "status": state.status,
        "usage": to_payload(state),
        "limits": limits,
        "logo_url": profile.logo_url if profile else None
    }
