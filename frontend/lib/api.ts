export type DocumentType = {
  doc_type: string;
  title: string;
  category: string;
  procedure: string;
};

export type DocumentHistoryItem = {
  id: string;
  title: string;
  document_type: string;
  document_category: string;
  generated_text: string;
  preview_text: string;
  ai_model: string | null;
  used_ai: boolean;
  has_docx_export: boolean;
  has_pdf_export: boolean;
  last_exported_at: string | null;
  e_court_ready: boolean;
  filing_blockers: string[];
  case_id: string | null;
  created_at: string;
};

export type DocumentsHistoryResponse = {
  user_id: string;
  total: number;
  page: number;
  page_size: number;
  pages: number;
  sort_by: string;
  sort_dir: "asc" | "desc";
  query: string | null;
  doc_type: string | null;
  has_docx_export: boolean | null;
  has_pdf_export: boolean | null;
  items: DocumentHistoryItem[];
  usage: SubscriptionResponse["usage"];
};

export type DocumentUpdateResponse = {
  status: string;
  id: string;
  has_docx_export: boolean;
  has_pdf_export: boolean;
};

export type DocumentProcessualRepairResponse = {
  status: string;
  id: string;
  repaired: boolean;
  has_docx_export: boolean;
  has_pdf_export: boolean;
  pre_generation_gate_checks: {
    code: string;
    status: string;
    message: string;
  }[];
  processual_validation_checks: {
    code: string;
    status: string;
    message: string;
  }[];
};

export type DocumentProcessualCheckResponse = {
  status: string;
  id: string;
  is_valid: boolean;
  blockers: string[];
  pre_generation_gate_checks: {
    code: string;
    status: string;
    message: string;
  }[];
  processual_validation_checks: {
    code: string;
    status: string;
    message: string;
  }[];
};

export type DocumentBulkProcessualRepairResponse = {
  status: string;
  requested: number;
  processed: number;
  repaired: number;
  missing_ids: string[];
  items: {
    id: string;
    status: string;
    repaired: boolean;
    is_valid: boolean;
    blockers: string[];
  }[];
};

export type DocumentDeleteResponse = {
  status: string;
  id: string;
};

export type DashboardStats = {
  total_documents: number;
  total_analyses: number;
  total_cases: number;
  hours_saved: number;
  recent_activity: {
    type: "document" | "forum" | "case";
    title: string;
    timestamp: string;
    id: string;
    icon: string;
    user_name?: string;
  }[];
  system_status: string;
  weekly_docs_stats: number[];
  cases_stats: Record<string, number>;
  registry_alerts: {
    id: string;
    title: string;
    severity: string;
    timestamp: string;
  }[];
};

export type DocumentBulkDeleteResponse = {
  status: string;
  requested: number;
  deleted: number;
  deleted_ids: string[];
  missing_ids: string[];
};

export type DocumentDetailResponse = {
  id: string;
  document_type: string;
  document_category: string;
  form_data: Record<string, unknown>;
  generated_text: string;
  preview_text: string;
  calculations: Record<string, unknown>;
  ai_model: string | null;
  used_ai: boolean;
  ai_error: string | null;
  has_docx_export: boolean;
  has_pdf_export: boolean;
  last_exported_at: string | null;
  e_court_ready: boolean;
  filing_blockers: string[];
  case_id: string | null;
  created_at: string;
};

export type DocumentCloneResponse = {
  status: string;
  source_id: string;
  document_id: string;
  created_at: string;
  usage: SubscriptionResponse["usage"];
};

export type DocumentVersionItem = {
  id: string;
  document_id: string;
  version_number: number;
  action: string;
  created_at: string;
};

export type DocumentVersionsResponse = {
  document_id: string;
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: DocumentVersionItem[];
};

export type DocumentVersionDetailResponse = {
  id: string;
  document_id: string;
  version_number: number;
  action: string;
  generated_text: string;
  created_at: string;
};

export type DocumentVersionDiffResponse = {
  document_id: string;
  target_version_id: string;
  target_version_number: number;
  against: string;
  against_version_number: number | null;
  diff_text: string;
  added_lines: number;
  removed_lines: number;
};

export type DocumentRestoreResponse = {
  status: string;
  id: string;
  restored_from_version_id: string;
  restored_to_version_number: number;
  has_docx_export: boolean;
  has_pdf_export: boolean;
};

export type ECourtSubmissionItem = {
  id: string;
  document_id: string | null;
  provider: string;
  external_submission_id: string;
  status: string;
  court_name: string;
  signer_method: string | null;
  tracking_url: string | null;
  error_message: string | null;
  submitted_at: string;
  updated_at: string;
};

export type ECourtSubmitResponse = {
  status: string;
  submission: ECourtSubmissionItem;
};

export type ECourtHistoryResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: ECourtSubmissionItem[];
};

export type ECourtStatusResponse = {
  submission: ECourtSubmissionItem;
};

export type RegistryWatchItem = {
  id: string;
  user_id: string;
  source: string;
  registry_type: string;
  identifier: string;
  entity_name: string;
  status: string;
  check_interval_hours: number;
  last_checked_at: string | null;
  next_check_at: string | null;
  last_change_at: string | null;
  latest_snapshot: Record<string, unknown> | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type RegistryWatchListResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: RegistryWatchItem[];
};

export type RegistryWatchCreateResponse = {
  status: string;
  item: RegistryWatchItem;
};

export type RegistryWatchCheckResponse = {
  status: string;
  item: RegistryWatchItem;
  event_id: string;
  event_type: string;
};

export type RegistryWatchDeleteResponse = {
  status: string;
  id: string;
};

export type RegistryMonitorEventItem = {
  id: string;
  watch_item_id: string;
  user_id: string;
  event_type: string;
  severity: string;
  title: string;
  details: Record<string, unknown>;
  observed_at: string;
  created_at: string;
};

export type RegistryMonitorEventsResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: RegistryMonitorEventItem[];
};

export type RegistryMonitoringStatusResponse = {
  total_watch_items: number;
  active_watch_items: number;
  due_watch_items: number;
  warning_watch_items: number;
  state_changed_events_24h: number;
  last_event_at: string | null;
  by_status: Record<string, number>;
};

export type RegistryCheckDueResponse = {
  status: string;
  scanned: number;
  checked: number;
  state_changed: number;
};

export type ForumPost = {
  id: string;
  user_id: string;
  user_name: string;
  title: string;
  content: string;
  category: string | null;
  case_id: string | null;
  created_at: string;
  comment_count: number;
};

export type ForumComment = {
  id: string;
  post_id: string;
  user_id: string;
  content: string;
  created_at: string;
};

export type KnowledgeEntry = {
  id: string;
  user_id: string;
  title: string;
  content: string;
  category: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
};

export type ForumPostDetail = ForumPost & {
  comments: ForumComment[];
};

export type DocumentsHistoryQuery = {
  page?: number;
  page_size?: number;
  query?: string;
  doc_type?: string;
  case_id?: string;
  has_docx_export?: boolean;
  has_pdf_export?: boolean;
  sort_by?: "created_at" | "document_type" | "document_category";
  sort_dir?: "asc" | "desc";
};

export type FormField = {
  key: string;
  type: string;
  required: boolean;
  options?: string[];
};

export type GenerateResponse = {
  document_id: string;
  created_at: string;
  doc_type: string;
  title: string;
  preview_text: string;
  generated_text: string;
  prompt_system: string;
  prompt_user: string;
  calculations: Record<string, string | number>;
  used_ai: boolean;
  ai_model: string;
  ai_error: string;
  quality_guard_applied: boolean;
  pre_generation_gate_checks: {
    code: string;
    status: string;
    message: string;
  }[];
  processual_validation_checks: {
    code: string;
    status: string;
    message: string;
  }[];
  case_id: string | null;
  case_law_refs: {
    id: string;
    source: string;
    decision_id: string;
    case_number: string | null;
    court_name: string | null;
    court_type: string | null;
    decision_date: string | null;
    summary: string | null;
    relevance_score: number;
  }[];
  usage: {
    id: string;
    user_id: string;
    plan: string;
    status: string;
    analyses_used: number;
    analyses_limit: number | null;
    docs_used: number;
    docs_limit: number | null;
    current_period_start: string | null;
    current_period_end: string | null;
    created_at: string | null;
    updated_at: string | null;
  };
};

export type GenerateBundleResponse = {
  bundle_id: string;
  items: GenerateResponse[];
  total_count: number;
  created_at: string;
};

export type BillingPlan = {
  code: string;
  price_usd: number;
  limits: string;
  analyses_limit: number | null;
  docs_limit: number | null;
};

export type SubscribeResponse = {
  status: string;
  plan: string;
  user_id: string;
  mode: string;
  message: string;
  usage: SubscriptionResponse["usage"];
  payment_id: string | null;
  liqpay_order_id: string | null;
  liqpay_checkout_url: string | null;
  liqpay_data: string | null;
  liqpay_signature: string | null;
  created_at: string;
};

export type SubscriptionResponse = {
  user_id: string;
  plan: string;
  status: string;
  usage: {
    id: string;
    user_id: string;
    plan: string;
    status: string;
    analyses_used: number;
    analyses_limit: number | null;
    docs_used: number;
    docs_limit: number | null;
    current_period_start: string | null;
    current_period_end: string | null;
    created_at: string | null;
    updated_at: string | null;
  };
  limits: {
    analyses_limit: number | null;
    docs_limit: number | null;
  };
};

export type DeadlineItem = {
  id: string;
  user_id: string;
  title: string;
  document_id: string | null;
  deadline_type: string | null;
  start_date: string | null;
  end_date: string | null;
  reminder_sent: boolean;
  notes: string | null;
  created_at: string;
};

export type DeadlineListResponse = {
  total: number;
  items: DeadlineItem[];
};

export type FullCalculationResult = {
  court_fee_uah: number;
  penalty_uah: number;
  process_deadline: string;
  limitation_deadline: string;
  total_claim_uah: number;
  total_with_fee_uah: number;
};

export type FullCalculationResponse = {
  status: string;
  result: FullCalculationResult;
  saved: boolean;
  calculation_id: string | null;
  created_at: string | null;
};

export type CalculationHistoryItem = {
  id: string;
  user_id: string;
  calculation_type: string;
  title: string | null;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type CalculationHistoryResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: CalculationHistoryItem[];
};

export type CalculationDetailResponse = {
  item: CalculationHistoryItem;
};

export type AutoProcessDocumentItem = {
  id: string;
  doc_type: string;
  title: string;
  created_at: string;
  preview_text: string;
  used_ai: boolean;
  ai_model: string | null;
  ai_error: string | null;
  quality_guard_applied: boolean;
  pre_generation_gate_checks: {
    code: string;
    status: string;
    message: string;
  }[];
  processual_validation_checks: {
    code: string;
    status: string;
    message: string;
  }[];
};

export type AutoProcessResponse = {
  status: string;
  source_file_name: string;
  extracted_chars: number;
  processual_only_mode: boolean;
  procedural_conclusions: string[];
  recommended_doc_types: string[];
  generated_documents: AutoProcessDocumentItem[];
  warnings: string[];
  usage: SubscriptionResponse["usage"];
};

export type DecisionAnalysisIssue = {
  topic: string;
  court_position: string;
  legal_basis: string[];
  practical_effect: string | null;
};

export type DecisionAnalysisCaseLawRef = {
  id: string;
  source: string;
  decision_id: string;
  court_name: string | null;
  court_type: string | null;
  decision_date: string | null;
  case_number: string | null;
  summary: string | null;
};

export type DecisionAnalysisStageRecommendation = {
  stage: string;
  actions: string[];
  risks: string[];
};

export type DecisionAnalysisStagePacket = {
  stage: string;
  objective: string;
  key_documents: string[];
  checklist: string[];
  exit_criteria: string[];
};

export type DecisionAnalysisSideAssessment = {
  side: string;
  opposing_side: string;
  confidence: number;
  rationale: string[];
};

export type DecisionAnalysisDefensePlanItem = {
  code: string;
  stage: string;
  goal: string;
  actions: string[];
  target_documents: string[];
};

