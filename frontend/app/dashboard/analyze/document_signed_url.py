"""
FastAPI router for generating time-limited signed URLs for document export.

Endpoint: GET /api/documents/{document_id}/signed-url?format=pdf|docx

Returns a pre-signed URL pointing to the document file in object storage
(e.g. Cloudflare R2, AWS S3). The URL is valid for a configurable duration
(default: 15 minutes) and requires no additional auth headers.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user

router = APIRouter()

SIGNED_URL_TTL_MINUTES = int(os.environ.get("SIGNED_URL_TTL_MINUTES", "15"))


# ---------------------------------------------------------------------------
# Object storage client abstraction
# ---------------------------------------------------------------------------

# In production, replace with actual R2/S3 SDK call.
# This uses Cloudflare R2 (S3-compatible) as the default.

try:
    import boto3
    from botocore.config import Config as BotoConfig

    _s3 = boto3.client(
        "s3",
        endpoint_url=os.environ.get("R2_ENDPOINT_URL"),
        aws_access_key_id=os.environ.get("R2_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("R2_SECRET_ACCESS_KEY"),
        config=BotoConfig(signature_version="s3v4"),
        region_name=os.environ.get("R2_REGION", "auto"),
    )
    _R2_BUCKET = os.environ.get("R2_BUCKET", "legal-ai-documents")
    _S3_AVAILABLE = True
except (ImportError, Exception):
    _s3 = None
    _R2_BUCKET = ""
    _S3_AVAILABLE = False


def _generate_presigned_url(object_key: str, ttl_seconds: int) -> str:
    """Generate a pre-signed GET URL for the given object key."""
    if not _S3_AVAILABLE or _s3 is None:
        raise RuntimeError("Object storage client is not configured")

    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": _R2_BUCKET, "Key": object_key},
        ExpiresIn=ttl_seconds,
    )


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class SignedUrlResponse(BaseModel):
    url: str
    expires_at: str
    format: str
    document_id: str


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.get(
    "/{document_id}/signed-url",
    response_model=SignedUrlResponse,
    summary="Get a time-limited signed URL for document download",
)
async def get_signed_url(
    document_id: UUID,
    format: str = Query(..., regex="^(pdf|docx)$"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    # Verify document exists and belongs to user
    row = (
        await session.execute(
            text("""
                SELECT id, docx_url, pdf_url
                FROM generated_documents
                WHERE id = :doc_id AND user_id = :user_id
            """),
            {"doc_id": document_id, "user_id": current_user.id},
        )
    ).first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Determine the object storage key from the stored URL
    url_field = row.pdf_url if format == "pdf" else row.docx_url

    if not url_field:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No {format.upper()} export available for this document. Export the document first.",
        )

    # Extract object key: stored URLs may be full URLs or plain keys
    # e.g. "https://bucket.r2.dev/documents/abc.pdf" → "documents/abc.pdf"
    # or plain "documents/abc.pdf" → "documents/abc.pdf"
    object_key = url_field
    for prefix in ("https://", "http://"):
        if object_key.startswith(prefix):
            # Strip protocol + domain, keep path
            object_key = "/".join(object_key.split("/")[3:])
            break

    ttl_seconds = SIGNED_URL_TTL_MINUTES * 60
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

    try:
        signed_url = _generate_presigned_url(object_key, ttl_seconds)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage is not configured. Use the legacy export endpoint.",
        )

    return SignedUrlResponse(
        url=signed_url,
        expires_at=expires_at.isoformat(),
        format=format,
        document_id=str(document_id),
    )
