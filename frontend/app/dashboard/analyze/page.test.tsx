import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AnalyzePage from "./page";
import { analyzeIntake, getContractAnalysisHistory, processContractAnalysis } from "@/lib/api";

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ href, children, onClick, ...props }: any) => (
    <a
      href={href}
      {...props}
      onClick={(event) => {
        event.preventDefault();
        onClick?.(event);
      }}
    >
      {children}
    </a>
  ),
}));

jest.mock("@/lib/api", () => ({
  analyzeIntake: jest.fn(),
  getContractAnalysisHistory: jest.fn(),
  processContractAnalysis: jest.fn(),
}));

const analyzeIntakeMock = analyzeIntake as jest.MockedFunction<typeof analyzeIntake>;
const getContractAnalysisHistoryMock = getContractAnalysisHistory as jest.MockedFunction<typeof getContractAnalysisHistory>;
const processContractAnalysisMock = processContractAnalysis as jest.MockedFunction<typeof processContractAnalysis>;

function makeHistory() {
  return {
    total: 1,
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
    items: [
      {
        id: "analysis-1",
        user_id: "demo-user",
        file_name: "договір оренди.pdf",
        file_url: null,
        file_size: null,
        contract_type: "lease",
        risk_level: "medium",
        critical_risks: [],
        medium_risks: ["Плаваючий строк оплати"],
        ok_points: [],
        recommendations: [],
        summary: "Є пункт зі слабким строком оплати.",
        issues: ["Нечітке формулювання відповідальності"],
        ai_model: "gpt-test",
        tokens_used: 100,
        processing_time_ms: 250,
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
      },
    ],
  };
}

function makeIntake() {
  return {
    id: "intake-1",
    user_id: "demo-user",
    source_file_name: "pozov.docx",
    classified_type: "lawsuit_debt_loan",
    document_language: "uk",
    jurisdiction: "ua",
    primary_party_role: "plaintiff",
    identified_parties: [{ plaintiff: "ТОВ Альфа" }, { defendant: "ТОВ Бета" }],
    subject_matter: "Стягнення боргу за договором позики",
    financial_exposure_amount: 500000,
    financial_exposure_currency: "UAH",
    financial_exposure_type: "claim_amount",
    document_date: "2026-03-01",
    deadline_from_document: "2026-03-15",
    urgency_level: "high",
    risk_level_legal: "medium",
    risk_level_procedural: "high",
    risk_level_financial: "medium",
    detected_issues: [
      {
        issue_type: "missing_evidence",
        severity: "high",
        description: "Не вистачає підтвердження вручення претензії.",
        impact: "Може послабити доказову позицію.",
      },
    ],
    classifier_confidence: 0.87,
    classifier_model: "gpt-test",
    raw_text_preview: "Позовна заява про стягнення боргу...",
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

describe("AnalyzePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    getContractAnalysisHistoryMock.mockResolvedValue(makeHistory());
    analyzeIntakeMock.mockResolvedValue(makeIntake());
    processContractAnalysisMock.mockResolvedValue(makeHistory().items[0]);
  });

  it("uploads file and renders intake analysis", async () => {
    const user = userEvent.setup();
    render(<AnalyzePage />);

    const file = new File(["Позовна заява"], "pozov.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    await user.upload(screen.getByLabelText("Файл документа"), file);
    await user.click(screen.getByRole("button", { name: "Запустити intake-аналіз" }));

    await waitFor(() => expect(analyzeIntakeMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Результат intake-аналізу")).toBeInTheDocument();
    expect(screen.getByText("lawsuit_debt_loan")).toBeInTheDocument();
    expect(screen.getByText("Стягнення боргу за договором позики")).toBeInTheDocument();
    expect(screen.getByText("Не вистачає підтвердження вручення претензії.")).toBeInTheDocument();
  });

  it("stores case-law seed from intake result", async () => {
    const user = userEvent.setup();
    render(<AnalyzePage />);

    const file = new File(["Позовна заява"], "pozov.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    await user.upload(screen.getByLabelText("Файл документа"), file);
    await user.click(screen.getByRole("button", { name: "Запустити intake-аналіз" }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: "Передати в судову практику" })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("link", { name: "Передати в судову практику" }));

    const stored = JSON.parse(localStorage.getItem("legal_ai_case_law_seed_v1") || "{}");
    expect(stored.query).toContain("Стягнення боргу за договором позики");
    expect(stored.query).toContain("lawsuit_debt_loan");
  });

  it("runs quick contract analysis and refreshes history", async () => {
    const user = userEvent.setup();
    render(<AnalyzePage />);

    await user.type(screen.getByLabelText("Назва файлу"), "dogovir_orendy_2026.pdf");
    await user.type(
      screen.getByLabelText("Текст договору"),
      "Це текст договору оренди з умовами оплати та відповідальності сторін."
    );
    await user.click(screen.getByRole("button", { name: "Швидкий аналіз" }));

    await waitFor(() => expect(processContractAnalysisMock).toHaveBeenCalledTimes(1));
    expect(processContractAnalysisMock.mock.calls[0]?.[0]).toMatchObject({
      file_name: "dogovir_orendy_2026.pdf",
    });
    expect(screen.getByText("Останній quick-аналіз")).toBeInTheDocument();
    expect(screen.getAllByText("Є пункт зі слабким строком оплати.").length).toBeGreaterThan(0);
    expect(getContractAnalysisHistoryMock).toHaveBeenCalledTimes(2);
  });
});
