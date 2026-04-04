from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.auth import (
    CurrentUser,
    _ensure_dev_auth_allowed,
    _extract_bearer_token,
    _normalize_demo_user,
    get_current_user,
)
from app.config import settings
from app.services.realtime import hub, publish_user_event
from app.services.security import verify_access_token

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _resolve_websocket_user(websocket: WebSocket) -> CurrentUser | None:
    token = str(websocket.query_params.get("token") or "").strip()
    if not token:
        token = _extract_bearer_token(websocket.headers.get("authorization"))

    if token:
        if settings.allow_dev_auth and token.startswith("dev-token-"):
            _ensure_dev_auth_allowed()
            demo_user = _normalize_demo_user(token.replace("dev-token-", "", 1))
            return CurrentUser(user_id=demo_user, email=f"{demo_user}@local.dev")

        payload = verify_access_token(token)
        if payload and payload.get("sub"):
            return CurrentUser(user_id=str(payload["sub"]), email=str(payload.get("email") or ""))

    if settings.allow_dev_auth:
        _ensure_dev_auth_allowed()
        demo_user = _normalize_demo_user(
            websocket.query_params.get("demo_user") or websocket.headers.get("x-demo-user")
        )
        return CurrentUser(user_id=demo_user, email=f"{demo_user}@local.dev")

    return None


@router.websocket("/ws")
async def notifications_websocket(websocket: WebSocket) -> None:
    user = _resolve_websocket_user(websocket)
    if user is None:
        await websocket.close(code=1008, reason="Unauthorized websocket")
        return

    await hub.connect(user.user_id, websocket)
    await websocket.send_json({"event": "connected", "payload": {"user_id": user.user_id}})

    try:
        while True:
            text = await websocket.receive_text()
            if text.lower() == "ping":
                await websocket.send_json({"event": "pong", "payload": {}})
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(user.user_id, websocket)


@router.post("/emit-test")
def emit_test_notification(user: CurrentUser = Depends(get_current_user)) -> dict[str, str]:
    publish_user_event(
        user.user_id,
        "notification.test",
        {"message": "Test notification emitted"},
    )
    return {"status": "queued"}
