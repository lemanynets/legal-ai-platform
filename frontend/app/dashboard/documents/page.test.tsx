import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import DocumentsHistoryPage from "./page";
import {
  cloneDocument,
  deleteDocument,
  exportDocument,
  getCases,
  getDocumentDetail,
  getDocumentsHistory,
  getECourtCourts,
  submitToECourt,
  updateDocument,
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  bulkDeleteDocuments: jest.fn(),
  cloneDocument: jest.fn(),
  deleteDocument: jest.fn(),
  exportDocument: jest.fn(),
  getDocumentDetail: jest.fn(),
  getDocumentsHistory: jest.fn(),
  updateDocument: jest.fn(),
  getCases: jest.fn(),
  submitToECourt: jest.fn(),
  getECourtCourts: jest.fn(),
}));

const getDocumentsHistoryMock = getDocumentsHistory as jest.MockedFunction<typeof getDocumentsHistory>;
const getCasesMock = getCases as jest.MockedFunction<typeof getCases>;
const exportDocumentMock = exportDocument as jest.MockedFunction<typeof exportDocument>;
const getDocumentDetailMock = getDocumentDetail as jest.MockedFunction<typeof getDocumentDetail>;
const updateDocumentMock = updateDocument as jest.MockedFunction<typeof updateDocument>;
const deleteDocumentMock = deleteDocument as jest.MockedFunction<typeof deleteDocument>;
const cloneDocumentMock = cloneDocument as jest.MockedFunction<typeof cloneDocument>;
const getECourtCourtsMock = getECourtCourts as jest.MockedFunction<typeof getECourtCourts>;
const submitToECourtMock = submitToECourt as jest.MockedFunction<typeof submitToECourt>;

