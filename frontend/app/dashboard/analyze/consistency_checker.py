"""
Wave 2 · STORY-4 — Cross-section consistency checker.

Four independent checkers; results accumulate into ir.inconsistencies.
Non-empty inconsistencies list blocks 'final' status.

Checkers:
  check_party_names_consistent  — same name for same role across all sections
  check_dates_consistent        — dates in facts don't contradict each other
  check_amounts_consistent      — monetary amounts in facts match claims
  check_claims_reference_facts  — each claim references at least one fact/thesis

Public entry point: check_all(ir) → list[Inconsistency]

Unit tests: tests/test_consistency.py
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Callable

from .document_ir import DocumentIR, Inconsistency


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

CheckerFn = Callable[[DocumentIR], list[Inconsistency]]

_CHECKERS: list[CheckerFn] = []


def _checker(fn: CheckerFn) -> CheckerFn:
    _CHECKERS.append(fn)
    return fn


def check_all(ir: DocumentIR) -> list[Inconsistency]:
    """Run all registered checkers and return the combined list.

    Does NOT mutate ir.inconsistencies — caller decides whether to assign.
    """
    results: list[Inconsistency] = []
    for fn in _CHECKERS:
        results.extend(fn(ir))
    return results


# ---------------------------------------------------------------------------
# Checker 1 — Party name consistency
# ---------------------------------------------------------------------------

@_checker
def check_party_names_consistent(ir: DocumentIR) -> list[Inconsistency]:
    """Each role must have exactly one distinct (normalised) name.

    Unit test: two 'позивач' entries with different names → PARTY_NAME_MISMATCH.
    """
    by_role: dict[str, set[str]] = defaultdict(set)
    for party in ir.parties:
        by_role[party.role.lower()].add(_normalise_name(party.name))

    inconsistencies: list[Inconsistency] = []
    for role, names in by_role.items():
        if len(names) > 1:
            inconsistencies.append(
                Inconsistency(
                    code="PARTY_NAME_MISMATCH",
                    description=(
                        f"Роль '{role}' має суперечливі імена: {', '.join(sorted(names))}."
                    ),
                    affected_sections=["parties"],
                )
            )

    # Also check that party names mentioned in facts/legal_basis match the parties list
    all_party_names = {_normalise_name(p.name) for p in ir.parties}
    for fact in ir.facts:
        for name in _extract_likely_names(fact.text):
            # If a name looks like it could be a party but doesn't match any party, warn
            if name and name not in all_party_names:
                # Only flag as inconsistency if it looks substantially different
                # (heuristic: full name with ≥2 words not in parties list)
                if len(name.split()) >= 2:
                    inconsistencies.append(
                        Inconsistency(
                            code="PARTY_NAME_MISMATCH",
                            description=(
                                f"Ім'я '{name}' у розділі 'facts' не знайдено у списку сторін."
                            ),
                            affected_sections=["parties", "facts"],
                        )
                    )
                    break  # one warning per fact is enough

    return inconsistencies


# ---------------------------------------------------------------------------
# Checker 2 — Date consistency
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(
    r"\b(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{4})\b"
    r"|\b(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\b"
)


@_checker
def check_dates_consistent(ir: DocumentIR) -> list[Inconsistency]:
    """Dates within facts must not contradict each other logically.

    Current check: a fact with an earlier explicit date appearing AFTER a
    fact with a later date is flagged (list order implies chronology).

    Unit test: fact[0].date = "2024-12-01", fact[1].date = "2023-01-01" → DATE_CONTRADICTION.
    """
    dated_facts = [f for f in ir.facts if f.date]
    inconsistencies: list[Inconsistency] = []

    for i in range(len(dated_facts) - 1):
        a = dated_facts[i]
        b = dated_facts[i + 1]
        try:
            da = _parse_date(a.date)  # type: ignore[arg-type]
            db = _parse_date(b.date)  # type: ignore[arg-type]
            if da and db and da > db:
                inconsistencies.append(
                    Inconsistency(
                        code="DATE_CONTRADICTION",
                        description=(
                            f"Факт '{a.id}' ({a.date}) йде перед фактом '{b.id}' ({b.date}), "
                            "але хронологічно пізніший."
                        ),
                        affected_sections=["facts"],
                    )
                )
        except (ValueError, TypeError):
            pass  # unparseable dates are ignored

    return inconsistencies


# ---------------------------------------------------------------------------
# Checker 3 — Amount consistency
# ---------------------------------------------------------------------------

_AMOUNT_RE = re.compile(r"(\d[\d\s]*(?:[.,]\d+)?)\s*(грн|UAH|USD|EUR)", re.IGNORECASE)


@_checker
def check_amounts_consistent(ir: DocumentIR) -> list[Inconsistency]:
    """Monetary totals in facts must not significantly contradict claims.

    Heuristic: if the largest amount extracted from facts is more than 10%
    larger than the largest claim amount, flag as AMOUNT_MISMATCH.

    Unit test: facts mention 100_000 UAH, claim.amount = 50_000 → AMOUNT_MISMATCH.
    """
    fact_amounts = _extract_amounts_from_texts([f.text for f in ir.facts])
    claim_amounts = [
        c.amount for c in ir.claims
        if c.amount is not None and c.relief_type == "monetary"
    ]

    if not fact_amounts or not claim_amounts:
        return []

    max_fact = max(fact_amounts)
    max_claim = max(claim_amounts)

    if max_fact > max_claim * 1.10:
        return [
            Inconsistency(
                code="AMOUNT_MISMATCH",
                description=(
                    f"Найбільша сума у фактах ({max_fact:,.0f}) перевищує найбільшу вимогу "
                    f"({max_claim:,.0f}) більш ніж на 10%."
                ),
                affected_sections=["facts", "claims"],
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Checker 4 — Claims reference facts/legal_basis
# ---------------------------------------------------------------------------

@_checker
def check_claims_reference_facts(ir: DocumentIR) -> list[Inconsistency]:
    """Each claim must reference at least one fact OR one legal thesis.

    Unit test: claim with supporting_fact_ids=[] and supporting_thesis_ids=[] → CLAIM_UNREFERENCED.
    """
    if not ir.facts and not ir.legal_basis:
        return []  # doc type doesn't use facts/legal_basis

    inconsistencies: list[Inconsistency] = []
    valid_fact_ids = {f.id for f in ir.facts}
    valid_thesis_ids = {t.id for t in ir.legal_basis}

    for claim in ir.claims:
        linked_facts = [f for f in claim.supporting_fact_ids if f in valid_fact_ids]
        linked_theses = [t for t in claim.supporting_thesis_ids if t in valid_thesis_ids]
        if not linked_facts and not linked_theses and (ir.facts or ir.legal_basis):
            inconsistencies.append(
                Inconsistency(
                    code="CLAIM_UNREFERENCED",
                    description=(
                        f"Вимога '{claim.id}' ({claim.text[:60]}…) "
                        "не посилається на жоден факт або правову тезу."
                    ),
                    affected_sections=["facts", "legal_basis", "claims"],
                )
            )

    return inconsistencies


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise_name(name: str) -> str:
    return " ".join(name.strip().split()).lower()


def _extract_likely_names(text: str) -> list[str]:
    """Very rough heuristic: capitalised multi-word sequences."""
    matches = re.findall(r"\b([А-ЯІЇЄҐ][а-яіїєґ\']+(?:\s[А-ЯІЇЄҐ][а-яіїєґ\']+){1,2})\b", text)
    return [_normalise_name(m) for m in matches]


def _parse_date(date_str: str) -> tuple[int, int, int] | None:
    """Return (year, month, day) or None."""
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})", date_str)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"(\d{1,2})[./](\d{1,2})[./](\d{4})", date_str)
    if m:
        return int(m.group(3)), int(m.group(2)), int(m.group(1))
    return None


def _extract_amounts_from_texts(texts: list[str]) -> list[float]:
    amounts: list[float] = []
    for text in texts:
        for m in _AMOUNT_RE.finditer(text):
            raw = m.group(1).replace(" ", "").replace(",", ".")
            try:
                amounts.append(float(raw))
            except ValueError:
                pass
    return amounts
