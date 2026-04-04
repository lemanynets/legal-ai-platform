from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import re
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import CaseLawCache, DocumentCaseLawRef
from app.services.case_law_cache import is_supreme_court_name


ALLOWED_CASE_LAW_SOURCES = {"edrsr", "data_gov_ua", "opendatabot"}

DOC_TYPE_DEFAULT_TAGS: dict[str, tuple[str, ...]] = {
    "lawsuit_debt_loan": ("debt", "loan", "receipt", "interest", "penalty", "625"),
    "lawsuit_debt_sale": ("debt", "sale", "purchase", "contract", "payment", "penalty"),
    "appeal_complaint": ("appeal", "complaint", "procedure"),
    "pretension_debt_return": ("debt", "pretension", "pretrial"),
    "contract_services": ("services", "contract", "liability"),
}

DOC_TYPE_COURT_TYPE: dict[str, str] = {
    "lawsuit_debt_loan": "civil",
    "lawsuit_debt_sale": "civil",
    "appeal_complaint": "civil",
}

TOP_CLAIM_DOC_TYPES: set[str] = {
    "lawsuit_debt_loan",
    "lawsuit_debt_sale",
    "appeal_complaint",
    "pretension_debt_return",
}

WORD_PATTERN = re.compile(r"[^\W_]+", flags=re.UNICODE)


@dataclass(frozen=True)
class CaseLawMatch:
    id: str
    source: str
    decision_id: str
    court_name: str | None
    court_type: str | None
    decision_date: str | None
    case_number: str | None
    summary: str | None
    legal_positions: dict[str, Any]
    subject_categories: list[str]
    relevance_score: float


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _tokenize(value: str) -> list[str]:
    return [token.lower() for token in WORD_PATTERN.findall(value) if token]


def _coerce_strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _extract_tags(document_type: str, form_data: dict[str, Any]) -> list[str]:
    tags: list[str] = [*DOC_TYPE_DEFAULT_TAGS.get(document_type, ())]
    probe_keys = (
        "debt_basis",
        "fact_summary",
        "request_summary",
        "claim_subject",
        "contract_type",
        "document_type",
    )
    for key in probe_keys:
        value = form_data.get(key)
        if isinstance(value, str):
            tags.extend(_tokenize(value))
    tags.extend(_coerce_strings(form_data.get("claim_requests")))

    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        cleaned = _normalize_text(str(tag))
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _decision_recency_score(decision_date: date | None) -> float:
    if decision_date is None:
        return 0.0
    age_days = max((date.today() - decision_date).days, 0)
    if age_days <= 365:
        return 0.2
    if age_days <= 365 * 3:
        return 0.1
    return 0.03


def _score_case_law(
    row: CaseLawCache,
    *,
    query_tags: list[str],
    preferred_court_type: str | None,
) -> float:
    query_set = set(query_tags)
    row_set = {_normalize_text(item) for item in _coerce_strings(row.subject_categories)}
    overlap_count = len(query_set.intersection(row_set))

    overlap_score = 0.0
    if query_set:
        overlap_score = overlap_count / len(query_set)

    court_bonus = 0.0
    if preferred_court_type and row.court_type and _normalize_text(row.court_type) == _normalize_text(preferred_court_type):
        court_bonus = 0.2

    popularity_score = min(max(int(row.reference_count or 0), 0), 100) / 1000
    recency_score = _decision_recency_score(row.decision_date)
    base = 0.12 if overlap_count > 0 else 0.0
    score = base + overlap_score * 0.6 + court_bonus + popularity_score + recency_score
    return round(min(score, 1.0), 2)


def _serialize_match(row: CaseLawCache, score: float) -> CaseLawMatch:
    return CaseLawMatch(
        id=row.id,
        source=row.source,
        decision_id=row.decision_id,
        court_name=row.court_name,
        court_type=row.court_type,
        decision_date=row.decision_date.isoformat() if row.decision_date else None,
        case_number=row.case_number,
        summary=row.summary,
        legal_positions=row.legal_positions or {},
        subject_categories=_coerce_strings(row.subject_categories),
        relevance_score=score,
    )


def enrich_document_with_case_law(
    db: Session,
    *,
    document_type: str,
    form_data: dict[str, Any],
    limit: int = 5,
    scan_limit: int = 400,
) -> list[CaseLawMatch]:
    safe_limit = max(1, min(limit, 20))
    safe_scan_limit = max(safe_limit, min(scan_limit, 2000))
    tags = _extract_tags(document_type, form_data)
    preferred_court_type = DOC_TYPE_COURT_TYPE.get(document_type)
    threshold = date.today() - timedelta(days=max(1, settings.case_law_generation_max_age_days))

    stmt = (
        select(CaseLawCache)
        .where(CaseLawCache.source.in_(tuple(ALLOWED_CASE_LAW_SOURCES)))
        .where((CaseLawCache.decision_date.is_(None)) | (CaseLawCache.decision_date >= threshold))
        .order_by(desc(CaseLawCache.decision_date), desc(CaseLawCache.created_at))
        .limit(safe_scan_limit)
    )
    rows = list(db.execute(stmt).scalars().all())
    if not rows:
        fallback_stmt = (
            select(CaseLawCache)
            .order_by(desc(CaseLawCache.decision_date), desc(CaseLawCache.created_at))
            .limit(safe_scan_limit)
        )
        rows = list(db.execute(fallback_stmt).scalars().all())
    if settings.case_law_generation_supreme_only and rows:
        filtered = [row for row in rows if is_supreme_court_name(row.court_name)]
        if filtered:
            rows = filtered

    scored: list[tuple[CaseLawCache, float]] = []
    for row in rows:
        score = _score_case_law(row, query_tags=tags, preferred_court_type=preferred_court_type)
        if tags and score <= 0:
            continue
        if tags and score < settings.case_law_generation_min_relevance_score:
            continue
        scored.append((row, score))

    scored.sort(
        key=lambda item: (
            item[1],
            item[0].decision_date or date.min,
            int(item[0].reference_count or 0),
            item[0].created_at,
        ),
        reverse=True,
    )

    selected = scored[:safe_limit]
    return [_serialize_match(row, score) for row, score in selected]


