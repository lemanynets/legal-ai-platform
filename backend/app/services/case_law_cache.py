from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import Text, asc, cast, desc, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AuditLog, CaseLawCache


@dataclass(frozen=True)
class UpsertStats:
    created: int
    updated: int
    total: int
    used_sources: list[str] = field(default_factory=list)
    seed_fallback_used: bool = False
    fetched_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchStats:
    items: list[CaseLawCache]
    total: int
    page: int
    page_size: int
    pages: int
    sort_by: str
    sort_dir: str


@dataclass(frozen=True)
class DigestStats:
    items: list[CaseLawCache]
    total: int
    days: int
    limit: int
    only_supreme: bool
    court_type: str | None
    sources: list[str]


@dataclass(frozen=True)
class SyncStatus:
    total_records: int
    sources: dict[str, int]
    latest_decision_date: date | None
    oldest_decision_date: date | None
    last_sync_at: datetime | None
    last_sync_action: str | None
    last_sync_query: str | None
    last_sync_limit: int | None
    last_sync_created: int | None
    last_sync_updated: int | None
    last_sync_total: int | None
    last_sync_sources: list[str]
    last_sync_seed_fallback_used: bool | None


def is_supreme_court_name(court_name: str | None) -> bool:
    if not court_name:
        return False
    normalized = str(court_name).strip().lower()
    if not normalized:
        return False
    return "supreme" in normalized or "верховн" in normalized


def _supreme_court_clause():
    normalized_name = func.lower(func.coalesce(CaseLawCache.court_name, ""))
    return or_(normalized_name.like("%supreme%"), normalized_name.like("%верховн%"))


