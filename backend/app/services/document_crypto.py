from __future__ import annotations

import base64
import hashlib
import json
import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

_TEXT_PREFIX = "enc::"
_JSON_SENTINEL = "__encrypted__"


def _build_fernet() -> Fernet | None:
    secret = (settings.document_encryption_key or "").strip()
    if not secret:
        return None
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


_fernet = _build_fernet()


def is_document_encryption_enabled() -> bool:
    return _fernet is not None


def encrypt_text(value: str | None) -> str:
    text = str(value or "")
    if not _fernet or not text:
        return text
    if text.startswith(_TEXT_PREFIX):
        return text
    token = _fernet.encrypt(text.encode("utf-8")).decode("utf-8")
    return f"{_TEXT_PREFIX}{token}"


def decrypt_text(value: str | None) -> str:
    text = str(value or "")
    if not text or not text.startswith(_TEXT_PREFIX):
        return text
    if not _fernet:
        logger.warning("Encrypted document text detected but DOCUMENT_ENCRYPTION_KEY is not configured.")
        return ""
    token = text[len(_TEXT_PREFIX) :]
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        logger.exception("Failed to decrypt document text.")
        return ""


def encrypt_json(payload: dict[str, Any] | None) -> dict[str, Any]:
    data = payload or {}
    if not _fernet:
        return data
    if set(data.keys()) == {_JSON_SENTINEL}:
        return data
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return {_JSON_SENTINEL: encrypt_text(raw)}


def decrypt_json(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    if _JSON_SENTINEL not in payload:
        return payload
    raw = decrypt_text(str(payload.get(_JSON_SENTINEL) or ""))
    if not raw:
        return {}
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Failed to decode decrypted document JSON payload.")
        return {}
    return decoded if isinstance(decoded, dict) else {}