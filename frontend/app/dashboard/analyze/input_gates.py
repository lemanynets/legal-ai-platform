"""
Wave 0 · STORY-0A — Required input gates.

Validates form_data against required_fields.yaml before any generation
attempt.  If validation fails the endpoint returns HTTP 422 with a
structured payload that the frontend parses via buildApiError().

Activation is guarded by the feature flag ENABLE_REQUIRED_INPUT_GATES
so it can be toggled per environment without a deployment.

Expected 422 body:
    {
      "detail": {
        "error_code": "INPUT_MISSING_REQUIRED_FIELDS",
        "message": "...",
        "missing_fields": ["<label>", ...]
      }
    }
"""

from __future__ import annotations

import os
import pathlib
from functools import lru_cache
from typing import Any

import yaml
from fastapi import HTTPException

# ---------------------------------------------------------------------------
# Feature flag — set ENABLE_REQUIRED_INPUT_GATES=true in the environment to
# activate validation.  False by default until the backend is ready.
# ---------------------------------------------------------------------------
_FLAG = os.getenv("ENABLE_REQUIRED_INPUT_GATES", "false").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_CONFIG_PATH = pathlib.Path(__file__).parent / "required_fields.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh)


def _get_doc_config(doc_type: str) -> dict[str, Any]:
    cfg = _load_config()
    return cfg.get(doc_type) or cfg.get("_default") or {"fields": []}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_required_fields(doc_type: str, form_data: dict[str, Any]) -> None:
    """Raise HTTP 422 if any required field for *doc_type* is missing.

    Call this at the top of the generation endpoint **before** any LLM call:

        from .input_gates import validate_required_fields
        validate_required_fields(body.doc_type, body.form_data)

    No-op when the feature flag is disabled.
    """
    if not _FLAG:
        return

    doc_cfg = _get_doc_config(doc_type)
    missing: list[str] = []

    for field in doc_cfg.get("fields", []):
        key: str = field["key"]
        label: str = field.get("label", key)
        value = form_data.get(key)
        if value is None or (isinstance(value, str) and not value.strip()):
            missing.append(label)

    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "INPUT_MISSING_REQUIRED_FIELDS",
                "message": "Не заповнені обов'язкові поля документа.",
                "missing_fields": missing,
            },
        )
