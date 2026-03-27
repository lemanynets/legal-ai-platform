"""
FastAPI router for document intake analysis with content-hash caching.

Endpoint: POST /api/analyze/intake
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user
from app.services.intake_analyzer import run_intake_analysis  # existing AI pipeline

from .intake_cache import compute_content_hash, lookup_cached_analysis, store_analysis_cache

router = APIRouter()


@router.post("/intake", summary="Analyze uploaded document with content-hash caching")
async def analyze_intake(
    file: UploadFile = File(...),
    jurisdiction: str = Form("UA"),
    case_id: Optional[str] = Form(None),
    mode: str = Query("standard"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    file_bytes = await file.read()
    content_hash = compute_content_hash(file_bytes)

    # --- Cache lookup ---
    cached = await lookup_cached_analysis(
        session,
        user_id=current_user.id,
        content_hash=content_hash,
        jurisdiction=jurisdiction,
        mode=mode,
    )
    if cached is not None:
        # Overwrite transient fields with current request context
        cached["source_file_name"] = file.filename
        if case_id:
            cached["case_id"] = case_id
        cached["cache_hit"] = True
        return cached

    # --- Cache miss: run full AI pipeline ---
    start_ms = time.monotonic()

    result = await run_intake_analysis(
        file_bytes=file_bytes,
        file_name=file.filename,
        jurisdiction=jurisdiction,
        case_id=case_id,
        mode=mode,
        user=current_user,
        session=session,
    )

    elapsed_ms = int((time.monotonic() - start_ms) * 1000)

    # Convert to dict for caching (Pydantic model or dict)
    result_dict = result if isinstance(result, dict) else result.dict()

    # --- Store in cache ---
    await store_analysis_cache(
        session,
        user_id=current_user.id,
        content_hash=content_hash,
        jurisdiction=jurisdiction,
        mode=mode,
        source_file_name=file.filename,
        result=result_dict,
        ai_model=result_dict.get("classifier_model"),
        tokens_used=result_dict.get("tokens_used"),
        processing_time_ms=elapsed_ms,
    )

    result_dict["cache_hit"] = False
    return result_dict
