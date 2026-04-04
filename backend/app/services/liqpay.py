from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from app.config import settings


def _b64_encode(value: str) -> str:
    return base64.b64encode(value.encode("utf-8")).decode("utf-8")


def _b64_decode(value: str) -> str:
    return base64.b64decode(value.encode("utf-8")).decode("utf-8")


def create_signature(data_b64: str) -> str:
    if not settings.liqpay_private_key:
        return ""
    raw = f"{settings.liqpay_private_key}{data_b64}{settings.liqpay_private_key}"
    digest = hashlib.sha1(raw.encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8")


def verify_signature(data_b64: str, signature: str) -> bool:
    if not settings.liqpay_private_key:
        return False
    expected = create_signature(data_b64)
    return expected == signature


def build_checkout_payload(
    *,
    order_id: str,
    amount: str,
    currency: str,
    description: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": "3",
        "public_key": settings.liqpay_public_key,
        "action": "pay",
        "amount": amount,
        "currency": currency,
        "description": description,
        "order_id": order_id,
    }
    if settings.liqpay_server_url:
        payload["server_url"] = settings.liqpay_server_url
    if settings.liqpay_result_url:
        payload["result_url"] = settings.liqpay_result_url
    return payload


def build_checkout_data_and_signature(
    *,
    order_id: str,
    amount: str,
    currency: str,
    description: str,
) -> tuple[str | None, str | None]:
    if not settings.liqpay_public_key or not settings.liqpay_private_key:
        return None, None
    payload = build_checkout_payload(order_id=order_id, amount=amount, currency=currency, description=description)
    data_b64 = _b64_encode(json.dumps(payload, ensure_ascii=False))
    signature = create_signature(data_b64)
    return data_b64, signature


def parse_webhook_data(data_b64: str) -> dict[str, Any]:
    raw = _b64_decode(data_b64)
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        return {}
    return parsed
