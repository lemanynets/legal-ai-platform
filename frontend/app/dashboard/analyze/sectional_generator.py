"""
Wave 2 · STORY-3 — Sectional document generation orchestrator.

Replaces the single-pass "generate everything in one prompt" approach with
a 7-step controlled pipeline.  Each step targets a single IR section,
validates it, and retries up to _MAX_RETRIES times before falling back to
a draft placeholder.

Steps (in order):
  1. skeleton          — document structure + outline (sets header scaffold)
  2. header_parties    — DocumentHeader + all PartyItem entries
  3. facts             — FactItem list (background circumstances)
  4. legal_basis       — LegalThesis list (legal arguments, citation placeholders)
  5. claims            — ClaimItem list (прохальна частина)
  6. attachments_sig   — AttachmentItem list + SignatureBlock
  7. consistency_pass  — cross-section validation via consistency_checker

Feature flag: ENABLE_SECTIONAL_GENERATION (default false)
Per-doc_type override: sectional_config.yaml

Telemetry keys in structured logs:
  section_fail_rate           = failures / total section attempts (per section)
  section_retry_count         = per-step retry count
  section_regeneration_reason = why a section was retried (validator message)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from .consistency_checker import check_all, Inconsistency
from .document_ir import (
    AttachmentItem, ClaimItem, DocumentHeader, DocumentIR,
    FactItem, LegalThesis, PartyItem, SignatureBlock,
)
from .ir_validator import IRValidationError
from .section_validators import (
    validate_attachments_sig, validate_claims, validate_facts,
    validate_header_parties, validate_legal_basis,
)

logger = logging.getLogger("legal_ai.sectional_generator")

_MAX_RETRIES = 3
_SECTION_TIMEOUT_SECONDS = 30.0

_FLAG = os.getenv("ENABLE_SECTIONAL_GENERATION", "false").lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

@dataclass
class SectionTelemetry:
    step: str
    attempts: int = 0
    failed: bool = False
    retry_reasons: list[str] = field(default_factory=list)
    duration_ms: int = 0

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "attempts": self.attempts,
            "failed": self.failed,
            "section_retry_count": max(0, self.attempts - 1),
            "section_regeneration_reason": self.retry_reasons[-1] if self.retry_reasons else None,
            "duration_ms": self.duration_ms,
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def generate_document_sectional(
    doc_type: str,
    form_data: dict[str, Any],
    ir_id: str,
    token: str | None = None,
) -> DocumentIR:
    """Run the full 7-step sectional generation pipeline.

    Returns a DocumentIR with status='draft' if any non-fatal step failed,
    or status='needs_review'/'final' if all steps passed.

    Raises RuntimeError if ENABLE_SECTIONAL_GENERATION is false.
    """
    if not _FLAG:
        raise RuntimeError(
            "Sectional generation is disabled. "
            "Set ENABLE_SECTIONAL_GENERATION=true to activate."
        )

    import uuid
    ir = DocumentIR(
        id=str(uuid.uuid4()),
        document_type=doc_type,
        header=DocumentHeader(title=""),
    )

    telemetry: list[SectionTelemetry] = []
    any_step_failed = False

    # ── Step 1: skeleton ───────────────────────────────────────────────────
    tel = await _run_step(
        name="skeleton",
        ir=ir,
        step_fn=_step_skeleton,
        validator_fn=None,  # no validator for skeleton — just sets outline
        form_data=form_data,
        doc_type=doc_type,
    )
    telemetry.append(tel)
    any_step_failed |= tel.failed

    # ── Step 2: header + parties ───────────────────────────────────────────
    tel = await _run_step(
        name="header_parties",
        ir=ir,
        step_fn=_step_header_parties,
        validator_fn=validate_header_parties,
        form_data=form_data,
        doc_type=doc_type,
    )
    telemetry.append(tel)
    any_step_failed |= tel.failed

    # ── Step 3: facts ──────────────────────────────────────────────────────
    tel = await _run_step(
        name="facts",
        ir=ir,
        step_fn=_step_facts,
        validator_fn=validate_facts,
        form_data=form_data,
        doc_type=doc_type,
    )
    telemetry.append(tel)
    any_step_failed |= tel.failed

    # ── Step 4: legal_basis ────────────────────────────────────────────────
    tel = await _run_step(
        name="legal_basis",
        ir=ir,
        step_fn=_step_legal_basis,
        validator_fn=validate_legal_basis,
        form_data=form_data,
        doc_type=doc_type,
    )
    telemetry.append(tel)
    any_step_failed |= tel.failed

    # ── Step 5: claims ─────────────────────────────────────────────────────
    tel = await _run_step(
        name="claims",
        ir=ir,
        step_fn=_step_claims,
        validator_fn=validate_claims,
        form_data=form_data,
        doc_type=doc_type,
    )
    telemetry.append(tel)
    any_step_failed |= tel.failed

    # ── Step 6: attachments + signature ────────────────────────────────────
    tel = await _run_step(
        name="attachments_sig",
        ir=ir,
        step_fn=_step_attachments_sig,
        validator_fn=validate_attachments_sig,
        form_data=form_data,
        doc_type=doc_type,
    )
    telemetry.append(tel)
    any_step_failed |= tel.failed

    # ── Step 7: consistency pass ───────────────────────────────────────────
    inconsistencies = check_all(ir)
    ir.inconsistencies = inconsistencies
    tel = SectionTelemetry(step="consistency_pass", attempts=1)
    if inconsistencies:
        tel.failed = True
        tel.retry_reasons = [f"{inc.code}: {inc.description}" for inc in inconsistencies]
        any_step_failed = True
    telemetry.append(tel)

    # ── Finalise status ────────────────────────────────────────────────────
    ir.status = "draft" if any_step_failed else "needs_review"

    _log_pipeline(doc_type, ir, telemetry)
    return ir


# ---------------------------------------------------------------------------
# Step runner
# ---------------------------------------------------------------------------

async def _run_step(
    name: str,
    ir: DocumentIR,
    step_fn: Any,
    validator_fn: Any,
    form_data: dict[str, Any],
    doc_type: str,
) -> SectionTelemetry:
    tel = SectionTelemetry(step=name)
    t0 = time.perf_counter()

    for attempt in range(1, _MAX_RETRIES + 1):
        tel.attempts = attempt
        try:
            await asyncio.wait_for(
                step_fn(ir, form_data, doc_type),
                timeout=_SECTION_TIMEOUT_SECONDS,
            )
            if validator_fn:
                validator_fn(ir, doc_type)
            tel.duration_ms = int((time.perf_counter() - t0) * 1000)
            return tel
        except IRValidationError as exc:
            reason = "; ".join(exc.violations)
            tel.retry_reasons.append(f"attempt {attempt}: {reason}")
            logger.warning(
                json.dumps({
                    "event": "section_retry",
                    "step": name,
                    "attempt": attempt,
                    "section_regeneration_reason": reason,
                })
            )
            if attempt == _MAX_RETRIES:
                tel.failed = True
                tel.duration_ms = int((time.perf_counter() - t0) * 1000)
                logger.error(
                    json.dumps({
                        "event": "section_fail",
                        "step": name,
                        "section_fail_rate": 1.0,
                        "reason": reason,
                    })
                )
                return tel
        except asyncio.TimeoutError:
            reason = f"Section '{name}' timed out after {_SECTION_TIMEOUT_SECONDS}s"
            tel.retry_reasons.append(reason)
            tel.failed = True
            tel.duration_ms = int((time.perf_counter() - t0) * 1000)
            logger.error(json.dumps({"event": "section_timeout", "step": name}))
            return tel

    return tel


# ---------------------------------------------------------------------------
# Step stubs — replace with LLM calls in production
# ---------------------------------------------------------------------------

async def _step_skeleton(ir: DocumentIR, form_data: dict, doc_type: str) -> None:
    """Step 1: Build skeleton outline.  Sets ir.header.title at minimum."""
    ir.header.title = form_data.get("title", f"Документ типу {doc_type}")


async def _step_header_parties(ir: DocumentIR, form_data: dict, doc_type: str) -> None:
    """Step 2: Fill DocumentHeader + PartyItem list from form_data."""
    if form_data.get("court_name"):
        ir.header.court_name = form_data["court_name"]
    # TODO: LLM extracts parties from form_data fields


async def _step_facts(ir: DocumentIR, form_data: dict, doc_type: str) -> None:
    """Step 3: Generate FactItem list."""
    # TODO: LLM generates facts section
    pass


async def _step_legal_basis(ir: DocumentIR, form_data: dict, doc_type: str) -> None:
    """Step 4: Generate LegalThesis list with citation placeholders."""
    # TODO: LLM generates legal_basis; citations filled by citation_grounding step
    pass


async def _step_claims(ir: DocumentIR, form_data: dict, doc_type: str) -> None:
    """Step 5: Generate ClaimItem list (прохальна частина)."""
    # TODO: LLM generates claims based on facts + legal_basis
    pass


async def _step_attachments_sig(ir: DocumentIR, form_data: dict, doc_type: str) -> None:
    """Step 6: Fill AttachmentItem list + SignatureBlock."""
    ir.signature_block = SignatureBlock(date_placeholder=True)


# ---------------------------------------------------------------------------
# Telemetry logger
# ---------------------------------------------------------------------------

def _log_pipeline(doc_type: str, ir: DocumentIR, telemetry: list[SectionTelemetry]) -> None:
    logger.info(
        json.dumps({
            "event": "sectional_pipeline_complete",
            "doc_type": doc_type,
            "ir_id": ir.id,
            "status": ir.status,
            "steps": [t.to_log_dict() for t in telemetry],
            "inconsistencies": len(ir.inconsistencies),
        })
    )