describe("DocumentsHistoryPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    global.confirm = jest.fn(() => true);
    global.alert = jest.fn();
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      value: jest.fn(() => "blob:test-url"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      value: jest.fn(),
    });
    Object.defineProperty(HTMLAnchorElement.prototype, "click", {
      writable: true,
      value: jest.fn(),
    });

    getCasesMock.mockResolvedValue([
      {
        id: "case-1",
        user_id: "demo-user",
        title: "Case A",
        description: null,
        case_number: "711/9613/2012",
        status: "active",
        created_at: "2026-02-18T10:00:00Z",
        updated_at: "2026-02-18T10:00:00Z",
      },
    ]);
    (getDocumentsHistoryMock as any).mockResolvedValue({
      total: 2,
      page: 1,
      page_size: 12,
      pages: 1,
      items: [
        {
          id: "doc-1",
          title: "Debt claim",
          document_type: "lawsuit_debt_loan",
          document_category: "judicial",
          case_id: null,
          generated_text: "Generated text 1",
          preview_text: "Preview text 1",
          ai_model: "gpt-4",
          used_ai: true,
          has_docx_export: false,
          has_pdf_export: false,
          last_exported_at: null,
          e_court_ready: true,
          filing_blockers: [],
          created_at: "2026-02-18T10:00:00Z",
        },
        {
          id: "doc-2",
          title: "Contract",
          document_type: "contract_services",
          document_category: "contract",
          case_id: null,
          generated_text: "Generated text 2",
          preview_text: "Preview text 2",
          ai_model: null,
          used_ai: false,
          has_docx_export: false,
          has_pdf_export: false,
          last_exported_at: null,
          e_court_ready: true,
          filing_blockers: [],
          created_at: "2026-02-17T10:00:00Z",
        },
      ],
    });
    exportDocumentMock.mockResolvedValue(new Blob(["doc"], { type: "application/octet-stream" }));
    (getDocumentDetailMock as any).mockResolvedValue({
      id: "doc-1",
      title: "Debt claim",
      document_type: "lawsuit_debt_loan",
      document_category: "judicial",
      case_id: "case-1",
      generated_text: "Original generated text",
      prompt_system: "system",
      prompt_user: "user",
      calculations: {},
      used_ai: true,
      ai_model: "gpt-4",
      ai_error: "",
      quality_guard_applied: false,
      pre_generation_gate_checks: [],
      processual_validation_checks: [],
      case_law_refs: [],
      usage: {
        id: "sub-1",
        user_id: "demo-user",
        plan: "PRO_PLUS",
        status: "active",
        analyses_used: 0,
        analyses_limit: null,
        docs_used: 0,
        docs_limit: null,
        current_period_start: null,
        current_period_end: null,
        created_at: null,
        updated_at: null,
      },
      created_at: "2026-02-18T10:00:00Z",
    });
    (updateDocumentMock as any).mockResolvedValue({
      id: "doc-1",
      title: "Debt claim",
      document_type: "lawsuit_debt_loan",
      document_category: "judicial",
      case_id: "case-1",
      generated_text: "Updated text",
      preview_text: "Updated text",
      ai_model: "gpt-4",
      used_ai: true,
      has_docx_export: false,
      has_pdf_export: false,
      last_exported_at: null,
      e_court_ready: true,
      filing_blockers: [],
      created_at: "2026-02-18T10:00:00Z",
    });
    (cloneDocumentMock as any).mockResolvedValue({
      id: "doc-3",
      title: "Debt claim copy",
      document_type: "lawsuit_debt_loan",
      document_category: "judicial",
      case_id: null,
      generated_text: "Generated text copy",
      preview_text: "Preview copy",
      ai_model: "gpt-4",
      used_ai: true,
      has_docx_export: false,
      has_pdf_export: false,
      last_exported_at: null,
      e_court_ready: true,
      filing_blockers: [],
      created_at: "2026-02-18T12:00:00Z",
    });
    deleteDocumentMock.mockResolvedValue({ status: "deleted", id: "doc-1" });
    (getECourtCourtsMock as any).mockResolvedValue({ courts: ["Київський апеляційний суд"] });
    (submitToECourtMock as any).mockResolvedValue({
      status: "submitted",
      submission_id: "ecourt-submission-1",
      provider: "mock",
      route: null,
      accepted_at: null,
      message: "success",
    });
  });

  it("loads history and cases on page mount", async () => {
    render(<DocumentsHistoryPage />);

    await waitFor(() => expect(getCasesMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalled());
    expect(screen.getByText("Debt claim")).toBeInTheDocument();
    expect(screen.getByText("Contract")).toBeInTheDocument();
  });

  it("exports a document as DOCX", async () => {
    render(<DocumentsHistoryPage />);
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalled());

    fireEvent.click(screen.getAllByRole("button", { name: "DOCX" })[0]);
    await waitFor(() => expect(exportDocumentMock).toHaveBeenCalledTimes(1));
    expect(exportDocumentMock.mock.calls[0]?.[0]).toBe("doc-1");
    expect(exportDocumentMock.mock.calls[0]?.[1]).toBe("docx");
  });

  it("opens edit modal and saves updated content", async () => {
    const { container } = render(<DocumentsHistoryPage />);
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalled());

    const editButton = container.querySelector(".action-utility-buttons .btn-icon-link") as HTMLButtonElement;
    fireEvent.click(editButton);

    await waitFor(() => expect(getDocumentDetailMock).toHaveBeenCalledWith("doc-1", "", "demo-user"));

    const textarea = container.querySelector(".luxury-textarea") as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: "Updated generated text" } });

    const saveButton = Array.from(container.querySelectorAll(".modal-footer .btn")).find((button) =>
      (button as HTMLButtonElement).className.includes("btn-primary")
    ) as HTMLButtonElement;
    fireEvent.click(saveButton);

    await waitFor(() => expect(updateDocumentMock).toHaveBeenCalledTimes(1));
    expect(updateDocumentMock.mock.calls[0]?.[0]).toBe("doc-1");
    expect(updateDocumentMock.mock.calls[0]?.[1]).toBe("Updated generated text");
  });
});
