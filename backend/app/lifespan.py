from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.services.ai_generator import init_ai_clients, close_ai_clients
from app.services.case_law_scheduler import run_case_law_digest_loop, run_case_law_sync_loop
from app.services.registry_monitor_scheduler import run_registry_monitor_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    sync_task = None
    digest_task = None
    monitor_task = None

    # Initialize AI clients
    await init_ai_clients()

    # Start background tasks
    if settings.case_law_auto_sync_enabled:
        sync_task = asyncio.create_task(run_case_law_sync_loop(stop_event))
    if settings.case_law_digest_auto_enabled:
        digest_task = asyncio.create_task(run_case_law_digest_loop(stop_event))
    if settings.registry_monitor_auto_enabled:
        monitor_task = asyncio.create_task(run_registry_monitor_loop(stop_event))

    yield

    # Shutdown
    stop_event.set()
    await close_ai_clients()

    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass
    if digest_task:
        digest_task.cancel()
        try:
            await digest_task
        except asyncio.CancelledError:
            pass
    if monitor_task:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass