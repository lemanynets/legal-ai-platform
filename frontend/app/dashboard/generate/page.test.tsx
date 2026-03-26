import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import GeneratePage from "./page";
import {
  generateDocument,
  getCaseLawDigest,
  getCaseLawDigestDetail,
  getCaseLawDigestHistory,
  getDocumentFormSchema,
  getDocumentTypes,
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  getDocumentTypes: jest.fn(),
  getDocumentFormSchema: jest.fn(),
  generateDocument: jest.fn(),
  getCaseLawDigest: jest.fn(),
  getCaseLawDigestHistory: jest.fn(),
  getCaseLawDigestDetail: jest.fn(),
}));

const getDocumentTypesMock = getDocumentTypes as jest.MockedFunction<typeof getDocumentTypes>;
const getDocumentFormSchemaMock = getDocumentFormSchema as jest.MockedFunction<typeof getDocumentFormSchema>;
const generateDocumentMock = generateDocument as jest.MockedFunction<typeof generateDocument>;
const getCaseLawDigestMock = getCaseLawDigest as jest.MockedFunction<typeof getCaseLawDigest>;
const getCaseLawDigestHistoryMock = getCaseLawDigestHistory as jest.MockedFunction<typeof getCaseLawDigestHistory>;
const getCaseLawDigestDetailMock = getCaseLawDigestDetail as jest.MockedFunction<typeof getCaseLawDigestDetail>;