export type DecisionAnalysisEvidenceGapItem = {
  code: string;
  title: string;
  status: string;
  detail: string;
  recommended_actions: string[];
};

export type DecisionAnalysisDocumentPreparationItem = {
  doc_type: string;
  title: string;
  purpose: string;
  priority: string;
  readiness: string;
  blockers: string[];
};

export type DecisionAnalysisPracticeCoverage = {
  total_items: number;
  distinct_courts: number;
  court_types: Record<string, number>;
  instance_levels: Record<string, number>;
  latest_decision_date: string | null;
  oldest_decision_date: string | null;
  freshness_days: number | null;
  stale: boolean;
};

export type DecisionAnalysisQualityBlock = {
  code: string;
  title: string;
  status: string;
  score: number;
  summary: string;
  details: string[];
};

export type DecisionAnalysisTraceItem = {
  claim: string;
  support_type: string;
  reference: string;
  confidence: number;
};

export type DecisionAnalysisResponse = {
  status: string;
  source_file_name: string;
  extracted_chars: number;
  dispute_summary: string;
  procedural_context: string;
  key_issues: DecisionAnalysisIssue[];
  key_questions: string[];
  side_assessment: DecisionAnalysisSideAssessment;
  defense_plan: DecisionAnalysisDefensePlanItem[];
  evidence_gaps: DecisionAnalysisEvidenceGapItem[];
  document_preparation: DecisionAnalysisDocumentPreparationItem[];
  cassation_vulnerabilities: string[];
  final_conclusion: string;
  stage_recommendations: DecisionAnalysisStageRecommendation[];
  stage_packets: DecisionAnalysisStagePacket[];
  recent_practice: DecisionAnalysisCaseLawRef[];
  practice_coverage: DecisionAnalysisPracticeCoverage;
  quality_blocks: DecisionAnalysisQualityBlock[];
  traceability: DecisionAnalysisTraceItem[];
  overall_confidence_score: number;
  quality_gate: {
    status: string;
    can_proceed_to_filing: boolean;
    blockers: string[];
    recommendations: string[];
  };
  used_ai: boolean;
  ai_model: string;
  ai_error: string;
  warnings: string[];
  usage: SubscriptionResponse["usage"];
};

export type DecisionAnalysisPackageResponse = {
  status: string;
  source_file_name: string;
  extracted_chars: number;
  selected_doc_types: string[];
  skipped_doc_types: string[];
  generated_documents: AutoProcessDocumentItem[];
  side_assessment: DecisionAnalysisSideAssessment;
  evidence_gaps_missing_count: number;
  warnings: string[];
  usage: SubscriptionResponse["usage"];
};

export type DecisionAnalysisHistoryItem = {
  id: string;
  event_type: string;
  source_file_name: string | null;
  extracted_chars: number | null;
  status: string | null;
  quality_gate_status: string | null;
  overall_confidence_score: number | null;
  practice_total: number | null;
  practice_latest_decision_date: string | null;
  format: string | null;
  has_report_snapshot: boolean;
  created_at: string;
};

export type DecisionAnalysisHistoryResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  event: string | null;
  items: DecisionAnalysisHistoryItem[];
};

export type FullLawyerSummary = {
  dispute_type: string;
  procedure: string;
  urgency: string;
  claim_amount_uah: number | null;
  estimated_court_fee_uah: number | null;
  estimated_penalty_uah: number | null;
  estimated_total_with_fee_uah: number | null;
};

export type FullLawyerValidationCheck = {
  code: string;
  status: string;
  message: string;
};

export type FullLawyerContextRef = {
  source: string;
  ref_type: string;
  reference: string;
  note: string | null;
  relevance_score: number | null;
};

export type FullLawyerWorkflowStage = {
  code: string;
  title: string;
  status: "ok" | "warn" | "blocked" | string;
  details: string[];
  metrics: Record<string, unknown>;
};

export type FullLawyerReviewItem = {
  code: string;
  title: string;
  description: string;
  required: boolean;
};

export type FullLawyerTimelineItem = {
  code: string;
  title: string;
  date: string | null;
  status: string;
  note: string | null;
};

export type FullLawyerEvidenceMatrixItem = {
  code: string;
  title: string;
  found_in_source: boolean | null;
  status: string;
  note: string | null;
};

export type FullLawyerFactChronologyItem = {
  event: string;
  event_date: string | null;
  actor: string;
  evidence_status: string;
  source_excerpt: string | null;
  relevance: string;
};

export type FullLawyerBurdenOfProofItem = {
  issue: string;
  burden_on: string;
  required_evidence: string[];
  current_status: string;
  recommended_action: string;
};

export type FullLawyerDraftingInstructionItem = {
  doc_type: string;
  must_include: string[];
  factual_focus: string[];
  legal_focus: string[];
  style_notes: string[];
  status: string;
};

export type FullLawyerOpponentWeaknessItem = {
  weakness: string;
  severity: string;
  exploitation_step: string;
  supporting_basis: string;
  evidentiary_need: string;
};

export type FullLawyerEvidenceCollectionPlanItem = {
  priority: string;
  step: string;
  owner: string;
  deadline_hint: string;
  expected_result: string;
  status: string;
};

export type FullLawyerFactualCircumstanceBlockItem = {
  section: string;
  narrative: string;
  evidence_anchor: string;
  status: string;
};

export type FullLawyerLegalQualificationBlockItem = {
  qualification: string;
  norm_reference: string;
  application_to_facts: string;
  risk_note: string;
  status: string;
};

export type FullLawyerPrayerPartVariantItem = {
  variant: string;
  request_text: string;
  grounds: string;
  priority: string;
};

export type FullLawyerCounterargumentResponseItem = {
  opponent_argument: string;
  response_strategy: string;
  evidence_focus: string;
  success_probability: string;
};

export type FullLawyerDocumentNarrativeCompletenessItem = {
  section: string;
  status: string;
  action: string;
  note: string | null;
};

export type FullLawyerCaseLawApplicationItem = {
  legal_issue: string;
  reference: string;
  application_note: string;
  strength: string;
};

export type FullLawyerProceduralViolationHypothesisItem = {
  hypothesis: string;
  legal_basis: string;
  source_signal: string;
  viability: string;
  required_proof: string;
};

export type FullLawyerDocumentFactEnrichmentItem = {
  doc_type: string;
  missing_fact_block: string;
  insert_instruction: string;
  priority: string;
  status: string;
};

export type FullLawyerHearingPositioningNoteItem = {
  theme: string;
  supporting_points: string[];
  risk_counter: string;
  courtroom_phrase: string;
};

export type FullLawyerProcessStageActionItem = {
  stage_code: string;
  stage_title: string;
  objective: string;
  actions: string[];
  trigger: string;
  status: string;
};

export type FullLawyerArgumentMapItem = {
  issue: string;
  legal_basis: string;
  litigation_goal: string;
};

export type FullLawyerReadinessBreakdown = {
  score: number;
  decision: string;
  blockers: string[];
  strengths: string[];
  metrics: Record<string, unknown>;
};

export type FullLawyerPartyProfile = {
  completion_score: number;
  risk_level: string;
  plaintiff_detected: boolean;
  defendant_detected: boolean;
  missing_items: string[];
};

export type FullLawyerJurisdictionRecommendation = {
  procedure: string;
  suggested_route: string;
  legal_basis: string[];
  confidence: number;
  required_inputs: string[];
  warning: string | null;
};

export type FullLawyerDocQualityItem = {
  doc_type: string;
  score: number;
  status: string;
  issues: string[];
};

export type FullLawyerECourtPreview = {
  can_submit: boolean;
  provider: string;
  signer_methods: string[];
  required_attachments: string[];
  blockers: string[];
  note: string | null;
};

export type FullLawyerPriorityTask = {
  priority: string;
  task: string;
  due_date: string | null;
};

export type FullLawyerConsistencyItem = {
  code: string;
  status: string;
  message: string;
};

export type FullLawyerRemedyCoverageItem = {
  remedy: string;
  covered: boolean;
  covered_by: string[];
  note: string | null;
};

export type FullLawyerCitationCaseRef = {
  source: string;
  reference: string;
  note: string | null;
};

export type FullLawyerCitationPack = {
  statutory_refs: string[];
  case_refs: FullLawyerCitationCaseRef[];
  note: string | null;
};

export type FullLawyerFeeScenarioItem = {
  name: string;
  principal_uah: number | null;
  court_fee_uah: number | null;
  penalty_uah: number | null;
  total_with_fee_uah: number | null;
  note: string | null;
};

export type FullLawyerFilingRiskItem = {
  risk: string;
  probability: number;
  impact: string;
  mitigation: string;
};

export type FullLawyerDefectItem = {
  code: string;
  severity: string;
  issue: string;
  fix: string;
};

export type FullLawyerAdmissibilityItem = {
  evidence: string;
  admissibility: string;
  relevance: string;
  risk: string;
  recommendation: string;
};

export type FullLawyerMotionItem = {
  motion_type: string;
  priority: string;
  rationale: string;
  trigger: string;
};

export type FullLawyerHearingTask = {
  phase: string;
  task: string;
  output: string;
};

export type FullLawyerPackageCompleteness = {
  status: string;
  score: number;
  generated_documents_count: number;
  missing_evidence_items: number;
  unresolved_required_review_items: number;
  note: string | null;
};

export type FullLawyerObjectionItem = {
  objection: string;
  likelihood: string;
  rebuttal: string;
};

export type FullLawyerSettlementStrategy = {
  dispute_type: string;
  window: string;
  target_amount_uah: number | null;
  recommendation: string;
  note: string | null;
};

export type FullLawyerEnforcementStep = {
  step: string;
  timing: string;
  details: string;
};

export type FullLawyerCPCComplianceItem = {
  requirement: string;
  article: string;
  status: string;
  note: string | null;
};

export type FullLawyerDocumentSectionItem = {
  section: string;
  required: boolean;
  status: string;
  note: string | null;
};

export type FullLawyerDeadlineControlItem = {
  code: string;
  title: string;
  due_date: string | null;
  status: string;
  basis: string;
  note: string | null;
};

export type FullLawyerCourtFeeBreakdown = {
  principal_uah: number | null;
  penalty_uah: number | null;
  inflation_losses_uah: number | null;
  claim_price_uah: number | null;
  court_fee_uah: number | null;
  total_with_fee_uah: number | null;
  status: string;
  note: string | null;
};

export type FullLawyerAttachmentRegisterItem = {
  name: string;
  required: boolean;
  available: boolean;
  copies_for_court: number;
  status: string;
  note: string | null;
};

export type FullLawyerCPC175RequisiteItem = {
  requisite: string;
  status: string;
  source_signal: string;
  note: string | null;
};

export type FullLawyerCPC177AttachmentGroup = {
  attachment_group: string;
  required: boolean;
  status: string;
  items_total: number;
  items_available: number;
  note: string | null;
};

export type FullLawyerPrayerPartAudit = {
  status: string;
  score: number;
  target_total_uah: number | null;
  covered_requests: string[];
  missing_requests: string[];
  note: string | null;
};

export type FullLawyerFactNormEvidenceItem = {
  fact_issue: string;
  legal_norm: string;
  evidence: string;
  status: string;
  note: string | null;
};

export type FullLawyerRedFlagItem = {
  severity: string;
  flag: string;
  action: string;
};

export type FullLawyerTextSectionAuditItem = {
  section: string;
  status: string;
  note: string | null;
};

export type FullLawyerServicePlanItem = {
  recipient: string;
  method: string;
  status: string;
  note: string | null;
};

export type FullLawyerPrayerSuggestionItem = {
  priority: string;
  suggestion: string;
  rationale: string;
};

export type FullLawyerContradictionHotspotItem = {
  issue: string;
  severity: string;
  fix: string;
};

export type FullLawyerJudgeQuestionItem = {
  question: string;
  why_it_matters: string;
  prep_answer_hint: string;
};

export type FullLawyerCitationQualityGate = {
  status: string;
  score: number;
  cpc_refs_count: number;
  case_refs_count: number;
  issues: string[];
  note: string | null;
};

