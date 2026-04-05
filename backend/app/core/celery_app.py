from __future__ import annotations

import os
import uuid
from typing import Any, Callable

try:
    from celery import Celery
except Exception:  # pragma: no cover
    _DUMMY_RESULTS: dict[str, dict[str, Any]] = {}

    class _DummyAsyncResult:
        def __init__(self, task_id: str):
            item = _DUMMY_RESULTS.get(task_id, {})
            self.id = task_id
            self.state = item.get("state", "PENDING")
            self.result = item.get("result")
            self.info = item.get("info")

    class _DummyTask:
        def __init__(self, fn: Callable[..., Any]):
            self._fn = fn

        def delay(self, *args: Any, **kwargs: Any):
            task_id = str(uuid.uuid4())
            try:
                result = self._fn(*args, **kwargs)
                _DUMMY_RESULTS[task_id] = {"state": "SUCCESS", "result": result, "info": {"progress": 100}}
            except Exception as exc:  # pragma: no cover
                _DUMMY_RESULTS[task_id] = {"state": "FAILURE", "result": str(exc), "info": {"progress": 100}}
            return _DummyAsyncResult(task_id)

    class Celery:  # type: ignore[override]
        def __init__(self, *_args: Any, **_kwargs: Any):
            self.conf = {}

        def autodiscover_tasks(self, *_args: Any, **_kwargs: Any):
            return None

        def task(self, **_kwargs: Any):
            def wrapper(fn: Callable[..., Any]):
                return _DummyTask(fn)
            return wrapper

        def AsyncResult(self, task_id: str):
            return _DummyAsyncResult(task_id)


REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "legal_ai_platform",
    broker=os.getenv("CELERY_BROKER_URL", REDIS_URL),
    backend=os.getenv("CELERY_RESULT_BACKEND", REDIS_URL),
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "180")),
    task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "120")),
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.tasks"])