describe("GeneratePage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();

    getDocumentTypesMock.mockResolvedValue([
      { doc_type: "lawsuit_debt_loan", title: "Debt claim", category: "judicial", procedure: "civil" },
    ]);
    getDocumentFormSchemaMock.mockResolvedValue([
      { key: "plaintiff_name", type: "text", required: true },
      { key: "claim_requests", type: "array", required: false },
    ]);
    generateDocumentMock.mockResolvedValue({
      document_id: "doc-1",
      created_at: "2026-02-21T10:00:00Z",
      doc_type: "lawsuit_debt_loan",
      title: "Debt claim",
      preview_text: "Preview",
      generated_text: "Generated",
      prompt_system: "system",
      prompt_user: "user",
      calculations: {},
      used_ai: true,
      ai_model: "gpt-4o-mini",
      ai_error: "",
      quality_guard_applied: false,
      pre_generation_gate_checks: [{ code: "required_fields", status: "pass", message: "All required fields are present." }],
      processual_validation_checks: [{ code: "structure", status: "pass", message: "Structure is valid." }],
      case_law_refs: [
        {
          id: "cl-1",
          source: "opendatabot",
          decision_id: "d-001",
          case_number: "111/11/26",
          court_name: "Supreme Court",
          court_type: "civil",
          decision_date: "2026-02-20",
          summary: "Digest summary",
          relevance_score: 0.91,
        },
      ],
      usage: {
        id: "sub-1",
        user_id: "demo-user",
        plan: "PRO",
        status: "active",
        analyses_used: 0,
        analyses_limit: null,
        docs_used: 1,
        docs_limit: null,
        current_period_start: null,
        current_period_end: null,
        created_at: null,
        updated_at: null,
      },
    });
    getCaseLawDigestMock.mockResolvedValue({
      digest_id: null,
      saved: false,
      title: null,
      days: 365,
      limit: 5,
      total: 1,
      only_supreme: true,
      court_type: "civil",
      source: ["opendatabot"],
      generated_at: "2026-02-21T10:05:00Z",
      items: [
        {
          id: "cl-1",
          source: "opendatabot",
          decision_id: "d-001",
          court_name: "Supreme Court",
          court_type: "civil",
          decision_date: "2026-02-20",
          case_number: "111/11/26",
          subject_categories: ["debt"],
          summary: "Digest summary",
          legal_positions: {},
          prompt_snippet: "[opendatabot] case 111/11/26.",
        },
      ],
    });
    getCaseLawDigestHistoryMock.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 50,
      pages: 1,
      items: [
        {
          id: "digest-1",
          title: "Weekly digest",
          days: 365,
          limit: 5,
          total: 1,
          item_count: 1,
          only_supreme: true,
          court_type: "civil",
          source: ["opendatabot"],
          created_at: "2026-02-21T10:05:00Z",
        },
      ],
    });
    getCaseLawDigestDetailMock.mockResolvedValue({
      digest_id: "digest-1",
      saved: true,
      title: "Weekly digest",
      days: 365,
      limit: 5,
      total: 1,
      only_supreme: true,
      court_type: "civil",
      source: ["opendatabot"],
      generated_at: "2026-02-21T10:05:00Z",
      items: [
        {
          id: "cl-1",
          source: "opendatabot",
          decision_id: "d-001",
          court_name: "Supreme Court",
          court_type: "civil",
          decision_date: "2026-02-20",
          case_number: "111/11/26",
          subject_categories: ["debt"],
          summary: "Digest summary",
          legal_positions: {},
          prompt_snippet: "[opendatabot] case 111/11/26.",
        },
      ],
    });
  });

  it("restores stored prompt context from previous steps", async () => {
    localStorage.setItem("legal_ai_prompt_context", "stored precedent context");

    render(<GeneratePage />);

    await waitFor(() => expect(getDocumentTypesMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Контекст із Судової практики підхоплено в генерацію.")).toBeInTheDocument();
    expect((screen.getByLabelText("Additional legal context (from Case Law)") as HTMLTextAreaElement).value).toBe(
      "stored precedent context"
    );
  });

  it("blocks generation when required fields are missing", async () => {
    const user = userEvent.setup();
    render(<GeneratePage />);

    await waitFor(() => expect(getDocumentTypesMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentFormSchemaMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Згенерувати" }));

    expect(screen.getByText("Помилка: Заповніть обов'язкові поля: plaintiff_name")).toBeInTheDocument();
    expect(generateDocumentMock).not.toHaveBeenCalled();
  });

  it("submits generation with extra context and digest options", async () => {
    const user = userEvent.setup();
    render(<GeneratePage />);

    await waitFor(() => expect(getDocumentTypesMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentFormSchemaMock).toHaveBeenCalledTimes(1));

    await user.type(screen.getByLabelText("plaintiff_name"), "Ivan");
    await user.type(screen.getByLabelText("Additional legal context (from Case Law)"), "custom context");
    await user.click(screen.getByRole("button", { name: "Згенерувати" }));

    await waitFor(() => expect(generateDocumentMock).toHaveBeenCalledTimes(1));
    expect(generateDocumentMock.mock.calls[0]?.[0]).toBe("lawsuit_debt_loan");
    expect(generateDocumentMock.mock.calls[0]?.[1]).toMatchObject({ plaintiff_name: "Ivan" });
    expect(generateDocumentMock.mock.calls[0]?.[5]).toMatchObject({
      extra_prompt_context: "custom context",
      include_digest: true,
      digest_days: 365,
      digest_limit: 5,
      digest_only_supreme: true,
    });
    expect(screen.getByText("Документ згенеровано: Debt claim.")).toBeInTheDocument();
    expect(screen.getByText("Практика, яку підключено")).toBeInTheDocument();
  });

  it("loads digest into context", async () => {
    const user = userEvent.setup();
    render(<GeneratePage />);

    await waitFor(() => expect(getDocumentTypesMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentFormSchemaMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Завантажити свіжий digest" }));
    await waitFor(() => expect(getCaseLawDigestMock).toHaveBeenCalledTimes(1));

    const area = screen.getByLabelText("Additional legal context (from Case Law)") as HTMLTextAreaElement;
    expect(area.value).toContain("case 111/11/26");
  });

  it("loads selected saved digest into context", async () => {
    const user = userEvent.setup();
    render(<GeneratePage />);

    await waitFor(() => expect(getDocumentTypesMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getCaseLawDigestHistoryMock).toHaveBeenCalled());

    await user.selectOptions(screen.getByLabelText("Saved digest"), "digest-1");
    await user.click(screen.getByRole("button", { name: "Додати saved digest" }));
    await waitFor(() => expect(getCaseLawDigestDetailMock).toHaveBeenCalledTimes(1));

    const area = screen.getByLabelText("Additional legal context (from Case Law)") as HTMLTextAreaElement;
    expect(area.value).toContain("Saved case-law digest");
    expect(area.value).toContain("case 111/11/26");
  });

  it("submits generation with selected saved digest id when enabled", async () => {
    const user = userEvent.setup();
    render(<GeneratePage />);

    await waitFor(() => expect(getDocumentTypesMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getCaseLawDigestHistoryMock).toHaveBeenCalled());
    await waitFor(() => expect(getDocumentFormSchemaMock).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByLabelText("plaintiff_name")).toBeInTheDocument());

    await user.type(screen.getByLabelText("plaintiff_name"), "Olena");
    await user.selectOptions(screen.getByLabelText("Saved digest"), "digest-1");
    await user.selectOptions(screen.getByLabelText("Use selected saved digest in generation"), "true");
    await user.click(screen.getByRole("button", { name: "Згенерувати" }));

    await waitFor(() => expect(generateDocumentMock).toHaveBeenCalledTimes(1));
    expect(generateDocumentMock.mock.calls[0]?.[5]).toMatchObject({
      saved_digest_id: "digest-1",
      include_digest: true,
    });
  });
});