export type FullLawyerFilingDecisionCard = {
  decision: string;
  confidence: number;
  readiness_score: number;
  blockers: string[];
  next_step: string;
  note: string | null;
};

export type FullLawyerProcessualLanguageAudit = {
  status: string;
  score: number;
  formal_markers_found: number;
  informal_markers_found: number;
  note: string | null;
};

export type FullLawyerEvidenceGapAction = {
  evidence: string;
  priority: string;
  action: string;
  deadline_hint: string;
};

export type FullLawyerDeadlineAlertItem = {
  title: string;
  level: string;
  days_left: number;
  recommended_action: string;
};

export type FullLawyerFilingPacketItem = {
  order: number;
  item: string;
  required: boolean;
  status: string;
  note: string | null;
};

export type FullLawyerOpponentPlaybookItem = {
  scenario: string;
  counter_step: string;
  evidence_focus: string;
};

export type FullLawyerLimitationPeriodCard = {
  status: string;
  risk: string;
  reference_date: string | null;
  limitation_deadline: string | null;
  days_remaining: number;
  note: string | null;
};

export type FullLawyerJurisdictionChallengeGuard = {
  risk_level: string;
  route: string;
  weak_points: string[];
  mitigations: string[];
  note: string | null;
};

export type FullLawyerClaimFormulaCard = {
  status: string;
  principal_uah: number;
  penalty_uah: number;
  court_fee_uah: number;
  total_claim_uah: number;
  formula: string;
  note: string | null;
};

export type FullLawyerFilingCoverLetter = {
  status: string;
  subject: string;
  recipient: string;
  body_preview: string;
  note: string | null;
};

export type FullLawyerExecutionStepItem = {
  stage: string;
  status: string;
  trigger: string;
};

export type FullLawyerVersionControlCard = {
  status: string;
  generated_documents: number;
  unique_doc_types: number;
  revision_tag: string;
  note: string | null;
};

export type FullLawyerECourtPacketReadiness = {
  status: string;
  blockers: string[];
  missing_attachments: string[];
  recommended_submit_mode: string;
  note: string | null;
};

export type FullLawyerHearingScriptItem = {
  phase: string;
  script_hint: string;
  linked_basis: string;
};

export type FullLawyerSettlementOfferCard = {
  status: string;
  target_min_uah: number;
  target_max_uah: number;
  strategy_note: string;
  fallback_position: string;
  note: string | null;
};

export type FullLawyerAppealReserveCard = {
  status: string;
  reserve_deadline: string | null;
  trigger_conditions: string[];
  note: string | null;
};

export type FullLawyerProceduralCostsAllocatorCard = {
  status: string;
  plaintiff_upfront_costs_uah: number;
  defendant_target_recovery_uah: number;
  cost_components: Record<string, number>;
  note: string | null;
};

export type FullLawyerDocumentExportReadiness = {
  status: string;
  formats: string[];
  blockers: string[];
  note: string | null;
};

export type FullLawyerSubmissionChecklistItem = {
  step: string;
  status: string;
  detail: string;
};

export type FullLawyerMonitoringBoardItem = {
  track: string;
  priority: string;
  signal: string;
};

export type FullLawyerResearchBacklogItem = {
  task: string;
  priority: string;
  expected_output: string;
};

export type FullLawyerProceduralConsistencyScorecard = {
  status: string;
  score: number;
  validation_warn_count: number;
  text_warn_count: number;
  cpc_warn_count: number;
  note: string | null;
};

export type FullLawyerHearingEvidenceOrderItem = {
  order: number;
  evidence: string;
  priority: string;
  status: string;
  note: string | null;
};

export type FullLawyerDigitalSignatureReadiness = {
  status: string;
  signer_methods: string[];
  blockers: string[];
  note: string | null;
};

export type FullLawyerCaseLawWatchItem = {
  source: string;
  reference: string;
  watch_reason: string;
};

export type FullLawyerFinalSubmissionGate = {
  status: string;
  blockers: string[];
  critical_deadlines?: string[];
  next_step: string;
  hard_stop?: boolean;
  note: string | null;
};

export type FullLawyerCourtBehaviorForecastCard = {
  stance: string;
  confidence: number;
  high_impact_risks: number;
  high_severity_flags: number;
  question_load: number;
  note: string | null;
};

export type FullLawyerEvidenceCompressionItem = {
  step: string;
  status: string;
  detail: string;
};

export type FullLawyerFilingChannelStrategyCard = {
  status: string;
  primary_channel: string;
  backup_channel: string;
  checklist_warn_count: number;
  note: string | null;
};

export type FullLawyerLegalBudgetTimelineCard = {
  timeline_mode: string;
  estimated_upfront_uah: number;
  recommended_reserve_uah: number;
  settlement_floor_uah: number;
  urgent_deadlines: number;
  note: string | null;
};

export type FullLawyerCounterpartyPressureItem = {
  vector: string;
  pressure: string;
  coverage: string;
  action: string;
};

export type FullLawyerTimelineScenarioItem = {
  scenario: string;
  probability: string;
  focus: string;
};

export type FullLawyerEvidenceAuthenticityItem = {
  evidence: string;
  status: string;
  action: string;
};

export type FullLawyerRemedyPriorityItem = {
  remedy: string;
  priority: string;
  rationale: string;
};

export type FullLawyerJudgeQuestionDrillCard = {
  complexity: string;
  rounds: number;
  question_count: number;
  hotspot_count: number;
  note: string | null;
};

export type FullLawyerClientInstructionItem = {
  instruction: string;
  priority: string;
  note: string;
};

export type FullLawyerProceduralRiskHeatItem = {
  risk: string;
  level: string;
  source: string;
};

export type FullLawyerEvidenceDisclosureItem = {
  evidence: string;
  phase: string;
  status: string;
  note: string;
};

export type FullLawyerSettlementScriptItem = {
  stage: string;
  line: string;
  goal: string;
};

export type FullLawyerHearingReadinessScorecard = {
  status: string;
  score: number;
  script_count: number;
  evidence_ready: number;
  evidence_total: number;
  drill_rounds: number;
  note: string | null;
};

export type FullLawyerAdvocateSignoffPacket = {
  status: string;
  required_checks: Array<Record<string, string>>;
  note: string | null;
};

export type FullLawyerResponse = {
  status: string;
  source_file_name: string;
  extracted_chars: number;
  processual_only_mode: boolean;
  summary: FullLawyerSummary;
  legal_basis: string[];
  strategy_steps: string[];
  evidence_required: string[];
  risks: string[];
  missing_information: string[];
  clarifying_questions: string[];
  clarification_required: boolean;
  unresolved_questions: string[];
  next_actions: string[];
  validation_checks: FullLawyerValidationCheck[];
  context_refs: FullLawyerContextRef[];
  confidence_score: number;
  analysis_highlights: string[];
  procedural_conclusions: string[];
  recommended_doc_types: string[];
  generated_documents: AutoProcessDocumentItem[];
  filing_package: {
    generated: boolean;
    status?: string;
    reason?: string | null;
    is_draft?: boolean;
    items: {
      id: string;
      doc_type: string;
      title: string;
      created_at: string;
      is_draft?: boolean;
    }[];
    checklist: string[];
  };
  processual_package_gate: {
    status: string;
    can_generate_package: boolean;
    blockers: string[];
  };
  review_checklist: FullLawyerReviewItem[];
  review_required: boolean;
  unresolved_review_items: string[];
  workflow_stages: FullLawyerWorkflowStage[];
  ready_for_filing: boolean;
  procedural_timeline: FullLawyerTimelineItem[];
  evidence_matrix: FullLawyerEvidenceMatrixItem[];
  fact_chronology_matrix: FullLawyerFactChronologyItem[];
  burden_of_proof_map: FullLawyerBurdenOfProofItem[];
  drafting_instructions: FullLawyerDraftingInstructionItem[];
  opponent_weakness_map: FullLawyerOpponentWeaknessItem[];
  evidence_collection_plan: FullLawyerEvidenceCollectionPlanItem[];
  factual_circumstances_blocks: FullLawyerFactualCircumstanceBlockItem[];
  legal_qualification_blocks: FullLawyerLegalQualificationBlockItem[];
  prayer_part_variants: FullLawyerPrayerPartVariantItem[];
  counterargument_response_matrix: FullLawyerCounterargumentResponseItem[];
  document_narrative_completeness: FullLawyerDocumentNarrativeCompletenessItem[];
  case_law_application_matrix: FullLawyerCaseLawApplicationItem[];
  procedural_violation_hypotheses: FullLawyerProceduralViolationHypothesisItem[];
  document_fact_enrichment_plan: FullLawyerDocumentFactEnrichmentItem[];
  hearing_positioning_notes: FullLawyerHearingPositioningNoteItem[];
  process_stage_action_map: FullLawyerProcessStageActionItem[];
  legal_argument_map: FullLawyerArgumentMapItem[];
  readiness_breakdown: FullLawyerReadinessBreakdown;
  post_filing_plan: string[];
  party_profile: FullLawyerPartyProfile;
  jurisdiction_recommendation: FullLawyerJurisdictionRecommendation;
  generated_docs_quality: FullLawyerDocQualityItem[];
  e_court_submission_preview: FullLawyerECourtPreview;
  priority_queue: FullLawyerPriorityTask[];
  consistency_report: FullLawyerConsistencyItem[];
  remedy_coverage: FullLawyerRemedyCoverageItem[];
  citation_pack: FullLawyerCitationPack;
  fee_scenarios: FullLawyerFeeScenarioItem[];
  filing_risk_simulation: FullLawyerFilingRiskItem[];
  procedural_defect_scan: FullLawyerDefectItem[];
  evidence_admissibility_map: FullLawyerAdmissibilityItem[];
  motion_recommendations: FullLawyerMotionItem[];
  hearing_preparation_plan: FullLawyerHearingTask[];
  package_completeness: FullLawyerPackageCompleteness;
  opponent_objections: FullLawyerObjectionItem[];
  settlement_strategy: FullLawyerSettlementStrategy;
  enforcement_plan: FullLawyerEnforcementStep[];
  cpc_compliance_check: FullLawyerCPCComplianceItem[];
  procedural_document_blueprint: FullLawyerDocumentSectionItem[];
  deadline_control: FullLawyerDeadlineControlItem[];
  court_fee_breakdown: FullLawyerCourtFeeBreakdown;
  filing_attachments_register: FullLawyerAttachmentRegisterItem[];
  cpc_175_requisites_map: FullLawyerCPC175RequisiteItem[];
  cpc_177_attachments_map: FullLawyerCPC177AttachmentGroup[];
  prayer_part_audit: FullLawyerPrayerPartAudit;
  fact_norm_evidence_chain: FullLawyerFactNormEvidenceItem[];
  pre_filing_red_flags: FullLawyerRedFlagItem[];
  text_section_audit: FullLawyerTextSectionAuditItem[];
  service_plan: FullLawyerServicePlanItem[];
  prayer_rewrite_suggestions: FullLawyerPrayerSuggestionItem[];
  contradiction_hotspots: FullLawyerContradictionHotspotItem[];
  judge_questions_simulation: FullLawyerJudgeQuestionItem[];
  citation_quality_gate: FullLawyerCitationQualityGate;
  filing_decision_card: FullLawyerFilingDecisionCard;
  processual_language_audit: FullLawyerProcessualLanguageAudit;
  evidence_gap_actions: FullLawyerEvidenceGapAction[];
  deadline_alert_board: FullLawyerDeadlineAlertItem[];
  filing_packet_order: FullLawyerFilingPacketItem[];
  opponent_response_playbook: FullLawyerOpponentPlaybookItem[];
  limitation_period_card: FullLawyerLimitationPeriodCard;
  jurisdiction_challenge_guard: FullLawyerJurisdictionChallengeGuard;
  claim_formula_card: FullLawyerClaimFormulaCard;
  filing_cover_letter: FullLawyerFilingCoverLetter;
  execution_step_tracker: FullLawyerExecutionStepItem[];
  version_control_card: FullLawyerVersionControlCard;
  e_court_packet_readiness: FullLawyerECourtPacketReadiness;
  hearing_script_pack: FullLawyerHearingScriptItem[];
  settlement_offer_card: FullLawyerSettlementOfferCard;
  appeal_reserve_card: FullLawyerAppealReserveCard;
  procedural_costs_allocator_card: FullLawyerProceduralCostsAllocatorCard;
  document_export_readiness: FullLawyerDocumentExportReadiness;
  filing_submission_checklist_card: FullLawyerSubmissionChecklistItem[];
  post_filing_monitoring_board: FullLawyerMonitoringBoardItem[];
  legal_research_backlog: FullLawyerResearchBacklogItem[];
  procedural_consistency_scorecard: FullLawyerProceduralConsistencyScorecard;
  hearing_evidence_order_card: FullLawyerHearingEvidenceOrderItem[];
  digital_signature_readiness: FullLawyerDigitalSignatureReadiness;
  case_law_update_watchlist: FullLawyerCaseLawWatchItem[];
  final_submission_gate: FullLawyerFinalSubmissionGate;
  court_behavior_forecast_card: FullLawyerCourtBehaviorForecastCard;
  evidence_pack_compression_plan: FullLawyerEvidenceCompressionItem[];
  filing_channel_strategy_card: FullLawyerFilingChannelStrategyCard;
  legal_budget_timeline_card: FullLawyerLegalBudgetTimelineCard;
  counterparty_pressure_map: FullLawyerCounterpartyPressureItem[];
  courtroom_timeline_scenarios: FullLawyerTimelineScenarioItem[];
  evidence_authenticity_checklist: FullLawyerEvidenceAuthenticityItem[];
  remedy_priority_matrix: FullLawyerRemedyPriorityItem[];
  judge_question_drill_card: FullLawyerJudgeQuestionDrillCard;
  client_instruction_packet: FullLawyerClientInstructionItem[];
  procedural_risk_heatmap: FullLawyerProceduralRiskHeatItem[];
  evidence_disclosure_plan: FullLawyerEvidenceDisclosureItem[];
  settlement_negotiation_script: FullLawyerSettlementScriptItem[];
  hearing_readiness_scorecard: FullLawyerHearingReadinessScorecard;
  advocate_signoff_packet: FullLawyerAdvocateSignoffPacket;
  warnings: string[];
  usage: SubscriptionResponse["usage"];
};

