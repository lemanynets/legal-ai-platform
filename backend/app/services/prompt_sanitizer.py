"""Prompt injection guard – sanitizes user-supplied text before it enters AI prompts.

Strategy:
1. Strip known injection patterns (role overrides, system prompt leaks).
2. Escape delimiters that AI might interpret as instruction boundaries.
3. Truncate excessively long inputs to prevent context flooding.
"""
from __future__ import annotations

import re

# ── Injection patterns ───────────────────────────────────────────────
_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # Direct role / system overrides (EN + UA)
    (re.compile(
        r"(ignore|forget|disregard|override|bypass)\s+(all\s+)?(previous|above|prior|system)\s+(instructions?|prompts?|rules?|context)",
        re.IGNORECASE,
    ), "[заблоковано: спроба зміни інструкцій]"),
    (re.compile(
        r"(ігноруй|забудь|відкинь|обійди)\s+(всі\s+)?(попередні|системні|вищенаведені)\s+(інструкції|промпти|правила)",
        re.IGNORECASE,
    ), "[заблоковано: спроба зміни інструкцій]"),
    # "You are now..." role reassignment
    (re.compile(
        r"(you\s+are\s+now|act\s+as|pretend\s+to\s+be|switch\s+to\s+role|new\s+role\s*:)",
        re.IGNORECASE,
    ), "[заблоковано: спроба зміни ролі]"),
    (re.compile(
        r"(тепер\s+ти|дій\s+як|прикинься|зміни\s+роль|нова\s+роль\s*:)",
        re.IGNORECASE,
    ), "[заблоковано: спроба зміни ролі]"),
    # System prompt leak requests
    (re.compile(
        r"(show|reveal|print|output|repeat)\s+(your\s+)?(system\s+prompt|initial\s+instructions?|hidden\s+instructions?)",
        re.IGNORECASE,
    ), "[заблоковано: спроба витоку інструкцій]"),
    (re.compile(
        r"(покажи|виведи|повтори|розкрий)\s+(свій\s+)?(системний\s+промпт|початкові\s+інструкції|приховані\s+інструкції)",
        re.IGNORECASE,
    ), "[заблоковано: спроба витоку інструкцій]"),
    # Markdown/XML injection delimiters that mimic system boundaries
    (re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE), ""),
    (re.compile(r"```\s*system", re.IGNORECASE), ""),
    # "IMPORTANT:" / "CRITICAL:" override attempts
    (re.compile(
        r"^(IMPORTANT|CRITICAL|OVERRIDE|NOTE TO AI)\s*:",
        re.IGNORECASE | re.MULTILINE,
    ), "—"),
]

# Maximum characters per field value (prevents context flooding)
_MAX_FIELD_LENGTH = 5_000
_MAX_TOTAL_PAYLOAD_LENGTH = 50_000


def sanitize_text(value: str, *, max_length: int = _MAX_FIELD_LENGTH) -> str:
    """Sanitize a single text value destined for an AI prompt."""
    text = str(value or "").strip()
    if not text:
        return ""

    for pattern, replacement in _INJECTION_PATTERNS:
        text = pattern.sub(replacement, text)

    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "…[обрізано]"

    return text


def sanitize_form_data(form_data: dict, *, max_total: int = _MAX_TOTAL_PAYLOAD_LENGTH) -> dict:
    """Deep-sanitize an entire form_data dict before prompt building.

    Returns a new dict with all string values sanitized, lists sanitized element-wise,
    and nested dicts recursed. Non-string scalars (int, float, bool, None) pass through.
    """
    total_chars = 0

    def _sanitize_value(val, depth: int = 0):
        nonlocal total_chars
        if depth > 6:
            return val

        if isinstance(val, str):
            cleaned = sanitize_text(val)
            total_chars += len(cleaned)
            if total_chars > max_total:
                overflow = total_chars - max_total
                cleaned = cleaned[: max(0, len(cleaned) - overflow)] + "…[ліміт]"
            return cleaned

        if isinstance(val, list):
            return [_sanitize_value(item, depth + 1) for item in val[:50]]  # cap list length

        if isinstance(val, dict):
            return {k: _sanitize_value(v, depth + 1) for k, v in val.items()}

        # int, float, bool, None — pass through
        return val

    return _sanitize_value(form_data)


def sanitize_contract_text(text: str) -> str:
    """Sanitize raw contract text before analysis.

    More permissive than form_data — only strips injection patterns,
    allows longer text (contracts can be big).
    """
    return sanitize_text(text, max_length=100_000)