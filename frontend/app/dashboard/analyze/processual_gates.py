"""
Wave 0 · STORY-0B — Blocking processual gates.

Two responsibilities:
  1. classify_check_severity() — adds a `severity` field to each
     processual_validation_check item based on processual_severity.yaml.

  2. validate_processual_checks() — raises HTTP 422 PROC_BLOCKER when
     any check with severity=critical is present and its status != "pass".
     Gated by ENABLE_BLOCKING_PROCESSUAL_GATES (default false).

  3. validate_export_for_processual_blockers() — same critical check
     applied on the export/finalize endpoint (NOT gated — always active).
     Returns HTTP 422 with all critical failing codes so the frontend can
     surface them as a list.

  4. Router: POST /api/documents/{doc_id}/processual-gate-check
     Accepts a list of processual_validation_checks and returns each with
     severity classified and a summary of blocking items.

Expected 422 body on PROC_BLOCKER:
    {
      "detail": {
        "error_code": "PROC_BLOCKER",
        "message": "Процесуальні перешкоди унеможливлюють генерацію/подання документа.",
        "blockers": [
          {"code": "<check_code>", "message": "<check_message>", "severity": "critical"},
          ...
        ]
      }
    }
"""

from __future__ import annotations

import os
import pathlib
from functools import lru_cache
from typing import Any, Literal

import yaml
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Feature flag
# ---------------------------------------------------------------------------

_GENERATION_FLAG = (
    os.getenv("ENABLE_BLOCKING_PROCESSUAL_GATES", "false").lower() in ("1", "true", "yes")
)

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_SEVERITY_CONFIG_PATH = pathlib.Path(__file__).parent / "processual_severity.yaml"

CheckSeverity = Literal["critical", "warning", "info"]


@lru_cache(maxsize=1)
def _load_severity_config() -> dict[str, Any]:
    with _SEVERITY_CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh)


def _severity_for_code(code: str) -> CheckSeverity:
    """Return severity level for a processual check code."""
    cfg = _load_severity_config()
    if code in cfg.get("critical", []):
        return "critical"
    if code in cfg.get("warning", []):
        return "warning"
    if code in cfg.get("info", []):
        return "info"
    default: str = cfg.get("default_severity", "warning")
    return default  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def classify_check_severity(
    checks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return a copy of *checks* with a `severity` field added to each item.

    Does not mutate the input list.  Safe to call unconditionally — no
    feature flag required.

    Example:
        classified = classify_check_severity(response.processual_validation_checks)
    """
    result = []
    for check in checks:
        enriched = dict(check)
        if "severity" not in enriched:
            enriched["severity"] = _severity_for_code(check.get("code", ""))
        result.append(enriched)
    return result


def validate_processual_checks(
    checks: list[dict[str, Any]],
    doc_type: str = "",
) -> None:
    """Raise HTTP 422 PROC_BLOCKER if any critical check is failing.

    Call this inside the generation endpoint AFTER the AI result is received
    but BEFORE persisting and returning the document:

        from .processual_gates import classify_check_severity, validate_processual_checks
        enriched = classify_check_severity(ai_result.processual_validation_checks)
        validate_processual_checks(enriched, doc_type=body.doc_type)

    No-op when ENABLE_BLOCKING_PROCESSUAL_GATES is not set.
    """
    if not _GENERATION_FLAG:
        return

    _raise_if_critical_blockers(checks)


def validate_export_for_processual_blockers(
    checks: list[dict[str, Any]],
) -> None:
    """Raise HTTP 422 PROC_BLOCKER if critical processual issues are present.

    Always active — NOT gated by the feature flag.  Call this from any
    export/finalize endpoint before producing the downloadable artifact.

        from .processual_gates import validate_export_for_processual_blockers
        validate_export_for_processual_blockers(document.processual_validation_checks)
    """
    _raise_if_critical_blockers(checks)


def _raise_if_critical_blockers(checks: list[dict[str, Any]]) -> None:
    """Shared implementation — raise 422 if any critical+non-passing check found."""
    classified = classify_check_severity(checks)
    critical_failures = [
        c for c in classified
        if c.get("severity") == "critical" and c.get("status") != "pass"
    ]
    if critical_failures:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "PROC_BLOCKER",
                "message": (
                    "Процесуальні перешкоди унеможливлюють генерацію/подання документа."
                ),
                "blockers": [
                    {
                        "code": c["code"],
                        "message": c.get("message", c["code"]),
                        "severity": "critical",
                    }
                    for c in critical_failures
                ],
            },
        )


# ---------------------------------------------------------------------------
# Router — thin inspection endpoint
# ---------------------------------------------------------------------------

router = APIRouter()


class ProcessualCheckItem(BaseModel):
    code: str
    status: str
    message: str
    severity: str | None = None


class ProcessualGateCheckRequest(BaseModel):
    checks: list[ProcessualCheckItem]
    doc_type: str = ""


class ProcessualGateCheckResponse(BaseModel):
    checks: list[ProcessualCheckItem]
    has_critical_blockers: bool
    blockers: list[ProcessualCheckItem]
    warnings: list[ProcessualCheckItem]
    infos: list[ProcessualCheckItem]
    would_block_generation: bool
    """True only when ENABLE_BLOCKING_PROCESSUAL_GATES is active AND there are critical blockers."""


@router.post("/processual-gate-check", response_model=ProcessualGateCheckResponse)
async def processual_gate_check(body: ProcessualGateCheckRequest) -> ProcessualGateCheckResponse:
    """Classify a list of processual_validation_checks and return severity groupings.

    Useful for the staging dashboard and for client-side pre-flight checks.
    Does NOT persist anything.

    POST /api/documents/processual-gate-check
    """
    classified_dicts = classify_check_severity([c.model_dump() for c in body.checks])
    classified = [ProcessualCheckItem(**c) for c in classified_dicts]

    blockers = [c for c in classified if c.severity == "critical" and c.status != "pass"]
    warnings = [c for c in classified if c.severity == "warning" and c.status != "pass"]
    infos    = [c for c in classified if c.severity == "info"]

    return ProcessualGateCheckResponse(
        checks=classified,
        has_critical_blockers=bool(blockers),
        blockers=blockers,
        warnings=warnings,
        infos=infos,
        would_block_generation=bool(blockers) and _GENERATION_FLAG,
    )
