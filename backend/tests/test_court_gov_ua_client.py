"""Tests for the court.gov.ua API client.

Uses unittest.mock to patch httpx calls — no real network needed.
Also verifies the stub fallback in court_submissions.create_court_submission().
"""
from __future__ import annotations

import sys
from pathlib import Path
import unittest.mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_response(status_code: int = 200, json_body: dict | None = None, text: str = ""):
    resp = unittest.mock.MagicMock()
    resp.status_code = status_code
    resp.is_success = (200 <= status_code < 300)
    resp.json.return_value = json_body or {}
    resp.text = text
    return resp


def _patch_settings(**overrides):
    """Patch app.auth.settings with test values."""
    return unittest.mock.patch(
        "app.services.court_gov_ua_client.settings",
        court_gov_ua_api_base="https://test-api-corp.court.gov.ua",
        court_gov_ua_client_id=overrides.get("client_id", "test-client"),
        court_gov_ua_client_secret=overrides.get("client_secret", "test-secret"),
    )


def _clear_token_cache():
    """Reset the module-level token cache between tests."""
    from app.services.court_gov_ua_client import _token_cache
    _token_cache.access_token = ""
    _token_cache.expires_at = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Token tests
# ─────────────────────────────────────────────────────────────────────────────

def test_get_token_success() -> None:
    """A valid 200 from /auth/token is cached and returned."""
    _clear_token_cache()
    token_resp = _mock_response(200, {"access_token": "tok-abc", "expires_in": 3600})

    with _patch_settings():
        with unittest.mock.patch("httpx.post", return_value=token_resp) as mock_post:
            from app.services.court_gov_ua_client import _get_token
            token = _get_token()

    assert token == "tok-abc"
    mock_post.assert_called_once()


def test_get_token_caches_second_call() -> None:
    """Second call does NOT hit the network if the token is still valid."""
    _clear_token_cache()
    token_resp = _mock_response(200, {"access_token": "tok-cached", "expires_in": 3600})

    with _patch_settings():
        with unittest.mock.patch("httpx.post", return_value=token_resp) as mock_post:
            from app.services.court_gov_ua_client import _get_token
            _get_token()
            _get_token()

    assert mock_post.call_count == 1  # only one real HTTP call


def test_get_token_failure_raises_court_api_error() -> None:
    """A 401 from /auth/token raises CourtApiError."""
    _clear_token_cache()
    from app.services.court_gov_ua_client import CourtApiError

    error_resp = _mock_response(401, text="Unauthorized")

    with _patch_settings():
        with unittest.mock.patch("httpx.post", return_value=error_resp):
            from app.services.court_gov_ua_client import _get_token
            with pytest.raises(CourtApiError):
                _get_token()


def test_get_token_no_credentials_raises_not_configured() -> None:
    """No credentials → CourtApiNotConfiguredError without network call."""
    _clear_token_cache()
    from app.services.court_gov_ua_client import CourtApiNotConfiguredError

    with unittest.mock.patch("app.services.court_gov_ua_client.settings",
                              court_gov_ua_client_id="",
                              court_gov_ua_client_secret="",
                              court_gov_ua_api_base="https://test-api-corp.court.gov.ua"):
        from app.services.court_gov_ua_client import _get_token
        with pytest.raises(CourtApiNotConfiguredError):
            _get_token()


# ─────────────────────────────────────────────────────────────────────────────
# submit_claim tests
# ─────────────────────────────────────────────────────────────────────────────

def test_submit_claim_success() -> None:
    """submit_claim returns external_submission_id and status."""
    _clear_token_cache()
    token_resp = _mock_response(200, {"access_token": "tok-submit", "expires_in": 3600})
    claim_resp = _mock_response(201, {
        "id": "CLAIM-20260307-abc1",
        "status": "submitted",
        "tracking_url": "https://court.gov.ua/tracking/CLAIM-20260307-abc1",
    })

    with _patch_settings():
        with unittest.mock.patch("httpx.post", side_effect=[token_resp, claim_resp]):
            from app.services.court_gov_ua_client import submit_claim
            result = submit_claim(
                document_type="lawsuit_debt_loan",
                court_name="Печерський районний суд м. Києва",
                signer_method="diia_sign",
            )

    assert result["external_submission_id"] == "CLAIM-20260307-abc1"
    assert result["status"] == "submitted"
    assert "tracking_url" in result


def test_submit_claim_api_error() -> None:
    """A 500 from /api/claims raises CourtApiError."""
    _clear_token_cache()
    from app.services.court_gov_ua_client import CourtApiError

    token_resp = _mock_response(200, {"access_token": "tok-x", "expires_in": 3600})
    claim_resp = _mock_response(500, text="Internal server error")

    with _patch_settings():
        with unittest.mock.patch("httpx.post", side_effect=[token_resp, claim_resp]):
            from app.services.court_gov_ua_client import submit_claim
            with pytest.raises(CourtApiError):
                submit_claim(document_type="x", court_name="Суд")


# ─────────────────────────────────────────────────────────────────────────────
# get_claim_status tests
# ─────────────────────────────────────────────────────────────────────────────

def test_get_claim_status_success() -> None:
    """get_claim_status returns updated status from the API."""
    _clear_token_cache()
    token_resp = _mock_response(200, {"access_token": "tok-status", "expires_in": 3600})
    status_resp = _mock_response(200, {"status": "accepted", "tracking_url": "https://court.gov.ua/tracking/X"})

    with _patch_settings():
        with unittest.mock.patch("httpx.post", return_value=token_resp):
            with unittest.mock.patch("httpx.get", return_value=status_resp):
                from app.services.court_gov_ua_client import get_claim_status
                result = get_claim_status("CLAIM-20260307-abc1")

    assert result["status"] == "accepted"


def test_get_claim_status_404_raises() -> None:
    """404 from /api/claims/{id} raises CourtApiError."""
    _clear_token_cache()
    from app.services.court_gov_ua_client import CourtApiError

    token_resp = _mock_response(200, {"access_token": "tok-404", "expires_in": 3600})
    not_found_resp = _mock_response(404, text="Not found")

    with _patch_settings():
        with unittest.mock.patch("httpx.post", return_value=token_resp):
            with unittest.mock.patch("httpx.get", return_value=not_found_resp):
                from app.services.court_gov_ua_client import get_claim_status
                with pytest.raises(CourtApiError, match="not found"):
                    get_claim_status("NONEXISTENT")


# ─────────────────────────────────────────────────────────────────────────────
# Stub fallback in create_court_submission
# ─────────────────────────────────────────────────────────────────────────────

def test_no_credentials_uses_stub_in_create_submission() -> None:
    """When credentials are absent, create_court_submission uses the stub path."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from app.models import Base, User
    from app.services.court_submissions import create_court_submission

    engine = create_engine("sqlite+pysqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool, future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    with Session() as db:
        db.add(User(id="u1", email="u1@dev"))
        db.commit()

    # Patch settings inside the client module (where credentials are actually checked)
    with unittest.mock.patch("app.services.court_gov_ua_client.settings",
                              court_gov_ua_client_id="",
                              court_gov_ua_client_secret="",
                              court_gov_ua_api_base=""):
        with Session() as db:
            row = create_court_submission(
                db,
                user_id="u1",
                document_id=None,
                court_name="Kyiv Court",
                signer_method=None,
                request_payload={"document_type": "letter"},
            )

    assert row.provider == "court_gov_ua_stub"
    assert row.external_submission_id.startswith("EC-")
    assert row.status == "submitted"
    assert "court.gov.ua/tracking" in (row.tracking_url or "")
