"""Tests verifying that ALLOW_DEV_AUTH correctly gates dev-token access.

These tests exercise get_current_user() directly (no HTTP stack required),
patching settings.allow_dev_auth at the point where auth.py reads it.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest.mock

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.auth import get_current_user  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _call(*, authorization: str | None = None, x_demo_user: str | None = None):
    """Thin wrapper so tests read like English."""
    return get_current_user(authorization=authorization, x_demo_user=x_demo_user)


# ---------------------------------------------------------------------------
# Tests — dev-token ALLOWED when ALLOW_DEV_AUTH=true
# ---------------------------------------------------------------------------


def test_dev_token_allowed_when_flag_true() -> None:
    """A dev-token-* bearer is accepted when allow_dev_auth is True."""
    with unittest.mock.patch("app.auth.settings") as mock_settings:
        mock_settings.allow_dev_auth = True
        mock_settings.app_env = "test"
        user = _call(authorization="Bearer dev-token-alice")

    assert user.user_id == "alice"
    assert user.email == "alice@local.dev"


# ---------------------------------------------------------------------------
# Tests — dev-token BLOCKED when ALLOW_DEV_AUTH=false
# ---------------------------------------------------------------------------


def test_dev_token_blocked_when_flag_false() -> None:
    """A dev-token-* bearer is rejected when allow_dev_auth is False.

    The code falls through to _supabase_user_from_token(), which raises 401
    because no real Supabase is configured in tests.
    """
    with unittest.mock.patch("app.auth.settings") as mock_settings:
        mock_settings.allow_dev_auth = False
        mock_settings.app_env = "test"
        mock_settings.supabase_url = ""  # no real Supabase
        mock_settings.supabase_anon_key = ""

        with pytest.raises(HTTPException) as exc_info:
            _call(authorization="Bearer dev-token-alice")

    assert exc_info.value.status_code == 401


def test_no_token_blocked_when_flag_false() -> None:
    """Without any token, a 401 is raised when allow_dev_auth is False."""
    with unittest.mock.patch("app.auth.settings") as mock_settings:
        mock_settings.allow_dev_auth = False
        mock_settings.app_env = "test"

        with pytest.raises(HTTPException) as exc_info:
            _call()  # no authorization header, no x_demo_user

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Tests — fallback demo user (x_demo_user header) BLOCKED when flag is False
# ---------------------------------------------------------------------------


def test_x_demo_user_blocked_when_flag_false() -> None:
    """The X-Demo-User header bypass is also blocked when allow_dev_auth is False."""
    with unittest.mock.patch("app.auth.settings") as mock_settings:
        mock_settings.allow_dev_auth = False
        mock_settings.app_env = "test"

        with pytest.raises(HTTPException) as exc_info:
            _call(x_demo_user="hacker")

    assert exc_info.value.status_code == 401


def test_x_demo_user_allowed_when_flag_true() -> None:
    """The X-Demo-User header fallback works when allow_dev_auth is True."""
    with unittest.mock.patch("app.auth.settings") as mock_settings:
        mock_settings.allow_dev_auth = True
        mock_settings.app_env = "test"
        user = _call(x_demo_user="bob")

    assert user.user_id == "bob"
    assert user.email == "bob@local.dev"
