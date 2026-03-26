import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import StrategyStudioPage from "./page";
import {
  analyzeIntake,
  analyzePrecedentMap,
  createStrategyBlueprint,
  generateWithStrategy,
  getStrategyAudit,
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  analyzeIntake: jest.fn(),
  analyzePrecedentMap: jest.fn(),
  createStrategyBlueprint: jest.fn(),
  generateWithStrategy: jest.fn(),
  getStrategyAudit: jest.fn(),
}));

const analyzeIntakeMock = analyzeIntake as jest.MockedFunction<typeof analyzeIntake>;
const analyzePrecedentMapMock = analyzePrecedentMap as jest.MockedFunction<typeof analyzePrecedentMap>;
const createStrategyBlueprintMock = createStrategyBlueprint as jest.MockedFunction<typeof createStrategyBlueprint>;
const generateWithStrategyMock = generateWithStrategy as jest.MockedFunction<typeof generateWithStrategy>;
const getStrategyAuditMock = getStrategyAudit as jest.MockedFunction<typeof getStrategyAudit>;

function makeIntake() {
  return {
    id: "intake-1",
    user_id: "demo-user",
    source_file_name: "sprava.docx",
    classified_type: "court_decision",
    document_language: "uk",
    jurisdiction: "UA",
    primary_party_role: "plaintiff",
    identified_parties: [{ plaintiff: "ТОВ Альфа" }, { defendant: "ТОВ Бета" }],
    subject_matter: "Стягнення боргу",
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
    raw_text_preview: "Позовна заява...",
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
    query_used: "Стягнення боргу court_decision",
    groups: [
      {
        id: "group-1",
        pattern_type: "winning_pattern",
        pattern_description: "Сильний патерн",
        precedent_ids: ["case-1", "case-2"],
        precedent_count: 2,
        pattern_strength: 0.84,
        counter_arguments: [],
        mitigation_strategy: "Підсилити доказову базу",
        strategic_advantage: "Позитивна практика",
        vulnerability_to_appeal: "Низька",
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
        summary: "Позиція на користь позивача.",
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
    immediate_actions: [{ action: "Зібрати додаткові докази" }],
    procedural_roadmap: [{ step: 1, legal_action: "Подати апеляцію" }],
    evidence_strategy: [{ phase: "Перша інстанція" }],
    negotiation_playbook: [{ counterparty_offer: "Компроміс" }],
    risk_heat_map: [{ scenario: "Повний виграш" }],
    critical_deadlines: [{ event: "Подання апеляції", due_date: "2026-03-15" }],
    confidence_score: 0.78,
    confidence_rationale: "Є сильна практика.",
    recommended_next_steps: "1) Зібрати докази. 2) Готувати апеляцію.",
    created_at: "2026-03-08T10:10:00+00:00",
    updated_at: "2026-03-08T10:10:00+00:00",
  };
}

function makeGenerated() {
  return {
    document_id: "doc-1",
    strategy_blueprint_id: "strategy-1",
    doc_type: "appeal_complaint",
    title: "Апеляційна скарга",
    preview_text: "Короткий preview",
    generated_text: "Повний текст апеляційної скарги.",
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
    counter_argument_addresses: ["Пропуск строку", "Недостатність доказів"],
    evidence_positioning_notes: "Посилити блок доказів.",
    procedure_optimization_notes: "Подавати з процесуальним клопотанням.",
    appeal_proofing_notes: "Позиція стійка до апеляційних ризиків.",
    generated_at: "2026-03-08T10:16:00+00:00",
  };
}

describe("StrategyStudioPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    analyzeIntakeMock.mockResolvedValue(makeIntake());
    analyzePrecedentMapMock.mockResolvedValue(makePrecedentMap());
    createStrategyBlueprintMock.mockResolvedValue(makeStrategy());
    generateWithStrategyMock.mockResolvedValue(makeGenerated());
    getStrategyAuditMock.mockResolvedValue(makeAudit());
  });

  it("shows intake validation before upload", async () => {
    const user = userEvent.setup();
    render(<StrategyStudioPage />);

    await user.click(screen.getByRole("button", { name: "Запустити strategy intake" }));

    expect(screen.getByText("Помилка: Оберіть файл для strategy intake.")).toBeInTheDocument();
    expect(analyzeIntakeMock).not.toHaveBeenCalled();
  });

  it("runs the full strategy studio flow in sequence", async () => {
    const user = userEvent.setup();
    render(<StrategyStudioPage />);

    expect(screen.getByRole("button", { name: "Побудувати precedent map" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Створити strategy blueprint" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Згенерувати документ" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Завантажити strategy audit" })).toBeDisabled();

    const file = new File(["Матеріали справи"], "sprava.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    await user.upload(screen.getByLabelText("Файл для strategy intake"), file);
    await user.click(screen.getByRole("button", { name: "Запустити strategy intake" }));

    await waitFor(() => expect(analyzeIntakeMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Результат intake")).toBeInTheDocument();
    expect(screen.getByText("court_decision")).toBeInTheDocument();
    expect(screen.getByText("Стягнення боргу")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Побудувати precedent map" }));
    await waitFor(() => expect(analyzePrecedentMapMock).toHaveBeenCalledTimes(1));
    expect(analyzePrecedentMapMock).toHaveBeenCalledWith("intake-1", { limit: 15 }, expect.any(String), expect.any(String));
    expect(screen.getAllByText("Precedent map").length).toBeGreaterThan(0);
    expect(screen.getByText("winning_pattern")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Створити strategy blueprint" }));
    await waitFor(() => expect(createStrategyBlueprintMock).toHaveBeenCalledTimes(1));
    expect(screen.getAllByText("Strategy blueprint").length).toBeGreaterThan(0);
    expect(screen.getByText("1) Зібрати докази. 2) Готувати апеляцію.")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Тип документа для генерації"), "cassation_complaint");
    await user.click(screen.getByRole("button", { name: "Згенерувати документ" }));

    await waitFor(() => expect(generateWithStrategyMock).toHaveBeenCalledTimes(1));
    expect(generateWithStrategyMock.mock.calls[0]?.[0]).toMatchObject({
      strategy_blueprint_id: "strategy-1",
      doc_type: "cassation_complaint",
    });
    expect(screen.getByText("Згенерований документ")).toBeInTheDocument();
    expect(screen.getByText("Повний текст апеляційної скарги.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Завантажити strategy audit" }));

    await waitFor(() => expect(getStrategyAuditMock).toHaveBeenCalledTimes(1));
    expect(getStrategyAuditMock).toHaveBeenCalledWith("doc-1", expect.any(String), expect.any(String));
    expect(screen.getAllByText("Strategy audit").length).toBeGreaterThan(0);
    expect(screen.getByText("Посилити блок доказів.")).toBeInTheDocument();
    expect(screen.getByText("Подавати з процесуальним клопотанням.")).toBeInTheDocument();
  });
});