export type FullLawyerPreflightPackageHint = {
  status: string;
  can_generate_final_package: boolean;
  can_generate_draft_package: boolean;
  recommended_package_mode?: "final" | "draft" | "none" | string;
  blockers: string[];
  reason: string;
};

export type FullLawyerPreflightResponse = {
  status: string;
  source_file_name: string;
  extracted_chars: number;
  processual_only_mode: boolean;
  recommended_doc_types: string[];
  validation_checks: FullLawyerValidationCheck[];
  clarifying_questions: string[];
  unresolved_questions: string[];
  review_checklist: FullLawyerReviewItem[];
  unresolved_review_items: string[];
  deadline_control: FullLawyerDeadlineControlItem[];
  processual_package_gate: {
    status: string;
    can_generate_package: boolean;
    blockers: string[];
  };
  final_submission_gate: FullLawyerFinalSubmissionGate;
  package_generation_hint: FullLawyerPreflightPackageHint;
  next_actions: string[];
  warnings: string[];
  usage: SubscriptionResponse["usage"];
};

export type FullLawyerPreflightHistoryItem = {
  id: string;
  event_type: "upload" | "export" | string;
  source_file_name: string | null;
  extracted_chars: number | null;
  status: string | null;
  final_submission_gate_status: string | null;
  consume_quota: boolean;
  format: string | null;
  has_report_snapshot: boolean;
  created_at: string;
};

export type FullLawyerPreflightHistoryResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  event: string | null;
  items: FullLawyerPreflightHistoryItem[];
};

export type ContractAnalysisItem = {
  id: string;
  user_id: string;
  file_name: string | null;
  file_url: string | null;
  file_size: number | null;
  contract_type: string | null;
  risk_level: string | null;
  critical_risks: string[];
  medium_risks: string[];
  ok_points: string[];
  recommendations: string[];
  summary?: string;
  issues?: string[];
  ai_model: string | null;
  tokens_used: number | null;
  processing_time_ms: number | null;
  created_at: string;
  usage: SubscriptionResponse["usage"];
};

export type ContractAnalysisHistoryResponse = {
  total: number;
  items: ContractAnalysisItem[];
  usage: SubscriptionResponse["usage"];
};

export type CaseLawSearchItem = {
  id: string;
  source: string;
  decision_id: string;
  court_name: string | null;
  court_type: string | null;
  decision_date: string | null;
  case_number: string | null;
  subject_categories: string[];
  legal_positions: Record<string, unknown>;
  summary: string | null;
  reference_count: number;
};

export type CaseLawSearchResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  sort_by: string;
  sort_dir: "asc" | "desc";
  items: CaseLawSearchItem[];
};

export type CaseLawSyncResponse = {
  status: string;
  created: number;
  updated: number;
  total: number;
  sources: string[];
  seed_fallback_used: boolean;
  fetched_counts: Record<string, number>;
};

export type CaseLawSyncStatusResponse = {
  total_records: number;
  sources: Record<string, number>;
  latest_decision_date: string | null;
  oldest_decision_date: string | null;
  last_sync_at: string | null;
  last_sync_action: string | null;
  last_sync_query: string | null;
  last_sync_limit: number | null;
  last_sync_created: number | null;
  last_sync_updated: number | null;
  last_sync_total: number | null;
  last_sync_sources: string[];
  last_sync_seed_fallback_used: boolean | null;
};

export type CaseLawDigestItem = {
  id: string;
  source: string;
  decision_id: string;
  court_name: string | null;
  court_type: string | null;
  decision_date: string | null;
  case_number: string | null;
  subject_categories: string[];
  summary: string | null;
  legal_positions: Record<string, unknown>;
  prompt_snippet: string;
};

export type CaseLawDigestResponse = {
  digest_id: string | null;
  saved: boolean;
  title: string | null;
  days: number;
  limit: number;
  total: number;
  only_supreme: boolean;
  court_type: string | null;
  source: string[];
  generated_at: string;
  items: CaseLawDigestItem[];
};

export type CaseLawDigestHistoryItem = {
  id: string;
  title: string | null;
  days: number;
  limit: number;
  total: number;
  item_count: number;
  only_supreme: boolean;
  court_type: string | null;
  source: string[];
  created_at: string;
};

export type CaseLawDigestHistoryResponse = {
  total: number;
  page: number;
  page_size: number;
  pages: number;
  items: CaseLawDigestHistoryItem[];
};

export type AuditLogItem = {
  id: string;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  metadata: Record<string, unknown>;
  integrity_scope: string | null;
  integrity_prev_hash: string | null;
  integrity_hash: string | null;
  created_at: string;
};

export type AuditHistoryResponse = {
  user_id: string;
  total: number;
  page: number;
  page_size: number;
  pages: number;
  action: string | null;
  entity_type: string | null;
  query: string | null;
  items: AuditLogItem[];
};

export type AuditHistoryQuery = {
  page?: number;
  page_size?: number;
  action?: string;
  entity_type?: string;
  query?: string;
  sort_dir?: "asc" | "desc";
};

export type AuditIntegrityIssue = {
  row_id: string;
  created_at: string | null;
  code: string;
  message: string;
};

export type AuditIntegrityResponse = {
  scope: string;
  status: string;
  rows_total: number;
  rows_checked: number;
  truncated: boolean;
  head_hash: string | null;
  tail_hash: string | null;
  issues: AuditIntegrityIssue[];
  verified_at: string;
};

export type TeamUserItem = {
  user_id: string;
  email: string;
  workspace_id: string;
  role: string;
  full_name: string | null;
  company: string | null;
  created_at: string;
};

export type TeamUsersResponse = {
  workspace_id: string;
  actor_role: string;
  total: number;
  items: TeamUserItem[];
};

export type CompanyDetails = {
  name: string;
  code: string;
  status: string;
  ceo?: string;
  address?: string;
  activities?: string[];
  bankruptcy?: boolean;
  tax_debt?: number;
  is_sanctioned?: boolean;
  raw?: Record<string, unknown>;
};

function resolveApiBase(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (explicit) {
    const base = explicit.replace(/\/+$/, "");
    // If server-side (inside Docker) and targeting localhost, swap to internal "backend" service
    if (typeof window === "undefined" && (base.includes("localhost") || base.includes("127.0.0.1"))) {
      return base.replace(/localhost|127\.0\.0\.1/, "backend");
    }
    return base;
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8000";
    }
  }

  // Handle server-side inference when no environment variable is set
  if (typeof window === "undefined") {
    return "http://backend:8000";
  }

  // Safety fallback for Railway production when NEXT_PUBLIC_API_BASE_URL is missing.
  return "https://backend-production-0e53.up.railway.app";
}

const API_BASE = resolveApiBase();

type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
  demoUser?: string;
};

type ApiClientErrorInit = {
  status?: number;
  detail?: string;
  raw?: string;
  isNetwork?: boolean;
};

class ApiClientError extends Error {
  status?: number;
  detail?: string;
  raw?: string;
  isNetwork: boolean;

  constructor(message: string, init: ApiClientErrorInit = {}) {
    super(message);
    this.name = "ApiClientError";
    this.status = init.status;
    this.detail = init.detail;
    this.raw = init.raw;
    this.isNetwork = Boolean(init.isNetwork);
  }

  override toString(): string {
    return this.message;
  }
}

function stringifyDetail(detail: unknown): string {
  if (typeof detail === "string") {
    return detail.trim();
  }
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item.trim();
        if (item && typeof item === "object") {
          const record = item as Record<string, unknown>;
          const msg = typeof record.msg === "string" ? record.msg.trim() : "";
          const loc = Array.isArray(record.loc)
            ? record.loc.map((chunk) => String(chunk)).join(".")
            : "";
          return [loc, msg].filter(Boolean).join(": ");
        }
        return "";
      })
      .filter(Boolean);
    return parts.join("; ").trim();
  }
  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message.trim();
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return "";
    }
  }
  return "";
}

function localizeApiMessage(params: {
  status?: number;
  detail?: string;
  raw?: string;
  isNetwork?: boolean;
}): string {
  const status = params.status;
  const detail = (params.detail || "").trim();
  const raw = (params.raw || "").trim();
  const text = `${detail} ${raw}`.toLowerCase();

  if (params.isNetwork) {
    if (text.includes("iso-8859-1") || text.includes("headers") || text.includes("requestinit")) {
      return "Помилка заголовків запиту. Перезавантаж сторінку і спробуй ще раз.";
    }
    return "Не вдалося підключитися до сервера. Перевір з'єднання або стан backend.";
  }

  if (text.includes("insufficient_quota") || text.includes("analysis limit reached") || status === 402) {
    return "Ліміт тарифу або AI-квота вичерпано. Онови план або спробуй пізніше.";
  }
  if (text.includes("недостатньо тексту") || text.includes("not enough text")) {
    return "Недостатньо тексту для аналізу документа. Додай більш змістовний файл.";
  }
  if (text.includes("incorrect email or password") || text.includes("невірний email") || text.includes("неправильний email")) {
    return "Невірний email або пароль.";
  }
  if (text.includes("string contains non iso-8859-1 code point")) {
    return "Запит містить неприпустимі символи в заголовках. Очисть сесію і повтори.";
  }

  if (status === 401) return "Сесія завершилась або недійсна. Увійди знову.";
  if (status === 403) return "Немає доступу до цієї дії.";
  if (status === 404) return "Ресурс не знайдено.";
  if (status === 409) return "Конфлікт даних. Онови сторінку і повтори дію.";
  if (status === 422) return detail || "Помилка валідації даних. Перевір поля форми.";
  if (status === 429) return "Забагато запитів. Спробуй через хвилину.";
  if (typeof status === "number" && status >= 500) return "Сервер тимчасово недоступний. Спробуй пізніше.";

  if (detail) return detail;
  if (raw) return raw;
  if (status) return `API ${status}`;
  return "Невідома помилка запиту.";
}

