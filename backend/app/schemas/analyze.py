from __future__ import annotations
from datetime import date
from typing import Any
from pydantic import BaseModel, Field
from .strategy import AutoProcessDocumentItem


class AnalyzeProcessRequest(BaseModel):
    contract_text: str = Field(min_length=20)
    mode: str = "standard"  # standard, deep
    case_id: str | None = None
    file_name: str | None = None
    file_url: str | None = None
    file_size: int | None = Field(default=None, ge=0)


class AnalyzeBatchProcessRequest(BaseModel):
    items: list[AnalyzeProcessRequest] = Field(min_items=1, max_items=10)


class UnifiedAnalysisResult(BaseModel):
    id: str
    user_id: str
    mode: str  # e.g., "intake", "contract", "decision"
    result_data: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class GdprCheckRequest(BaseModel):
    text: str = Field(min_length=20)


class GdprCheckResponse(BaseModel):
    report: str
    compliant: bool
    issues: list[str] = Field(default_factory=list)


class ContractAnalysisItem(BaseModel):
    id: str
    user_id: str
    file_name: str | None = None
    file_url: str | None = None
    file_size: int | None = None
    contract_type: str | None = None
    risk_level: str | None = None
    critical_risks: list[str] = Field(default_factory=list)
    medium_risks: list[str] = Field(default_factory=list)
    ok_points: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    ai_model: str | None = None
    tokens_used: int | None = None
    processing_time_ms: int | None = None
    created_at: str
    usage: dict[str, Any] = Field(default_factory=dict)


class ContractAnalysisHistoryResponse(BaseModel):
    total: int
    items: list[ContractAnalysisItem]
    usage: dict[str, Any] = Field(default_factory=dict)


class DecisionAnalysisIssue(BaseModel):
    topic: str
    court_position: str
    legal_basis: list[str] = Field(default_factory=list)
    practical_effect: str | None = None


class DecisionAnalysisCaseLawRef(BaseModel):
    id: str
    source: str
    decision_id: str
    court_name: str | None = None
    court_type: str | None = None
    decision_date: str | None = None
    case_number: str | None = None
    summary: str | None = None


class DecisionAnalysisStageRecommendation(BaseModel):
    stage: str
    actions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class DecisionAnalysisStagePacket(BaseModel):
    stage: str
    objective: str
    key_documents: list[str] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    exit_criteria: list[str] = Field(default_factory=list)


class DecisionAnalysisSideAssessment(BaseModel):
    side: str = "unknown"
    opposing_side: str = "unknown"
    confidence: float = 0.0
    rationale: list[str] = Field(default_factory=list)


class DecisionAnalysisDefensePlanItem(BaseModel):
    code: str
    stage: str
    goal: str
    actions: list[str] = Field(default_factory=list)
    target_documents: list[str] = Field(default_factory=list)


class DecisionAnalysisEvidenceGapItem(BaseModel):
    code: str
    title: str
    status: str
    detail: str
    recommended_actions: list[str] = Field(default_factory=list)


class DecisionAnalysisDocumentPreparationItem(BaseModel):
    doc_type: str
    title: str
    purpose: str
    priority: str
    readiness: str
    blockers: list[str] = Field(default_factory=list)


class DecisionAnalysisPracticeCoverage(BaseModel):
    total_items: int = 0
    distinct_courts: int = 0
    court_types: dict[str, int] = Field(default_factory=dict)
    instance_levels: dict[str, int] = Field(default_factory=dict)
    latest_decision_date: str | None = None
    oldest_decision_date: str | None = None
    freshness_days: int | None = None
    stale: bool = True


class DecisionAnalysisQualityBlock(BaseModel):
    code: str
    title: str
    status: str
    score: float
    summary: str
    details: list[str] = Field(default_factory=list)


class DecisionAnalysisTraceItem(BaseModel):
    claim: str
    support_type: str
    reference: str
    confidence: float


