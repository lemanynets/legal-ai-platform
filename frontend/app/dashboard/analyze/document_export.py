"""
Wave 4 · STORY-7/8 — Final export endpoint.

POST /api/documents/{document_id}/export?format=docx|pdf

Pipeline:
  1. Load generated_document + ir_json from DB
  2. Resolve DocumentIR (from ir_json if available, else raise 422 IR_MISSING)
  3. Load processual_validation_checks from the document record
  4. validate_final_render_gate(ir, processual_checks=checks)  → 422 on failure
  5. renderer.render_docx(ir) / render_pdf(ir)
  6. Return FileResponse (inline) or stream bytes

Feature flag: ENABLE_IR_RENDERER per doc_type.
  - If disabled → falls back to legacy: return stored generated_text as .txt
    or delegates to the existing DOCX export service (no breaking change).

Error responses:
  422 IR_MISSING          — ir_json is NULL and renderer is required
  422 LAYOUT_COMPLIANCE_FAIL — one or more render gates failed
  500 RENDER_FAIL         — renderer raised an exception
"""

from __future__ import annotations

import io
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models.user import User
from app.services.auth import get_current_user

from .document_ir import DocumentIR
from .error_codes import IR_PARSE_FAIL, LAYOUT_COMPLIANCE_FAIL, RENDER_FAIL
from .ir_migration import migrate_ir
from .feature_flags import flags
from .final_render_gate import validate_final_render_gate
from .ir_validator import IRParseError, parse_ir_from_llm_output
from .renderer import DocumentRenderer

router = APIRouter()

ExportFormat = Literal["docx", "pdf"]

_MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pdf": "application/pdf",
}


# ---------------------------------------------------------------------------
# Export endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{document_id}/export",
    summary="Export document as DOCX or PDF via DocumentIR renderer",
    response_class=StreamingResponse,
)
async def export_document(
    document_id: str,
    format: ExportFormat = "docx",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """Export a generated document through the DocumentIR render pipeline.

    When ENABLE_IR_RENDERER is active for the document's doc_type:
      - Parses ir_json into DocumentIR
      - Runs all 5 render gates (validate_final_render_gate)
      - Renders DOCX/PDF via DocumentRenderer

    When ENABLE_IR_RENDERER is off:
      - Returns the legacy generated_text as-is (plain .txt)
      - No breaking change for doc_types not yet migrated

    Query params:
      format  "docx" (default) | "pdf"

    Response:
      Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
                 or application/pdf
      Content-Disposition: attachment; filename="{document_id}.{format}"
    """
    # ── 1. Load document row ─────────────────────────────────────────────
    row = await _fetch_document(session, document_id, current_user.id)

    doc_type: str = row["document_type"] or ""
    generated_text: str = row["generated_text"] or ""
    ir_json: dict | None = row["ir_json"]
    processual_checks: list[dict] = row["processual_validation_checks"] or []

    # ── 2. Feature flag — legacy fallback ────────────────────────────────
    if not flags.ir_renderer(doc_type):
        return _legacy_export(document_id, generated_text, format)

    # ── 3. Resolve DocumentIR ────────────────────────────────────────────
    if ir_json is None:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "IR_MISSING",
                "message": (
                    "Документ ще не має IR-структури. "
                    "Увімкни ir_pipeline для цього типу документів або "
                    "згенеруй документ повторно."
                ),
                "document_id": document_id,
            },
        )

    try:
        ir_json = migrate_ir(ir_json)  # upgrade schema if stored under older ir_version
        ir = DocumentIR(**ir_json)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": IR_PARSE_FAIL,
                "message": "Збережений ir_json не відповідає схемі DocumentIR.",
                "error": str(exc),
            },
        ) from exc

    # ── 4. Run all 5 render gates (raises 422 on failure) ─────────────────
    validate_final_render_gate(
        ir,
        doc_type=doc_type,
        generated_text=generated_text,
        processual_checks=processual_checks,
    )

    # ── 5. Render ─────────────────────────────────────────────────────────
    renderer = DocumentRenderer()
    try:
        if format == "pdf":
            file_bytes = renderer.render_pdf(ir)
        else:
            file_bytes = renderer.render_docx(ir)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": RENDER_FAIL,
                "message": f"Помилка рендерингу документа: {exc}",
            },
        ) from exc

    # ── 6. Stream response ─────────────────────────────────────────────────
    filename = f"{document_id}.{format}"
    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=_MIME[format],
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# Legacy fallback
# ---------------------------------------------------------------------------


def _legacy_export(
    document_id: str,
    generated_text: str,
    format: ExportFormat,
) -> StreamingResponse:
    """Return generated_text as plain UTF-8 download (no IR renderer)."""
    content = generated_text.encode("utf-8")
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{document_id}.txt"',
            "Content-Length": str(len(content)),
            "X-Legacy-Export": "true",
        },
    )


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _fetch_document(
    session: AsyncSession,
    document_id: str,
    user_id: str,
) -> dict:
    """Load document row; raises 404 if not found or not owned by user."""
    row = (
        await session.execute(
            text("""
                SELECT
                    id,
                    document_type,
                    generated_text,
                    ir_json,
                    ir_status,
                    processual_validation_checks
                FROM generated_documents
                WHERE id = :doc_id
                  AND user_id = :user_id
                LIMIT 1
            """),
            {"doc_id": document_id, "user_id": str(user_id)},
        )
    ).mappings().first()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "DOCUMENT_NOT_FOUND",
                "message": f"Документ {document_id!r} не знайдено.",
            },
        )

    return dict(row)
