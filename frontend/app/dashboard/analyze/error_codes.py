"""
Canonical error code constants — mirrors frontend/lib/error-codes.ts.

Backend MUST use these constants (never raw string literals) in all
HTTPException details so frontend can do exact-match error handling.

Import pattern:

    from app.dashboard.analyze.error_codes import (
        PROC_BLOCKER, LAYOUT_COMPLIANCE_FAIL, IR_VALIDATION_FAIL,
        ErrorCode,
    )
    raise HTTPException(422, {"error_code": PROC_BLOCKER, ...})
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Wave 0 — input gates
# ---------------------------------------------------------------------------

INPUT_MISSING_REQUIRED_FIELDS = "INPUT_MISSING_REQUIRED_FIELDS"

# ---------------------------------------------------------------------------
# Wave 0 — processual gates
# ---------------------------------------------------------------------------

PROC_BLOCKER = "PROC_BLOCKER"

# ---------------------------------------------------------------------------
# Wave 0 — export/filing gate
# ---------------------------------------------------------------------------

LAYOUT_COMPLIANCE_FAIL  = "LAYOUT_COMPLIANCE_FAIL"
MISSING_COURT           = "MISSING_COURT"
MISSING_PARTIES         = "MISSING_PARTIES"
MISSING_TITLE           = "MISSING_TITLE"
MISSING_CLAIMS          = "MISSING_CLAIMS"
MISSING_SIGNATURE_BLOCK = "MISSING_SIGNATURE_BLOCK"
MISSING_ATTACHMENTS     = "MISSING_ATTACHMENTS"

# ---------------------------------------------------------------------------
# Wave 1 — IR pipeline
# ---------------------------------------------------------------------------

IR_PARSE_FAIL      = "IR_PARSE_FAIL"
IR_VALIDATION_FAIL = "IR_VALIDATION_FAIL"

# ---------------------------------------------------------------------------
# Wave 2 — sectional generation
# ---------------------------------------------------------------------------

SECTION_INCONSISTENCY = "SECTION_INCONSISTENCY"

# ---------------------------------------------------------------------------
# Wave 3 — citation grounding
# ---------------------------------------------------------------------------

CITATION_GROUNDING_FAIL = "CITATION_GROUNDING_FAIL"
RETRIEVAL_TIMEOUT       = "RETRIEVAL_TIMEOUT"

# ---------------------------------------------------------------------------
# Wave 4 — rendering
# ---------------------------------------------------------------------------

RENDER_FAIL = "RENDER_FAIL"

# ---------------------------------------------------------------------------
# Structured set for validation / exhaustiveness checks
# ---------------------------------------------------------------------------

ErrorCode = frozenset({
    INPUT_MISSING_REQUIRED_FIELDS,
    PROC_BLOCKER,
    LAYOUT_COMPLIANCE_FAIL,
    MISSING_COURT,
    MISSING_PARTIES,
    MISSING_TITLE,
    MISSING_CLAIMS,
    MISSING_SIGNATURE_BLOCK,
    MISSING_ATTACHMENTS,
    IR_PARSE_FAIL,
    IR_VALIDATION_FAIL,
    SECTION_INCONSISTENCY,
    CITATION_GROUNDING_FAIL,
    RETRIEVAL_TIMEOUT,
    RENDER_FAIL,
})


def is_known_code(code: str) -> bool:
    return code in ErrorCode