class DecisionAnalysisQualityGate(BaseModel):
    status: str = "blocked"
    can_proceed_to_filing: bool = False
    blockers: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class DecisionAnalysisResponse(BaseModel):
    status: str
    source_file_name: str
    extracted_chars: int
    dispute_summary: str
    procedural_context: str
    key_issues: list[DecisionAnalysisIssue] = Field(default_factory=list)
    key_questions: list[str] = Field(default_factory=list)
    side_assessment: DecisionAnalysisSideAssessment = Field(
        default_factory=DecisionAnalysisSideAssessment
    )
    defense_plan: list[DecisionAnalysisDefensePlanItem] = Field(default_factory=list)
    evidence_gaps: list[DecisionAnalysisEvidenceGapItem] = Field(default_factory=list)
    document_preparation: list[DecisionAnalysisDocumentPreparationItem] = Field(
        default_factory=list
    )
    cassation_vulnerabilities: list[str] = Field(default_factory=list)
    final_conclusion: str
    stage_recommendations: list[DecisionAnalysisStageRecommendation] = Field(
        default_factory=list
    )
    stage_packets: list[DecisionAnalysisStagePacket] = Field(default_factory=list)
    recent_practice: list[DecisionAnalysisCaseLawRef] = Field(default_factory=list)
    practice_coverage: DecisionAnalysisPracticeCoverage = Field(
        default_factory=DecisionAnalysisPracticeCoverage
    )
    quality_blocks: list[DecisionAnalysisQualityBlock] = Field(default_factory=list)
    traceability: list[DecisionAnalysisTraceItem] = Field(default_factory=list)
    overall_confidence_score: float = 0.0
    quality_gate: DecisionAnalysisQualityGate = Field(
        default_factory=DecisionAnalysisQualityGate
    )
    used_ai: bool = False
    ai_model: str = ""
    ai_error: str = ""
    case_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class DecisionAnalysisHistoryItem(BaseModel):
    id: str
    event_type: str
    source_file_name: str | None = None
    extracted_chars: int | None = None
    status: str | None = None
    quality_gate_status: str | None = None
    overall_confidence_score: float | None = None
    practice_total: int | None = None
    practice_latest_decision_date: str | None = None
    format: str | None = None
    case_id: str | None = None
    has_report_snapshot: bool = False
    created_at: str


class DecisionAnalysisHistoryResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    event: str | None = None
    items: list[DecisionAnalysisHistoryItem] = Field(default_factory=list)


class DecisionAnalysisPackageResponse(BaseModel):
    status: str
    source_file_name: str
    extracted_chars: int
    selected_doc_types: list[str] = Field(default_factory=list)
    skipped_doc_types: list[str] = Field(default_factory=list)
    generated_documents: list[AutoProcessDocumentItem] = Field(default_factory=list)
    side_assessment: DecisionAnalysisSideAssessment = Field(
        default_factory=DecisionAnalysisSideAssessment
    )
    evidence_gaps_missing_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class FullLawyerSummary(BaseModel):
    dispute_type: str
    procedure: str
    urgency: str
    claim_amount_uah: float | None = None
    estimated_court_fee_uah: float | None = None
    estimated_penalty_uah: float | None = None
    estimated_total_with_fee_uah: float | None = None


class FullLawyerValidationCheck(BaseModel):
    code: str
    status: str
    message: str


class FullLawyerContextRef(BaseModel):
    source: str
    ref_type: str
    reference: str
    note: str | None = None
    relevance_score: float | None = None


class FullLawyerPackageItem(BaseModel):
    id: str
    doc_type: str
    title: str
    created_at: str
    is_draft: bool = False


class FullLawyerFilingPackage(BaseModel):
    generated: bool = False
    items: list[FullLawyerPackageItem] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    status: str = "not_requested"
    reason: str | None = None
    is_draft: bool = False


class FullLawyerProcessualPackageGate(BaseModel):
    status: str = "unknown"
    can_generate_package: bool = False
    blockers: list[str] = Field(default_factory=list)


class FullLawyerWorkflowStage(BaseModel):
    code: str
    title: str
    status: str
    details: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class FullLawyerReviewItem(BaseModel):
    code: str
    title: str
    description: str
    required: bool = True


class FullLawyerTimelineItem(BaseModel):
    code: str
    title: str
    date: str | None = None
    status: str
    note: str | None = None


class FullLawyerEvidenceMatrixItem(BaseModel):
    code: str
    title: str
    found_in_source: bool | None = None
    status: str
    note: str | None = None


class FullLawyerFactChronologyItem(BaseModel):
    event: str
    event_date: str | None = None
    actor: str
    evidence_status: str
    source_excerpt: str | None = None
    relevance: str


class FullLawyerBurdenOfProofItem(BaseModel):
    issue: str
    burden_on: str
    required_evidence: list[str] = Field(default_factory=list)
    current_status: str
    recommended_action: str


class FullLawyerDraftingInstructionItem(BaseModel):
    doc_type: str
    must_include: list[str] = Field(default_factory=list)
    factual_focus: list[str] = Field(default_factory=list)
    legal_focus: list[str] = Field(default_factory=list)
    style_notes: list[str] = Field(default_factory=list)
    status: str = "ok"


class FullLawyerOpponentWeaknessItem(BaseModel):
    weakness: str
    severity: str
    exploitation_step: str
    supporting_basis: str
    evidentiary_need: str


class FullLawyerEvidenceCollectionPlanItem(BaseModel):
    priority: str
    step: str
    owner: str
    deadline_hint: str
    expected_result: str
    status: str = "queued"


class FullLawyerFactualCircumstanceBlockItem(BaseModel):
    section: str
    narrative: str
    evidence_anchor: str
    status: str = "ok"


class FullLawyerLegalQualificationBlockItem(BaseModel):
    qualification: str
    norm_reference: str
    application_to_facts: str
    risk_note: str
    status: str = "ok"