function buildAuthHeaders(token?: string, demoUser?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  const normalizedToken = token?.trim();
  const normalizedDemoUser = demoUser?.trim();

  if (normalizedToken) {
    headers.Authorization = `Bearer ${normalizedToken}`;
  }

  // Demo header is only needed for unauthenticated/demo mode.
  // Browsers reject non-Latin-1 header values, so never send user-entered names here.
  if (!normalizedToken && normalizedDemoUser && /^[\x00-\x7F]+$/.test(normalizedDemoUser)) {
    headers["X-Demo-User"] = normalizedDemoUser;
  }
  return headers;
}

function buildHeaders(token?: string, demoUser?: string): HeadersInit {
  const headers = buildAuthHeaders(token, demoUser);
  headers["Content-Type"] = "application/json";
  return headers;
}

async function buildApiError(response: Response): Promise<Error> {
  const text = await response.text();
  let detail = "";

  try {
    const payload = JSON.parse(text) as { detail?: unknown };
    if (payload && "detail" in payload) {
      detail = stringifyDetail(payload.detail);
    }
  } catch {
    // Non-JSON response body, fallback to raw text.
  }

  const message = localizeApiMessage({
    status: response.status,
    detail,
    raw: text,
    isNetwork: false,
  });
  return new ApiClientError(message, { status: response.status, detail, raw: text });
}

function buildNetworkError(error: unknown): Error {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  const message = localizeApiMessage({ raw, isNetwork: true });
  return new ApiClientError(message, { raw, isNetwork: true });
}

async function safeFetch(input: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    throw buildNetworkError(error);
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string" && error.trim()) return error.trim();
  return "Невідома помилка.";
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await safeFetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: buildHeaders(options.token, options.demoUser),
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store"
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as T;
}

export async function getDocumentTypes(): Promise<DocumentType[]> {
  const data = await request<{ items: DocumentType[] }>("/api/documents/types");
  return data.items;
}

export async function getDocumentFormSchema(docType: string): Promise<FormField[]> {
  const data = await request<{ doc_type: string; schema: FormField[] }>(`/api/documents/form/${docType}`);
  return data.schema;
}

export async function getDocumentsHistory(
  params: DocumentsHistoryQuery = {},
  token?: string,
  demoUser?: string
): Promise<DocumentsHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.query?.trim()) search.set("query", params.query.trim());
  if (params.doc_type?.trim()) search.set("doc_type", params.doc_type.trim());
  if (params.case_id?.trim()) search.set("case_id", params.case_id.trim());
  if (params.has_docx_export !== undefined) search.set("has_docx_export", String(params.has_docx_export));
  if (params.has_pdf_export !== undefined) search.set("has_pdf_export", String(params.has_pdf_export));
  if (params.sort_by) search.set("sort_by", params.sort_by);
  if (params.sort_dir) search.set("sort_dir", params.sort_dir);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<DocumentsHistoryResponse>(`/api/documents/history${suffix}`, { token, demoUser });
}

export async function updateDocument(
  documentId: string,
  generatedText: string,
  token?: string,
  demoUser?: string,
  caseId?: string
): Promise<DocumentUpdateResponse> {
  return request<DocumentUpdateResponse>(`/api/documents/${documentId}`, {
    method: "PATCH",
    body: { generated_text: generatedText, case_id: caseId },
    token,
    demoUser
  });
}

