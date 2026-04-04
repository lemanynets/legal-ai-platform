from __future__ import annotations

import math
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.models import CaseLawCache, CaseLawDigest, CaseLawDigestItem


def build_digest_snippet_from_case_law_row(row: CaseLawCache) -> str:
    case_ref = row.case_number or row.decision_id
    summary = (row.summary or "").strip()
    positions = row.legal_positions if isinstance(row.legal_positions, dict) else {}
    position_chunks: list[str] = []
    for key, value in positions.items():
        text = str(value).strip()
        if not text:
            continue
        position_chunks.append(f"{key}: {text}")
        if len(position_chunks) >= 2:
            break
    position_text = "; ".join(position_chunks)
    parts = [
        f"[{row.source}] case {case_ref}",
        f"court: {row.court_name or row.court_type or '-'}",
        f"date: {row.decision_date.isoformat() if row.decision_date else '-'}",
    ]
    if summary:
        parts.append(f"summary: {summary[:240]}")
    if position_text:
        parts.append(f"positions: {position_text[:240]}")
    return ". ".join(parts)


def build_digest_prompt_text(
    *,
    generated_at: str,
    snippets: list[str],
) -> str:
    lines = [f"Weekly case-law digest ({generated_at})"]
    for index, snippet in enumerate(snippets, start=1):
        lines.append(f"{index}. {snippet}")
    return "\n".join(lines)


def save_case_law_digest(
    db: Session,
    *,
    user_id: str,
    rows: list[CaseLawCache],
    days: int,
    limit: int,
    only_supreme: bool,
    court_type: str | None,
    sources: list[str] | None,
    total: int,
    generated_at: str,
    title: str | None = None,
) -> CaseLawDigest:
    normalized_sources = [item.strip().lower() for item in (sources or []) if item.strip()]
    digest = CaseLawDigest(
        user_id=user_id,
        title=(title or "").strip() or None,
        days=days,
        limit=limit,
        only_supreme=only_supreme,
        court_type=(court_type or "").strip().lower() or None,
        sources_json=normalized_sources,
        total=total,
        item_count=len(rows),
    )
    db.add(digest)
    db.flush()

    snippets: list[str] = []
    for index, row in enumerate(rows, start=1):
        snippet = build_digest_snippet_from_case_law_row(row)
        snippets.append(snippet)
        db.add(
            CaseLawDigestItem(
                digest_id=digest.id,
                case_law_id=row.id,
                source=row.source,
                decision_id=row.decision_id,
                court_name=row.court_name,
                court_type=row.court_type,
                decision_date=row.decision_date,
                case_number=row.case_number,
                subject_categories=row.subject_categories or [],
                summary=row.summary,
                legal_positions=row.legal_positions or {},
                prompt_snippet=snippet,
                sort_order=index,
            )
        )
    digest.prompt_text = build_digest_prompt_text(generated_at=generated_at, snippets=snippets)
    db.commit()
    db.refresh(digest)
    return digest


def list_case_law_digests(
    db: Session,
    *,
    user_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[CaseLawDigest], int, int, int]:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    stmt = select(CaseLawDigest).where(CaseLawDigest.user_id == user_id)
    total = int(db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one() or 0)
    pages = max(1, math.ceil(total / safe_page_size)) if total > 0 else 1
    if safe_page > pages:
        safe_page = pages
    rows = list(
        db.execute(
            stmt.order_by(desc(CaseLawDigest.created_at), desc(CaseLawDigest.id))
            .offset((safe_page - 1) * safe_page_size)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return rows, total, safe_page, pages


def get_case_law_digest_by_id(db: Session, *, user_id: str, digest_id: str) -> CaseLawDigest | None:
    return db.execute(
        select(CaseLawDigest)
        .where(CaseLawDigest.id == digest_id, CaseLawDigest.user_id == user_id)
        .options(selectinload(CaseLawDigest.items))
        .limit(1)
    ).scalar_one_or_none()


def to_digest_item_payload(item: CaseLawDigestItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "source": item.source,
        "decision_id": item.decision_id,
        "court_name": item.court_name,
        "court_type": item.court_type,
        "decision_date": item.decision_date.isoformat() if item.decision_date else None,
        "case_number": item.case_number,
        "subject_categories": item.subject_categories or [],
        "summary": item.summary,
        "legal_positions": item.legal_positions or {},
        "prompt_snippet": item.prompt_snippet,
    }