class FullLawyerPrayerPartVariantItem(BaseModel):
    variant: str
    request_text: str
    grounds: str
    priority: str


class FullLawyerCounterargumentResponseItem(BaseModel):
    opponent_argument: str
    response_strategy: str
    evidence_focus: str
    success_probability: str


class FullLawyerDocumentNarrativeCompletenessItem(BaseModel):
    section: str
    status: str
    action: str
    note: str | None = None


class FullLawyerCaseLawApplicationItem(BaseModel):
    legal_issue: str
    reference: str
    application_note: str
    strength: str


class FullLawyerProceduralViolationHypothesisItem(BaseModel):
    hypothesis: str
    legal_basis: str
    source_signal: str
    viability: str
    required_proof: str


class FullLawyerDocumentFactEnrichmentItem(BaseModel):
    doc_type: str
    missing_fact_block: str
    insert_instruction: str
    priority: str
    status: str = "queued"


class FullLawyerHearingPositioningNoteItem(BaseModel):
    theme: str
    supporting_points: list[str] = Field(default_factory=list)
    risk_counter: str
    courtroom_phrase: str


class FullLawyerProcessStageActionItem(BaseModel):
    stage_code: str
    stage_title: str
    objective: str
    actions: list[str] = Field(default_factory=list)
    trigger: str
    status: str


class FullLawyerArgumentMapItem(BaseModel):
    issue: str
    legal_basis: str
    litigation_goal: str


class FullLawyerReadinessBreakdown(BaseModel):
    score: float = 0.0
    decision: str = "not_ready"
    blockers: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class FullLawyerPartyProfile(BaseModel):
    completion_score: float = 0.0
    risk_level: str = "high"
    plaintiff_detected: bool = False
    defendant_detected: bool = False
    missing_items: list[str] = Field(default_factory=list)


class FullLawyerJurisdictionRecommendation(BaseModel):
    procedure: str = "civil"
    suggested_route: str = ""
    legal_basis: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    required_inputs: list[str] = Field(default_factory=list)
    warning: str | None = None


class FullLawyerDocQualityItem(BaseModel):
    doc_type: str
    score: float = 0.0
    status: str = "low"
    issues: list[str] = Field(default_factory=list)


class FullLawyerECourtPreview(BaseModel):
    can_submit: bool = False
    provider: str = "court.gov.ua"
    signer_methods: list[str] = Field(default_factory=list)
    required_attachments: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerPriorityTask(BaseModel):
    priority: str
    task: str
    due_date: str | None = None


class FullLawyerConsistencyItem(BaseModel):
    code: str
    status: str
    message: str


class FullLawyerRemedyCoverageItem(BaseModel):
    remedy: str
    covered: bool
    covered_by: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerCitationCaseRef(BaseModel):
    source: str
    reference: str
    note: str | None = None


class FullLawyerCitationPack(BaseModel):
    statutory_refs: list[str] = Field(default_factory=list)
    case_refs: list[FullLawyerCitationCaseRef] = Field(default_factory=list)
    note: str | None = None


class FullLawyerFeeScenarioItem(BaseModel):
    name: str
    principal_uah: float | None = None
    court_fee_uah: float | None = None
    penalty_uah: float | None = None
    total_with_fee_uah: float | None = None
    note: str | None = None


class FullLawyerFilingRiskItem(BaseModel):
    risk: str
    probability: float
    impact: str
    mitigation: str


class FullLawyerDefectItem(BaseModel):
    code: str
    severity: str
    issue: str
    fix: str


class FullLawyerAdmissibilityItem(BaseModel):
    evidence: str
    admissibility: str
    relevance: str
    risk: str
    recommendation: str


class FullLawyerMotionItem(BaseModel):
    motion_type: str
    priority: str
    rationale: str
    trigger: str


class FullLawyerHearingTask(BaseModel):
    phase: str
    task: str
    output: str


class FullLawyerPackageCompleteness(BaseModel):
    status: str = "incomplete"
    score: float = 0.0
    generated_documents_count: int = 0
    missing_evidence_items: int = 0
    unresolved_required_review_items: int = 0
    note: str | None = None


class FullLawyerObjectionItem(BaseModel):
    objection: str
    likelihood: str
    rebuttal: str


class FullLawyerSettlementStrategy(BaseModel):
    dispute_type: str = "General dispute"
    window: str = "parallel"
    target_amount_uah: float | None = None
    recommendation: str = ""
    note: str | None = None


class FullLawyerEnforcementStep(BaseModel):
    step: str
    timing: str
    details: str


class FullLawyerCPCComplianceItem(BaseModel):
    requirement: str
    article: str
    status: str
    note: str | None = None


class FullLawyerDocumentSectionItem(BaseModel):
    section: str
    required: bool = True
    status: str
    note: str | None = None


