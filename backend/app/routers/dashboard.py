from __future__ import annotations
from typing import Any
from fastapi import APIRouter, Depends
from sqlalchemy import func, select, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import GeneratedDocument, ForumPost, Subscription, User, Case, RegistryMonitorEvent
from app.services.generated_documents import get_accessible_user_ids, get_document_generated_text

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

class DashboardStats(BaseModel):
    total_documents: int
    total_analyses: int
    total_cases: int
    hours_saved: float
    recent_activity: list[dict[str, Any]]
    system_status: str = "operational"
    weekly_docs_stats: list[int] = []
    cases_stats: dict[str, int] = {}
    registry_alerts: list[dict[str, Any]] = []

@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    accessible_user_ids = get_accessible_user_ids(db, user.user_id)

    user_filter = GeneratedDocument.user_id.in_(accessible_user_ids)
    case_filter = Case.user_id == user.user_id

    docs_count = db.query(func.count(GeneratedDocument.id)).filter(user_filter).scalar() or 0
    if docs_count == 0:
        from app.routers.documents import _seed_welcome_document
        _seed_welcome_document(db, user.user_id)
        docs_count = 1

    cases_count = db.query(func.count(Case.id)).filter(case_filter).scalar() or 0
    
    # Analyses
    sub = db.query(Subscription).filter(Subscription.user_id == user.user_id).order_by(desc(Subscription.created_at)).first()
    analyses_count = sub.analyses_used if sub else 0
    
    hours_saved = (docs_count * 0.5) + (analyses_count * 1.5)
    
    # Batch load activity
    recent_docs = db.query(GeneratedDocument).filter(user_filter).order_by(desc(GeneratedDocument.created_at)).limit(5).all()
    recent_posts = db.query(ForumPost).order_by(desc(ForumPost.created_at)).limit(3).all()
    recent_cases = db.query(Case).filter(case_filter).order_by(desc(Case.created_at)).limit(3).all()
    
    # Pre-fetch users for posts to avoid N+1
    user_ids = {p.user_id for p in recent_posts}
    users_map = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    
    activity = []
    for d in recent_docs:
        activity.append({
            "type": "document",
            "title": f"Згенеровано: {d.document_type}",
            "timestamp": d.created_at.isoformat(),
            "id": d.id,
            "icon": "📄"
        })
        
    for p in recent_posts:
         activity.append({
            "type": "forum",
            "title": f"Нове в обговоренні: {p.title}",
            "timestamp": p.created_at.isoformat(),
            "id": p.id,
            "user_name": users_map.get(p.user_id, "Колега"),
            "icon": "💬"
        })
        
    for c in recent_cases:
        activity.append({
            "type": "case",
            "title": f"Нова справа: {c.title}",
            "timestamp": c.created_at.isoformat(),
            "id": c.id,
            "icon": "📁"
        })
    
    activity.sort(key=lambda x: str(x["timestamp"]), reverse=True)

    cases_by_status = db.query(Case.status, func.count(Case.id)).filter(case_filter).group_by(Case.status).all()
    cases_stats = {status: count for status, count in cases_by_status}
    
    # Weekly stats optimized: Single query for last 7 days grouped by date
    seven_days_ago = datetime.now() - timedelta(days=7)
    date_trunc = func.date(GeneratedDocument.created_at)
    weekly_counts = db.query(date_trunc, func.count(GeneratedDocument.id)).filter(
        user_filter,
        GeneratedDocument.created_at >= seven_days_ago
    ).group_by(date_trunc).all()
    
    counts_map = {str(d): count for d, count in weekly_counts}
    weekly_stats = []
    today = datetime.now()
    for i in range(6, -1, -1):
        day_str = str((today - timedelta(days=i)).date())
        weekly_stats.append(counts_map.get(day_str, 0))

    # Registry Alerts
    alerts = db.query(RegistryMonitorEvent).filter(
        RegistryMonitorEvent.user_id == user.user_id,
        RegistryMonitorEvent.severity.in_(["warning", "critical", "error"])
    ).order_by(desc(RegistryMonitorEvent.created_at)).limit(3).all()
    
    registry_alerts = [{
        "id": a.id, "title": a.title, "severity": a.severity, "timestamp": a.created_at.isoformat()
    } for a in alerts]

    return DashboardStats(
        total_documents=docs_count,
        total_analyses=analyses_count,
        total_cases=cases_count,
        hours_saved=round(hours_saved, 1),
        recent_activity=activity[:10],
        weekly_docs_stats=weekly_stats,
        cases_stats=cases_stats,
        registry_alerts=registry_alerts
    )

class GlobalSearchResponse(BaseModel):
    cases: list[dict[str, Any]]
    documents: list[dict[str, Any]]
    forum: list[dict[str, Any]]

@router.get("/search", response_model=GlobalSearchResponse)
def global_search(
    q: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if len(q) < 2:
        return GlobalSearchResponse(cases=[], documents=[], forum=[])
    
    # Search Cases
    cases = db.query(Case).filter(
        Case.user_id == user.user_id,
        (Case.title.ilike(f"%{q}%")) | (Case.case_number.ilike(f"%{q}%"))
    ).limit(5).all()
    
    # Search Documents
    docs = db.query(GeneratedDocument).filter(
       GeneratedDocument.user_id == user.user_id,
       (GeneratedDocument.document_type.ilike(f"%{q}%")) | (GeneratedDocument.preview_text.ilike(f"%{q}%"))
    ).limit(5).all()
    # Search Forum (Only public or user's)
    posts = db.query(ForumPost).filter(
        (ForumPost.title.ilike(f"%{q}%")) | (ForumPost.content.ilike(f"%{q}%"))
    ).limit(5).all()
    
    return GlobalSearchResponse(
       cases=[{"id": c.id, "title": c.title, "number": c.case_number} for c in cases],
       documents=[{"id": d.id, "type": d.document_type, "preview": get_document_generated_text(d)[:100]} for d in docs],
       forum=[{"id": p.id, "title": p.title} for p in posts]
    )
