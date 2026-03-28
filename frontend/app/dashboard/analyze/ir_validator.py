"""
Wave 1 · STORY-1 — DocumentIR validator.

validate_ir(ir, doc_type) raises IRValidationError if the IR does not
satisfy the per-doc_type rules defined in ir_validator_config.yaml.

Usage inside the generation pipeline:

    from .ir_validator import validate_ir, IRValidationError, IRParseError
    try:
        validate_ir(ir, doc_type=body.doc_type)
    except IRValidationError as exc:
        raise HTTPException(422, {"error_code": "IR_VALIDATION_FAIL",
                                  "message": str(exc),
                                  "violations": exc.violations})

Unit tests: tests/test_ir_validator.py (coverage ≥ 90%)
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from .document_ir import DocumentIR


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

@dataclass
class IRValidationError(Exception):
    """Raised when a DocumentIR fails structural validation.

    `violations` is a list of human-readable failure descriptions.
    """

    violations: list[str]

    def __str__(self) -> str:
        return f"IR validation failed: {'; '.join(self.violations)}"


class IRParseError(Exception):
    """Raised when raw LLM output cannot be parsed into a DocumentIR."""


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_CONFIG_PATH = pathlib.Path(__file__).parent / "ir_validator_config.yaml"


@lru_cache(maxsize=1)
def _load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh)


def _doc_config(doc_type: str) -> dict[str, Any]:
    cfg = _load_config()
    return cfg.get(doc_type) or cfg.get("_default") or {}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_ir(ir: DocumentIR, doc_type: str = "") -> None:
    """Raise IRValidationError if the IR does not pass structural rules.

    No-op when doc_type has no config entry and _default is satisfied.
    Always safe to call; does NOT mutate the IR object.
    """
    cfg = _doc_config(doc_type or ir.document_type)
    violations: list[str] = []

    # 1 — Required top-level sections must be non-empty
    for section in cfg.get("required_sections", []):
        value = getattr(ir, section, None)
        if value is None:
            violations.append(f"Секція '{section}' є обов'язковою але відсутня.")
        elif isinstance(value, list) and not value:
            violations.append(f"Секція '{section}' є обов'язковою але порожня.")

    # 2 — Required party roles
    present_roles = {p.role.lower() for p in ir.parties}
    for role in cfg.get("required_party_roles", []):
        if role.lower() not in present_roles:
            violations.append(f"Відсутня обов'язкова сторона: '{role}'.")

    # 3 — Required header fields
    for hfield in cfg.get("required_header_fields", []):
        val = getattr(ir.header, hfield, None)
        if not val:
            violations.append(f"Обов'язкове поле заголовку '{hfield}' відсутнє.")

    # 4 — Minimum counts
    min_facts = cfg.get("min_facts", 0)
    if len(ir.facts) < min_facts:
        violations.append(
            f"Потрібно щонайменше {min_facts} фактичних обставин; є {len(ir.facts)}."
        )

    min_legal = cfg.get("min_legal_basis", 0)
    if len(ir.legal_basis) < min_legal:
        violations.append(
            f"Потрібно щонайменше {min_legal} правових тез; є {len(ir.legal_basis)}."
        )

    min_claims = cfg.get("min_claims", 0)
    if len(ir.claims) < min_claims:
        violations.append(
            f"Потрібно щонайменше {min_claims} вимог (прохальна частина); є {len(ir.claims)}."
        )

    # 5 — Signature block
    if cfg.get("signature_required", False) and ir.signature_block is None:
        violations.append("Блок підпису відсутній (підпис обов'язковий для цього типу документа).")

    # 6 — Citation ID referential integrity
    known_citation_ids = {c.id for c in ir.citations}
    for thesis in ir.legal_basis:
        for cid in thesis.citations:
            if cid not in known_citation_ids:
                violations.append(
                    f"Теза '{thesis.id}' посилається на невідому цитату '{cid}'."
                )

    # 7 — Final status requires zero inconsistencies and fully grounded theses
    if ir.status == "final":
        if ir.inconsistencies:
            violations.append(
                f"Документ зі статусом 'final' має {len(ir.inconsistencies)} "
                f"неузгодженостей — усуньте їх або змініть статус на 'needs_review'."
            )
        ungrounded = ir.ungrounded_theses()
        if ungrounded:
            violations.append(
                f"Документ зі статусом 'final' має {len(ungrounded)} непідкріплених тез "
                f"(grounding_status != 'grounded')."
            )

    if violations:
        raise IRValidationError(violations=violations)


def parse_ir_from_llm_output(raw: str, doc_type: str = "") -> DocumentIR:
    """Parse a DocumentIR from raw JSON string produced by the LLM.

    Raises IRParseError on any JSON or Pydantic validation failure.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IRParseError(f"LLM output is not valid JSON: {exc}") from exc
    try:
        return DocumentIR(**data)
    except Exception as exc:
        raise IRParseError(f"LLM JSON does not match DocumentIR schema: {exc}") from exc
