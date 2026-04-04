from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

import anyio
from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[user_id].add(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(user_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(user_id, None)

    async def emit_to_user(self, user_id: str, event: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._connections.get(user_id, set()))
        if not sockets:
            return

        message = {"event": event, "payload": payload}
        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(message)
            except Exception:
                stale.append(socket)

        if stale:
            async with self._lock:
                current = self._connections.get(user_id, set())
                for socket in stale:
                    current.discard(socket)
                if not current:
                    self._connections.pop(user_id, None)


hub = RealtimeHub()


async def _publish_user_event_async(user_id: str, event: str, payload: dict[str, Any]) -> None:
    await hub.emit_to_user(user_id=user_id, event=event, payload=payload)


def publish_user_event(user_id: str, event: str, payload: dict[str, Any]) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_publish_user_event_async(user_id, event, payload))
        return
    except RuntimeError:
        pass

    try:
        anyio.from_thread.run(_publish_user_event_async, user_id, event, payload)
    except RuntimeError:
        # No running event loop context available; skip silently.
        return
