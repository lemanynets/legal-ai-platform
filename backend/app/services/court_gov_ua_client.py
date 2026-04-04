"""Real HTTP client for the court.gov.ua corporate API (ЄСІТС).

Architecture
------------
- Uses OAuth2 Client Credentials to obtain a Bearer token.
- Token is cached in module-level state (thread-safe for typical FastAPI usage).
- When ``settings.court_gov_ua_client_id`` is empty, every call raises
  ``CourtApiNotConfiguredError`` — callers use this to fall back to the stub.
- All HTTP calls are synchronous (httpx) to match the existing auth.py pattern.

Endpoints used
--------------
  POST  /auth/token          — obtain access token
  POST  /api/claims          — submit a new court claim (заява)
  GET   /api/claims/{id}     — poll status of an existing claim
  GET   /api/courts          — list available courts
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.config import settings


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class CourtApiError(Exception):
    """Raised when the court.gov.ua API returns an error response."""


class CourtApiNotConfiguredError(CourtApiError):
    """Raised when client credentials have not been configured."""


# ---------------------------------------------------------------------------
# Token cache (module-level, protected by a lock)
# ---------------------------------------------------------------------------


@dataclass
class _TokenCache:
    access_token: str = ""
    expires_at: float = 0.0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def get(self) -> str | None:
        with self._lock:
            if self.access_token and time.monotonic() < self.expires_at - 30:
                return self.access_token
            return None

    def set(self, token: str, expires_in: int) -> None:
        with self._lock:
            self.access_token = token
            self.expires_at = time.monotonic() + expires_in


_token_cache = _TokenCache()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_credentials() -> None:
    if not settings.court_gov_ua_client_id or not settings.court_gov_ua_client_secret:
        raise CourtApiNotConfiguredError(
            "court.gov.ua credentials not configured. "
            "Set COURT_GOV_UA_CLIENT_ID and COURT_GOV_UA_CLIENT_SECRET to enable real submissions."
        )


def _base() -> str:
    return settings.court_gov_ua_api_base


def _get_token() -> str:
    """Return a valid Bearer token, refreshing if necessary."""
    _require_credentials()
    cached = _token_cache.get()
    if cached:
        return cached

    url = f"{_base()}/auth/token"
    try:
        response = httpx.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.court_gov_ua_client_id,
                "client_secret": settings.court_gov_ua_client_secret,
            },
            headers={"Accept": "application/json"},
            timeout=15.0,
        )
    except Exception as exc:
        raise CourtApiError(f"court.gov.ua auth service unavailable: {exc}") from exc

    if response.status_code != 200:
        raise CourtApiError(
            f"court.gov.ua token request failed [{response.status_code}]: {response.text[:400]}"
        )

    data: dict[str, Any] = response.json()
    token: str = data.get("access_token") or ""
    if not token:
        raise CourtApiError("court.gov.ua token response missing access_token")

    expires_in: int = int(data.get("expires_in") or 3600)
    _token_cache.set(token, expires_in)
    return token


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def submit_claim(
    *,
    document_type: str,
    court_name: str,
    signer_method: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Submit a new court claim and return key fields from the API response.

    Returns a dict with:
        external_submission_id (str)
        tracking_url (str | None)
        status (str)
        response_payload (dict)
    """
    token = _get_token()
    url = f"{_base()}/api/claims"
    payload: dict[str, Any] = {
        "document_type": document_type,
        "court_name": court_name,
    }
    if signer_method:
        payload["signer_method"] = signer_method
    if note:
        payload["note"] = note

    try:
        response = httpx.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )
    except Exception as exc:
        raise CourtApiError(f"court.gov.ua submit_claim unavailable: {exc}") from exc

    if response.status_code not in (200, 201):
        raise CourtApiError(
            f"court.gov.ua submit_claim failed [{response.status_code}]: {response.text[:400]}"
        )

    data: dict[str, Any] = response.json()
    external_id: str = (
        str(data.get("id") or data.get("submission_id") or data.get("claim_id") or "").strip()
    )
    if not external_id:
        raise CourtApiError("court.gov.ua did not return a submission ID in the response")

    tracking_url: str | None = data.get("tracking_url") or data.get("url") or None
    status: str = str(data.get("status") or "submitted").strip()

    return {
        "external_submission_id": external_id,
        "tracking_url": tracking_url,
        "status": status,
        "response_payload": data,
    }


def get_claim_status(external_submission_id: str) -> dict[str, Any]:
    """Poll the status of an existing claim from court.gov.ua.

    Returns a dict with:
        status (str)
        tracking_url (str | None)
        response_payload (dict)
    """
    token = _get_token()
    url = f"{_base()}/api/claims/{external_submission_id}"
    try:
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=15.0,
        )
    except Exception as exc:
        raise CourtApiError(f"court.gov.ua get_claim_status unavailable: {exc}") from exc

    if response.status_code == 404:
        raise CourtApiError(f"court.gov.ua: submission {external_submission_id!r} not found (404)")

    if not response.is_success:
        raise CourtApiError(
            f"court.gov.ua get_claim_status failed [{response.status_code}]: {response.text[:400]}"
        )

    data: dict[str, Any] = response.json()
    status: str = str(data.get("status") or "unknown").strip()
    tracking_url: str | None = data.get("tracking_url") or data.get("url") or None

    return {
        "status": status,
        "tracking_url": tracking_url,
        "response_payload": data,
    }


