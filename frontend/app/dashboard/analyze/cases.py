from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List

from app.db import get_session
from app.models.case import Case, CaseCreate, CaseUpdate, CaseInDB, CaseDetail
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()

@router.post("/", response_model=CaseInDB, status_code=status.HTTP_201_CREATED, summary="Create a new case")
async def create_case(
    case_in: CaseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    new_case = Case(
        user_id=current_user.id,
        title=case_in.title,
        description=case_in.description,
        case_number=case_in.case_number,
        status=case_in.status
    )
    session.add(new_case)
    await session.commit()
    await session.refresh(new_case)
    return new_case

@router.get("/", response_model=List[CaseInDB], summary="Get all cases for the current user")
async def get_cases(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Case).filter(Case.user_id == current_user.id).order_by(Case.created_at.desc())
    )
    cases = result.scalars().all()
    return cases

@router.get("/{case_id}", response_model=CaseDetail, summary="Get a specific case by ID")
async def get_case(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Case)
        .options(
            selectinload(Case.documents),
            selectinload(Case.forum_posts)
        ).filter(Case.id == case_id, Case.user_id == current_user.id)
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case

@router.patch("/{case_id}", response_model=CaseInDB, summary="Update an existing case")
async def update_case(
    case_id: UUID,
    case_update: CaseUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Case).filter(Case.id == case_id, Case.user_id == current_user.id)
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    update_data = case_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(case, key, value)
    
    session.add(case)
    await session.commit()
    await session.refresh(case)
    return case

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a case")
async def delete_case(
    case_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Case).filter(Case.id == case_id, Case.user_id == current_user.id)
    )
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")

    await session.delete(case)
    await session.commit()
    return