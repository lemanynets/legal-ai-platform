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
# LLM extraction prompt builder
# ---------------------------------------------------------------------------

_IR_EXTRACTION_SYSTEM = """\
Ти — юридичний асистент. Твоє завдання — проаналізувати текст українського \
правового документа та повернути ТІЛЬКИ валідний JSON об'єкт у форматі \
DocumentIR. Жодного додаткового тексту — тільки JSON.

Обов'язкові поля у відповіді:
- id: унікальний рядок (UUID або slug)
- document_type: тип документа зі списку нижче або "unknown"
- ir_version: завжди "1.0"
- status: "needs_review"
- header: { title, court_name, court_type, case_number, document_date, jurisdiction }
- parties: масив { id, role, name } — мінімум 1 запис
- facts: масив { id, text } — мінімум 1 факт
- legal_basis: масив { id, text, citations: [], grounding_status: "draft", citation_coverage: 0.0 }
- claims: масив { id, text, relief_type, supporting_fact_ids: [], supporting_thesis_ids: [] }
- attachments: масив { id, title, required, provided }
- signature_block: { signer_name, signer_role, date_placeholder: true }
- citations: []
- inconsistencies: []
- citation_coverage: 0.0

Для договорів (dohovir_*) court_name може бути null або порожнім рядком.
Якщо поле відсутнє в тексті — використовуй порожній рядок або порожній масив,
але не пропускай поле повністю.
"""

_SUPPORTED_DOC_TYPES = [
    "pozov_do_sudu", "pozov_trudovyi", "appeal_complaint",
    "zaява_do_sudu", "skarha_administratyvna",
    "dohovir_kupivli_prodazhu", "dohovir_orendi", "dohovir_nadannia_posluh",
    "pretenziya", "dovirennist",
]


def _build_extraction_prompt(
    doc_type: str,
    generated_text: str,
    form_data: dict[str, Any],
) -> str:
    """Build user-turn extraction prompt with document context."""
    form_context = ""
    if form_data:
        relevant_keys = [
            "plaintiff_name", "defendant_name", "court_name", "case_number",
            "claim_amount", "claim_description", "party_name", "contract_subject",
            "claimant_name", "respondent_name",
        ]
        pairs = [
            f"  {k}: {v}"
            for k, v in form_data.items()
            if k in relevant_keys and v
        ]
        if pairs:
            form_context = "\n\nДані з форми введення:\n" + "\n".join(pairs)

    return (
        f"Тип документа: {doc_type}\n"
        f"{form_context}\n\n"
        f"Текст документа:\n{generated_text[:6000]}\n\n"
        "Поверни JSON об'єкт DocumentIR."
    )


# ---------------------------------------------------------------------------
# LLM client factory
# ---------------------------------------------------------------------------

def _get_llm_client():  # type: ignore[return]
    """Return an Anthropic or OpenAI client depending on env vars.

    Priority: ANTHROPIC_API_KEY → OPENAI_API_KEY → raise.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        try:
            import anthropic  # noqa: PLC0415
            return ("anthropic", anthropic.AsyncAnthropic(api_key=anthropic_key))
        except ImportError as e:
            raise IRParseError(
                "anthropic Python package not installed. "
                "Run: pip install anthropic"
            ) from e

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            import openai  # noqa: PLC0415
            return ("openai", openai.AsyncOpenAI(api_key=openai_key))
        except ImportError as e:
            raise IRParseError(
                "openai Python package not installed. "
                "Run: pip install openai"
            ) from e

    raise IRParseError(
        "Не знайдено ANTHROPIC_API_KEY або OPENAI_API_KEY. "
        "Встанови одну зі змінних середовища або вимкни IR pipeline: "
        "ENABLE_DOCUMENT_IR_PIPELINE=off"
    )


async def _call_anthropic(client: Any, prompt: str) -> str:
    """Call Anthropic claude-sonnet-4-6 with structured extraction."""
    msg = await client.messages.create(
        model=os.getenv("IR_EXTRACTION_MODEL", "claude-sonnet-4-6"),
        max_tokens=4096,
        system=_IR_EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    return msg.content[0].text


async def _call_openai(client: Any, prompt: str) -> str:
    """Call OpenAI gpt-4o with JSON mode for structured extraction."""
    response = await client.chat.completions.create(
        model=os.getenv("IR_EXTRACTION_MODEL", "gpt-4o"),
        response_format={"type": "json_object"},
        temperature=0.0,
        messages=[
            {"role": "system", "content": _IR_EXTRACTION_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# LLM extraction — production implementation
# ---------------------------------------------------------------------------

_MAX_RETRIES = int(os.getenv("IR_EXTRACTION_MAX_RETRIES", "2"))


async def _generate_ir(
    generated_text: str,
    doc_type: str,
    form_data: dict[str, Any],
) -> DocumentIR:
    """Extract DocumentIR from generated_text using the configured LLM.

    Tries up to _MAX_RETRIES times on IRParseError before giving up.
    Falls back from Anthropic to OpenAI automatically based on env vars.

    Raises:
        IRParseError  — when JSON cannot be parsed after all retries.
        IRParseError  — when no API keys are configured.
    """
    provider, client = _get_llm_client()
    prompt = _build_extraction_prompt(doc_type, generated_text, form_data)

    last_error: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            if provider == "anthropic":
                raw = await _call_anthropic(client, prompt)
            else:
                raw = await _call_openai(client, prompt)

            ir = parse_ir_from_llm_output(raw, doc_type)
            if not ir.id:
                import uuid as _uuid
                object.__setattr__(ir, "id", str(_uuid.uuid4()))
            return ir

        except IRParseError as exc:
            last_error = exc
            logger.warning(json.dumps({
                "event": "ir_extract_retry",
                "attempt": attempt,
                "max_retries": _MAX_RETRIES,
                "error": str(exc)[:200],
            }))
            if attempt == _MAX_RETRIES:
                break
            # Retry with a nudge hint
            prompt = (
                prompt
                + f"\n\n[Спроба {attempt} не вдалась: {str(exc)[:120]}. "
                "Переконайся, що відповідь — ТІЛЬКИ валідний JSON без markdown-блоків.]"
            )

    raise IRParseError(
        f"IR extraction failed after {_MAX_RETRIES} retries: {last_error}"
    ) from last_error
