"""
Wave 1+ — DocumentIR schema migration.

Converts stored ir_json dicts from older ir_version formats to the current
"1.0" schema so the application can always load historical documents without
rewriting every stored row.

Usage (in the export / IR load path):

    from .ir_migration import migrate_ir
    data = row["ir_json"]          # dict from JSONB column
    data = migrate_ir(data)        # upgrades in-place if needed
    ir   = DocumentIR(**data)

Migration rules:
    None → 1.0   (pre-versioned data, heuristic recovery)
    1.0  → 1.0   (no-op — current version)

When adding a new schema version (e.g. 1.1):
  1. Add a rule entry to _MIGRATION_CHAIN for "1.0" → "1.1".
  2. Implement the corresponding _migrate_* function.
  3. Bump _CURRENT_VERSION.
  4. Write a test in tests/test_ir_migration.py for the new rule.

SQL helper (use when backfilling):

    UPDATE generated_documents
    SET    ir_json = ir_json || '{"ir_version": "1.0"}'
    WHERE  ir_json IS NOT NULL
      AND  ir_json->>'ir_version' IS NULL;
"""

from __future__ import annotations

import copy
import logging
from typing import Any

logger = logging.getLogger("legal_ai.ir_migration")

_CURRENT_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Migration registry
# ---------------------------------------------------------------------------
# Each key is the FROM version; value is (to_version, transform_fn).
# Chain is followed automatically by migrate_ir().

MigrationFn = Any  # Callable[[dict], dict]

_MIGRATION_CHAIN: dict[str, tuple[str, MigrationFn]] = {
    # pre-versioned → 1.0
    None: ("1.0", "_migrate_none_to_1_0"),  # resolved at runtime
}


def migrate_ir(data: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *data* upgraded to the current IR schema version.

    Non-destructive: the original dict is never mutated.
    If *data* is already at _CURRENT_VERSION, returns *data* unchanged
    (same object — no copy overhead for the common path).

    Raises:
        ValueError  — if migration cannot complete (unknown intermediate version).
    """
    version = data.get("ir_version")
    if version == _CURRENT_VERSION:
        return data  # fast path: already current

    result = copy.deepcopy(data)
    hops = 0
    max_hops = 20  # safety guard against misconfigured chains

    while result.get("ir_version") != _CURRENT_VERSION:
        from_ver = result.get("ir_version")
        if from_ver not in _MIGRATION_CHAIN:
            raise ValueError(
                f"No migration path from ir_version={from_ver!r} to {_CURRENT_VERSION!r}. "
                "Add a rule to ir_migration._MIGRATION_CHAIN."
            )
        to_ver, fn_name = _MIGRATION_CHAIN[from_ver]
        fn = globals().get(fn_name)
        if fn is None:
            raise ValueError(
                f"Migration function {fn_name!r} not found in ir_migration.py."
            )
        logger.info(
            "Migrating DocumentIR from ir_version=%r → %r (doc_id=%r)",
            from_ver,
            to_ver,
            result.get("id"),
        )
        result = fn(result)
        hops += 1
        if hops >= max_hops:
            raise ValueError(
                f"Migration chain exceeded {max_hops} hops — "
                "possible loop in _MIGRATION_CHAIN."
            )

    return result


def ir_needs_migration(data: dict[str, Any]) -> bool:
    """Return True if *data* is not at the current schema version."""
    return data.get("ir_version") != _CURRENT_VERSION


# ---------------------------------------------------------------------------
# Migration: None / missing → 1.0
# ---------------------------------------------------------------------------

def _migrate_none_to_1_0(data: dict[str, Any]) -> dict[str, Any]:
    """Recover pre-versioned IR data (produced before ir_version was added).

    Heuristic rules applied:
    - Set ir_version = "1.0"
    - Set status = "needs_review" if absent
    - Ensure citations = [] if absent
    - Ensure inconsistencies = [] if absent
    - Ensure citation_coverage = 0.0 if absent
    - Flatten legacy `body` key: some early prototypes stored the entire
      document content under a top-level `body` dict.
    - Rename legacy `sections.header` → `header` (flat) if nested.
    - Ensure all list fields exist (parties, facts, legal_basis, claims,
      attachments) — fill with [] rather than crash.
    - Set signature_block to None if absent.
    """
    d = dict(data)

    # Flatten legacy nested structure: {"sections": {"header": ..., ...}}
    if "sections" in d and isinstance(d["sections"], dict):
        for section_key, section_val in d.pop("sections").items():
            if section_key not in d:
                d[section_key] = section_val

    # Flatten legacy `body` wrapper
    if "body" in d and isinstance(d["body"], dict):
        body = d.pop("body")
        for k, v in body.items():
            if k not in d:
                d[k] = v

    # Ensure required fields with safe defaults
    d.setdefault("ir_version", "1.0")
    d.setdefault("status", "needs_review")
    d.setdefault("citations", [])
    d.setdefault("inconsistencies", [])
    d.setdefault("citation_coverage", 0.0)
    d.setdefault("parties", [])
    d.setdefault("facts", [])
    d.setdefault("legal_basis", [])
    d.setdefault("claims", [])
    d.setdefault("attachments", [])
    d.setdefault("signature_block", None)

    # Ensure header exists — create minimal if absent
    if "header" not in d or d["header"] is None:
        d["header"] = {
            "title": d.pop("title", ""),
            "court_name": d.pop("court_name", ""),
            "court_type": d.pop("court_type", None),
            "case_number": d.pop("case_number", None),
            "document_date": d.pop("document_date", None),
            "jurisdiction": d.pop("jurisdiction", "UA"),
        }

    # Normalise grounding_status on each LegalThesis
    for thesis in d.get("legal_basis", []):
        if isinstance(thesis, dict):
            thesis.setdefault("citations", [])
            thesis.setdefault("grounding_status", "draft")
            thesis.setdefault("citation_coverage", 0.0)

    # Normalise claim supporting_* lists
    for claim in d.get("claims", []):
        if isinstance(claim, dict):
            claim.setdefault("supporting_fact_ids", [])
            claim.setdefault("supporting_thesis_ids", [])

    d["ir_version"] = "1.0"
    return d


# ---------------------------------------------------------------------------
# Future migrations go here:
#
# def _migrate_1_0_to_1_1(data: dict) -> dict:
#     d = dict(data)
#     # ... transform fields ...
#     d["ir_version"] = "1.1"
#     return d
#
# Then add to _MIGRATION_CHAIN:
#   "1.0": ("1.1", "_migrate_1_0_to_1_1"),
# ---------------------------------------------------------------------------
