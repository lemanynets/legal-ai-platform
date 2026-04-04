from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models.knowledge_base import KnowledgeBaseEntry

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])

class KnowledgeEntryCreate(BaseModel):
    title: str
    content: str
    category: str | None = None
    tags: list[str] | None = None

@router.get("/")
def get_entries(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: str | None = Query(None),
) -> list[dict[str, Any]]:
    query = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.user_id == user.user_id)
    if category:
        query = query.filter(KnowledgeBaseEntry.category == category)
    
    entries = query.order_by(KnowledgeBaseEntry.created_at.desc()).all()
    
    # If empty and no filters, seed some initial documents for better UX
    if not entries and not category:
        _seed_initial_knowledge(db, user.user_id)
        # Re-fetch
        entries = db.query(KnowledgeBaseEntry).filter(KnowledgeBaseEntry.user_id == user.user_id).order_by(KnowledgeBaseEntry.created_at.desc()).all()

    return [e.to_dict() for e in entries]

def _seed_initial_knowledge(db: Session, user_id: str):
    seeds = [
        {
            "title": "Позовна заява про стягнення боргу (Золотий стандарт)",
            "category": "Позовна заява",
            "content": "До [Назва суду]\nПозивач: [ПІБ/Назва]\nВідповідач: [ПІБ/Назва]\n\nПОЗОВНА ЗАЯВА\nпро стягнення заборгованості за договором позики...\n\nОбґрунтування: Відповідно до ст. 1046 ЦК України за договором позики одна сторона (позикодавець) передає у власність другій стороні (позичальникові) грошові кошти...",
            "tags": "стягнення,борг,цивільне"
        },
        {
            "title": "Клопотання про витребування доказів",
            "category": "Клопотання",
            "content": "В провадженні суду перебуває справа №...\n\nКЛОПОТАННЯ\nпро витребування доказів\n\nКеруючись ст. 84 ЦПК України, прошу витребувати від [Назва установи] наступні документи...",
            "tags": "процес,докази,цпк"
        },
        {
            "title": "Шаблон договору про надання правової допомоги",
            "category": "Шаблон",
            "content": "Договір №__\nпро надання правової допомоги\nм. Київ \"__\" _______ 202__р.\n\nАдвокат [ПІБ], що діє на підставі свідоцтва №..., з однієї сторони, та [ПІБ Клієнта], з іншої сторони...",
            "tags": "адвокат,договір,гонорар"
        }
    ]
    for s in seeds:
        entry = KnowledgeBaseEntry(
            user_id=user_id,
            title=s["title"],
            content=s["content"],
            category=s["category"],
            tags=s["tags"]
        )
        db.add(entry)
    db.commit()

@router.post("/")
def create_entry(
    payload: KnowledgeEntryCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    entry = KnowledgeBaseEntry(
        user_id=user.user_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        tags=",".join(payload.tags) if payload.tags else None
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry.to_dict()

@router.delete("/{entry_id}")
def delete_entry(
    entry_id: str,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = db.query(KnowledgeBaseEntry).filter(
        KnowledgeBaseEntry.id == entry_id,
        KnowledgeBaseEntry.user_id == user.user_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    db.delete(entry)
    db.commit()
    return {"status": "ok"}
