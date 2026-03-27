"""
Pydantic schemas for the document intake / batch-analyze endpoints.

This module is the canonical definition for request/response shapes used
by the intake and batch-analyze routers.  The separate backend must import
from (or replicate) these definitions in its own app/schemas/analyze.py.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class AnalyzeIntakeRequest(BaseModel):
    """Single-file intake analysis request.

    File content is received as multipart/form-data; this schema covers the
    non-file form fields that accompany the upload.
    """

    jurisdiction: str = Field(
        default="UA",
        description="ISO 3166-1 alpha-2 country code for the governing legal system.",
    )
    case_id: Optional[str] = Field(
        default=None,
        description="UUID of an existing Case to associate this analysis with.",
    )
    mode: Literal["standard", "deep"] = Field(
        default="standard",
        description=(
            "'standard' uses the fast classifier model; "
            "'deep' uses a more expensive model with extended legal instructions."
        ),
    )


class AnalyzeBatchProcessRequest(BaseModel):
    """Batch re-analysis of documents that are already stored in the system.

    Accepts a list of *existing* document intake IDs and re-runs the full
    intake analysis pipeline for each, respecting the shared cache.  This is
    distinct from the multipart upload endpoint — no files are transferred.

    Typical use-cases:
    - Re-classify documents after the classifier model is updated.
    - Back-fill tags or risk scores for legacy documents.
    - Trigger analysis for documents imported via the admin import endpoint.
    """

    document_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of existing document intake UUIDs to re-process.",
    )
    jurisdiction: str = Field(
        default="UA",
        description="ISO 3166-1 alpha-2 jurisdiction code to use for all documents in the batch.",
    )
    mode: Literal["standard", "deep"] = Field(
        default="standard",
        description="Analysis depth to apply to every item in the batch.",
    )
    case_id: Optional[str] = Field(
        default=None,
        description="If set, associates every re-processed document with this Case UUID.",
    )
    invalidate_cache: bool = Field(
        default=False,
        description=(
            "When True the content-hash cache entry for each document is "
            "dropped before re-analysis, forcing a fresh AI call."
        ),
    )


class AnalyzeBatchProcessResponseItem(BaseModel):
    """Per-document result inside a batch response."""

    document_id: str
    status: Literal["ok", "error", "cache_hit"]
    cache_hit: bool = False
    error: Optional[str] = None


class AnalyzeBatchProcessResponse(BaseModel):
    """Top-level response for POST /api/analyze/batch."""

    total: int
    processed: int
    failed: int
    items: List[AnalyzeBatchProcessResponseItem]
