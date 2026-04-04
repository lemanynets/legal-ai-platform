import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import FullLawyerPage from "./page";
import { autoProcessFullLawyer, autoProcessFullLawyerPreflight, exportFullLawyerPreflightReport } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  autoProcessFullLawyer: jest.fn(),
  autoProcessFullLawyerPreflight: jest.fn(),
  exportFullLawyerPreflightReport: jest.fn(),
  exportDocument: jest.fn()
}));

const autoProcessFullLawyerMock = autoProcessFullLawyer as jest.MockedFunction<typeof autoProcessFullLawyer>;
const autoProcessFullLawyerPreflightMock = autoProcessFullLawyerPreflight as jest.MockedFunction<typeof autoProcessFullLawyerPreflight>;
const exportFullLawyerPreflightReportMock = exportFullLawyerPreflightReport as jest.MockedFunction<typeof exportFullLawyerPreflightReport>;

describe("FullLawyerPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    autoProcessFullLawyerPreflightMock.mockResolvedValue({
      status: "ok",
      source_file_name: "sample.txt",
      extracted_chars: 1400,
      processual_only_mode: true,
      recommended_doc_types: ["lawsuit_debt_loan"],
      validation_checks: [],
      clarifying_questions: [],
      unresolved_questions: [],
      review_checklist: [],
      unresolved_review_items: [],
      deadline_control: [],
      processual_package_gate: {
        status: "pending",
        can_generate_package: false,
        blockers: ["Preflight does not generate documents. Run Full Lawyer generation first, then assemble filing package."]
      },
      final_submission_gate: {
        status: "blocked",
        blockers: ["Strict filing mode requires PASS status at final submission gate."],
        critical_deadlines: [],
        next_step: "Resolve blockers and rerun Full Lawyer.",
        hard_stop: true,
        note: "Final submission gate is the last internal checkpoint before actual filing action."
      },
      package_generation_hint: {
        status: "blocked",
        can_generate_final_package: false,
        can_generate_draft_package: true,
        recommended_package_mode: "draft",
        blockers: ["Preflight does not generate documents. Run Full Lawyer generation first, then assemble filing package."],
        reason: "Generate procedural documents first; final package can be produced after quality gates pass."
      },
      next_actions: ["Run full generation."],
      warnings: [],
      usage: {
        id: "sub-1",
        user_id: "demo-user",
        plan: "PRO",
        status: "active",
        analyses_used: 1,
        analyses_limit: null,
        docs_used: 1,
        docs_limit: null,
        current_period_start: null,
        current_period_end: null,
        created_at: null,
        updated_at: null
      }
    });
    exportFullLawyerPreflightReportMock.mockResolvedValue(new Blob(["test"], { type: "application/pdf" }));
    autoProcessFullLawyerMock.mockResolvedValue({
      status: "ok",
      source_file_name: "sample.txt",
      extracted_chars: 1400,
      processual_only_mode: true,
      summary: {
        dispute_type: "Debt recovery dispute",
        procedure: "civil",
        urgency: "medium",
        claim_amount_uah: 120000,
        estimated_court_fee_uah: 1800,
        estimated_penalty_uah: 600,
        estimated_total_with_fee_uah: 122400
      },
      legal_basis: ["Civil Code of Ukraine articles 1046, 1049, 625."],
      strategy_steps: ["Prepare evidence matrix."],
      evidence_required: ["Loan agreement"],
      risks: ["Limitation period risk"],
      missing_information: ["Missing debtor address"],
      clarifying_questions: ["Please confirm debtor address."],
      clarification_required: false,
      unresolved_questions: [],
      next_actions: ["Resolve warnings and confirm facts."],
      validation_checks: [
        {
          code: "claim_amount_detected",
          status: "pass",
          message: "Claim amount detected (120000 UAH)."
        }
      ],
      context_refs: [
        {
          source: "opendatabot",
          ref_type: "case_law",
          reference: "Case 111/11/26",
          note: "Relevant position.",
          relevance_score: 0.82
        }
      ],
      confidence_score: 0.82,
      analysis_highlights: ["Debt profile validated."],
      procedural_conclusions: ["Prepare debt recovery claim"],
      recommended_doc_types: ["lawsuit_debt_loan"],
      generated_documents: [
        {
          id: "doc-1",
          doc_type: "lawsuit_debt_loan",
          title: "Debt recovery lawsuit",
          created_at: "2026-02-27T10:00:00Z",
          preview_text: "Preview text",
          used_ai: true,
          ai_model: "gpt-4o-mini",
          ai_error: "",
          quality_guard_applied: false,
          pre_generation_gate_checks: [],
          processual_validation_checks: []
        }
      ],
      filing_package: {
        generated: true,
        items: [
          {
            id: "pkg-1",
            doc_type: "filing_package_cover",
            title: "Filing package cover",
            created_at: "2026-02-27T10:02:00Z"
          }
        ],
        checklist: ["Signed procedural document."]
      },
      processual_package_gate: {
        status: "pass",
        can_generate_package: true,
        blockers: []
      },
      review_checklist: [
        {
          code: "confirm_parties_and_addresses",
          title: "Confirm full party identification data",
          description: "Full names, tax IDs, and addresses are complete and verified.",
          required: true
        }
      ],
      review_required: false,
      unresolved_review_items: [],
      workflow_stages: [
        {
          code: "block_1_ai_analysis",
          title: "Block 1 — AI Analysis & Drafting",
          status: "ok",
          details: ["LLM analyzed uploaded text."],
          metrics: { procedural_conclusions: 1 }
        },
        {
          code: "block_2_case_law_rag",
          title: "Block 2 — Case Law Retrieval (RAG)",
          status: "ok",
          details: ["Context references attached: 2."],
          metrics: { context_refs_count: 2 }
        },
        {
          code: "block_3_rule_validation",
          title: "Block 3 — Rule Validation",
          status: "warn",
          details: ["Warnings: 1."],
          metrics: { checks_warn: 1 }
        },
        {
          code: "block_4_human_review_gate",
          title: "Block 4 — Human Review & Approval",
          status: "ok",
          details: ["No unresolved questions."],
          metrics: { unresolved_questions: 0 }
        }
      ],
      ready_for_filing: false,
      procedural_timeline: [
        {
          code: "today_review",
          title: "Current review date",
          date: "2026-02-28",
          status: "info",
          note: "Baseline date used for deadline pre-checks."
        }
      ],
      evidence_matrix: [
        {
          code: "contract",
          title: "Contract",
          found_in_source: true,
          status: "ok",
          note: "Detected in uploaded text."
        }
      ],
      fact_chronology_matrix: [
        {
          event: "Loan agreement signed",
          event_date: "2025-01-10",
          actor: "Borrower and lender",
          evidence_status: "supported",
          source_excerpt: "Signed loan agreement detected.",
          relevance: "high"
        }
      ],
      burden_of_proof_map: [
        {
          issue: "Existence of debt",
          burden_on: "plaintiff",
          required_evidence: ["Loan agreement", "Bank transfer statement"],
          current_status: "partial",
          recommended_action: "Add certified payment statement."
        }
      ],
      drafting_instructions: [
        {
          doc_type: "lawsuit_debt_loan",
          must_include: ["Exact claim amount", "Parties details"],
          factual_focus: ["Timeline of debt origin"],
          legal_focus: ["Civil Code of Ukraine articles 1046, 1049, 625."],
          style_notes: ["Formal processual tone"],
          status: "ok"
        }
      ],
      opponent_weakness_map: [
        {
          weakness: "No proof of repayment",
          severity: "high",
          exploitation_step: "Emphasize lack of repayment evidence.",
          supporting_basis: "Obligation to prove repayment lies on debtor.",
          evidentiary_need: "Bank statements for full period."
        }
      ],
      evidence_collection_plan: [
        {
          priority: "high",
          step: "Request bank statement",
          owner: "Plaintiff legal team",
          deadline_hint: "Before filing",
          expected_result: "Confirmed debt transfer and non-repayment.",
          status: "queued"
        }
      ],
      factual_circumstances_blocks: [
        {
          section: "Loan issuance facts",
          narrative: "Defendant received loan funds and accepted repayment terms.",
          evidence_anchor: "Loan agreement + transfer statement",
          status: "ok"
        }
      ],
      legal_qualification_blocks: [
        {
          qualification: "Loan obligation breach",
          norm_reference: "Civil Code of Ukraine articles 1046, 1049, 625.",
          application_to_facts: "Non-repayment after due date qualifies as monetary breach.",
          risk_note: "Need clear due date proof.",
          status: "ok"
        }
      ],
      prayer_part_variants: [
        {
          variant: "Base claim",
          request_text: "Recover principal, surcharge, and court costs.",
          grounds: "Contract and statutory norms.",
          priority: "high"
        }
      ],
      counterargument_response_matrix: [
        {
          opponent_argument: "Debt already repaid",
          response_strategy: "Require documentary proof of each alleged payment.",
          evidence_focus: "Bank statements and payment receipts.",
          success_probability: "medium_high"
        }
      ],
      document_narrative_completeness: [
        {
          section: "Facts and chronology",
          status: "partial",
          action: "Add exact due-date sequence and repayment timeline.",
          note: "Chronology should be explicit for court review."
        }
      ],
      case_law_application_matrix: [
        {
          legal_issue: "Post-judgment 3% annual interest",
          reference: "VPSU case 310/11534/13-ц",
          application_note: "Money obligation remains until factual execution.",
          strength: "high"
        }
      ],
      procedural_violation_hypotheses: [
        {
          hypothesis: "Insufficient party identification may trigger leave-without-move.",
          legal_basis: "CPC Art. 175",
          source_signal: "Missing full defendant address marker.",
          viability: "medium",
          required_proof: "Provide complete address and identifier evidence."
        }
      ],
      document_fact_enrichment_plan: [
        {
          doc_type: "lawsuit_debt_loan",
          missing_fact_block: "Detailed chronology of non-payment periods",
          insert_instruction: "Add month-by-month timeline with source references.",
          priority: "high",
          status: "queued"
        }
      ],
      hearing_positioning_notes: [
        {
          theme: "Chronology-first hearing narrative",
          supporting_points: ["Debt origin", "Due date", "No repayment proof"],
          risk_counter: "Preempt defense about alleged informal settlements.",
          courtroom_phrase: "Facts are sequential, documented, and legally qualified."
        }
      ],
      process_stage_action_map: [
        {
          stage_code: "first_instance_filing",
          stage_title: "First instance filing",
          objective: "Submit complete and admissible package.",
          actions: ["Finalize CPC requisites", "Attach evidence register"],
          trigger: "All hard-stop blockers resolved.",
          status: "ready"
        }
      ],
      legal_argument_map: [
        {
          issue: "Argument 1",
          legal_basis: "Civil Code of Ukraine articles 1046, 1049, 625.",
          litigation_goal: "Recover principal debt, 3% annual interest, and inflation losses."
        }
      ],
      readiness_breakdown: {
        score: 82.5,
        decision: "not_ready",
        blockers: ["Validation warnings: 1."],
        strengths: ["Generated documents: 1."],
        metrics: {
          warn_count: 1
        }
      },
      post_filing_plan: ["Track deadlines for court responses and prepare draft replies in advance."],
      party_profile: {
        completion_score: 70,
        risk_level: "medium",
        plaintiff_detected: true,
        defendant_detected: true,
        missing_items: ["Missing full addresses for procedural delivery."]
      },
      jurisdiction_recommendation: {
        procedure: "civil",
        suggested_route: "Local general court primarily by defendant domicile (alternative routes may apply).",
        legal_basis: ["CPC jurisdiction rules."],
        confidence: 0.55,
        required_inputs: ["Full defendant address"],
        warning: "Party identification data is incomplete; jurisdiction confidence is reduced."
      },
      generated_docs_quality: [
        {
          doc_type: "lawsuit_debt_loan",
          score: 86.3,
          status: "high",
          issues: []
        }
      ],
      e_court_submission_preview: {
        can_submit: false,
        provider: "court.gov.ua",
        signer_methods: ["Дія.Підпис", "КЕП токен"],
        required_attachments: ["lawsuit_debt_loan:doc-1"],
        blockers: ["Readiness gate not satisfied."],
        note: "Pre-check only. Final submission requires live e-court integration."
      },
      priority_queue: [
        {
          priority: "high",
          task: "Validation warnings: 1.",
          due_date: "2026-03-01"
        }
      ],
      consistency_report: [
        {
          code: "amount_alignment",
          status: "pass",
          message: "Detected amount and principal amount are consistent."
        }
      ],
      remedy_coverage: [
        {
          remedy: "Debt principal recovery",
          covered: true,
          covered_by: ["lawsuit_debt_loan"],
          note: "Covered by selected document package."
        }
      ],
      citation_pack: {
        statutory_refs: ["Civil Code of Ukraine articles 1046, 1049, 625."],
        case_refs: [
          {
            source: "opendatabot",
            reference: "Case 111/11/26",
            note: "Relevant position."
          }
        ],
        note: "Use statutory refs as primary basis and case refs for motivation support."
      },
      fee_scenarios: [
        {
          name: "base",
          principal_uah: 120000,
          court_fee_uah: 1800,
          penalty_uah: 600,
          total_with_fee_uah: 122400,
          note: "Scenario uses +/-15% principal sensitivity."
        }
      ],
      filing_risk_simulation: [
        {
          risk: "Claim return/leave-without-move due to formal defects",
          probability: 0.2,
          impact: "high",
          mitigation: "Resolve warnings, complete party data, and verify CPC requisites before filing."
        }
      ],
      procedural_defect_scan: [
        {
          code: "no_critical_defects",
          severity: "low",
          issue: "No critical procedural defects detected in current pre-check.",
          fix: "Proceed with final legal review and filing package assembly."
        }
      ],
      evidence_admissibility_map: [
        {
          evidence: "Contract",
          admissibility: "high",
          relevance: "high",
          risk: "low",
          recommendation: "Attach as primary evidence and reference in factual matrix."
        }
      ],
      motion_recommendations: [
        {
          motion_type: "Motion to secure claim (asset freeze)",
          priority: "medium",
          rationale: "Debt recovery path may require interim protection of enforcement potential.",
          trigger: "Use if risk of asset disposal or evasion is present."
        }
      ],
      hearing_preparation_plan: [
        {
          phase: "Opening statement",
          task: "Prepare concise case theory for Debt recovery dispute.",
          output: "2-3 minute oral opening with requested remedies."
        }
      ],
      package_completeness: {
        status: "incomplete",
        score: 82,
        generated_documents_count: 1,
        missing_evidence_items: 1,
        unresolved_required_review_items: 0,
        note: "Pre-filing package completeness estimate based on current workflow outputs."
      },
      opponent_objections: [
        {
          objection: "Challenge to procedural admissibility of claim",
          likelihood: "medium",
          rebuttal: "Demonstrate compliance with procedural requisites and eliminate all validation warnings."
        }
      ],
      settlement_strategy: {
        dispute_type: "Debt recovery dispute",
        window: "parallel",
        target_amount_uah: 122400,
        recommendation: "Run parallel path: fix blockers while sending structured settlement offer.",
        note: "Settlement strategy is advisory and should be approved by responsible lawyer."
      },
      enforcement_plan: [
        {
          step: "Prepare enforcement-ready document set",
          timing: "pre-judgment",
          details: "Maintain clean evidence index and payment details for future enforcement stage."
        }
      ],
      cpc_compliance_check: [
        {
          requirement: "Court and jurisdiction details",
          article: "CPC Art. 175(3), Arts. 27-30",
          status: "pass",
          note: "Claim should explicitly identify court and jurisdiction basis."
        }
      ],
      procedural_document_blueprint: [
        {
          section: "Header: court and parties",
          required: true,
          status: "ok",
          note: "Court name, parties, addresses, identifiers, contact details."
        }
      ],
      deadline_control: [
        {
          code: "filing_target",
          title: "Target filing date for initial package",
          due_date: "2026-03-05",
          status: "ok",
          basis: "Internal litigation planning",
          note: "Baseline filing window for current procedural package."
        }
      ],
      court_fee_breakdown: {
        principal_uah: 120000,
        penalty_uah: 600,
        inflation_losses_uah: 0,
        claim_price_uah: 120600,
        court_fee_uah: 1800,
        total_with_fee_uah: 122400,
        status: "estimated",
        note: "Court fee is an estimate and must be confirmed against current statutory rates before filing."
      },
      filing_attachments_register: [
        {
          name: "Main procedural document (signed)",
          required: true,
          available: true,
          copies_for_court: 1,
          status: "ok",
          note: "Primary claim/complaint text ready for filing."
        }
      ],
      cpc_175_requisites_map: [
        {
          requisite: "Court designation",
          status: "pass",
          source_signal: "court marker in source text",
          note: "Claim header should contain exact court name and jurisdiction route."
        }
      ],
      cpc_177_attachments_map: [
        {
          attachment_group: "Main claim document",
          required: true,
          status: "pass",
          items_total: 1,
          items_available: 1,
          note: "Signed main procedural text for filing."
        }
      ],
      prayer_part_audit: {
        status: "ready",
        score: 88,
        target_total_uah: 122400,
        covered_requests: ["Debt principal recovery"],
        missing_requests: [],
        note: "Prayer part should be concrete: principal claim, surcharge, court costs, and procedural asks."
      },
      fact_norm_evidence_chain: [
        {
          fact_issue: "Argument 1",
          legal_norm: "Civil Code of Ukraine articles 1046, 1049, 625.",
          evidence: "Contract",
          status: "linked",
          note: "Every key fact should map to at least one admissible evidence source."
        }
      ],
      pre_filing_red_flags: [
        {
          severity: "medium",
          flag: "CPC compliance gap: Court and jurisdiction details",
          action: "Fill missing requisites under CPC before final submission."
        }
      ],
      text_section_audit: [
        {
          section: "Header: court and parties",
          status: "ok",
          note: "Section markers were checked against generated text draft."
        }
      ],
      service_plan: [
        {
          recipient: "Court",
          method: "E-court or paper filing",
          status: "ready",
          note: "Submit signed claim with annex register and fee proof."
        }
      ],
      prayer_rewrite_suggestions: [
        {
          priority: "high",
          suggestion: "State a precise monetary request (122400 UAH) and split principal/surcharge/costs.",
          rationale: "Courts require a concrete and calculable prayer part."
        }
      ],
      contradiction_hotspots: [
        {
          issue: "Missing CPC requisite: Court designation",
          severity: "medium",
          fix: "Complete this requisite in claim body and header."
        }
      ],
      judge_questions_simulation: [
        {
          question: "How exactly does evidence prove: Argument 1?",
          why_it_matters: "Court will test whether factual assertions are actually substantiated.",
          prep_answer_hint: "Prepare a direct evidence chain and cite Civil Code of Ukraine articles 1046, 1049, 625.."
        }
      ],
      citation_quality_gate: {
        status: "strong",
        score: 91,
        cpc_refs_count: 1,
        case_refs_count: 1,
        issues: [],
        note: "Citation quality gate is advisory; final legal citation set should be advocate-approved."
      },
      filing_decision_card: {
        decision: "conditional_go",
        confidence: 0.82,
        readiness_score: 82.5,
        blockers: ["Validation warnings: 1."],
        next_step: "Resolve listed blockers, rerun checks, then submit.",
        note: "Decision card is a pre-filing control aid, not a substitute for advocate sign-off."
      },
      processual_language_audit: {
        status: "medium",
        score: 74,
        formal_markers_found: 3,
        informal_markers_found: 0,
        note: "Language audit checks whether draft uses formal procedural style suitable for court filing."
      },
      evidence_gap_actions: [
        {
          evidence: "Bank statement",
          priority: "high",
          action: "Collect original/certified copy and map this evidence to specific fact statements.",
          deadline_hint: "Before final filing package assembly."
        }
      ],
      deadline_alert_board: [
        {
          title: "Target filing date for initial package",
          level: "warning",
          days_left: 3,
          recommended_action: "Track and prepare filing step."
        }
      ],
      filing_packet_order: [
        {
          order: 1,
          item: "Procedural document: lawsuit_debt_loan",
          required: true,
          status: "ready",
          note: "doc-1"
        }
      ],
      opponent_response_playbook: [
        {
          scenario: "Challenge to procedural admissibility of claim",
          counter_step: "Demonstrate compliance with procedural requisites and eliminate all validation warnings.",
          evidence_focus: "Link rebuttal to documentary proof and norm references."
        }
      ],
      limitation_period_card: {
        status: "ok",
        risk: "low",
        reference_date: "2026-02-27",
        limitation_deadline: "2029-02-27",
        days_remaining: 1094,
        note: "Limitation period card is an estimate and must be confirmed by lawyer for specific claim type."
      },
      jurisdiction_challenge_guard: {
        risk_level: "medium",
        route: "Local general court primarily by defendant domicile (alternative routes may apply).",
        weak_points: ["Jurisdiction confidence is below recommended threshold."],
        mitigations: ["Collect full defendant/plaintiff address and venue facts before filing."],
        note: "Guard focuses on potential jurisdiction objections from court or opponent."
      },
      claim_formula_card: {
        status: "ok",
        principal_uah: 120000,
        penalty_uah: 600,
        court_fee_uah: 1800,
        total_claim_uah: 122400,
        formula: "120000.00 + 600.00 + 1800.00 = 122400.00 UAH",
        note: "Claim formula card should match the final prayer part before filing."
      },
      filing_cover_letter: {
        status: "ready",
        subject: "Filing package submission: Debt recovery dispute",
        recipient: "Court registry / E-court portal",
        body_preview:
          "Please accept procedural package for Debt recovery dispute. Current filing decision: conditional_go. Ready packet items: 1/1.",
        note: "Cover letter preview is generated for internal workflow and should be reviewed before sending."
      },
      execution_step_tracker: [
        {
          stage: "Prepare enforcement-ready document set",
          status: "planned",
          trigger: "Proceed when judgment/writ prerequisites are met."
        }
      ],
      version_control_card: {
        status: "stable",
        generated_documents: 1,
        unique_doc_types: 1,
        revision_tag: "v1",
        note: "Version control card tracks draft maturity before e-court submission."
      },
      e_court_packet_readiness: {
        status: "conditional",
        blockers: [],
        missing_attachments: [],
        recommended_submit_mode: "e-court with KEP",
        note: "Readiness check is technical and processual pre-check before real court API submission."
      },
      hearing_script_pack: [
        {
          phase: "Opening",
          script_hint: "Argument 1 -> Recover principal debt, 3% annual interest, and inflation losses..",
          linked_basis: "Civil Code of Ukraine articles 1046, 1049, 625."
        }
      ],
      settlement_offer_card: {
        status: "active",
        target_min_uah: 104040,
        target_max_uah: 122400,
        strategy_note: "Settlement window: parallel.",
        fallback_position: "Proceed to filing stage if offer rejected.",
        note: "Offer card is advisory and should be approved by responsible lawyer."
      },
      appeal_reserve_card: {
        status: "standby",
        reserve_deadline: null,
        trigger_conditions: [
          "Court decision partially/fully rejects core relief.",
          "Material procedural violation detected after judgment.",
          "New evidence or legal position affects outcome."
        ],
        note: "Appeal reserve card keeps appellate path prepared even during first-instance strategy."
      },
      procedural_costs_allocator_card: {
        status: "litigation_ready",
        plaintiff_upfront_costs_uah: 1800,
        defendant_target_recovery_uah: 122400,
        cost_components: {
          principal_uah: 120000,
          penalty_uah: 600,
          court_fee_uah: 1800
        },
        note: "Costs allocation card is indicative; court has final discretion on costs distribution."
      },
      document_export_readiness: {
        status: "ready",
        formats: ["pdf", "docx"],
        blockers: [],
        note: "Export readiness verifies draft quality before producing final PDF/DOCX package."
      },
      filing_submission_checklist_card: [
        {
          step: "Finalize filing packet composition",
          status: "ok",
          detail: "Missing items: 0."
        }
      ],
      post_filing_monitoring_board: [
        {
          track: "Track deadlines for court responses and prepare draft replies in advance.",
          priority: "medium",
          signal: "Routine monitoring."
        }
      ],
      legal_research_backlog: [
        {
          task: "No critical research backlog items detected.",
          priority: "low",
          expected_output: "Maintain monitoring of fresh Supreme Court positions."
        }
      ],
      procedural_consistency_scorecard: {
        status: "strong",
        score: 88,
        validation_warn_count: 1,
        text_warn_count: 0,
        cpc_warn_count: 0,
        note: "Consistency scorecard aggregates key quality gates before final submission."
      },
      hearing_evidence_order_card: [
        {
          order: 1,
          evidence: "Contract",
          priority: "high",
          status: "ready",
          note: "Order for oral presentation at hearing stage."
        }
      ],
      digital_signature_readiness: {
        status: "conditional",
        signer_methods: ["Дія.Підпис", "КЕП токен", "File-based key"],
        blockers: [],
        note: "Digital signature readiness is a pre-check for external submission flow."
      },
      case_law_update_watchlist: [
        {
          source: "opendatabot",
          reference: "Case 111/11/26",
          watch_reason: "Track if newer position changes argument strength."
        }
      ],
      final_submission_gate: {
        status: "conditional_pass",
        blockers: [],
        critical_deadlines: ["appeal_deadline:urgent:2026-03-05"],
        next_step: "Resolve blockers and rerun Full Lawyer.",
        hard_stop: true,
        note: "Final submission gate is the last internal checkpoint before actual filing action."
      },
      court_behavior_forecast_card: {
        stance: "balanced",
        confidence: 0.75,
        high_impact_risks: 1,
        high_severity_flags: 0,
        question_load: 1,
        note: "Forecast card is heuristic and helps prepare hearing behavior scenarios."
      },
      evidence_pack_compression_plan: [
        {
          step: "Create core hearing pack",
          status: "ok",
          detail: "High-priority evidence items selected: 1."
        }
      ],
      filing_channel_strategy_card: {
        status: "conditional",
        primary_channel: "hybrid",
        backup_channel: "paper_filing",
        checklist_warn_count: 0,
        note: "Channel strategy balances technical readiness and procedural reliability."
      },
      legal_budget_timeline_card: {
        timeline_mode: "standard",
        estimated_upfront_uah: 1800,
        recommended_reserve_uah: 3672,
        settlement_floor_uah: 104040,
        urgent_deadlines: 0,
        note: "Budget timeline card is planning-only and should be validated with client strategy."
      },
      counterparty_pressure_map: [
        {
          vector: "Challenge to procedural admissibility of claim",
          pressure: "medium",
          coverage: "covered",
          action: "Keep rebuttal updated for hearing."
        }
      ],
      courtroom_timeline_scenarios: [
        {
          scenario: "Base litigation path",
          probability: "high",
          focus: "Keep filing and hearing milestones within current calendar."
        }
      ],
      evidence_authenticity_checklist: [
        {
          evidence: "Contract",
          status: "ok",
          action: "Keep original/certified copy and include source metadata."
        }
      ],
      remedy_priority_matrix: [
        {
          remedy: "Debt principal recovery",
          priority: "high",
          rationale: "Core remedy is already covered and should remain first in prayer part."
        }
      ],
      judge_question_drill_card: {
        complexity: "low",
        rounds: 1,
        question_count: 1,
        hotspot_count: 1,
        note: "Drill card defines how intense oral prep should be before hearing."
      },
      client_instruction_packet: [
        {
          instruction: "Confirm filing mandate and risk tolerance.",
          priority: "high",
          note: "Current decision mode: conditional_go."
        }
      ],
      procedural_risk_heatmap: [
        {
          risk: "Claim return/leave-without-move due to formal defects",
          level: "medium",
          source: "filing_risk_simulation"
        }
      ],
      evidence_disclosure_plan: [
        {
          evidence: "Contract",
          phase: "hearing_core",
          status: "ready",
          note: "Disclose in structured order with provenance and relevance references."
        }
      ],
      settlement_negotiation_script: [
        {
          stage: "Opening position",
          line: "Our structured claim range is 104040.00-122400.00 UAH with documented legal basis.",
          goal: "Anchor negotiation around litigable numbers."
        }
      ],
      hearing_readiness_scorecard: {
        status: "partial",
        score: 75,
        script_count: 1,
        evidence_ready: 1,
        evidence_total: 1,
        drill_rounds: 1,
        note: "Hearing readiness scorecard is a practical prep KPI, not legal advice."
      },
      advocate_signoff_packet: {
        status: "review_needed",
        required_checks: [
          { check: "Final submission gate", status: "conditional_pass" },
          { check: "Filing decision", status: "conditional_go" }
        ],
        note: "Packet summarizes minimum controls before advocate sign-off decision."
      },
      warnings: [],
      usage: {
        id: "sub-1",
        user_id: "demo-user",
        plan: "PRO",
        status: "active",
        analyses_used: 1,
        analyses_limit: null,
        docs_used: 1,
        docs_limit: null,
        current_period_start: null,
        current_period_end: null,
        created_at: null,
        updated_at: null
      }
    });
  });

  it("uploads file and renders strategy result", async () => {
    const user = userEvent.setup();
    render(<FullLawyerPage />);
    expect(screen.getByLabelText(/Автопрефлайт перед повним запуском/i)).toBeInTheDocument();

    const file = new File(["Debt under loan agreement 120000 UAH"], "sample.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText(/Файл \(txt\/pdf\/docx\)/i), file);
    expect(screen.getByRole("button", { name: /Запустити з preflight-виправленнями/i })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Запустити повний режим|Запустити Full Lawyer/i }));

    await waitFor(() => expect(autoProcessFullLawyerMock).toHaveBeenCalledTimes(1));
    expect(autoProcessFullLawyerPreflightMock).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText(/Сформовано документів: 1/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Debt recovery dispute/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Confidence score|Впевненість|Оцінка впевненості/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Estimated court fee|Орієнтовний судовий збір/)).toBeInTheDocument();
    expect(screen.getByText(/Resolve warnings and confirm facts/)).toBeInTheDocument();
    expect(screen.getAllByText(/lawsuit_debt_loan/).length).toBeGreaterThan(0);
    expect(screen.getByText(/filing_package_cover/)).toBeInTheDocument();
    expect(screen.getByText(/Prepare debt recovery claim/)).toBeInTheDocument();
    expect(screen.getByText(/Workflow stages/)).toBeInTheDocument();
    expect(screen.getByText(/Ready for filing|Готовність до подання/)).toBeInTheDocument();
    expect(screen.getByText(/AI analysis highlights/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural timeline/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence matrix/)).toBeInTheDocument();
    expect(screen.getByText(/Fact chronology matrix/)).toBeInTheDocument();
    expect(screen.getByText(/Burden of proof map/)).toBeInTheDocument();
    expect(screen.getByText(/Drafting instructions/)).toBeInTheDocument();
    expect(screen.getByText(/Opponent weakness map/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence collection plan/)).toBeInTheDocument();
    expect(screen.getByText(/Factual circumstances blocks/)).toBeInTheDocument();
    expect(screen.getByText(/Legal qualification blocks/)).toBeInTheDocument();
    expect(screen.getByText(/Prayer part variants/)).toBeInTheDocument();
    expect(screen.getByText(/Counterargument response matrix/)).toBeInTheDocument();
    expect(screen.getByText(/Document narrative completeness/)).toBeInTheDocument();
    expect(screen.getByText(/Case law application matrix/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural violation hypotheses/)).toBeInTheDocument();
    expect(screen.getByText(/Document fact enrichment plan/)).toBeInTheDocument();
    expect(screen.getByText(/Hearing positioning notes/)).toBeInTheDocument();
    expect(screen.getByText(/Process stage action map/)).toBeInTheDocument();
    expect(screen.getByText(/Readiness breakdown/)).toBeInTheDocument();
    expect(screen.getByText(/Party profile/)).toBeInTheDocument();
    expect(screen.getByText(/Jurisdiction recommendation/)).toBeInTheDocument();
    expect(screen.getByText(/E-court submission preview/)).toBeInTheDocument();
    expect(screen.getByText(/Consistency report/)).toBeInTheDocument();
    expect(screen.getByText(/Remedy coverage/)).toBeInTheDocument();
    expect(screen.getByText(/Citation pack/)).toBeInTheDocument();
    expect(screen.getByText(/Fee scenarios/)).toBeInTheDocument();
    expect(screen.getByText(/Filing risk simulation/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural defect scan/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence admissibility map/)).toBeInTheDocument();
    expect(screen.getByText(/Motion recommendations/)).toBeInTheDocument();
    expect(screen.getByText(/Hearing preparation plan/)).toBeInTheDocument();
    expect(screen.getByText(/Package completeness/)).toBeInTheDocument();
    expect(screen.getByText(/Opponent objections/)).toBeInTheDocument();
    expect(screen.getByText(/Settlement strategy/)).toBeInTheDocument();
    expect(screen.getByText(/Enforcement plan/)).toBeInTheDocument();
    expect(screen.getByText(/CPC compliance check/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural document blueprint/)).toBeInTheDocument();
    expect(screen.getByText(/Deadline control/)).toBeInTheDocument();
    expect(screen.getByText(/Court fee breakdown/)).toBeInTheDocument();
    expect(screen.getByText(/Filing attachments register/)).toBeInTheDocument();
    expect(screen.getByText(/CPC 175 requisites map/)).toBeInTheDocument();
    expect(screen.getByText(/CPC 177 attachments map/)).toBeInTheDocument();
    expect(screen.getByText(/Prayer part audit/)).toBeInTheDocument();
    expect(screen.getByText(/Fact-norm-evidence chain/)).toBeInTheDocument();
    expect(screen.getByText(/Pre-filing red flags/)).toBeInTheDocument();
    expect(screen.getByText(/Text section audit/)).toBeInTheDocument();
    expect(screen.getByText(/Service plan/)).toBeInTheDocument();
    expect(screen.getByText(/Prayer rewrite suggestions/)).toBeInTheDocument();
    expect(screen.getByText(/Contradiction hotspots/)).toBeInTheDocument();
    expect(screen.getByText(/Judge questions simulation/)).toBeInTheDocument();
    expect(screen.getByText(/Citation quality gate/)).toBeInTheDocument();
    expect(screen.getByText(/Filing decision card/)).toBeInTheDocument();
    expect(screen.getByText(/Processual language audit/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence gap actions/)).toBeInTheDocument();
    expect(screen.getByText(/Deadline alert board/)).toBeInTheDocument();
    expect(screen.getByText(/Filing packet order/)).toBeInTheDocument();
    expect(screen.getByText(/Opponent response playbook/)).toBeInTheDocument();
    expect(screen.getByText(/Limitation period card/)).toBeInTheDocument();
    expect(screen.getByText(/Jurisdiction challenge guard/)).toBeInTheDocument();
    expect(screen.getByText(/Claim formula card/)).toBeInTheDocument();
    expect(screen.getByText(/Filing cover letter/)).toBeInTheDocument();
    expect(screen.getByText(/Execution step tracker/)).toBeInTheDocument();
    expect(screen.getByText(/Version control card/)).toBeInTheDocument();
    expect(screen.getByText(/E-court packet readiness/)).toBeInTheDocument();
    expect(screen.getByText(/Hearing script pack/)).toBeInTheDocument();
    expect(screen.getByText(/Settlement offer card/)).toBeInTheDocument();
    expect(screen.getByText(/Appeal reserve card/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural costs allocator card/)).toBeInTheDocument();
    expect(screen.getByText(/Document export readiness/)).toBeInTheDocument();
    expect(screen.getByText(/Filing submission checklist card/)).toBeInTheDocument();
    expect(screen.getByText(/Post-filing monitoring board/)).toBeInTheDocument();
    expect(screen.getByText(/Legal research backlog/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural consistency scorecard/)).toBeInTheDocument();
    expect(screen.getByText(/Hearing evidence order card/)).toBeInTheDocument();
    expect(screen.getByText(/Digital signature readiness/)).toBeInTheDocument();
    expect(screen.getByText(/Case law update watchlist/)).toBeInTheDocument();
    expect(screen.getByText(/Final submission gate/)).toBeInTheDocument();
    expect(screen.getByText(/Жорсткий стоп: подання заблоковане/)).toBeInTheDocument();
    expect(screen.getByText(/Критичні строки:/)).toBeInTheDocument();
    expect(screen.getByText(/appeal_deadline:urgent:2026-03-05/)).toBeInTheDocument();
    expect(screen.getByText(/Court behavior forecast card/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence pack compression plan/)).toBeInTheDocument();
    expect(screen.getByText(/Filing channel strategy card/)).toBeInTheDocument();
    expect(screen.getByText(/Legal budget timeline card/)).toBeInTheDocument();
    expect(screen.getByText(/Counterparty pressure map/)).toBeInTheDocument();
    expect(screen.getByText(/Courtroom timeline scenarios/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence authenticity checklist/)).toBeInTheDocument();
    expect(screen.getByText(/Remedy priority matrix/)).toBeInTheDocument();
    expect(screen.getByText(/Judge question drill card/)).toBeInTheDocument();
    expect(screen.getByText(/Client instruction packet/)).toBeInTheDocument();
    expect(screen.getByText(/Procedural risk heatmap/)).toBeInTheDocument();
    expect(screen.getByText(/Evidence disclosure plan/)).toBeInTheDocument();
    expect(screen.getByText(/Settlement negotiation script/)).toBeInTheDocument();
    expect(screen.getByText(/Hearing readiness scorecard/)).toBeInTheDocument();
    expect(screen.getByText(/Advocate signoff packet/)).toBeInTheDocument();
    expect(screen.getByText(/Filing package status/)).toBeInTheDocument();
  });
});
