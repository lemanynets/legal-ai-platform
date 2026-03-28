"""
Central feature-flag registry.

Consolidates all ENABLE_* flags for Wave 0–4 into one module with:
  - Environment variable reads (primary source)
  - Per-doc_type overrides from feature_flags.yaml
  - Hot reload: call reload() to re-read YAML without restart
  - Type-safe access: use the Flag enum or named helpers

Feature flags table (source of truth mirrors roadmap):

  Flag                              Type              Default prod  Scope
  ─────────────────────────────────────────────────────────────────────────
  ENABLE_REQUIRED_INPUT_GATES       bool per doc_type false         Wave 0
  ENABLE_BLOCKING_PROCESSUAL_GATES  bool per doc_type false         Wave 0
  ENABLE_DOCUMENT_IR_PIPELINE       off|shadow|on     off           Wave 1–2
  ENABLE_SECTIONAL_GENERATION       bool per doc_type false         Wave 2
  ENABLE_IR_RENDERER                bool per doc_type false         Wave 4
  ENABLE_CITATION_GROUNDING_GATE    bool per doc_type false         Wave 3

Usage:

    from .feature_flags import flags
    if flags.sectional_generation("appeal_complaint"):
        result = await generate_document_sectional(...)
    if flags.ir_renderer("pozov_do_sudu"):
        docx_bytes = renderer.render_docx(ir)
"""

from __future__ import annotations

import os
import pathlib
from functools import lru_cache
from typing import Any, Literal

import yaml

_CONFIG_PATH = pathlib.Path(__file__).parent / "feature_flags.yaml"

IRPipelineMode = Literal["off", "shadow", "on"]


@lru_cache(maxsize=1)
def _load() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return {}
    with _CONFIG_PATH.open() as fh:
        return yaml.safe_load(fh) or {}


def reload() -> None:
    """Force re-read of feature_flags.yaml (hot config reload)."""
    _load.cache_clear()


def _bool_env(name: str, default: bool = False) -> bool:
    return os.getenv(name, "1" if default else "0").lower() in ("1", "true", "yes")


def _str_env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _per_type(section: str, doc_type: str, fallback: Any) -> Any:
    cfg = _load()
    per_type: dict[str, Any] = cfg.get(section, {}).get("per_doc_type", {})
    return per_type.get(doc_type, fallback)


# ---------------------------------------------------------------------------
# Named flag helpers
# ---------------------------------------------------------------------------

class _Flags:
    """Typed access to all feature flags.

    Methods accept an optional doc_type for per-type overrides.
    """

    # ── Wave 0 ────────────────────────────────────────────────────────────

    def required_input_gates(self, doc_type: str = "") -> bool:
        """ENABLE_REQUIRED_INPUT_GATES — validate required fields before generation."""
        global_val = _bool_env("ENABLE_REQUIRED_INPUT_GATES", False)
        if not doc_type:
            return global_val
        return bool(_per_type("required_input_gates", doc_type, global_val))

    def blocking_processual_gates(self, doc_type: str = "") -> bool:
        """ENABLE_BLOCKING_PROCESSUAL_GATES — critical processual checks block generation."""
        global_val = _bool_env("ENABLE_BLOCKING_PROCESSUAL_GATES", False)
        if not doc_type:
            return global_val
        return bool(_per_type("blocking_processual_gates", doc_type, global_val))

    # ── Wave 1–2 ──────────────────────────────────────────────────────────

    def ir_pipeline(self, doc_type: str = "") -> IRPipelineMode:
        """ENABLE_DOCUMENT_IR_PIPELINE — off | shadow | on."""
        global_val: str = _str_env("ENABLE_DOCUMENT_IR_PIPELINE", "off").lower()
        if global_val not in ("off", "shadow", "on"):
            global_val = "off"
        if not doc_type:
            return global_val  # type: ignore[return-value]
        override = _per_type("ir_pipeline", doc_type, global_val)
        if override not in ("off", "shadow", "on"):
            return global_val  # type: ignore[return-value]
        return override  # type: ignore[return-value]

    def sectional_generation(self, doc_type: str = "") -> bool:
        """ENABLE_SECTIONAL_GENERATION — use 7-step sectional pipeline."""
        global_val = _bool_env("ENABLE_SECTIONAL_GENERATION", False)
        if not doc_type:
            return global_val
        return bool(_per_type("sectional_generation", doc_type, global_val))

    # ── Wave 3 ────────────────────────────────────────────────────────────

    def citation_grounding_gate(self, doc_type: str = "") -> bool:
        """ENABLE_CITATION_GROUNDING_GATE — block export when theses are ungrounded."""
        global_val = _bool_env("ENABLE_CITATION_GROUNDING_GATE", False)
        if not doc_type:
            return global_val
        return bool(_per_type("citation_grounding_gate", doc_type, global_val))

    # ── Wave 4 ────────────────────────────────────────────────────────────

    def ir_renderer(self, doc_type: str = "") -> bool:
        """ENABLE_IR_RENDERER — use DocumentIR-driven DOCX/PDF renderer."""
        global_val = _bool_env("ENABLE_IR_RENDERER", False)
        if not doc_type:
            return global_val
        return bool(_per_type("ir_renderer", doc_type, global_val))


flags = _Flags()