def _positions_to_text(legal_positions: dict[str, Any]) -> str:
    if not isinstance(legal_positions, dict) or not legal_positions:
        return ""
    chunks: list[str] = []
    for key, value in legal_positions.items():
        text = str(value).strip()
        if not text:
            continue
        chunks.append(f"{key}: {text}")
        if len(chunks) >= 2:
            break
    joined = "; ".join(chunks)
    return joined[:300]


def build_motivation_reference_block(document_type: str, case_law_refs: list[CaseLawMatch]) -> str:
    if document_type not in TOP_CLAIM_DOC_TYPES or not case_law_refs:
        return ""
    lines = ["Case law references for motivation section:"]
    for index, item in enumerate(case_law_refs, start=1):
        case_ref = item.case_number or item.decision_id
        court = item.court_name or item.court_type or "Court not specified"
        date_text = item.decision_date or "n/a"
        lines.append(f"{index}. {court}, case {case_ref}, date {date_text}, source {item.source}.")
    return "\n".join(lines)


def inject_motivation_references(
    *,
    document_type: str,
    generated_text: str,
    case_law_refs: list[CaseLawMatch],
) -> str:
    if document_type not in TOP_CLAIM_DOC_TYPES or not case_law_refs:
        return generated_text
    normalized_text = (generated_text or "").strip()
    if not normalized_text:
        return generated_text

    refs = [item.case_number or item.decision_id for item in case_law_refs]
    lower_text = normalized_text.lower()
    if any(str(ref).lower() in lower_text for ref in refs if ref):
        return generated_text

    block = build_motivation_reference_block(document_type, case_law_refs)
    if not block:
        return generated_text
    return f"{normalized_text}\n\n{block}"


def build_case_law_prompt_context(case_law_refs: list[CaseLawMatch]) -> str:
    if not case_law_refs:
        return ""

    lines = ["Use these court decisions in the legal reasoning section and cite them directly:"]
    for index, item in enumerate(case_law_refs, start=1):
        case_ref = item.case_number or item.decision_id
        summary = (item.summary or "").strip()
        court = item.court_name or "Court not specified"
        date_text = item.decision_date or "n/a"
        position_text = _positions_to_text(item.legal_positions)

        line = f"{index}. [{item.source}] case {case_ref}, {court}, date {date_text}"
        if summary:
            line += f". Summary: {summary[:280]}"
        if position_text:
            line += f". Key positions: {position_text}"
        lines.append(line)
    return "\n".join(lines)


def _to_decimal(value: float | int | str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def attach_case_law_refs_to_document(
    db: Session,
    *,
    document_id: str,
    case_law_refs: list[CaseLawMatch],
) -> int:
    if not case_law_refs:
        return 0

    case_ids: list[str] = []
    seen: set[str] = set()
    for item in case_law_refs:
        if item.id in seen:
            continue
        seen.add(item.id)
        case_ids.append(item.id)

    if not case_ids:
        return 0

    existing_stmt = select(DocumentCaseLawRef.case_law_id).where(
        DocumentCaseLawRef.document_id == document_id,
        DocumentCaseLawRef.case_law_id.in_(case_ids),
    )
    existing_case_ids = set(db.execute(existing_stmt).scalars().all())

    rows_stmt = select(CaseLawCache).where(CaseLawCache.id.in_(case_ids))
    rows = {row.id: row for row in db.execute(rows_stmt).scalars().all()}

    linked = 0
    for item in case_law_refs:
        row = rows.get(item.id)
        if row is None:
            continue

        if item.id not in existing_case_ids:
            db.add(
                DocumentCaseLawRef(
                    document_id=document_id,
                    case_law_id=item.id,
                    relevance_score=_to_decimal(item.relevance_score),
                )
            )
            linked += 1

        row.reference_count = int(row.reference_count or 0) + 1

    db.commit()
    return linked


def clone_case_law_refs(
    db: Session,
    *,
    source_document_id: str,
    target_document_id: str,
) -> int:
    source_refs = list(
        db.execute(
            select(DocumentCaseLawRef).where(DocumentCaseLawRef.document_id == source_document_id)
        ).scalars().all()
    )
    if not source_refs:
        return 0

    linked = 0
    case_id_counts: dict[str, int] = {}
    for ref in source_refs:
        db.add(
            DocumentCaseLawRef(
                document_id=target_document_id,
                case_law_id=ref.case_law_id,
                relevance_score=ref.relevance_score,
            )
        )
        linked += 1
        case_id_counts[ref.case_law_id] = case_id_counts.get(ref.case_law_id, 0) + 1

    rows = list(db.execute(select(CaseLawCache).where(CaseLawCache.id.in_(tuple(case_id_counts.keys())))).scalars().all())
    for row in rows:
        row.reference_count = int(row.reference_count or 0) + case_id_counts.get(row.id, 0)

    db.commit()
    return linked