export async function repairProcessualDocument(
  documentId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentProcessualRepairResponse> {
  return request<DocumentProcessualRepairResponse>(`/api/documents/${documentId}/processual-repair`, {
    method: "POST",
    token,
    demoUser
  });
}

export async function getDocumentProcessualCheck(
  documentId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentProcessualCheckResponse> {
  return request<DocumentProcessualCheckResponse>(`/api/documents/${documentId}/processual-check`, {
    token,
    demoUser
  });
}

export async function bulkRepairProcessualDocuments(
  ids: string[],
  token?: string,
  demoUser?: string
): Promise<DocumentBulkProcessualRepairResponse> {
  return request<DocumentBulkProcessualRepairResponse>("/api/documents/bulk-processual-repair", {
    method: "POST",
    body: { ids },
    token,
    demoUser
  });
}

export async function getDocumentDetail(
  documentId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentDetailResponse> {
  return request<DocumentDetailResponse>(`/api/documents/${documentId}`, { token, demoUser });
}

export async function cloneDocument(
  documentId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentCloneResponse> {
  return request<DocumentCloneResponse>(`/api/documents/${documentId}/clone`, {
    method: "POST",
    token,
    demoUser
  });
}

export async function getDocumentVersions(
  documentId: string,
  page: number = 1,
  pageSize: number = 20,
  token?: string,
  demoUser?: string
): Promise<DocumentVersionsResponse> {
  return request<DocumentVersionsResponse>(
    `/api/documents/${documentId}/versions?page=${page}&page_size=${pageSize}`,
    { token, demoUser }
  );
}

export async function getDocumentVersionDetail(
  documentId: string,
  versionId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentVersionDetailResponse> {
  return request<DocumentVersionDetailResponse>(`/api/documents/${documentId}/versions/${versionId}`, { token, demoUser });
}

export async function getDocumentVersionDiff(
  documentId: string,
  versionId: string,
  against: string = "current",
  token?: string,
  demoUser?: string
): Promise<DocumentVersionDiffResponse> {
  const encodedAgainst = encodeURIComponent(against);
  return request<DocumentVersionDiffResponse>(`/api/documents/${documentId}/versions/${versionId}/diff?against=${encodedAgainst}`, {
    token,
    demoUser
  });
}

export async function restoreDocumentVersion(
  documentId: string,
  versionId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentRestoreResponse> {
  return request<DocumentRestoreResponse>(`/api/documents/${documentId}/versions/${versionId}/restore`, {
    method: "POST",
    token,
    demoUser
  });
}

export async function submitToECourt(
  payload: {
    document_id: string;
    court_name: string;
    signer_method?: string;
    note?: string;
  },
  token?: string,
  demoUser?: string
): Promise<ECourtSubmitResponse> {
  return request<ECourtSubmitResponse>("/api/e-court/submit", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getECourtHistory(
  params: {
    page?: number;
    page_size?: number;
    status?: string;
  } = {},
  token?: string,
  demoUser?: string
): Promise<ECourtHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.status?.trim()) search.set("status", params.status.trim());
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<ECourtHistoryResponse>(`/api/e-court/history${suffix}`, { token, demoUser });
}

export async function getECourtStatus(
  submissionId: string,
  token?: string,
  demoUser?: string
): Promise<ECourtStatusResponse> {
  return request<ECourtStatusResponse>(`/api/e-court/${submissionId}/status`, { token, demoUser });
}

export async function createRegistryWatchItem(
  payload: {
    source?: string;
    registry_type: string;
    identifier: string;
    entity_name: string;
    check_interval_hours?: number;
    notes?: string;
  },
  token?: string,
  demoUser?: string
): Promise<RegistryWatchCreateResponse> {
  return request<RegistryWatchCreateResponse>("/api/monitoring/watch-items", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getRegistryWatchItems(
  params: {
    page?: number;
    page_size?: number;
    registry_type?: string;
    status?: string;
    query?: string;
  } = {},
  token?: string,
  demoUser?: string
): Promise<RegistryWatchListResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.registry_type?.trim()) search.set("registry_type", params.registry_type.trim());
  if (params.status?.trim()) search.set("status", params.status.trim());
  if (params.query?.trim()) search.set("query", params.query.trim());
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<RegistryWatchListResponse>(`/api/monitoring/watch-items${suffix}`, { token, demoUser });
}

export async function checkRegistryWatchItem(
  watchItemId: string,
  payload: {
    observed_status?: string;
    summary?: string;
    details?: Record<string, unknown>;
  } = {},
  token?: string,
  demoUser?: string
): Promise<RegistryWatchCheckResponse> {
  return request<RegistryWatchCheckResponse>(`/api/monitoring/watch-items/${watchItemId}/check`, {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function deleteRegistryWatchItem(
  watchItemId: string,
  token?: string,
  demoUser?: string
): Promise<RegistryWatchDeleteResponse> {
  return request<RegistryWatchDeleteResponse>(`/api/monitoring/watch-items/${watchItemId}`, {
    method: "DELETE",
    token,
    demoUser
  });
}

export async function getRegistryMonitorEvents(
  params: {
    page?: number;
    page_size?: number;
    watch_item_id?: string;
    severity?: string;
    event_type?: string;
  } = {},
  token?: string,
  demoUser?: string
): Promise<RegistryMonitorEventsResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.watch_item_id?.trim()) search.set("watch_item_id", params.watch_item_id.trim());
  if (params.severity?.trim()) search.set("severity", params.severity.trim());
  if (params.event_type?.trim()) search.set("event_type", params.event_type.trim());
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<RegistryMonitorEventsResponse>(`/api/monitoring/events${suffix}`, { token, demoUser });
}

export async function getRegistryMonitoringStatus(
  token?: string,
  demoUser?: string
): Promise<RegistryMonitoringStatusResponse> {
  return request<RegistryMonitoringStatusResponse>("/api/monitoring/status", { token, demoUser });
}

export async function runRegistryCheckDue(
  payload: { limit?: number } = {},
  token?: string,
  demoUser?: string
): Promise<RegistryCheckDueResponse> {
  return request<RegistryCheckDueResponse>("/api/monitoring/check-due", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function deleteDocument(
  documentId: string,
  token?: string,
  demoUser?: string
): Promise<DocumentDeleteResponse> {
  return request<DocumentDeleteResponse>(`/api/documents/${documentId}`, {
    method: "DELETE",
    token,
    demoUser
  });
}

export async function bulkDeleteDocuments(
  ids: string[],
  token?: string,
  demoUser?: string
): Promise<DocumentBulkDeleteResponse> {
  return request<DocumentBulkDeleteResponse>("/api/documents/bulk-delete", {
    method: "POST",
    body: { ids },
    token,
    demoUser
  });
}

export async function getCompanyByCode(
  code: string,
  token?: string,
  demoUser?: string
): Promise<CompanyDetails> {
  return request<CompanyDetails>(`/api/opendatabot/company/${code}`, {
    token,
    demoUser
  });
}

export async function exportDocumentsHistory(
  format: "csv" | "zip",
  params: Omit<DocumentsHistoryQuery, "page" | "page_size"> = {},
  token?: string,
  demoUser?: string
): Promise<Blob> {
  const search = new URLSearchParams();
  search.set("format", format);
  if (params.query?.trim()) search.set("query", params.query.trim());
  if (params.doc_type?.trim()) search.set("doc_type", params.doc_type.trim());
  if (params.has_docx_export !== undefined) search.set("has_docx_export", String(params.has_docx_export));
  if (params.has_pdf_export !== undefined) search.set("has_pdf_export", String(params.has_pdf_export));
  if (params.sort_by) search.set("sort_by", params.sort_by);
  if (params.sort_dir) search.set("sort_dir", params.sort_dir);

  const response = await safeFetch(`${API_BASE}/api/documents/history/export?${search.toString()}`, {
    method: "GET",
    headers: buildAuthHeaders(token, demoUser),
    cache: "no-store"
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return response.blob();
}

export async function generateDocument(
  docType: string,
  formData: Record<string, unknown>,
  tariff: string,
  token?: string,
  demoUser?: string,
  options?: {
    extra_prompt_context?: string;
    saved_digest_id?: string;
    include_digest?: boolean;
    digest_days?: number;
    digest_limit?: number;
    digest_only_supreme?: boolean;
    digest_court_type?: string;
    digest_source?: string[];
    mode?: string;
    case_id?: string;
    style?: string;
    precedent_ids?: string[];
    bundle_doc_types?: string[];
  }
): Promise<GenerateResponse | GenerateBundleResponse> {
  return request<GenerateResponse | GenerateBundleResponse>("/api/documents/generate", {
    method: "POST",
    body: {
      doc_type: docType,
      form_data: formData,
      tariff,
      ...options
    },
    token,
    demoUser
  });
}

export async function getBillingPlans(): Promise<BillingPlan[]> {
  const data = await request<{ items: BillingPlan[] }>("/api/billing/plans");
  return data.items;
}

export async function getCurrentSubscription(token?: string, demoUser?: string): Promise<SubscriptionResponse> {
  return request<SubscriptionResponse>("/api/billing/subscription", { token, demoUser });
}

export async function autoProcessDocument(
  payload: {
    file: File;
    max_documents?: number;
    processual_only?: boolean;
  },
  onEvent: (data: any) => void,
  token?: string,
  demoUser?: string
): Promise<AutoProcessResponse> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.max_documents !== undefined) {
    form.append("max_documents", String(payload.max_documents));
  }
  if (payload.processual_only !== undefined) {
    form.append("processual_only", String(payload.processual_only));
  }

  const response = await safeFetch(`${API_BASE}/api/auto/process-stream`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }

  if (!response.body) {
    throw new ApiClientError("Сервер не повернув потік даних.", { raw: "No response body" });
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let finalResult: AutoProcessResponse | null = null;
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const dataStr = line.slice(6).trim();
        if (!dataStr) continue;
        try {
          const parsed = JSON.parse(dataStr);
          onEvent(parsed);

          if (parsed.step === "generation" && parsed.status === "done" && parsed.result) {
            finalResult = parsed.result;
          }
        } catch (e) {
          console.error("Failed to parse SSE JSON", e);
        }
      }
    }
  }

  if (buffer.startsWith("data: ")) {
    try {
      const parsed = JSON.parse(buffer.slice(6).trim());
      onEvent(parsed);
      if (parsed.step === "generation" && parsed.status === "done" && parsed.result) {
        finalResult = parsed.result;
      }
    } catch (e) {
      // ignore
    }
  }

  if (!finalResult) {
    throw new ApiClientError("Потік завершився без фінального результату.", { raw: "Stream closed without final result." });
  }

  return finalResult;
}

export async function autoProcessDecisionAnalysis(
  payload: {
    file: File;
    include_recent_case_law?: boolean;
    case_law_days?: number;
    case_law_limit?: number;
    case_law_court_type?: string;
    case_law_source?: string;
    only_supreme_case_law?: boolean;
    ai_enhance?: boolean;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<DecisionAnalysisResponse> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.include_recent_case_law !== undefined) {
    form.append("include_recent_case_law", String(payload.include_recent_case_law));
  }
  if (payload.case_law_days !== undefined) {
    form.append("case_law_days", String(payload.case_law_days));
  }
  if (payload.case_law_limit !== undefined) {
    form.append("case_law_limit", String(payload.case_law_limit));
  }
  if (payload.case_law_court_type?.trim()) {
    form.append("case_law_court_type", payload.case_law_court_type.trim());
  }
  if (payload.case_law_source?.trim()) {
    form.append("case_law_source", payload.case_law_source.trim());
  }
  if (payload.only_supreme_case_law !== undefined) {
    form.append("only_supreme_case_law", String(payload.only_supreme_case_law));
  }
  if (payload.ai_enhance !== undefined) {
    form.append("ai_enhance", String(payload.ai_enhance));
  }
  if (payload.case_id?.trim()) {
    form.append("case_id", payload.case_id.trim());
  }

  const response = await safeFetch(`${API_BASE}/api/auto/decision-analysis`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as DecisionAnalysisResponse;
}

export async function exportDecisionAnalysisReport(
  payload: {
    file: File;
    format: "pdf" | "docx";
    include_recent_case_law?: boolean;
    case_law_days?: number;
    case_law_limit?: number;
    case_law_court_type?: string;
    case_law_source?: string;
    only_supreme_case_law?: boolean;
    ai_enhance?: boolean;
    consume_quota?: boolean;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<Blob> {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("format", payload.format);
  if (payload.include_recent_case_law !== undefined) {
    form.append("include_recent_case_law", String(payload.include_recent_case_law));
  }
  if (payload.case_law_days !== undefined) {
    form.append("case_law_days", String(payload.case_law_days));
  }
  if (payload.case_law_limit !== undefined) {
    form.append("case_law_limit", String(payload.case_law_limit));
  }
  if (payload.case_law_court_type?.trim()) {
    form.append("case_law_court_type", payload.case_law_court_type.trim());
  }
  if (payload.case_law_source?.trim()) {
    form.append("case_law_source", payload.case_law_source.trim());
  }
  if (payload.only_supreme_case_law !== undefined) {
    form.append("only_supreme_case_law", String(payload.only_supreme_case_law));
  }
  if (payload.ai_enhance !== undefined) {
    form.append("ai_enhance", String(payload.ai_enhance));
  }
  if (payload.consume_quota !== undefined) {
    form.append("consume_quota", String(payload.consume_quota));
  }
  if (payload.case_id?.trim()) {
    form.append("case_id", payload.case_id.trim());
  }

  const response = await safeFetch(`${API_BASE}/api/auto/decision-analysis/export`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return response.blob();
}

export async function getDecisionAnalysisHistory(
  params: {
    page?: number;
    page_size?: number;
    event?: "all" | "upload" | "export";
  } = {},
  token?: string,
  demoUser?: string
): Promise<DecisionAnalysisHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.event) search.set("event", params.event);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<DecisionAnalysisHistoryResponse>(`/api/auto/decision-analysis/history${suffix}`, { token, demoUser });
}

export async function exportDecisionAnalysisHistoryReport(
  auditId: string,
  format: "pdf" | "docx",
  token?: string,
  demoUser?: string
): Promise<Blob> {
  const response = await safeFetch(`${API_BASE}/api/auto/decision-analysis/history/${auditId}/export?format=${format}`, {
    method: "GET",
    headers: buildAuthHeaders(token, demoUser),
    cache: "no-store"
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return response.blob();
}

export async function autoProcessDecisionAnalysisPackage(
  payload: {
    file: File;
    max_documents?: number;
    include_warn_readiness?: boolean;
    include_recent_case_law?: boolean;
    case_law_days?: number;
    case_law_limit?: number;
    case_law_court_type?: string;
    case_law_source?: string;
    only_supreme_case_law?: boolean;
    ai_enhance?: boolean;
    consume_analysis_quota?: boolean;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<DecisionAnalysisPackageResponse> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.max_documents !== undefined) {
    form.append("max_documents", String(payload.max_documents));
  }
  if (payload.include_warn_readiness !== undefined) {
    form.append("include_warn_readiness", String(payload.include_warn_readiness));
  }
  if (payload.include_recent_case_law !== undefined) {
    form.append("include_recent_case_law", String(payload.include_recent_case_law));
  }
  if (payload.case_law_days !== undefined) {
    form.append("case_law_days", String(payload.case_law_days));
  }
  if (payload.case_law_limit !== undefined) {
    form.append("case_law_limit", String(payload.case_law_limit));
  }
  if (payload.case_law_court_type?.trim()) {
    form.append("case_law_court_type", payload.case_law_court_type.trim());
  }
  if (payload.case_law_source?.trim()) {
    form.append("case_law_source", payload.case_law_source.trim());
  }
  if (payload.only_supreme_case_law !== undefined) {
    form.append("only_supreme_case_law", String(payload.only_supreme_case_law));
  }
  if (payload.ai_enhance !== undefined) {
    form.append("ai_enhance", String(payload.ai_enhance));
  }
  if (payload.consume_analysis_quota !== undefined) {
    form.append("consume_analysis_quota", String(payload.consume_analysis_quota));
  }
  if (payload.case_id?.trim()) {
    form.append("case_id", payload.case_id.trim());
  }

  const response = await safeFetch(`${API_BASE}/api/auto/decision-analysis/package`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as DecisionAnalysisPackageResponse;
}

export async function autoProcessFullLawyer(
  payload: {
    file: File;
    max_documents?: number;
    processual_only?: boolean;
    clarifications_json?: Record<string, string>;
    review_confirmations_json?: Record<string, boolean>;
    generate_package?: boolean;
    generate_package_draft_on_hard_stop?: boolean;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<FullLawyerResponse> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.max_documents !== undefined) {
    form.append("max_documents", String(payload.max_documents));
  }
  if (payload.processual_only !== undefined) {
    form.append("processual_only", String(payload.processual_only));
  }
  if (payload.clarifications_json !== undefined) {
    form.append("clarifications_json", JSON.stringify(payload.clarifications_json));
  }
  if (payload.review_confirmations_json !== undefined) {
    form.append("review_confirmations_json", JSON.stringify(payload.review_confirmations_json));
  }
  if (payload.generate_package !== undefined) {
    form.append("generate_package", String(payload.generate_package));
  }
  if (payload.generate_package_draft_on_hard_stop !== undefined) {
    form.append("generate_package_draft_on_hard_stop", String(payload.generate_package_draft_on_hard_stop));
  }
  if (payload.case_id?.trim()) {
    form.append("case_id", payload.case_id.trim());
  }

  const response = await safeFetch(`${API_BASE}/api/auto/full-lawyer`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as FullLawyerResponse;
}

export async function autoProcessFullLawyerPreflight(
  payload: {
    file: File;
    max_documents?: number;
    processual_only?: boolean;
    clarifications_json?: Record<string, string>;
    review_confirmations_json?: Record<string, boolean>;
    consume_quota?: boolean;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<FullLawyerPreflightResponse> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.max_documents !== undefined) {
    form.append("max_documents", String(payload.max_documents));
  }
  if (payload.processual_only !== undefined) {
    form.append("processual_only", String(payload.processual_only));
  }
  if (payload.clarifications_json !== undefined) {
    form.append("clarifications_json", JSON.stringify(payload.clarifications_json));
  }
  if (payload.review_confirmations_json !== undefined) {
    form.append("review_confirmations_json", JSON.stringify(payload.review_confirmations_json));
  }
  if (payload.consume_quota !== undefined) {
    form.append("consume_quota", String(payload.consume_quota));
  }
  if (payload.case_id?.trim()) {
    form.append("case_id", payload.case_id.trim());
  }

  const response = await safeFetch(`${API_BASE}/api/auto/full-lawyer/preflight`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as FullLawyerPreflightResponse;
}

export async function exportFullLawyerPreflightReport(
  payload: {
    file: File;
    format: "pdf" | "docx";
    max_documents?: number;
    processual_only?: boolean;
    clarifications_json?: Record<string, string>;
    review_confirmations_json?: Record<string, boolean>;
    consume_quota?: boolean;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<Blob> {
  const form = new FormData();
  form.append("file", payload.file);
  form.append("format", payload.format);
  if (payload.max_documents !== undefined) {
    form.append("max_documents", String(payload.max_documents));
  }
  if (payload.processual_only !== undefined) {
    form.append("processual_only", String(payload.processual_only));
  }
  if (payload.clarifications_json !== undefined) {
    form.append("clarifications_json", JSON.stringify(payload.clarifications_json));
  }
  if (payload.review_confirmations_json !== undefined) {
    form.append("review_confirmations_json", JSON.stringify(payload.review_confirmations_json));
  }
  if (payload.consume_quota !== undefined) {
    form.append("consume_quota", String(payload.consume_quota));
  }
  if (payload.case_id?.trim()) {
    form.append("case_id", payload.case_id.trim());
  }

  const response = await safeFetch(`${API_BASE}/api/auto/full-lawyer/preflight/export`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store"
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return response.blob();
}

export async function getFullLawyerPreflightHistory(
  params: {
    page?: number;
    page_size?: number;
    event?: "all" | "upload" | "export";
  } = {},
  token?: string,
  demoUser?: string
): Promise<FullLawyerPreflightHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.event) search.set("event", params.event);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<FullLawyerPreflightHistoryResponse>(`/api/auto/full-lawyer/preflight/history${suffix}`, { token, demoUser });
}

export async function exportFullLawyerPreflightHistoryReport(
  auditId: string,
  format: "pdf" | "docx",
  token?: string,
  demoUser?: string
): Promise<Blob> {
  const response = await safeFetch(`${API_BASE}/api/auto/full-lawyer/preflight/history/${auditId}/export?format=${format}`, {
    method: "GET",
    headers: buildAuthHeaders(token, demoUser),
    cache: "no-store"
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return response.blob();
}

export async function calculateFullClaim(
  payload: {
    claim_amount_uah: number;
    principal_uah: number;
    debt_start_date: string;
    debt_end_date: string;
    process_start_date: string;
    process_days?: number;
    violation_date: string;
    limitation_years?: number;
    court_fee_rate?: number;
    court_fee_min_uah?: number;
    annual_penalty_rate?: number;
    save?: boolean;
    title?: string;
    notes?: string;
  },
  token?: string,
  demoUser?: string
): Promise<FullCalculationResponse> {
  return request<FullCalculationResponse>("/api/calculate/full", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getCalculationHistory(
  params: {
    page?: number;
    page_size?: number;
    calculation_type?: string;
  } = {},
  token?: string,
  demoUser?: string
): Promise<CalculationHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.calculation_type?.trim()) search.set("calculation_type", params.calculation_type.trim());
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<CalculationHistoryResponse>(`/api/calculate/history${suffix}`, { token, demoUser });
}

export async function getCalculationDetail(
  calculationId: string,
  token?: string,
  demoUser?: string
): Promise<CalculationDetailResponse> {
  return request<CalculationDetailResponse>(`/api/calculate/${calculationId}`, { token, demoUser });
}

export async function subscribePlan(
  plan: string,
  mode: "subscription" | "pay_per_use",
  token?: string,
  demoUser?: string
): Promise<SubscribeResponse> {
  return request<SubscribeResponse>("/api/billing/subscribe", {
    method: "POST",
    body: { plan, mode },
    token,
    demoUser
  });
}

export async function getAuthMe(
  token?: string,
  demoUser?: string
): Promise<{ user_id: string; email: string; workspace_id: string; role: string }> {
  return request<{ user_id: string; email: string; workspace_id: string; role: string }>("/api/auth/me", { token, demoUser });
}

export async function getTeamUsers(token?: string, demoUser?: string): Promise<TeamUsersResponse> {
  return request<TeamUsersResponse>("/api/auth/team/users", { token, demoUser });
}

export async function updateTeamUserRole(
  payload: {
    target_user_id: string;
    role: string;
    email?: string;
    full_name?: string;
    company?: string;
  },
  token?: string,
  demoUser?: string
): Promise<{ status: string; item: TeamUserItem }> {
  return request<{ status: string; item: TeamUserItem }>("/api/auth/team/users/role", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getDeadlines(token?: string, demoUser?: string): Promise<DeadlineListResponse> {
  return request<DeadlineListResponse>("/api/deadlines", { token, demoUser });
}

export async function createDeadline(
  payload: {
    title: string;
    deadline_type?: string;
    start_date?: string;
    end_date?: string;
    notes?: string;
    document_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<DeadlineItem> {
  return request<DeadlineItem>("/api/deadlines", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function processContractAnalysis(
  payload: {
    contract_text: string;
    mode?: string;
    file_name?: string;
    file_url?: string;
    file_size?: number;
  },
  token?: string,
  demoUser?: string
): Promise<ContractAnalysisItem> {
  return request<ContractAnalysisItem>("/api/analyze/process", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getContractAnalysisHistory(
  token?: string,
  demoUser?: string
): Promise<ContractAnalysisHistoryResponse> {
  return request<ContractAnalysisHistoryResponse>("/api/analyze/history", { token, demoUser });
}

export async function getContractAnalysis(
  analysisId: string,
  token?: string,
  demoUser?: string
): Promise<ContractAnalysisItem> {
  return request<ContractAnalysisItem>(`/api/analyze/${analysisId}`, { token, demoUser });
}

export async function deleteContractAnalysis(
  analysisId: string,
  token?: string,
  demoUser?: string
): Promise<{ status: string; id: string }> {
  return request<{ status: string; id: string }>(`/api/analyze/${analysisId}`, {
    method: "DELETE",
    token,
    demoUser
  });
}

export async function exportDocument(
  documentId: string,
  format: "docx" | "pdf",
  report = false,
  token?: string,
  demoUser?: string
): Promise<Blob> {
  const response = await safeFetch(`${API_BASE}/api/documents/${documentId}/export?format=${format}&report=${String(report)}`, {
    method: "GET",
    headers: buildAuthHeaders(token, demoUser),
    cache: "no-store"
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return response.blob();
}

export async function searchCaseLaw(
  params: {
    query?: string;
    court_type?: string;
    only_supreme?: boolean;
    source?: string;
    tags?: string;
    date_from?: string;
    date_to?: string;
    fresh_days?: number;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_dir?: "asc" | "desc";
  } = {},
  token?: string,
  demoUser?: string
): Promise<CaseLawSearchResponse> {
  const search = new URLSearchParams();
  if (params.query) search.set("query", params.query);
  if (params.court_type) search.set("court_type", params.court_type);
  if (params.only_supreme !== undefined) search.set("only_supreme", String(params.only_supreme));
  if (params.source) search.set("source", params.source);
  if (params.tags) search.set("tags", params.tags);
  if (params.date_from) search.set("date_from", params.date_from);
  if (params.date_to) search.set("date_to", params.date_to);
  if (params.fresh_days) search.set("fresh_days", String(params.fresh_days));
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.sort_by) search.set("sort_by", params.sort_by);
  if (params.sort_dir) search.set("sort_dir", params.sort_dir);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<CaseLawSearchResponse>(`/api/case-law/search${suffix}`, { token, demoUser });
}

export async function getCaseLawDigest(
  params: {
    days?: number;
    limit?: number;
    court_type?: string;
    source?: string;
    only_supreme?: boolean;
  } = {},
  token?: string,
  demoUser?: string
): Promise<CaseLawDigestResponse> {
  const search = new URLSearchParams();
  if (params.days) search.set("days", String(params.days));
  if (params.limit) search.set("limit", String(params.limit));
  if (params.court_type) search.set("court_type", params.court_type);
  if (params.source) search.set("source", params.source);
  if (params.only_supreme !== undefined) search.set("only_supreme", String(params.only_supreme));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<CaseLawDigestResponse>(`/api/case-law/digest${suffix}`, { token, demoUser });
}

export async function generateCaseLawDigest(
  payload: {
    days?: number;
    limit?: number;
    court_type?: string;
    source?: string[];
    only_supreme?: boolean;
    save?: boolean;
    title?: string;
  } = {},
  token?: string,
  demoUser?: string
): Promise<CaseLawDigestResponse> {
  return request<CaseLawDigestResponse>("/api/case-law/digest/generate", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getCaseLawDigestHistory(
  params: { page?: number; page_size?: number } = {},
  token?: string,
  demoUser?: string
): Promise<CaseLawDigestHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<CaseLawDigestHistoryResponse>(`/api/case-law/digest/history${suffix}`, { token, demoUser });
}

export async function getCaseLawDigestDetail(
  digestId: string,
  token?: string,
  demoUser?: string
): Promise<CaseLawDigestResponse> {
  return request<CaseLawDigestResponse>(`/api/case-law/digest/history/${digestId}`, { token, demoUser });
}

export async function importCaseLaw(
  records: Array<{
    source?: string;
    decision_id: string;
    court_name?: string;
    court_type?: string;
    decision_date?: string;
    case_number?: string;
    subject_categories?: string[];
    legal_positions?: Record<string, unknown>;
    full_text?: string;
    summary?: string;
  }>,
  token?: string,
  demoUser?: string
): Promise<{ created: number; updated: number; total: number }> {
  return request<{ created: number; updated: number; total: number }>("/api/case-law/import", {
    method: "POST",
    body: { records },
    token,
    demoUser
  });
}

export async function syncCaseLaw(
  payload: { query?: string; limit?: number; sources?: string[]; allow_seed_fallback?: boolean } = {},
  token?: string,
  demoUser?: string
): Promise<CaseLawSyncResponse> {
  return request<CaseLawSyncResponse>("/api/case-law/sync", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getCaseLawSyncStatus(token?: string, demoUser?: string): Promise<CaseLawSyncStatusResponse> {
  return request<CaseLawSyncStatusResponse>("/api/case-law/sync/status", { token, demoUser });
}

export async function deleteKnowledgeEntry(entryId: string, token?: string, demoUser?: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/knowledge-base/${entryId}`, { method: "DELETE", token, demoUser });
}

export * from "./api/core";
export * from "./api/cases";

export async function globalSearch(q: string, token?: string, demoUser?: string): Promise<GlobalSearchResponse> {
  return request<GlobalSearchResponse>(`/api/dashboard/search?q=${encodeURIComponent(q)}`, { token, demoUser });
}

export type GlobalSearchResponse = {
  cases: Array<{ id: string, title: string, number: string | null }>;
  documents: Array<{ id: string, type: string, preview: string }>;
  forum: Array<{ id: string, title: string }>;
};

export async function getUserInfo(
  token?: string,
  demoUser?: string
): Promise<{ user_id: string; email: string; workspace_id: string; role: string; full_name?: string; company?: string; logo_url?: string; entity_type?: string; tax_id?: string; address?: string; phone?: string; }> {
  return request("/api/auth/me", { token, demoUser });
}

export async function updateUserInfo(
  payload: { logo_url?: string; full_name?: string; company?: string; entity_type?: string; tax_id?: string; address?: string; phone?: string; },
  token?: string,
  demoUser?: string
): Promise<{ status: string }> {
  return request<{ status: string }>("/api/auth/me", {
    method: "PATCH",
    body: payload,
    token,
    demoUser
  });
}

export async function getAuditHistory(
  params: AuditHistoryQuery = {},
  token?: string,
  demoUser?: string
): Promise<AuditHistoryResponse> {
  const search = new URLSearchParams();
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  if (params.action?.trim()) search.set("action", params.action.trim());
  if (params.entity_type?.trim()) search.set("entity_type", params.entity_type.trim());
  if (params.query?.trim()) search.set("query", params.query.trim());
  if (params.sort_dir) search.set("sort_dir", params.sort_dir);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<AuditHistoryResponse>(`/api/audit/history${suffix}`, { token, demoUser });
}

export async function getAuditIntegrity(
  params: { max_rows?: number } = {},
  token?: string,
  demoUser?: string
): Promise<AuditIntegrityResponse> {
  const search = new URLSearchParams();
  if (params.max_rows) search.set("max_rows", String(params.max_rows));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<AuditIntegrityResponse>(`/api/audit/integrity${suffix}`, { token, demoUser });
}

export type DocumentIntakeIssueItem = {
  issue_type: string;
  severity: string;
  description: string;
  impact: string;
  snippet?: string;
  start_index?: number;
  end_index?: number;
};


export type DocumentIntakeResponse = {
  id: string;
  user_id: string;
  source_file_name: string | null;
  classified_type: string;
  document_language: string | null;
  jurisdiction: string;
  primary_party_role: string | null;
  identified_parties: Array<Record<string, string>>;
  subject_matter: string | null;
  financial_exposure_amount: number | null;
  financial_exposure_currency: string | null;
  financial_exposure_type: string | null;
  document_date: string | null;
  deadline_from_document: string | null;
  urgency_level: string | null;
  risk_level_legal: string | null;
  risk_level_procedural: string | null;
  risk_level_financial: string | null;
  detected_issues: DocumentIntakeIssueItem[];
  classifier_confidence: number | null;
  classifier_model: string | null;
  raw_text_preview: string | null;
  created_at: string;
  usage: SubscriptionResponse["usage"];
};

export type PrecedentGroupItem = {
  id: string;
  pattern_type: string;
  pattern_description: string | null;
  precedent_ids: string[];
  precedent_count: number;
  pattern_strength: number | null;
  counter_arguments: string[];
  mitigation_strategy: string | null;
  strategic_advantage: string | null;
  vulnerability_to_appeal: string | null;
  created_at: string;
};

export type PrecedentMapRefItem = {
  id: string;
  source: string;
  decision_id: string;
  case_number: string | null;
  court_name: string | null;
  decision_date: string | null;
  summary: string | null;
  pattern_type: string;
  relevance_score: number;
};

export type PrecedentMapResponse = {
  intake_id: string;
  query_used: string;
  groups: PrecedentGroupItem[];
  refs: PrecedentMapRefItem[];
};

export type StrategyBlueprintResponse = {
  id: string;
  intake_id: string;
  precedent_group_id: string | null;
  immediate_actions: Array<Record<string, unknown>>;
  procedural_roadmap: Array<Record<string, unknown>>;
  evidence_strategy: Array<Record<string, unknown>>;
  negotiation_playbook: Array<Record<string, unknown>>;
  risk_heat_map: Array<Record<string, unknown>>;
  critical_deadlines: Array<Record<string, unknown>>;
  swot_analysis?: {
    strengths: string[];
    weaknesses: string[];
    opportunities: string[];
    threats: string[];
  };
  win_probability?: number;
  financial_strategy?: {
    expected_recovery_min: number;
    expected_recovery_max: number;
    estimated_court_fees: number;
    estimated_attorney_costs: number;
    economic_viability_score: number;
    roi_rationale: string;
  };
  timeline_projection?: Array<{
    stage: string;
    duration_days: number;
    status: string;
  }>;
  penalty_forecast?: {
    three_percent_annual: number;
    inflation_losses: number;
    penalties_contractual: number;
    total_extra: number;
    basis_days: number;
  };
  confidence_score: number | null;
  confidence_rationale: string | null;
  recommended_next_steps: string | null;
  created_at: string;
  updated_at: string;
};

export type GenerateWithStrategyResponse = {
  document_id: string;
  strategy_blueprint_id: string;
  doc_type: string;
  title: string;
  preview_text: string;
  generated_text: string;
  used_ai: boolean;
  ai_model: string;
  ai_error: string;
  quality_guard_applied: boolean;
  pre_generation_gate_checks: Array<{ code: string; status: string; message: string }>;
  processual_validation_checks: Array<{ code: string; status: string; message: string }>;
  case_law_refs: Array<{
    id: string;
    source: string;
    decision_id: string;
    case_number: string | null;
    court_name: string | null;
    court_type: string | null;
    decision_date: string | null;
    summary: string | null;
    relevance_score: number;
  }>;
  strategy_audit_id: string;
  created_at: string;
  usage: SubscriptionResponse["usage"];
};

export type StrategyAuditResponse = {
  id: string;
  document_id: string;
  strategy_blueprint_id: string | null;
  precedent_citations: string[];
  counter_argument_addresses: string[];
  evidence_positioning_notes: string | null;
  procedure_optimization_notes: string | null;
  appeal_proofing_notes: string | null;
  generated_at: string;
};

export type JudgeSimulationResponse = {
  id: string;
  strategy_blueprint_id: string;
  document_id: string | null;
  verdict_probability: number;
  judge_persona: string;
  key_vulnerabilities: string[];
  strong_points: string[];
  procedural_risks: string[];
  suggested_corrections: string[];
  judge_commentary: string;
  decision_rationale: string;
  created_at: string;
};

export type GdprComplianceResponse = {
  report: string;
  compliant?: boolean;
  issues?: string[];
};

export async function analyzeGdprCompliance(
  payload: { text: string },
  token?: string,
  demoUser?: string
): Promise<GdprComplianceResponse> {
  const text = String(payload.text || "").trim();
  if (!text) {
    throw new Error("Немає тексту для GDPR-перевірки.");
  }
  return request<GdprComplianceResponse>("/api/analyze/gdpr-check", {
    method: "POST",
    body: { text },
    token,
    demoUser,
  });
}

export async function analyzeIntake(
  payload: { file: File; jurisdiction?: string; case_id?: string },
  token?: string,
  demoUser?: string,
  options?: { mode?: "standard" | "deep" }
): Promise<DocumentIntakeResponse> {
  const form = new FormData();
  form.append("file", payload.file);
  if (payload.jurisdiction) {
    form.append("jurisdiction", payload.jurisdiction);
  }
  if (payload.case_id) {
    form.append("case_id", payload.case_id);
  }

  const mode = options?.mode || "standard";
  const response = await safeFetch(`${API_BASE}/api/analyze/intake?mode=${mode}`, {
    method: "POST",
    headers: buildAuthHeaders(token, demoUser),
    body: form,
    cache: "no-store",
  });
  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as DocumentIntakeResponse;
}

export async function analyzePrecedentMap(
  intakeId: string,
  params: { limit?: number } = {},
  token?: string,
  demoUser?: string
): Promise<PrecedentMapResponse> {
  const search = new URLSearchParams();
  if (params.limit) search.set("limit", String(params.limit));
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<PrecedentMapResponse>(`/api/analyze/${intakeId}/precedent-map${suffix}`, {
    method: "POST",
    token,
    demoUser
  });
}

export async function createStrategyBlueprint(
  payload: { intake_id: string; regenerate?: boolean; refresh_precedent_map?: boolean; precedent_limit?: number },
  token?: string,
  demoUser?: string
): Promise<StrategyBlueprintResponse> {
  return request<StrategyBlueprintResponse>("/api/strategy/blueprint", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function generateWithStrategy(
  payload: {
    strategy_blueprint_id: string;
    doc_type?: string;
    bundle_doc_types?: string[];
    form_data?: Record<string, unknown>;
    extra_prompt_context?: string;
    case_id?: string;
  },
  token?: string,
  demoUser?: string
): Promise<GenerateWithStrategyResponse> {
  return request<GenerateWithStrategyResponse>("/api/generate-with-strategy", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getStrategyAudit(
  documentId: string,
  token?: string,
  demoUser?: string
): Promise<StrategyAuditResponse> {
  return request<StrategyAuditResponse>(`/api/documents/${documentId}/strategy-audit`, { token, demoUser });
}

export function getExportDocxUrl(documentId: string, token?: string, demoUser?: string): string {
  // We use window.location.origin if API_BASE is relative, but usually API_BASE is absolute
  const base = API_BASE.startsWith('http') ? API_BASE : "";
  return `${base}/api/documents/${documentId}/export/docx?token=${token || ""}&demo_user=${demoUser || ""}`;
}

export async function runJudgeSimulation(
  payload: { strategy_id: string; document_id?: string },
  token?: string,
  demoUser?: string
): Promise<JudgeSimulationResponse> {
  return request<JudgeSimulationResponse>("/api/strategy/simulate-judge", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// E-Court extras (ЄСІТС / court.gov.ua) — sync + courts list
// ─────────────────────────────────────────────────────────────────────────────

export type ECourtCourtsResponse = {
  courts: string[];
  source: "court_gov_ua" | "fallback" | string;
};

export async function syncECourtStatus(
  submissionId: string,
  token?: string,
  demoUser?: string
): Promise<ECourtStatusResponse & { synced_live: boolean }> {
  return request<ECourtStatusResponse & { synced_live: boolean }>(
    `/api/e-court/${submissionId}/sync-status`,
    { method: "POST", token, demoUser }
  );
}

export async function getECourtCourts(
  token?: string,
  demoUser?: string
): Promise<ECourtCourtsResponse> {
  return request<ECourtCourtsResponse>("/api/e-court/courts", { token, demoUser });
}

export type ECourtHearingItem = {
  id: string;
  case_number: string;
  court_name: string;
  date: string;
  time: string | null;
  subject: string | null;
  judge: string | null;
  status: string | null;
};

export type ECourtHearingsResponse = {
  items: ECourtHearingItem[];
  total: number;
};

export async function getECourtHearings(
  token?: string,
  demoUser?: string
): Promise<ECourtHearingsResponse> {
  return request<ECourtHearingsResponse>("/api/e-court/hearings", { token, demoUser });
}

export type PublicCourtSearchResponse = {
  status: string;
  case_number: string;
  assignments: any[];
  history: any[];
};

export async function searchPublicCourtCase(
  caseNumber: string,
  token?: string,
  demoUser?: string
): Promise<PublicCourtSearchResponse> {
  return request<PublicCourtSearchResponse>(`/api/e-court/public-search?case_number=${encodeURIComponent(caseNumber)}`, { token, demoUser });
}

// ─────────────────────────────────────────────────────────────────────────────
// Forum API
// ─────────────────────────────────────────────────────────────────────────────

export async function getForumPosts(params: { case_id?: string } = {}, token?: string, demoUser?: string): Promise<ForumPost[]> {
  const search = new URLSearchParams();
  if (params.case_id?.trim()) search.set("case_id", params.case_id.trim());
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<ForumPost[]>(`/forum/posts${suffix}`, { token, demoUser });
}

export async function createForumPost(
  payload: { title: string; content: string; category?: string; case_id?: string },
  token?: string,
  demoUser?: string
): Promise<ForumPost> {
  return request<ForumPost>("/forum/posts", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getForumPostDetail(
  postId: string,
  token?: string,
  demoUser?: string
): Promise<ForumPostDetail> {
  return request<ForumPostDetail>(`/forum/posts/${postId}`, { token, demoUser });
}

export async function createForumComment(
  postId: string,
  payload: { content: string },
  token?: string,
  demoUser?: string
): Promise<ForumComment> {
  return request<ForumComment>(`/forum/posts/${postId}/comments`, {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

export async function getDashboardStats(
  token?: string,
  demoUser?: string
): Promise<DashboardStats> {
  return request<DashboardStats>(`/api/dashboard/stats`, { token, demoUser });
}



export async function getKnowledgeEntries(
  params: { category?: string } = {},
  token?: string,
  demoUser?: string
): Promise<KnowledgeEntry[]> {
  const search = new URLSearchParams();
  if (params.category) search.set("category", params.category);
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<KnowledgeEntry[]>(`/api/knowledge-base/${suffix}`, { token, demoUser });
}

export async function createKnowledgeEntry(
  payload: { title: string; content: string; category?: string; tags?: string[] },
  token?: string,
  demoUser?: string
): Promise<KnowledgeEntry> {
  return request<KnowledgeEntry>("/api/knowledge-base/", {
    method: "POST",
    body: payload,
    token,
    demoUser
  });
}

// ─── Опендатабот: Судові справи ───────────────────────────────────────────────

export type CourtCaseSide = {
  role: string;
  name: string;
  code: string;
};

export type CourtCaseDecision = {
  id: string;
  date: string;
  type: string;
  url: string;
  summary: string;
};

export type CourtCase = {
  number: string;
  court: string;
  judge: string;
  sides: CourtCaseSide[];
  proceeding_type: string;
  subject: string;
  claim_price: number | string | null;
  date?: string;
  start_date: string;
  next_hearing_date: string;
  last_status: string;
  schedule_count?: number | null;
  judgment_code?: number | null;
  live?: number | null;
  last_document_date?: string;
  instance_info: Record<string, unknown>;
  instance_result: string;
  decisions: CourtCaseDecision[];
  stages?: Record<string, unknown>;
};

export type OpendatabotUsage = {
  limit: number;
  used: number;
  remaining: number;
  expires_at: string | null;
  api_url: string;
};

export async function getCourtCase(
  params: { number: string; judgmentCode?: number | null },
  token?: string,
  demoUser?: string
): Promise<CourtCase> {
  const encoded = encodeURIComponent(params.number);
  const search = new URLSearchParams();
  if (params.judgmentCode) {
    search.set("judgment_code", String(params.judgmentCode));
  }
  const suffix = search.toString() ? `?${search.toString()}` : "";
  return request<CourtCase>(`/api/opendatabot/court-cases/${encoded}${suffix}`, {
    token,
    demoUser,
  });
}

export async function getOpendatabotUsage(
  token?: string,
  demoUser?: string
): Promise<OpendatabotUsage> {
  return request<OpendatabotUsage>("/api/opendatabot/usage", {
    token,
    demoUser,
  });
}

export async function getCompanyDetails(
  code: string,
  token?: string,
  demoUser?: string
): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>(`/api/opendatabot/company/${code}`, {
    token,
    demoUser,
  });
}
