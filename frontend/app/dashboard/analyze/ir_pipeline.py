"""
Wave 1 · STORY-2 — Shadow mode IR pipeline.

Controls whether the DocumentIR pipeline runs alongside the legacy
free-text generation, and whether the IR drives the final output.

Environment variable: ENABLE_DOCUMENT_IR_PIPELINE
  "off"    — IR pipeline disabled (default).  Legacy path unchanged.
  "shadow" — IR is generated and validated; result is LOGGED but the
             legacy generated_text is returned to the user unchanged.
             Failures are caught and logged; user never sees IR errors.
  "on"     — IR pipeline is the primary path.  IR drives the renderer.
             Failures bubble up as 422 IR_PARSE_FAIL / IR_VALIDATION_FAIL.

Per-doc_type override: set ir_pipeline_mode in ir_pipeline_config.yaml.
Flag is read once at import time but config file is watched via lru_cache
so it can be reloaded without a restart by calling _reload_pipeline_config().

Structured log format (emitted for each IR run):
    {
      "event": "ir_pipeline",
      "doc_type": "...",
      "mode": "shadow|on",
      "status": "ok|ir_parse_fail|ir_validation_fail",
      "ir_id": "...",          # present on success
      "violations": [...],     # present on ir_validation_fail
      "error": "...",          # present on ir_parse_fail
      "citation_coverage": N,  # 0.0–1.0
      "duration_ms": N
    }

Metrics derived from logs:
  ir_parse_fail_rate      = count(status=ir_parse_fail) / count(event=ir_pipeline)
  ir_validation_fail_rate = count(status=ir_validation_fail) / count(event=ir_pipeline)
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import time
from functools import lru_cache
from typing import Any, Literal

import yaml
from fastapi import HTTPException

from .document_ir import DocumentIR
from .ir_validator import IRParseError, IRValidationError, parse_ir_from_llm_output, validate_ir

logger = logging.getLogger("legal_ai.ir_pipeline")

# ---------------------------------------------------------------------------
# Feature flag + config
# ---------------------------------------------------------------------------

PipelineMode = Literal["off", "shadow", "on"]

_GLOBAL_MODE: PipelineMode = (
    os.getenv("ENABLE_DOCUMENT_IR_PIPELINE", "off").lower()  # type: ignore[assignment]
)

_CONFIG_PATH = pathlib.Path(__file__).parent / "ir_pipeline_config.yaml"


@lru_cache(maxsize=1)
def _load_pipeline_config() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh) or {}


def reload_pipeline_config() -> None:
    """Force reload of ir_pipeline_config.yaml (for hot config changes)."""
    _load_pipeline_config.cache_clear()


def pipeline_mode_for_doc_type(doc_type: str) -> PipelineMode:
    """Return effective pipeline mode for a given doc_type.

    Per-doc_type overrides in ir_pipeline_config.yaml take precedence
    over the global ENABLE_DOCUMENT_IR_PIPELINE env var.
    """
    cfg = _load_pipeline_config()
    per_type: dict[str, str] = cfg.get("per_doc_type", {})
    mode = per_type.get(doc_type, _GLOBAL_MODE)
    if mode not in ("off", "shadow", "on"):
        return "off"
    return mode  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Pipeline entry point
# ---------------------------------------------------------------------------

async def run_ir_pipeline(
    doc_type: str,
    generated_text: str,
    form_data: dict[str, Any] | None = None,
) -> DocumentIR | None:
    """Run the IR pipeline for a completed document generation.

    Returns:
        DocumentIR when mode == "on" and pipeline succeeds.
        None when mode == "shadow" (IR logged but not returned)
          or mode == "off" (pipeline not run).

    Raises HTTPException(422) only when mode == "on" and pipeline fails.
    """
    mode = pipeline_mode_for_doc_type(doc_type)
    if mode == "off":
        return None

    t0 = time.perf_counter()
    ir: DocumentIR | None = None
    log_entry: dict[str, Any] = {
        "event": "ir_pipeline",
        "doc_type": doc_type,
        "mode": mode,
    }

    try:
        ir = await _generate_ir(generated_text, doc_type, form_data or {})
        validate_ir(ir, doc_type)
        log_entry.update(
            status="ok",
            ir_id=ir.id,
            citation_coverage=ir.citation_coverage,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        logger.info(json.dumps(log_entry))

        return ir if mode == "on" else None

    except IRParseError as exc:
        log_entry.update(
            status="ir_parse_fail",
            error=str(exc),
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        logger.warning(json.dumps(log_entry))

        if mode == "on":
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "IR_PARSE_FAIL",
                    "message": (
                        "Сервер повернув некоректну структуру документа. Спробуй ще раз."
                    ),
                    "error": str(exc),
                },
            )
        return None  # shadow: swallow

    except IRValidationError as exc:
        log_entry.update(
            status="ir_validation_fail",
            violations=exc.violations,
            ir_id=ir.id if ir else None,
            duration_ms=int((time.perf_counter() - t0) * 1000),
        )
        logger.warning(json.dumps(log_entry))

        if mode == "on":
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "IR_VALIDATION_FAIL",
                    "message": "Структура згенерованого документа не пройшла валідацію.",
                    "violations": exc.violations,
                },
            )
        return None  # shadow: swallow


# ---------------------------------------------------------------------------
# LLM stub — replace with real implementation
# ---------------------------------------------------------------------------

async def _generate_ir(
    generated_text: str,
    doc_type: str,
    form_data: dict[str, Any],
) -> DocumentIR:
    """Generate a DocumentIR from the legacy generated_text.

    STUB — in production this calls the LLM with a structured extraction
    prompt and parses the JSON response via parse_ir_from_llm_output().

    The prompt should instruct the model to output a JSON object that
    matches the DocumentIR schema exactly.
    """
    import uuid

    # In production: replace with actual LLM call + json extraction
    raise IRParseError(
        "IR generation not yet implemented. "
        "Set ENABLE_DOCUMENT_IR_PIPELINE=off until Wave 1 is complete."
    )