class FullLawyerDeadlineControlItem(BaseModel):
    code: str
    title: str
    due_date: str | None = None
    status: str
    basis: str
    note: str | None = None


class FullLawyerCourtFeeBreakdown(BaseModel):
    principal_uah: float | None = None
    penalty_uah: float | None = None
    inflation_losses_uah: float | None = None
    claim_price_uah: float | None = None
    court_fee_uah: float | None = None
    total_with_fee_uah: float | None = None
    status: str = "estimated"
    note: str | None = None


class FullLawyerAttachmentRegisterItem(BaseModel):
    name: str
    required: bool = True
    available: bool = False
    copies_for_court: int = 1
    status: str = "missing"
    note: str | None = None


class FullLawyerCPC175RequisiteItem(BaseModel):
    requisite: str
    status: str
    source_signal: str
    note: str | None = None


class FullLawyerCPC177AttachmentGroup(BaseModel):
    attachment_group: str
    required: bool = True
    status: str
    items_total: int = 0
    items_available: int = 0
    note: str | None = None


class FullLawyerPrayerPartAudit(BaseModel):
    status: str = "needs_improvement"
    score: float = 0.0
    target_total_uah: float | None = None
    covered_requests: list[str] = Field(default_factory=list)
    missing_requests: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerFactNormEvidenceItem(BaseModel):
    fact_issue: str
    legal_norm: str
    evidence: str
    status: str
    note: str | None = None


class FullLawyerRedFlagItem(BaseModel):
    severity: str
    flag: str
    action: str


class FullLawyerTextSectionAuditItem(BaseModel):
    section: str
    status: str
    note: str | None = None


class FullLawyerServicePlanItem(BaseModel):
    recipient: str
    method: str
    status: str
    note: str | None = None


class FullLawyerPrayerSuggestionItem(BaseModel):
    priority: str
    suggestion: str
    rationale: str


class FullLawyerContradictionHotspotItem(BaseModel):
    issue: str
    severity: str
    fix: str


class FullLawyerJudgeQuestionItem(BaseModel):
    question: str
    why_it_matters: str
    prep_answer_hint: str


class FullLawyerCitationQualityGate(BaseModel):
    status: str = "weak"
    score: float = 0.0
    cpc_refs_count: int = 0
    case_refs_count: int = 0
    issues: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerFilingDecisionCard(BaseModel):
    decision: str = "hold"
    confidence: float = 0.0
    readiness_score: float = 0.0
    blockers: list[str] = Field(default_factory=list)
    next_step: str = ""
    note: str | None = None


class FullLawyerProcessualLanguageAudit(BaseModel):
    status: str = "weak"
    score: float = 0.0
    formal_markers_found: int = 0
    informal_markers_found: int = 0
    note: str | None = None


class FullLawyerEvidenceGapAction(BaseModel):
    evidence: str
    priority: str
    action: str
    deadline_hint: str


class FullLawyerDeadlineAlertItem(BaseModel):
    title: str
    level: str
    days_left: int
    recommended_action: str


class FullLawyerFilingPacketItem(BaseModel):
    order: int
    item: str
    required: bool = True
    status: str
    note: str | None = None


class FullLawyerOpponentPlaybookItem(BaseModel):
    scenario: str
    counter_step: str
    evidence_focus: str


class FullLawyerLimitationPeriodCard(BaseModel):
    status: str = "ok"
    risk: str = "low"
    reference_date: str | None = None
    limitation_deadline: str | None = None
    days_remaining: int = 0
    note: str | None = None


class FullLawyerJurisdictionChallengeGuard(BaseModel):
    risk_level: str = "low"
    route: str = ""
    weak_points: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerClaimFormulaCard(BaseModel):
    status: str = "warn"
    principal_uah: float = 0.0
    penalty_uah: float = 0.0
    court_fee_uah: float = 0.0
    total_claim_uah: float = 0.0
    formula: str = ""
    note: str | None = None


class FullLawyerFilingCoverLetter(BaseModel):
    status: str = "draft"
    subject: str = ""
    recipient: str = ""
    body_preview: str = ""
    note: str | None = None


class FullLawyerExecutionStepItem(BaseModel):
    stage: str
    status: str
    trigger: str


class FullLawyerVersionControlCard(BaseModel):
    status: str = "draft_only"
    generated_documents: int = 0
    unique_doc_types: int = 0
    revision_tag: str = "v1"
    note: str | None = None


class FullLawyerECourtPacketReadiness(BaseModel):
    status: str = "not_ready"
    blockers: list[str] = Field(default_factory=list)
    missing_attachments: list[str] = Field(default_factory=list)
    recommended_submit_mode: str = "hold submission"
    note: str | None = None


class FullLawyerHearingScriptItem(BaseModel):
    phase: str
    script_hint: str
    linked_basis: str


