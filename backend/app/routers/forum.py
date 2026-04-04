from __future__ import annotations
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import ForumPost, ForumComment, User

router = APIRouter(prefix="/forum", tags=["forum"])

# Schemas
class CommentBase(BaseModel):
    content: str

class CommentResponse(CommentBase):
    id: str
    user_id: str
    user_name: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class PostCreate(BaseModel):
    title: str
    content: str
    category: str | None = None
    case_id: str | None = None

class PostResponse(BaseModel):
    id: str
    user_id: str
    user_name: str | None
    title: str
    content: str
    category: str | None
    case_id: str | None = None
    created_at: datetime
    comment_count: int

    class Config:
        from_attributes = True

class PostDetailResponse(PostResponse):
    comments: list[CommentResponse]

# Routes
@router.post("/posts", response_model=PostResponse)
def create_post(
    payload: PostCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = ForumPost(
        id=str(uuid4()),
        user_id=user.user_id,
        title=payload.title,
        content=payload.content,
        category=payload.category,
        case_id=payload.case_id
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    
    # Simple workaround for username in response
    creator = db.get(User, user.user_id)
    return {
        **post.__dict__,
        "user_name": creator.full_name if creator else user.email,
        "comment_count": 0
    }

@router.get("/posts", response_model=list[PostResponse])
def list_posts(
    case_id: str | None = None,
    db: Session = Depends(get_db)
):
    query = select(ForumPost)
    if case_id:
        query = query.where(ForumPost.case_id == case_id)
    
    posts = db.execute(
        query.order_by(desc(ForumPost.created_at))
    ).scalars().all()
    
    results = []
    for p in posts:
        creator = db.get(User, p.user_id)
        results.append({
            "id": p.id,
            "user_id": p.user_id,
            "user_name": creator.full_name if creator else "Unknown",
            "title": p.title,
            "content": p.content,
            "category": p.category,
            "case_id": p.case_id,
            "created_at": p.created_at,
            "comment_count": len(p.comments)
        })
    return results

@router.get("/posts/{post_id}", response_model=PostDetailResponse)
def get_post(
    post_id: str,
    db: Session = Depends(get_db)
):
    post = db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    creator = db.get(User, post.user_id)
    comments = []
    for c in post.comments:
        c_user = db.get(User, c.user_id)
        comments.append({
            "id": c.id,
            "user_id": c.user_id,
            "user_name": c_user.full_name if c_user else "Unknown",
            "content": c.content,
            "created_at": c.created_at
        })

    return {
        "id": post.id,
        "user_id": post.user_id,
        "user_name": creator.full_name if creator else "Unknown",
        "title": post.title,
        "content": post.content,
        "category": post.category,
        "case_id": post.case_id,
        "created_at": post.created_at,
        "comment_count": len(post.comments),
        "comments": comments
    }

@router.post("/posts/{post_id}/comments", response_model=CommentResponse)
def create_comment(
    post_id: str,
    payload: CommentBase,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post = db.get(ForumPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
        
    comment = ForumComment(
        id=str(uuid4()),
        post_id=post_id,
        user_id=user.user_id,
        content=payload.content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    creator = db.get(User, user.user_id)
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "user_name": creator.full_name if creator else user.email,
        "content": comment.content,
        "created_at": comment.created_at
    }