def _parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _coerce_tags(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip().lower() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [chunk.strip().lower() for chunk in value.split(",") if chunk.strip()]
    return []


def _normalize_record(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(data.get("source") or "manual").strip().lower(),
        "decision_id": str(data.get("decision_id") or "").strip(),
        "court_name": str(data.get("court_name") or "").strip() or None,
        "court_type": str(data.get("court_type") or "").strip().lower() or None,
        "decision_date": _parse_date(data.get("decision_date")),
        "case_number": str(data.get("case_number") or "").strip() or None,
        "subject_categories": _coerce_tags(data.get("subject_categories")),
        "legal_positions": data.get("legal_positions") if isinstance(data.get("legal_positions"), dict) else {},
        "full_text": str(data.get("full_text") or "").strip() or None,
        "summary": str(data.get("summary") or "").strip() or None,
    }


def upsert_case_law_records(db: Session, records: list[dict[str, Any]]) -> UpsertStats:
    created = 0
    updated = 0

    for raw in records:
        normalized = _normalize_record(raw)
        source = normalized["source"]
        decision_id = normalized["decision_id"]
        if not decision_id:
            continue

        stmt = (
            select(CaseLawCache)
            .where(CaseLawCache.source == source, CaseLawCache.decision_id == decision_id)
            .limit(1)
        )
        row = db.execute(stmt).scalar_one_or_none()
        if row is None:
            row = CaseLawCache(**normalized, reference_count=0)
            db.add(row)
            created += 1
            continue

        row.court_name = normalized["court_name"]
        row.court_type = normalized["court_type"]
        row.decision_date = normalized["decision_date"]
        row.case_number = normalized["case_number"]
        row.subject_categories = normalized["subject_categories"]
        row.legal_positions = normalized["legal_positions"]
        row.full_text = normalized["full_text"]
        row.summary = normalized["summary"]
        row.updated_at = datetime.now(timezone.utc)
        updated += 1

    db.commit()
    return UpsertStats(created=created, updated=updated, total=created + updated)


def search_case_law(
    db: Session,
    *,
    query: str | None = None,
    court_type: str | None = None,
    only_supreme: bool = False,
    sources: list[str] | None = None,
    tags: list[str] | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    fresh_days: int | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "decision_date",
    sort_dir: str = "desc",
) -> SearchStats:
    safe_page = max(1, page)
    safe_page_size = max(1, min(page_size, 100))
    safe_sort_dir = "asc" if str(sort_dir).strip().lower() == "asc" else "desc"
    sort_columns = {
        "decision_date": CaseLawCache.decision_date,
        "court_type": CaseLawCache.court_type,
        "case_number": CaseLawCache.case_number,
        "summary": CaseLawCache.summary,
        "source": CaseLawCache.source,
        "reference_count": CaseLawCache.reference_count,
        "created_at": CaseLawCache.created_at,
    }
    safe_sort_by = sort_by if sort_by in sort_columns else "decision_date"

    stmt = select(CaseLawCache)
    if court_type:
        stmt = stmt.where(CaseLawCache.court_type == court_type.strip().lower())
    if only_supreme:
        stmt = stmt.where(_supreme_court_clause())

    wanted_sources = [item.strip().lower() for item in (sources or []) if item.strip()]
    if wanted_sources:
        stmt = stmt.where(CaseLawCache.source.in_(tuple(wanted_sources)))

    if query and query.strip():
        q = f"%{query.strip()}%"
        stmt = stmt.where(
            or_(
                CaseLawCache.summary.ilike(q),
                CaseLawCache.full_text.ilike(q),
                CaseLawCache.case_number.ilike(q),
                CaseLawCache.court_name.ilike(q),
                CaseLawCache.decision_id.ilike(q),
            )
        )

    wanted_tags = [tag.strip().lower() for tag in (tags or []) if tag.strip()]
    if wanted_tags:
        tags_text = cast(CaseLawCache.subject_categories, Text)
        stmt = stmt.where(or_(*[tags_text.ilike(f"%{tag}%") for tag in wanted_tags]))

    if date_from is not None:
        stmt = stmt.where(CaseLawCache.decision_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(CaseLawCache.decision_date <= date_to)
    if fresh_days is not None:
        threshold = date.today() - timedelta(days=max(1, fresh_days))
        stmt = stmt.where(CaseLawCache.decision_date.is_not(None), CaseLawCache.decision_date >= threshold)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.execute(count_stmt).scalar_one() or 0)
    pages = (total + safe_page_size - 1) // safe_page_size if total > 0 else 1
    if safe_page > pages:
        safe_page = pages

    sort_column = sort_columns[safe_sort_by]
    order_clause = asc(sort_column) if safe_sort_dir == "asc" else desc(sort_column)
    offset = (safe_page - 1) * safe_page_size

    rows = list(
        db.execute(
            stmt.order_by(order_clause, desc(CaseLawCache.created_at))
            .offset(offset)
            .limit(safe_page_size)
        )
        .scalars()
        .all()
    )
    return SearchStats(
        items=rows,
        total=total,
        page=safe_page,
        page_size=safe_page_size,
        pages=pages,
        sort_by=safe_sort_by,
        sort_dir=safe_sort_dir,
    )


def get_case_law_digest(
    db: Session,
    *,
    days: int = 7,
    limit: int = 20,
    court_type: str | None = None,
    sources: list[str] | None = None,
    only_supreme: bool = True,
) -> DigestStats:
    safe_days = max(1, min(days, 3650))
    safe_limit = max(1, min(limit, 100))
    threshold = date.today() - timedelta(days=safe_days)

    stmt = select(CaseLawCache).where(
        CaseLawCache.decision_date.is_not(None),
        CaseLawCache.decision_date >= threshold,
    )
    normalized_court_type = (court_type or "").strip().lower() or None
    if normalized_court_type:
        stmt = stmt.where(CaseLawCache.court_type == normalized_court_type)

    normalized_sources = [item.strip().lower() for item in (sources or []) if item.strip()]
    if normalized_sources:
        stmt = stmt.where(CaseLawCache.source.in_(tuple(normalized_sources)))

    if only_supreme:
        stmt = stmt.where(_supreme_court_clause())

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = int(db.execute(count_stmt).scalar_one() or 0)
    rows = list(
        db.execute(
            stmt.order_by(desc(CaseLawCache.decision_date), desc(CaseLawCache.created_at)).limit(safe_limit)
        )
        .scalars()
        .all()
    )
    return DigestStats(
        items=rows,
        total=total,
        days=safe_days,
        limit=safe_limit,
        only_supreme=only_supreme,
        court_type=normalized_court_type,
        sources=normalized_sources,
    )


def _fetch_opendatabot(query: str | None, limit: int) -> list[dict[str, Any]]:
    if not settings.opendatabot_api_key:
        return []

    base_url = settings.opendatabot_api_url.rstrip("/")
    if not base_url:
        return []

    params = {"limit": max(1, min(limit, 100))}
    if query and query.strip():
        params["q"] = query.strip()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{base_url}/court/decisions/search",
                headers={"Authorization": f"Bearer {settings.opendatabot_api_key}"},
                params=params,
            )
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return []

    records: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "source": "opendatabot",
                "decision_id": item.get("id") or item.get("decision_id") or item.get("uid"),
                "court_name": item.get("court_name"),
                "court_type": item.get("court_type"),
                "decision_date": item.get("decision_date") or item.get("date"),
                "case_number": item.get("case_number"),
                "subject_categories": item.get("subject_categories") or item.get("tags") or [],
                "legal_positions": item.get("legal_positions") or {},
                "full_text": item.get("full_text") or item.get("text"),
                "summary": item.get("summary") or item.get("snippet"),
            }
        )
    return records