class FullLawyerSettlementOfferCard(BaseModel):
    status: str = "optional"
    target_min_uah: float = 0.0
    target_max_uah: float = 0.0
    strategy_note: str = ""
    fallback_position: str = ""
    note: str | None = None


class FullLawyerAppealReserveCard(BaseModel):
    status: str = "standby"
    reserve_deadline: str | None = None
    trigger_conditions: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerProceduralCostsAllocatorCard(BaseModel):
    status: str = "preliminary"
    plaintiff_upfront_costs_uah: float = 0.0
    defendant_target_recovery_uah: float = 0.0
    cost_components: dict[str, float] = Field(default_factory=dict)
    note: str | None = None


class FullLawyerDocumentExportReadiness(BaseModel):
    status: str = "not_ready"
    formats: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerSubmissionChecklistItem(BaseModel):
    step: str
    status: str
    detail: str


class FullLawyerMonitoringBoardItem(BaseModel):
    track: str
    priority: str
    signal: str


class FullLawyerResearchBacklogItem(BaseModel):
    task: str
    priority: str
    expected_output: str


class FullLawyerProceduralConsistencyScorecard(BaseModel):
    status: str = "weak"
    score: float = 0.0
    validation_warn_count: int = 0
    text_warn_count: int = 0
    cpc_warn_count: int = 0
    note: str | None = None


class FullLawyerHearingEvidenceOrderItem(BaseModel):
    order: int
    evidence: str
    priority: str
    status: str
    note: str | None = None


class FullLawyerDigitalSignatureReadiness(BaseModel):
    status: str = "not_ready"
    signer_methods: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    note: str | None = None


class FullLawyerCaseLawWatchItem(BaseModel):
    source: str
    reference: str
    watch_reason: str


class FullLawyerFinalSubmissionGate(BaseModel):
    status: str = "blocked"
    blockers: list[str] = Field(default_factory=list)
    critical_deadlines: list[str] = Field(default_factory=list)
    next_step: str = ""
    hard_stop: bool = True
    note: str | None = None


class FullLawyerCourtBehaviorForecastCard(BaseModel):
    stance: str = "balanced"
    confidence: float = 0.0
    high_impact_risks: int = 0
    high_severity_flags: int = 0
    question_load: int = 0
    note: str | None = None


class FullLawyerEvidenceCompressionItem(BaseModel):
    step: str
    status: str
    detail: str


class FullLawyerFilingChannelStrategyCard(BaseModel):
    status: str = "fallback"
    primary_channel: str = "paper_filing"
    backup_channel: str = "e_court_after_fixes"
    checklist_warn_count: int = 0
    note: str | None = None


class FullLawyerLegalBudgetTimelineCard(BaseModel):
    timeline_mode: str = "standard"
    estimated_upfront_uah: float = 0.0
    recommended_reserve_uah: float = 0.0
    settlement_floor_uah: float = 0.0
    urgent_deadlines: int = 0
    note: str | None = None


class FullLawyerCounterpartyPressureItem(BaseModel):
    vector: str
    pressure: str
    coverage: str
    action: str


class FullLawyerTimelineScenarioItem(BaseModel):
    scenario: str
    probability: str
    focus: str


class FullLawyerEvidenceAuthenticityItem(BaseModel):
    evidence: str
    status: str
    action: str


class FullLawyerRemedyPriorityItem(BaseModel):
    remedy: str
    priority: str
    rationale: str


class FullLawyerJudgeQuestionDrillCard(BaseModel):
    complexity: str = "low"
    rounds: int = 1
    question_count: int = 0
    hotspot_count: int = 0
    note: str | None = None


class FullLawyerClientInstructionItem(BaseModel):
    instruction: str
    priority: str
    note: str


class FullLawyerProceduralRiskHeatItem(BaseModel):
    risk: str
    level: str
    source: str


class FullLawyerEvidenceDisclosureItem(BaseModel):
    evidence: str
    phase: str
    status: str
    note: str


class FullLawyerSettlementScriptItem(BaseModel):
    stage: str
    line: str
    goal: str


class FullLawyerHearingReadinessScorecard(BaseModel):
    status: str = "not_ready"
    score: float = 0.0
    script_count: int = 0
    evidence_ready: int = 0
    evidence_total: int = 0
    drill_rounds: int = 0
    note: str | None = None


class FullLawyerAdvocateSignoffPacket(BaseModel):
    status: str = "review_needed"
    required_checks: list[dict[str, str]] = Field(default_factory=list)
    note: str | None = None


class FullLawyerPreflightPackageHint(BaseModel):
    status: str = "blocked"
    can_generate_final_package: bool = False
    can_generate_draft_package: bool = False
    recommended_package_mode: str = "none"
    blockers: list[str] = Field(default_factory=list)
    reason: str = ""


