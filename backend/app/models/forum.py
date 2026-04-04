from __future__ import annotations
from datetime import datetime
from sqlalchemy import DateTime, String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, utcnow

class ForumPost(Base):
    __tablename__ = "forum_posts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)
    case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)

    user = relationship("User", back_populates="forum_posts")
    case = relationship("Case", back_populates="forum_posts")
    comments = relationship("ForumComment", back_populates="post", cascade="all, delete-orphan")

class ForumComment(Base):
    __tablename__ = "forum_comments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    post_id: Mapped[str] = mapped_column(String(64), ForeignKey("forum_posts.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(64), ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)

    post = relationship("ForumPost", back_populates="comments")
    user = relationship("User", back_populates="forum_comments")