def _sample_seed_records(limit: int) -> list[dict[str, Any]]:
    samples = [
        {
            "source": "manual_seed",
            "decision_id": "vs-625-civil-001",
            "court_name": "Supreme Court of Ukraine",
            "court_type": "civil",
            "decision_date": "2025-10-15",
            "case_number": "000/0000/25",
            "subject_categories": ["debt", "loan", "article 625"],
            "legal_positions": {
                "article 625 civil code": "3% annual interest and inflation losses are recoverable regardless of debtor fault."
            },
            "summary": "Supreme Court position on debt recovery and application of article 625.",
        },
        {
            "source": "manual_seed",
            "decision_id": "vs-cpc-proof-002",
            "court_name": "Supreme Court of Ukraine",
            "court_type": "civil",
            "decision_date": "2025-09-02",
            "case_number": "000/0001/25",
            "subject_categories": ["evidence", "civil procedure", "written evidence"],
            "legal_positions": {
                "civil procedure code": "The court evaluates admissibility and relevance of evidence in totality, not in isolation."
            },
            "summary": "Supreme Court position on evidence standards in civil debt disputes.",
        },
        {
            "source": "manual_seed",
            "decision_id": "vs-commercial-003",
            "court_name": "Supreme Court of Ukraine",
            "court_type": "commercial",
            "decision_date": "2025-08-12",
            "case_number": "000/0002/25",
            "subject_categories": ["commercial procedure", "contract", "penalty"],
            "legal_positions": {
                "commercial procedure code": "Penalty amount may be reduced by the court using proportionality criteria."
            },
            "summary": "Supreme Court position in commercial disputes on contractual penalties.",
        },
    ]
    return samples[: max(1, min(limit, len(samples)))]


def _normalize_sync_sources(value: list[str] | None) -> list[str]:
    if value:
        items = [item.strip().lower() for item in value if item and item.strip()]
    else:
        items = [item.strip().lower() for item in settings.case_law_auto_sync_sources.split(",") if item.strip()]
    normalized: list[str] = []
    for item in items:
        if item not in normalized:
            normalized.append(item)
    return normalized


