from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

class GenerateRequest(BaseModel):
    doc_type: str
    form_data: dict[str, Any] = Field(default_factory=dict)
    mode: str = "standard"  # standard, deep
    style: str = "persuasive"  # persuasive, aggressive, conciliatory, analytical
    precedent_ids: list[str] = Field(default_factory=list)
    case_id: str | None = None
    tariff: str = "FREE"
    extra_prompt_context: str | None = None
    saved_digest_id: str | None = None
    include_digest: bool = False
    digest_days: int = Field(default=7, ge=1, le=3650)
    digest_limit: int = Field(default=5, ge=1, le=100)
    digest_only_supreme: bool = True
    digest_court_type: str | None = None
    digest_source: list[str] = Field(default_factory=list)
    bundle_doc_types: list[str] = Field(default_factory=list)  # for multi-doc generation


class CaseLawRefItem(BaseModel):
    id: str
    source: str
    decision_id: str
    case_number: str | None = None
    court_name: str | None = None
    court_type: str | None = None
    decision_date: str | None = None
    summary: str | None = None
    relevance_score: float = 0.0


class ProcessualValidationCheck(BaseModel):
    code: str
    status: str
    message: str


class GenerateResponse(BaseModel):
    document_id: str = ""
    created_at: str = ""
    doc_type: str
    title: str
    preview_text: str
    generated_text: str
    prompt_system: str
    prompt_user: str
    calculations: dict[str, Any] = Field(default_factory=dict)
    used_ai: bool = False
    ai_model: str = ""
    ai_error: str = ""
    quality_guard_applied: bool = False
    pre_generation_gate_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    processual_validation_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    case_id: str | None = None
    case_law_refs: list[CaseLawRefItem] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class GenerateBundleResponse(BaseModel):
    bundle_id: str
    items: list[GenerateResponse]
    total_count: int
    created_at: str


class DocumentHistoryItem(BaseModel):
    id: str
    title: str
    document_type: str
    document_category: str
    case_id: str | None = None
    generated_text: str
    preview_text: str
    ai_model: str | None = None
    used_ai: bool
    has_docx_export: bool = False
    has_pdf_export: bool = False
    last_exported_at: str | None = None
    e_court_ready: bool = False
    filing_blockers: list[str] = Field(default_factory=list)
    created_at: str


class DocumentsHistoryResponse(BaseModel):
    user_id: str
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    sort_by: str = "created_at"
    sort_dir: str = "desc"
    query: str | None = None
    doc_type: str | None = None
    has_docx_export: bool | None = None
    has_pdf_export: bool | None = None
    items: list[DocumentHistoryItem]
    usage: dict[str, Any] = Field(default_factory=dict)


class DocumentUpdateRequest(BaseModel):
    generated_text: str = Field(min_length=1)
    case_id: str | None = None


class DocumentUpdateResponse(BaseModel):
    status: str
    id: str
    has_docx_export: bool
    has_pdf_export: bool


class DocumentProcessualRepairResponse(BaseModel):
    status: str
    id: str
    repaired: bool
    has_docx_export: bool
    has_pdf_export: bool
    pre_generation_gate_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    processual_validation_checks: list[ProcessualValidationCheck] = Field(default_factory=list)


class DocumentProcessualCheckResponse(BaseModel):
    status: str
    id: str
    is_valid: bool
    blockers: list[str] = Field(default_factory=list)
    pre_generation_gate_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    processual_validation_checks: list[ProcessualValidationCheck] = Field(default_factory=list)


class DocumentBulkProcessualRepairRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, min_length=1, max_length=200)


class DocumentBulkProcessualRepairItem(BaseModel):
    id: str
    status: str
    repaired: bool
    is_valid: bool
    blockers: list[str] = Field(default_factory=list)


class DocumentBulkProcessualRepairResponse(BaseModel):
    status: str
    requested: int
    processed: int
    repaired: int
    missing_ids: list[str] = Field(default_factory=list)
    items: list[DocumentBulkProcessualRepairItem] = Field(default_factory=list)


class DocumentDeleteResponse(BaseModel):
    status: str
    id: str


class DocumentBulkDeleteRequest(BaseModel):
    ids: list[str] = Field(default_factory=list, min_length=1, max_length=200)


class DocumentBulkDeleteResponse(BaseModel):
    status: str
    requested: int
    deleted: int
    deleted_ids: list[str] = Field(default_factory=list)
    missing_ids: list[str] = Field(default_factory=list)


class DocumentDetailResponse(BaseModel):
    id: str
    document_type: str
    document_category: str
    case_id: str | None = None
    form_data: dict[str, Any] = Field(default_factory=dict)
    generated_text: str
    preview_text: str
    calculations: dict[str, Any] = Field(default_factory=dict)
    ai_model: str | None = None
    used_ai: bool
    ai_error: str | None = None
    has_docx_export: bool = False
    has_pdf_export: bool = False
    last_exported_at: str | None = None
    e_court_ready: bool = False
    filing_blockers: list[str] = Field(default_factory=list)
    created_at: str


class DocumentCloneResponse(BaseModel):
    status: str
    source_id: str
    document_id: str
    created_at: str
    usage: dict[str, Any] = Field(default_factory=dict)


class DocumentVersionItem(BaseModel):
    id: str
    document_id: str
    version_number: int
    action: str
    created_at: str


class DocumentVersionsResponse(BaseModel):
    document_id: str
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    items: list[DocumentVersionItem] = Field(default_factory=list)


class DocumentRestoreResponse(BaseModel):
    status: str
    id: str
    restored_from_version_id: str
    restored_to_version_number: int
    has_docx_export: bool
    has_pdf_export: bool


class DocumentVersionDetailResponse(BaseModel):
    id: str
    document_id: str
    version_number: int
    action: str
    generated_text: str
    created_at: str


class DocumentVersionDiffResponse(BaseModel):
    document_id: str
    target_version_id: str
    target_version_number: int
    against: str
    against_version_number: int | None = None
    diff_text: str
    added_lines: int = 0
    removed_lines: int = 0
