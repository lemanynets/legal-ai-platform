import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import StrategyStudioPage from "./page";
import {
  analyzeIntake,
  analyzePrecedentMap,
  createStrategyBlueprint,
  generateWithStrategy,
  getCases,
  getExportDocxUrl,
  getStrategyAudit,
  runJudgeSimulation,
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  analyzeIntake: jest.fn(),
  analyzePrecedentMap: jest.fn(),
  createStrategyBlueprint: jest.fn(),
  generateWithStrategy: jest.fn(),
  getCases: jest.fn(),
  getStrategyAudit: jest.fn(),
  runJudgeSimulation: jest.fn(),
  getExportDocxUrl: jest.fn(),
}));

const analyzeIntakeMock = analyzeIntake as jest.MockedFunction<typeof analyzeIntake>;
const analyzePrecedentMapMock = analyzePrecedentMap as jest.MockedFunction<typeof analyzePrecedentMap>;
const createStrategyBlueprintMock = createStrategyBlueprint as jest.MockedFunction<typeof createStrategyBlueprint>;
const generateWithStrategyMock = generateWithStrategy as jest.MockedFunction<typeof generateWithStrategy>;
const getCasesMock = getCases as jest.MockedFunction<typeof getCases>;
const getStrategyAuditMock = getStrategyAudit as jest.MockedFunction<typeof getStrategyAudit>;
const runJudgeSimulationMock = runJudgeSimulation as jest.MockedFunction<typeof runJudgeSimulation>;
const getExportDocxUrlMock = getExportDocxUrl as jest.MockedFunction<typeof getExportDocxUrl>;

function makeIntake() {
  const identifiedParties: Array<Record<string, string>> = [
    { plaintiff: "Alpha LLC", defendant: "" },
    { plaintiff: "", defendant: "Beta LLC" },
  ];

  return {
    id: "intake-1",
    user_id: "demo-user",
    source_file_name: "case.docx",
    classified_type: "court_decision",
    document_language: "uk",
    jurisdiction: "UA",
    primary_party_role: "plaintiff",
    identified_parties: identifiedParties,
    subject_matter: "Debt recovery",
    financial_exposure_amount: 500000,
    financial_exposure_currency: "UAH",
    financial_exposure_type: "claim_amount",
    document_date: "2026-03-01",
    deadline_from_document: "2026-03-15",
    urgency_level: "high",
    risk_level_legal: "medium",
    risk_level_procedural: "high",
    risk_level_financial: "medium",
    detected_issues: [],
    classifier_confidence: 0.9,
    classifier_model: "gpt-test",
    raw_text_preview: "claim preview",
    created_at: "2026-03-08T10:00:00+00:00",
    usage: {
      id: "sub-1",
      user_id: "demo-user",
      plan: "PRO_PLUS",
      status: "active",
      analyses_used: 1,
      analyses_limit: null,
      docs_used: 0,
      docs_limit: null,
      current_period_start: null,
      current_period_end: null,
      created_at: null,
      updated_at: null,
    },
  };
}

function makePrecedentMap() {
  return {
    intake_id: "intake-1",
    query_used: "debt court_decision",
    groups: [
      {
        id: "group-1",
        pattern_type: "winning_pattern",
        pattern_description: "Strong pattern",
        precedent_ids: ["case-1", "case-2"],
        precedent_count: 2,
        pattern_strength: 0.84,
        counter_arguments: [],
        mitigation_strategy: "Tighten evidence",
        strategic_advantage: "Positive practice",
        vulnerability_to_appeal: "Low",
        created_at: "2026-03-08T10:05:00+00:00",
      },
    ],
    refs: [
      {
        id: "case-1",
        source: "manual_seed",
        decision_id: "vs-1",
        case_number: "123/100/25",
        court_name: "Supreme Court",
        decision_date: "2025-11-10",
        summary: "Pro claimant position.",
        pattern_type: "winning_pattern",
        relevance_score: 0.93,
      },
    ],
  };
}

function makeStrategy() {
  return {
    id: "strategy-1",
    intake_id: "intake-1",
    precedent_group_id: "group-1",
    immediate_actions: [{ action: "Collect evidence" }],
    procedural_roadmap: [{ step: 1, legal_action: "File appeal" }],
    evidence_strategy: [{ phase: "first_instance" }],
    negotiation_playbook: [{ counterparty_offer: "Compromise" }],
    risk_heat_map: [{ scenario: "best_case" }],
    critical_deadlines: [{ event: "appeal filing", due_date: "2026-03-15" }],
    confidence_score: 0.78,
    confidence_rationale: "Strong precedent baseline.",
    recommended_next_steps: "1) Collect evidence. 2) Prepare appeal.",
    created_at: "2026-03-08T10:10:00+00:00",
    updated_at: "2026-03-08T10:10:00+00:00",
  };
}