def _fetch_json_feed(query: str | None, limit: int) -> list[dict[str, Any]]:
    feed_url = settings.case_law_json_feed_url.strip()
    if not feed_url:
        return []

    params: dict[str, Any] = {"limit": max(1, min(limit, 200))}
    if query and query.strip():
        params["q"] = query.strip()

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(feed_url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    raw_items: Any
    if isinstance(payload, dict):
        raw_items = payload.get("items") or payload.get("results") or payload.get("data")
    else:
        raw_items = payload
    if not isinstance(raw_items, list):
        return []

    records: list[dict[str, Any]] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        records.append(
            {
                "source": item.get("source") or "json_feed",
                "decision_id": item.get("id") or item.get("decision_id") or item.get("uid"),
                "court_name": item.get("court_name"),
                "court_type": item.get("court_type"),
                "decision_date": item.get("decision_date") or item.get("date"),
                "case_number": item.get("case_number"),
                "subject_categories": item.get("subject_categories") or item.get("tags") or [],
                "legal_positions": item.get("legal_positions") or {},
                "full_text": item.get("full_text") or item.get("text"),
                "summary": item.get("summary") or item.get("snippet"),
            }
        )
    return records


def sync_case_law_sources(
    db: Session,
    *,
    query: str | None = None,
    limit: int = 100,
    sources: list[str] | None = None,
    allow_seed_fallback: bool | None = None,
) -> UpsertStats:
    safe_limit = max(1, min(limit, 200))
    requested_sources = _normalize_sync_sources(sources)

    records: list[dict[str, Any]] = []
    fetched_counts: dict[str, int] = {}

    if not requested_sources or "opendatabot" in requested_sources:
        from_opendatabot = _fetch_opendatabot(query=query, limit=safe_limit)
        records.extend(from_opendatabot)
        fetched_counts["opendatabot"] = len(from_opendatabot)

    if not requested_sources or "json_feed" in requested_sources:
        from_json_feed = _fetch_json_feed(query=query, limit=safe_limit)
        records.extend(from_json_feed)
        fetched_counts["json_feed"] = len(from_json_feed)

    effective_seed_fallback = settings.case_law_allow_seed_fallback if allow_seed_fallback is None else bool(allow_seed_fallback)
    seed_fallback_used = False
    if not records and effective_seed_fallback:
        seed_records = _sample_seed_records(safe_limit)
        records.extend(seed_records)
        fetched_counts["manual_seed"] = len(seed_records)
        seed_fallback_used = True

    stats = upsert_case_law_records(db, records)
    return UpsertStats(
        created=stats.created,
        updated=stats.updated,
        total=stats.total,
        used_sources=requested_sources or ["opendatabot", "json_feed"],
        seed_fallback_used=seed_fallback_used,
        fetched_counts=fetched_counts,
    )


def _coerce_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_case_law_sync_status(db: Session, *, user_id: str | None = None) -> SyncStatus:
    total_records = int(db.execute(select(func.count()).select_from(CaseLawCache)).scalar_one() or 0)
    grouped_rows = list(
        db.execute(select(CaseLawCache.source, func.count()).group_by(CaseLawCache.source)).all()
    )
    sources = {str(source): int(count or 0) for source, count in grouped_rows}
    latest_decision_date = db.execute(select(func.max(CaseLawCache.decision_date))).scalar_one()
    oldest_decision_date = db.execute(select(func.min(CaseLawCache.decision_date))).scalar_one()

    sync_actions = ("case_law_sync", "case_law_sync_auto")
    sync_stmt = select(AuditLog).where(AuditLog.action.in_(sync_actions))
    if user_id:
        sync_stmt = sync_stmt.where(or_(AuditLog.user_id == user_id, AuditLog.user_id.is_(None)))
    last_sync = db.execute(sync_stmt.order_by(desc(AuditLog.created_at), desc(AuditLog.id)).limit(1)).scalar_one_or_none()
    metadata = last_sync.metadata_json if last_sync and isinstance(last_sync.metadata_json, dict) else {}
    raw_sources = metadata.get("sources")
    if isinstance(raw_sources, list):
        last_sync_sources = [str(item).strip().lower() for item in raw_sources if str(item).strip()]
    else:
        last_sync_sources = []
    raw_seed_fallback = metadata.get("seed_fallback_used")
    seed_fallback_used = bool(raw_seed_fallback) if isinstance(raw_seed_fallback, bool) else None

    return SyncStatus(
        total_records=total_records,
        sources=sources,
        latest_decision_date=latest_decision_date,
        oldest_decision_date=oldest_decision_date,
        last_sync_at=last_sync.created_at if last_sync else None,
        last_sync_action=last_sync.action if last_sync else None,
        last_sync_query=(metadata.get("query") if isinstance(metadata.get("query"), str) else None),
        last_sync_limit=_coerce_int(metadata.get("limit")),
        last_sync_created=_coerce_int(metadata.get("created")),
        last_sync_updated=_coerce_int(metadata.get("updated")),
        last_sync_total=_coerce_int(metadata.get("total")),
        last_sync_sources=last_sync_sources,
        last_sync_seed_fallback_used=seed_fallback_used,
    )