class FullLawyerPreflightResponse(BaseModel):
    status: str
    source_file_name: str
    extracted_chars: int
    processual_only_mode: bool = True
    recommended_doc_types: list[str] = Field(default_factory=list)
    validation_checks: list[FullLawyerValidationCheck] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    review_checklist: list[FullLawyerReviewItem] = Field(default_factory=list)
    unresolved_review_items: list[str] = Field(default_factory=list)
    deadline_control: list[FullLawyerDeadlineControlItem] = Field(default_factory=list)
    processual_package_gate: FullLawyerProcessualPackageGate = Field(
        default_factory=FullLawyerProcessualPackageGate
    )
    final_submission_gate: FullLawyerFinalSubmissionGate = Field(
        default_factory=FullLawyerFinalSubmissionGate
    )
    package_generation_hint: FullLawyerPreflightPackageHint = Field(
        default_factory=FullLawyerPreflightPackageHint
    )
    next_actions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


class FullLawyerPreflightHistoryItem(BaseModel):
    id: str
    event_type: str
    source_file_name: str | None = None
    extracted_chars: int | None = None
    status: str | None = None
    final_submission_gate_status: str | None = None
    consume_quota: bool = False
    format: str | None = None
    has_report_snapshot: bool = False
    created_at: str


class FullLawyerPreflightHistoryResponse(BaseModel):
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1
    event: str | None = None
    items: list[FullLawyerPreflightHistoryItem] = Field(default_factory=list)


