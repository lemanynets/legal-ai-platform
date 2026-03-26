from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from pydantic import BaseModel, Field

from app.db import Base


class Case(Base):
    __tablename__ = "cases"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    case_number = Column(String, nullable=True, index=True)
    status = Column(String, default="active", nullable=False)  # e.g., active, closed, pending
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    documents = relationship("GeneratedDocument", back_populates="case")
    forum_posts = relationship("ForumPost", back_populates="case")

    def __repr__(self):
        return f"<Case(id={self.id}, title='{self.title}')>"


class CaseBase(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = Field(None, max_length=2048)
    case_number: Optional[str] = Field(None, max_length=100)
    status: str = Field("active", max_length=50)


class CaseCreate(CaseBase):
    pass


class CaseUpdate(CaseBase):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    status: Optional[str] = Field(None, max_length=50)


class CaseInDB(CaseBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentStub(BaseModel):
    id: UUID
    document_type: str
    document_category: str
    created_at: datetime

    class Config:
        from_attributes = True

class ForumPostStub(BaseModel):
    id: UUID
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class CaseDetail(CaseInDB):
    documents: list[DocumentStub] = []
    forum_posts: list[ForumPostStub] = []