function makeGenerated() {
  return {
    document_id: "doc-1",
    strategy_blueprint_id: "strategy-1",
    doc_type: "appeal_complaint",
    title: "Appeal complaint",
    preview_text: "Short preview",
    generated_text: "Full text of appeal complaint.",
    used_ai: true,
    ai_model: "gpt-test",
    ai_error: "",
    quality_guard_applied: false,
    pre_generation_gate_checks: [],
    processual_validation_checks: [],
    case_law_refs: [],
    strategy_audit_id: "audit-1",
    created_at: "2026-03-08T10:15:00+00:00",
    usage: {
      id: "sub-1",
      user_id: "demo-user",
      plan: "PRO_PLUS",
      status: "active",
      analyses_used: 1,
      analyses_limit: null,
      docs_used: 1,
      docs_limit: null,
      current_period_start: null,
      current_period_end: null,
      created_at: null,
      updated_at: null,
    },
  };
}

function makeAudit() {
  return {
    id: "audit-1",
    document_id: "doc-1",
    strategy_blueprint_id: "strategy-1",
    precedent_citations: ["123/100/25", "123/101/25"],
    counter_argument_addresses: ["deadline miss", "insufficient evidence"],
    evidence_positioning_notes: "Strengthen evidence section.",
    procedure_optimization_notes: "File with procedural motion.",
    appeal_proofing_notes: "Position is resilient for appeal.",
    generated_at: "2026-03-08T10:16:00+00:00",
  };
}

function getInputById<T extends Element>(id: string): T {
  const element = document.querySelector(`#${id}`) as T | null;
  if (!element) {
    throw new Error(`Element not found by id: ${id}`);
  }
  return element;
}

describe("StrategyStudioPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getCasesMock.mockResolvedValue([]);
    analyzeIntakeMock.mockResolvedValue(makeIntake());
    analyzePrecedentMapMock.mockResolvedValue(makePrecedentMap());
    createStrategyBlueprintMock.mockResolvedValue(makeStrategy());
    generateWithStrategyMock.mockResolvedValue(makeGenerated());
    getStrategyAuditMock.mockResolvedValue(makeAudit());
    runJudgeSimulationMock.mockResolvedValue({
      id: "sim-1",
      strategy_blueprint_id: "strategy-1",
      document_id: "doc-1",
      verdict_probability: 0.7,
      judge_persona: "Balanced",
      key_vulnerabilities: [],
      strong_points: [],
      procedural_risks: [],
      suggested_corrections: [],
      judge_commentary: "ok",
      decision_rationale: "ok",
      created_at: "2026-03-08T10:16:00+00:00",
    });
    getExportDocxUrlMock.mockReturnValue("http://localhost/doc.docx");
  });

  it("shows intake validation before upload", async () => {
    const user = userEvent.setup();
    render(<StrategyStudioPage />);

    await user.click(screen.getByRole("button", { name: /strategy intake/i }));

    expect(screen.getByText(/оберіть файл для strategy intake/i)).toBeInTheDocument();
    expect(analyzeIntakeMock).not.toHaveBeenCalled();
  });

  it("runs the full strategy studio flow in sequence", async () => {
    const user = userEvent.setup();
    render(<StrategyStudioPage />);

    expect(screen.getByRole("button", { name: /precedent map/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /strategy blueprint/i })).toBeDisabled();
    expect(screen.getByRole("button", { name: /strategy audit/i })).toBeDisabled();

    const file = new File(["case materials"], "case.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    await user.upload(getInputById<HTMLInputElement>("strategy-file"), file);
    await user.click(screen.getByRole("button", { name: /strategy intake/i }));

    await waitFor(() => expect(analyzeIntakeMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Результат intake/i)).toBeInTheDocument();
    expect(screen.getByText("court_decision")).toBeInTheDocument();
    expect(screen.getByText("Debt recovery")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /precedent map/i }));
    await waitFor(() => expect(analyzePrecedentMapMock).toHaveBeenCalledTimes(1));
    expect(analyzePrecedentMapMock).toHaveBeenCalledWith("intake-1", { limit: 15 }, expect.any(String), expect.any(String));
    expect(screen.getAllByText("Precedent map").length).toBeGreaterThan(0);
    expect(screen.getByText("winning_pattern")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /strategy blueprint/i }));
    await waitFor(() => expect(createStrategyBlueprintMock).toHaveBeenCalledTimes(1));
    expect(screen.getAllByText("Strategy blueprint").length).toBeGreaterThan(0);
    expect(screen.getByText("1) Collect evidence. 2) Prepare appeal.")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/тип документа/i), "cassation_complaint");
    await user.click(screen.getByRole("button", { name: /згенерувати документ/i }));

    await waitFor(() => expect(generateWithStrategyMock).toHaveBeenCalledTimes(1));
    expect(generateWithStrategyMock.mock.calls[0]?.[0]).toMatchObject({
      strategy_blueprint_id: "strategy-1",
      doc_type: "cassation_complaint",
    });
    expect(screen.getByText(/Згенерований документ/i)).toBeInTheDocument();
    expect(screen.getByText("Full text of appeal complaint.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /strategy audit/i }));
    await waitFor(() => expect(getStrategyAuditMock).toHaveBeenCalledTimes(1));
    expect(getStrategyAuditMock).toHaveBeenCalledWith("doc-1", expect.any(String), expect.any(String));
    expect(screen.getAllByText("Strategy audit").length).toBeGreaterThan(0);
    expect(screen.getByText("Strengthen evidence section.")).toBeInTheDocument();
  });
});