class FullLawyerResponse(BaseModel):
    status: str
    source_file_name: str
    extracted_chars: int
    processual_only_mode: bool = True
    case_id: str | None = None
    summary: FullLawyerSummary
    legal_basis: list[str] = Field(default_factory=list)
    strategy_steps: list[str] = Field(default_factory=list)
    evidence_required: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    clarification_required: bool = False
    unresolved_questions: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    validation_checks: list[FullLawyerValidationCheck] = Field(default_factory=list)
    context_refs: list[FullLawyerContextRef] = Field(default_factory=list)
    confidence_score: float = 0.0
    analysis_highlights: list[str] = Field(default_factory=list)
    procedural_conclusions: list[str] = Field(default_factory=list)
    recommended_doc_types: list[str] = Field(default_factory=list)
    generated_documents: list[AutoProcessDocumentItem] = Field(default_factory=list)
    filing_package: FullLawyerFilingPackage = Field(
        default_factory=FullLawyerFilingPackage
    )
    processual_package_gate: FullLawyerProcessualPackageGate = Field(
        default_factory=FullLawyerProcessualPackageGate
    )
    review_checklist: list[FullLawyerReviewItem] = Field(default_factory=list)
    review_required: bool = False
    unresolved_review_items: list[str] = Field(default_factory=list)
    workflow_stages: list[FullLawyerWorkflowStage] = Field(default_factory=list)
    ready_for_filing: bool = False
    procedural_timeline: list[FullLawyerTimelineItem] = Field(default_factory=list)
    evidence_matrix: list[FullLawyerEvidenceMatrixItem] = Field(default_factory=list)
    fact_chronology_matrix: list[FullLawyerFactChronologyItem] = Field(
        default_factory=list
    )
    burden_of_proof_map: list[FullLawyerBurdenOfProofItem] = Field(default_factory=list)
    drafting_instructions: list[FullLawyerDraftingInstructionItem] = Field(
        default_factory=list
    )
    opponent_weakness_map: list[FullLawyerOpponentWeaknessItem] = Field(
        default_factory=list
    )
    evidence_collection_plan: list[FullLawyerEvidenceCollectionPlanItem] = Field(
        default_factory=list
    )
    factual_circumstances_blocks: list[FullLawyerFactualCircumstanceBlockItem] = Field(
        default_factory=list
    )
    legal_qualification_blocks: list[FullLawyerLegalQualificationBlockItem] = Field(
        default_factory=list
    )
    prayer_part_variants: list[FullLawyerPrayerPartVariantItem] = Field(
        default_factory=list
    )
    counterargument_response_matrix: list[FullLawyerCounterargumentResponseItem] = (
        Field(default_factory=list)
    )
    document_narrative_completeness: list[
        FullLawyerDocumentNarrativeCompletenessItem
    ] = Field(default_factory=list)
    case_law_application_matrix: list[FullLawyerCaseLawApplicationItem] = Field(
        default_factory=list
    )
    procedural_violation_hypotheses: list[
        FullLawyerProceduralViolationHypothesisItem
    ] = Field(default_factory=list)
    document_fact_enrichment_plan: list[FullLawyerDocumentFactEnrichmentItem] = Field(
        default_factory=list
    )
    hearing_positioning_notes: list[FullLawyerHearingPositioningNoteItem] = Field(
        default_factory=list
    )
    process_stage_action_map: list[FullLawyerProcessStageActionItem] = Field(
        default_factory=list
    )
    legal_argument_map: list[FullLawyerArgumentMapItem] = Field(default_factory=list)
    readiness_breakdown: FullLawyerReadinessBreakdown = Field(
        default_factory=FullLawyerReadinessBreakdown
    )
    post_filing_plan: list[str] = Field(default_factory=list)
    party_profile: FullLawyerPartyProfile = Field(
        default_factory=FullLawyerPartyProfile
    )
    jurisdiction_recommendation: FullLawyerJurisdictionRecommendation = Field(
        default_factory=FullLawyerJurisdictionRecommendation
    )
    generated_docs_quality: list[FullLawyerDocQualityItem] = Field(default_factory=list)
    e_court_submission_preview: FullLawyerECourtPreview = Field(
        default_factory=FullLawyerECourtPreview
    )
    priority_queue: list[FullLawyerPriorityTask] = Field(default_factory=list)
    consistency_report: list[FullLawyerConsistencyItem] = Field(default_factory=list)
    remedy_coverage: list[FullLawyerRemedyCoverageItem] = Field(default_factory=list)
    citation_pack: FullLawyerCitationPack = Field(
        default_factory=FullLawyerCitationPack
    )
    fee_scenarios: list[FullLawyerFeeScenarioItem] = Field(default_factory=list)
    filing_risk_simulation: list[FullLawyerFilingRiskItem] = Field(default_factory=list)
    procedural_defect_scan: list[FullLawyerDefectItem] = Field(default_factory=list)
    evidence_admissibility_map: list[FullLawyerAdmissibilityItem] = Field(
        default_factory=list
    )
    motion_recommendations: list[FullLawyerMotionItem] = Field(default_factory=list)
    hearing_preparation_plan: list[FullLawyerHearingTask] = Field(default_factory=list)
    package_completeness: FullLawyerPackageCompleteness = Field(
        default_factory=FullLawyerPackageCompleteness
    )
    opponent_objections: list[FullLawyerObjectionItem] = Field(default_factory=list)
    settlement_strategy: FullLawyerSettlementStrategy = Field(
        default_factory=FullLawyerSettlementStrategy
    )
    enforcement_plan: list[FullLawyerEnforcementStep] = Field(default_factory=list)
    cpc_compliance_check: list[FullLawyerCPCComplianceItem] = Field(
        default_factory=list
    )
    procedural_document_blueprint: list[FullLawyerDocumentSectionItem] = Field(
        default_factory=list
    )
    deadline_control: list[FullLawyerDeadlineControlItem] = Field(default_factory=list)
    court_fee_breakdown: FullLawyerCourtFeeBreakdown = Field(
        default_factory=FullLawyerCourtFeeBreakdown
    )
    filing_attachments_register: list[FullLawyerAttachmentRegisterItem] = Field(
        default_factory=list
    )
    cpc_175_requisites_map: list[FullLawyerCPC175RequisiteItem] = Field(
        default_factory=list
    )
    cpc_177_attachments_map: list[FullLawyerCPC177AttachmentGroup] = Field(
        default_factory=list
    )
    prayer_part_audit: FullLawyerPrayerPartAudit = Field(
        default_factory=FullLawyerPrayerPartAudit
    )
    fact_norm_evidence_chain: list[FullLawyerFactNormEvidenceItem] = Field(
        default_factory=list
    )
    pre_filing_red_flags: list[FullLawyerRedFlagItem] = Field(default_factory=list)
    text_section_audit: list[FullLawyerTextSectionAuditItem] = Field(
        default_factory=list
    )
    service_plan: list[FullLawyerServicePlanItem] = Field(default_factory=list)
    prayer_rewrite_suggestions: list[FullLawyerPrayerSuggestionItem] = Field(
        default_factory=list
    )
    contradiction_hotspots: list[FullLawyerContradictionHotspotItem] = Field(
        default_factory=list
    )
    judge_questions_simulation: list[FullLawyerJudgeQuestionItem] = Field(
        default_factory=list
    )
    citation_quality_gate: FullLawyerCitationQualityGate = Field(
        default_factory=FullLawyerCitationQualityGate
    )
    filing_decision_card: FullLawyerFilingDecisionCard = Field(
        default_factory=FullLawyerFilingDecisionCard
    )
    processual_language_audit: FullLawyerProcessualLanguageAudit = Field(
        default_factory=FullLawyerProcessualLanguageAudit
    )
    evidence_gap_actions: list[FullLawyerEvidenceGapAction] = Field(
        default_factory=list
    )
    deadline_alert_board: list[FullLawyerDeadlineAlertItem] = Field(
        default_factory=list
    )
    filing_packet_order: list[FullLawyerFilingPacketItem] = Field(default_factory=list)
    opponent_response_playbook: list[FullLawyerOpponentPlaybookItem] = Field(
        default_factory=list
    )
    limitation_period_card: FullLawyerLimitationPeriodCard = Field(
        default_factory=FullLawyerLimitationPeriodCard
    )
    jurisdiction_challenge_guard: FullLawyerJurisdictionChallengeGuard = Field(
        default_factory=FullLawyerJurisdictionChallengeGuard
    )
    claim_formula_card: FullLawyerClaimFormulaCard = Field(
        default_factory=FullLawyerClaimFormulaCard
    )
    filing_cover_letter: FullLawyerFilingCoverLetter = Field(
        default_factory=FullLawyerFilingCoverLetter
    )
    execution_step_tracker: list[FullLawyerExecutionStepItem] = Field(
        default_factory=list
    )
    version_control_card: FullLawyerVersionControlCard = Field(
        default_factory=FullLawyerVersionControlCard
    )
    e_court_packet_readiness: FullLawyerECourtPacketReadiness = Field(
        default_factory=FullLawyerECourtPacketReadiness
    )
    hearing_script_pack: list[FullLawyerHearingScriptItem] = Field(default_factory=list)
    settlement_offer_card: FullLawyerSettlementOfferCard = Field(
        default_factory=FullLawyerSettlementOfferCard
    )
    appeal_reserve_card: FullLawyerAppealReserveCard = Field(
        default_factory=FullLawyerAppealReserveCard
    )
    procedural_costs_allocator_card: FullLawyerProceduralCostsAllocatorCard = Field(
        default_factory=FullLawyerProceduralCostsAllocatorCard
    )
    document_export_readiness: FullLawyerDocumentExportReadiness = Field(
        default_factory=FullLawyerDocumentExportReadiness
    )
    filing_submission_checklist_card: list[FullLawyerSubmissionChecklistItem] = Field(
        default_factory=list
    )
    post_filing_monitoring_board: list[FullLawyerMonitoringBoardItem] = Field(
        default_factory=list
    )
    legal_research_backlog: list[FullLawyerResearchBacklogItem] = Field(
        default_factory=list
    )
    procedural_consistency_scorecard: FullLawyerProceduralConsistencyScorecard = Field(
        default_factory=FullLawyerProceduralConsistencyScorecard
    )
    hearing_evidence_order_card: list[FullLawyerHearingEvidenceOrderItem] = Field(
        default_factory=list
    )
    digital_signature_readiness: FullLawyerDigitalSignatureReadiness = Field(
        default_factory=FullLawyerDigitalSignatureReadiness
    )
    case_law_update_watchlist: list[FullLawyerCaseLawWatchItem] = Field(
        default_factory=list
    )
    final_submission_gate: FullLawyerFinalSubmissionGate = Field(
        default_factory=FullLawyerFinalSubmissionGate
    )
    court_behavior_forecast_card: FullLawyerCourtBehaviorForecastCard = Field(
        default_factory=FullLawyerCourtBehaviorForecastCard
    )
    evidence_pack_compression_plan: list[FullLawyerEvidenceCompressionItem] = Field(
        default_factory=list
    )
    filing_channel_strategy_card: FullLawyerFilingChannelStrategyCard = Field(
        default_factory=FullLawyerFilingChannelStrategyCard
    )
    legal_budget_timeline_card: FullLawyerLegalBudgetTimelineCard = Field(
        default_factory=FullLawyerLegalBudgetTimelineCard
    )
    counterparty_pressure_map: list[FullLawyerCounterpartyPressureItem] = Field(
        default_factory=list
    )
    courtroom_timeline_scenarios: list[FullLawyerTimelineScenarioItem] = Field(
        default_factory=list
    )
    evidence_authenticity_checklist: list[FullLawyerEvidenceAuthenticityItem] = Field(
        default_factory=list
    )
    remedy_priority_matrix: list[FullLawyerRemedyPriorityItem] = Field(
        default_factory=list
    )
    judge_question_drill_card: FullLawyerJudgeQuestionDrillCard = Field(
        default_factory=FullLawyerJudgeQuestionDrillCard
    )
    client_instruction_packet: list[FullLawyerClientInstructionItem] = Field(
        default_factory=list
    )
    procedural_risk_heatmap: list[FullLawyerProceduralRiskHeatItem] = Field(
        default_factory=list
    )
    evidence_disclosure_plan: list[FullLawyerEvidenceDisclosureItem] = Field(
        default_factory=list
    )
    settlement_negotiation_script: list[FullLawyerSettlementScriptItem] = Field(
        default_factory=list
    )
    hearing_readiness_scorecard: FullLawyerHearingReadinessScorecard = Field(
        default_factory=FullLawyerHearingReadinessScorecard
    )
    advocate_signoff_packet: FullLawyerAdvocateSignoffPacket = Field(
        default_factory=FullLawyerAdvocateSignoffPacket
    )
    warnings: list[str] = Field(default_factory=list)
    usage: dict[str, Any] = Field(default_factory=dict)


# Resolve forward refs explicitly for Pydantic v2 after schema split.
DecisionAnalysisPackageResponse.model_rebuild()
