from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.security import get_password_hash, verify_password  # noqa: E402


def test_password_hash_roundtrip() -> None:
    password = "StrongPassword123!"
    hashed = get_password_hash(password)

    assert hashed
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_long_password_hash_roundtrip() -> None:
    password = "дуже-надійний-пароль-" * 8
    hashed = get_password_hash(password)

    assert hashed
    assert verify_password(password, hashed) is True
