import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AnalyzePage from "./page";
import { analyzeIntake, getCases, getContractAnalysisHistory, processContractAnalysis } from "@/lib/api";

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
  getCases: jest.fn(),
  getContractAnalysisHistory: jest.fn(),
  processContractAnalysis: jest.fn(),
  createCase: jest.fn(),
  getCase: jest.fn(),
  analyzeGdprCompliance: jest.fn(),
}));

const analyzeIntakeMock = analyzeIntake as jest.MockedFunction<typeof analyzeIntake>;
const getCasesMock = getCases as jest.MockedFunction<typeof getCases>;
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
        file_name: "contract.pdf",
        file_url: null,
        file_size: null,
        contract_type: "lease",
        risk_level: "medium",
        critical_risks: [],
        medium_risks: [],
        ok_points: [],
        recommendations: [],
        summary: "Summary from quick analysis.",
        issues: [],
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
  const identifiedParties: Array<Record<string, string>> = [
    { plaintiff: "Alpha LLC", defendant: "" },
    { plaintiff: "", defendant: "Beta LLC" },
  ];

  return {
    id: "intake-1",
    user_id: "demo-user",
    source_file_name: "claim.docx",
    classified_type: "lawsuit_debt_loan",
    document_language: "uk",
    jurisdiction: "ua",
    primary_party_role: "plaintiff",
    identified_parties: identifiedParties,
    subject_matter: "Debt recovery under loan agreement",
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
        description: "No proof of claim notice service.",
        impact: "May weaken procedural position.",
      },
    ],
    classifier_confidence: 0.87,
    classifier_model: "gpt-test",
    raw_text_preview: "Claim text preview...",
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

function getInputById<T extends Element>(id: string): T {
  const element = document.querySelector(`#${id}`) as T | null;
  if (!element) {
    throw new Error(`Element not found by id: ${id}`);
  }
  return element;
}

describe("AnalyzePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    getCasesMock.mockResolvedValue([]);
    getContractAnalysisHistoryMock.mockResolvedValue(makeHistory());
    analyzeIntakeMock.mockResolvedValue(makeIntake());
    processContractAnalysisMock.mockResolvedValue(makeHistory().items[0]);
  });

  it("uploads file and renders intake analysis", async () => {
    const user = userEvent.setup();
    render(<AnalyzePage />);

    const file = new File(["claim body"], "claim.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    await user.upload(getInputById<HTMLInputElement>("document-files"), file);
    await user.click(screen.getByRole("button", { name: /intake/i }));

    await waitFor(() => expect(analyzeIntakeMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Результат intake-аналізу/i)).toBeInTheDocument();
    expect(screen.getByText("lawsuit_debt_loan")).toBeInTheDocument();
    expect(screen.getByText("Debt recovery under loan agreement")).toBeInTheDocument();
    expect(screen.getByText("No proof of claim notice service.")).toBeInTheDocument();
  });

  it("stores case-law seed from intake result", async () => {
    const user = userEvent.setup();
    render(<AnalyzePage />);

    const file = new File(["claim body"], "claim.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });

    await user.upload(getInputById<HTMLInputElement>("document-files"), file);
    await user.click(screen.getByRole("button", { name: /intake/i }));

    await waitFor(() => {
      expect(screen.getByRole("link", { name: /судову практику/i })).toBeInTheDocument();
    });
    await user.click(screen.getByRole("link", { name: /судову практику/i }));

    const stored = JSON.parse(localStorage.getItem("legal_ai_case_law_seed_v1") || "{}");
    expect(stored.query).toContain("Debt recovery under loan agreement");
    expect(stored.query).toContain("lawsuit_debt_loan");
  });

  it("runs quick contract analysis and refreshes history", async () => {
    const user = userEvent.setup();
    render(<AnalyzePage />);

    await user.type(getInputById<HTMLInputElement>("quick-file-name"), "contract_2026.pdf");
    await user.type(
      getInputById<HTMLTextAreaElement>("quick-contract-text"),
      "This is a long contract text with payment and liability clauses."
    );
    await user.click(screen.getByRole("button", { name: /швидкий аналіз/i }));

    await waitFor(() => expect(processContractAnalysisMock).toHaveBeenCalledTimes(1));
    expect(processContractAnalysisMock.mock.calls[0]?.[0]).toMatchObject({
      file_name: "contract_2026.pdf",
    });
    expect(screen.getByText(/Останній quick-аналіз/i)).toBeInTheDocument();
    expect(screen.getAllByText("Summary from quick analysis.").length).toBeGreaterThan(0);
    expect(getContractAnalysisHistoryMock).toHaveBeenCalledTimes(2);
  });
});
