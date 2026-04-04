from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from .documents import ProcessualValidationCheck, CaseLawRefItem

class AutoProcessDocumentItem(BaseModel):
    id: str
    doc_type: str
    title: str
    created_at: str
    preview_text: str
    used_ai: bool
    ai_model: str | None = None
    ai_error: str | None = None
    quality_guard_applied: bool = False
    pre_generation_gate_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    processual_validation_checks: list[ProcessualValidationCheck] = Field(default_factory=list)


class AutoProcessResponse(BaseModel):
    status: str
    source_file_name: str
    extracted_chars: int
    processual_only_mode: bool = True
    procedural_conclusions: list[str] = Field(default_factory=list)
    recommended_doc_types: list[str] = Field(default_factory=list)
    generated_documents: list[AutoProcessDocumentItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    case_id: str | None = None
    usage: dict[str, Any] = Field(default_factory=dict)


class DocumentIntakeIssueItem(BaseModel):
    issue_type: str
    severity: str
    description: str
    impact: str
    snippet: str | None = None
    start_index: int | None = None
    end_index: int | None = None



class DocumentIntakeResponse(BaseModel):
    id: str
    user_id: str
    source_file_name: str | None = None
    classified_type: str
    document_language: str | None = None
    jurisdiction: str
    primary_party_role: str | None = None
    identified_parties: list[dict[str, str]] = Field(default_factory=list)
    subject_matter: str | None = None
    financial_exposure_amount: float | None = None
    financial_exposure_currency: str | None = None
    financial_exposure_type: str | None = None
    document_date: str | None = None
    deadline_from_document: str | None = None
    urgency_level: str | None = None
    risk_level_legal: str | None = None
    risk_level_procedural: str | None = None
    risk_level_financial: str | None = None
    detected_issues: list[DocumentIntakeIssueItem] = Field(default_factory=list)
    classifier_confidence: float | None = None
    classifier_model: str | None = None
    raw_text_preview: str | None = None
    created_at: str
    usage: dict[str, Any] = Field(default_factory=dict)


class PrecedentMapRefItem(BaseModel):
    id: str
    source: str
    decision_id: str
    case_number: str | None = None
    court_name: str | None = None
    decision_date: str | None = None
    summary: str | None = None
    pattern_type: str
    relevance_score: float = 0.0


class PrecedentGroupItem(BaseModel):
    id: str
    pattern_type: str
    pattern_description: str | None = None
    precedent_ids: list[str] = Field(default_factory=list)
    precedent_count: int = 0
    pattern_strength: float | None = None
    counter_arguments: list[str] = Field(default_factory=list)
    mitigation_strategy: str | None = None
    strategic_advantage: str | None = None
    vulnerability_to_appeal: str | None = None
    created_at: str


class PrecedentMapResponse(BaseModel):
    intake_id: str
    query_used: str
    groups: list[PrecedentGroupItem] = Field(default_factory=list)
    refs: list[PrecedentMapRefItem] = Field(default_factory=list)


class StrategyBlueprintRequest(BaseModel):
    intake_id: str
    regenerate: bool = True
    refresh_precedent_map: bool = True
    precedent_limit: int = Field(default=15, ge=5, le=30)


class StrategyBlueprintResponse(BaseModel):
    id: str
    intake_id: str
    precedent_group_id: str | None = None
    immediate_actions: list[dict[str, Any]] = Field(default_factory=list)
    procedural_roadmap: list[dict[str, Any]] = Field(default_factory=list)
    evidence_strategy: list[dict[str, Any]] = Field(default_factory=list)
    negotiation_playbook: list[dict[str, Any]] = Field(default_factory=list)
    risk_heat_map: list[dict[str, Any]] = Field(default_factory=list)
    critical_deadlines: list[dict[str, Any]] = Field(default_factory=list)
    swot_analysis: dict[str, list[str]] | None = None
    win_probability: float | None = None
    financial_strategy: dict[str, Any] | None = None
    timeline_projection: list[dict[str, Any]] | None = None
    penalty_forecast: dict[str, Any] | None = None
    confidence_score: float | None = None
    confidence_rationale: str | None = None
    recommended_next_steps: str | None = None
    created_at: str
    updated_at: str


class GenerateWithStrategyRequest(BaseModel):
    strategy_blueprint_id: str
    doc_type: str | None = None
    bundle_doc_types: list[str] = Field(default_factory=list)
    form_data: dict[str, Any] = Field(default_factory=dict)
    extra_prompt_context: str | None = None


class GenerateWithStrategyResponse(BaseModel):
    document_id: str
    strategy_blueprint_id: str
    doc_type: str
    title: str
    preview_text: str
    generated_text: str
    used_ai: bool = False
    ai_model: str = ""
    ai_error: str = ""
    quality_guard_applied: bool = False
    pre_generation_gate_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    processual_validation_checks: list[ProcessualValidationCheck] = Field(default_factory=list)
    case_law_refs: list[CaseLawRefItem] = Field(default_factory=list)
    strategy_audit_id: str
    created_at: str
    usage: dict[str, Any] = Field(default_factory=dict)


class GenerateBundleWithStrategyResponse(BaseModel):
    strategy_blueprint_id: str
    items: list[GenerateWithStrategyResponse]
    created_at: str
    usage: dict[str, Any] = Field(default_factory=dict)


class StrategyAuditResponse(BaseModel):
    id: str
    document_id: str
    strategy_blueprint_id: str | None = None
    precedent_citations: list[str] = Field(default_factory=list)
    counter_argument_addresses: list[str] = Field(default_factory=list)
    evidence_positioning_notes: str | None = None
    procedure_optimization_notes: str | None = None
    appeal_proofing_notes: str | None = None
    generated_at: str


class JudgeSimulationResponse(BaseModel):
    id: str
    strategy_blueprint_id: str
    document_id: str | None = None
    verdict_probability: float
    judge_persona: str
    key_vulnerabilities: list[str] = Field(default_factory=list)
    strong_points: list[str] = Field(default_factory=list)
    procedural_risks: list[str] = Field(default_factory=list)
    suggested_corrections: list[str] = Field(default_factory=list)
    judge_commentary: str
    decision_rationale: str
    created_at: str
