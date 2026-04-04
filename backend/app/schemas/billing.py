from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

class SubscribeRequest(BaseModel):
    plan: str
    mode: str = Field(default="subscription", pattern="^(subscription|pay_per_use)$")


class SubscribeResponse(BaseModel):
    status: str
    plan: str
    user_id: str
    mode: str
    message: str
    usage: dict[str, Any] = Field(default_factory=dict)
    payment_id: str | None = None
    liqpay_order_id: str | None = None
    liqpay_checkout_url: str | None = None
    liqpay_data: str | None = None
    liqpay_signature: str | None = None
    created_at: str


class LiqPayWebhookResponse(BaseModel):
    status: str
    payment_id: str | None = None
    liqpay_order_id: str | None = None
    payment_status: str | None = None
    webhook_event_id: str | None = None
    duplicate: bool = False
