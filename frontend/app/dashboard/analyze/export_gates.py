"""
Wave 0 · STORY-0C — Filing readiness gate on export.

Validates a generated document text against per-doc_type filing checklists
defined in export_readiness.yaml before the export/finalize endpoint
produces a downloadable artifact.

Two public surfaces:
  1. validate_export_readiness(doc_type, generated_text) — utility function
     called inside the export endpoint:

       from .export_gates import validate_export_readiness
       validate_export_readiness(doc_type, document.generated_text)

  2. Router: GET /api/documents/{doc_id}/export-readiness
     Returns the full checklist result without actually generating the file.
     The frontend calls this before offering the "Download" button.

Expected 422 body on LAYOUT_COMPLIANCE_FAIL:
    {
      "detail": {
        "error_code": "LAYOUT_COMPLIANCE_FAIL",
        "message": "Документ не відповідає вимогам для подання. Усуньте вказані проблеми.",
        "blockers": [
          {"code": "MISSING_COURT",   "message": "Назва суду", "severity": "critical"},
          {"code": "MISSING_PARTIES", "message": "Сторони (позивач / відповідач)", "severity": "critical"},
          ...
        ]
      }
    }
"""

from __future__ import annotations

import pathlib
import re
from functools import lru_cache
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

_CONFIG_PATH = pathlib.Path(__file__).parent / "export_readiness.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# Internal: run checks
# ---------------------------------------------------------------------------

def _run_checks(doc_type: str, text: str) -> list[dict[str, str]]:
    """Return a list of failing check dicts.  Each dict has code/label/severity."""
    cfg = _load_config()
    failing: list[dict[str, str]] = []

    global_checks: list[dict[str, Any]] = cfg.get("_global", {}).get("checks", [])
    doc_extra_checks: list[dict[str, Any]] = cfg.get(doc_type, {}).get("extra_checks", [])

    all_checks = list(global_checks) + list(doc_extra_checks)

    for check in all_checks:
        # Skip checks excluded for this doc_type
        skip_for: list[str] = check.get("skip_for", [])
        if doc_type in skip_for:
            continue

        code: str = check["code"]
        label: str = check["label"]
        patterns: list[str] = check.get("patterns", [])

        if not patterns:
            continue

        # At least one pattern must match (case-insensitive substring)
        matched = any(
            re.search(re.escape(p), text, re.IGNORECASE) for p in patterns
        )
        if not matched:
            failing.append({"code": code, "message": label, "severity": "critical"})

    return failing


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_export_readiness(doc_type: str, generated_text: str) -> None:
    """Raise HTTP 422 LAYOUT_COMPLIANCE_FAIL if required filing elements are absent.

    Call this inside the export endpoint BEFORE producing the artifact:

        from .export_gates import validate_export_readiness
        validate_export_readiness(document.doc_type, document.generated_text)

    If the document passes all checks, this is a no-op.
    """
    if not generated_text or not generated_text.strip():
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "LAYOUT_COMPLIANCE_FAIL",
                "message": "Документ порожній — генерація не виконана або результат не збережений.",
                "blockers": [
                    {"code": "LAYOUT_COMPLIANCE_FAIL", "message": "Текст документа відсутній.", "severity": "critical"}
                ],
            },
        )

    failing = _run_checks(doc_type, generated_text)
    if failing:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "LAYOUT_COMPLIANCE_FAIL",
                "message": "Документ не відповідає вимогам для подання. Усуньте вказані проблеми.",
                "blockers": failing,
            },
        )


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


class ReadinessCheckResult(BaseModel):
    code: str
    label: str
    passed: bool
    severity: str = "critical"


class ExportReadinessResponse(BaseModel):
    doc_type: str
    ready: bool
    """True only when all checks pass."""
    checks: list[ReadinessCheckResult]
    blocking_codes: list[str]
    """Codes of checks that are failing (always critical for now)."""


def _full_check_list(doc_type: str, text: str) -> list[ReadinessCheckResult]:
    """Return ALL checks (passed and failed) for the given doc_type and text."""
    cfg = _load_config()
    results: list[ReadinessCheckResult] = []

    global_checks: list[dict[str, Any]] = cfg.get("_global", {}).get("checks", [])
    doc_extra_checks: list[dict[str, Any]] = cfg.get(doc_type, {}).get("extra_checks", [])

    all_checks = list(global_checks) + list(doc_extra_checks)

    for check in all_checks:
        skip_for: list[str] = check.get("skip_for", [])
        if doc_type in skip_for:
            continue

        code: str = check["code"]
        label: str = check["label"]
        patterns: list[str] = check.get("patterns", [])

        if not patterns:
            continue

        matched = any(
            re.search(re.escape(p), text, re.IGNORECASE) for p in patterns
        )
        results.append(
            ReadinessCheckResult(code=code, label=label, passed=matched, severity="critical")
        )

    return results


@router.get("/{doc_id}/export-readiness", response_model=ExportReadinessResponse)
async def check_export_readiness(
    doc_id: str,
    generated_text: str = Query(..., description="The generated document text to validate."),
    doc_type: str = Query(default="", description="Document type key for per-type checklist."),
) -> ExportReadinessResponse:
    """Return filing readiness status without producing an export artifact.

    GET /api/documents/{doc_id}/export-readiness?doc_type=pozov_do_sudu&generated_text=...

    The frontend should call this endpoint when the user opens the export
    modal to decide whether to show the "Download" button or an error panel.

    In production the generated_text parameter will likely be replaced by
    reading the stored document from the database using doc_id.
    """
    if not generated_text.strip():
        return ExportReadinessResponse(
            doc_type=doc_type,
            ready=False,
            checks=[ReadinessCheckResult(code="LAYOUT_COMPLIANCE_FAIL", label="Текст документа відсутній", passed=False)],
            blocking_codes=["LAYOUT_COMPLIANCE_FAIL"],
        )

    checks = _full_check_list(doc_type, generated_text)
    failing_codes = [c.code for c in checks if not c.passed]

    return ExportReadinessResponse(
        doc_type=doc_type,
        ready=not failing_codes,
        checks=checks,
        blocking_codes=failing_codes,
    )
