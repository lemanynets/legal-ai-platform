"""
FastAPI router for batch document re-analysis.

Endpoint: POST /api/analyze/batch

Re-runs the intake analysis pipeline for a list of existing document IDs.
Results are cache-aware: documents whose content hash is already in the
cache return immediately unless `invalidate_cache=True` is set.
"""

import asyncio
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user
from app.services.intake_analyzer import run_intake_analysis  # existing AI pipeline

from .intake_cache import invalidate_user_cache, lookup_cached_analysis
from .schemas import (
    AnalyzeBatchProcessRequest,
    AnalyzeBatchProcessResponse,
    AnalyzeBatchProcessResponseItem,
)

router = APIRouter()

# Maximum concurrent AI calls inside a single batch request
_MAX_BATCH_CONCURRENCY = 3


@router.post(
    "/batch",
    response_model=AnalyzeBatchProcessResponse,
    summary="Batch re-analysis of existing documents",
)
async def analyze_batch(
    payload: AnalyzeBatchProcessRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> AnalyzeBatchProcessResponse:
    semaphore = asyncio.Semaphore(_MAX_BATCH_CONCURRENCY)

    async def _process_one(document_id: str) -> AnalyzeBatchProcessResponseItem:
        async with semaphore:
            try:
                if payload.invalidate_cache:
                    await invalidate_user_cache(
                        session,
                        user_id=current_user.id,
                        document_id=document_id,
                    )

                # Check cache first (re-uses existing content hash if present)
                cached = await lookup_cached_analysis(
                    session,
                    user_id=current_user.id,
                    content_hash=document_id,  # batch re-analysis uses doc ID as hash key
                    jurisdiction=payload.jurisdiction,
                    mode=payload.mode,
                )
                if cached is not None:
                    return AnalyzeBatchProcessResponseItem(
                        document_id=document_id,
                        status="cache_hit",
                        cache_hit=True,
                    )

                await run_intake_analysis(
                    document_id=document_id,
                    jurisdiction=payload.jurisdiction,
                    case_id=payload.case_id,
                    mode=payload.mode,
                    user=current_user,
                    session=session,
                )
                return AnalyzeBatchProcessResponseItem(
                    document_id=document_id,
                    status="ok",
                    cache_hit=False,
                )
            except Exception as exc:  # noqa: BLE001
                return AnalyzeBatchProcessResponseItem(
                    document_id=document_id,
                    status="error",
                    error=str(exc),
                )

    results: List[AnalyzeBatchProcessResponseItem] = await asyncio.gather(
        *[_process_one(doc_id) for doc_id in payload.document_ids]
    )

    failed = sum(1 for r in results if r.status == "error")

    return AnalyzeBatchProcessResponse(
        total=len(results),
        processed=len(results) - failed,
        failed=failed,
        items=results,
    )