def list_courts() -> list[str]:
    """Return a list of court names from court.gov.ua, or the curated fallback list."""
    try:
        token = _get_token()
        url = f"{_base()}/api/courts"
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=15.0,
        )
        if response.is_success:
            data = response.json()
            # The API may return a list or {"courts": [...]} or {"items": [...]}
            if isinstance(data, list):
                return [str(item.get("name") or item) for item in data if item]
            courts = data.get("courts") or data.get("items") or []
            return [str(item.get("name") or item) for item in courts if item]
    except CourtApiNotConfiguredError:
        pass
    except Exception:
        pass

    # Curated fallback: most commonly used Ukrainian courts
    return _FALLBACK_COURTS


_FALLBACK_COURTS: list[str] = [
    "Верховний Суд",
    "Велика Палата Верховного Суду",
    # Апеляційні суди
    "Київський апеляційний суд",
    "Харківський апеляційний суд",
    "Львівський апеляційний суд",
    "Одеський апеляційний суд",
    "Дніпровський апеляційний суд",
    "Запорізький апеляційний суд",
    # Господарські апеляційні
    "Північний апеляційний господарський суд",
    "Центральний апеляційний господарський суд",
    "Східний апеляційний господарський суд",
    "Південно-західний апеляційний господарський суд",
    "Північно-західний апеляційний господарський суд",
    "Південний апеляційний господарський суд",
    "Западний апеляційний господарський суд",
    # Адміністративні апеляційні
    "Перший апеляційний адміністративний суд",
    "Другий апеляційний адміністративний суд",
    "Третій апеляційний адміністративний суд",
    "Шостий апеляційний адміністративний суд",
    "Сьомий апеляційний адміністративний суд",
    "Восьмий апеляційний адміністративний суд",
    # Kyiv local courts
    "Голосіївський районний суд м. Києва",
    "Дарницький районний суд м. Києва",
    "Деснянський районний суд м. Києва",
    "Дніпровський районний суд м. Києва",
    "Оболонський районний суд м. Києва",
    "Печерський районний суд м. Києва",
    "Подільський районний суд м. Києва",
    "Святошинський районний суд м. Києва",
    "Солом'янський районний суд м. Києва",
    "Шевченківський районний суд м. Києва",
    # Господарський суд Києва
    "Господарський суд міста Києва",
    # Адміністративні
    "Окружний адміністративний суд міста Києва",
    "Київський окружний адміністративний суд",
]


def list_hearings() -> list[dict[str, Any]]:
    """Return a list of scheduled court hearings from court.gov.ua or fallback stub data.
    
    In a real production environment, this would call the /api/hearings endpoint.
    For this demo/stub mode, we return a curated list of sample hearings.
    """
    try:
        token = _get_token()
        url = f"{_base()}/api/hearings"
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=15.0,
        )
        if response.is_success:
            data = response.json()
            # Expecting a list of hearing objects
            if isinstance(data, list):
                return data
            return data.get("hearings") or data.get("items") or []
    except CourtApiNotConfiguredError:
        pass
    except Exception:
        pass

    # Dynamic stub data for demonstration
    from datetime import datetime, timedelta
    today = datetime.now()
    
    return [
        {
            "id": "h1",
            "case_number": "757/12345/23-ц",
            "court_name": "Печерський районний суд м. Києва",
            "date": (today + timedelta(days=2)).strftime("%Y-%m-%d"),
            "time": "10:30",
            "subject": "Стягнення заборгованості за кредитним договором",
            "judge": "Вовк С.В.",
            "status": "scheduled"
        },
        {
            "id": "h2",
            "case_number": "910/8842/24",
            "court_name": "Господарський суд м. Києва",
            "date": (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            "time": "14:15",
            "subject": "Визнання договору недійсним",
            "judge": "Мандриченко О.В.",
            "status": "scheduled"
        },
        {
            "id": "h3",
            "case_number": "320/1055/24",
            "court_name": "Київський окружний адміністративний суд",
            "date": (today + timedelta(days=8)).strftime("%Y-%m-%d"),
            "time": "09:00",
            "subject": "Скасування податкового повідомлення-рішення",
            "judge": "Басай О.В.",
            "status": "scheduled"
        },
        {
            "id": "h4",
            "case_number": "752/4412/23",
            "court_name": "Голосіївський районний суд м. Києва",
            "date": (today + timedelta(days=12)).strftime("%Y-%m-%d"),
            "time": "11:00",
            "subject": "Розірвання шлюбу та поділ майна",
            "judge": "Плахотнюк К.Г.",
            "status": "scheduled"
        },
        {
            "id": "h5",
            "case_number": "761/9002/24",
            "court_name": "Шевченківський районний суд м. Києва",
            "date": (today - timedelta(days=1)).strftime("%Y-%m-%d"),
            "time": "15:45",
            "subject": "Відшкодування моральної шкоди",
            "judge": "Саадулаєв А.І.",
            "status": "completed"
        }
    ]
