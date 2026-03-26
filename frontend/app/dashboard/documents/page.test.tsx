import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import DocumentsPage from "./page";
import {
  bulkRepairProcessualDocuments,
  bulkDeleteDocuments,
  cloneDocument,
  getECourtHistory,
  getDocumentDetail,
  getDocumentProcessualCheck,
  getDocumentVersionDetail,
  getDocumentVersionDiff,
  getDocumentVersions,
  getDocumentsHistory,
  repairProcessualDocument,
  restoreDocumentVersion,
  submitToECourt
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  getDocumentsHistory: jest.fn(),
  getDocumentDetail: jest.fn(),
  getDocumentVersionDetail: jest.fn(),
  getDocumentVersionDiff: jest.fn(),
  getDocumentVersions: jest.fn(),
  getDocumentProcessualCheck: jest.fn(),
  bulkRepairProcessualDocuments: jest.fn(),
  repairProcessualDocument: jest.fn(),
  restoreDocumentVersion: jest.fn(),
  updateDocument: jest.fn(),
  exportDocument: jest.fn(),
  cloneDocument: jest.fn(),
  deleteDocument: jest.fn(),
  bulkDeleteDocuments: jest.fn(),
  exportDocumentsHistory: jest.fn(),
  submitToECourt: jest.fn(),
  getECourtHistory: jest.fn()
}));

const getDocumentsHistoryMock = getDocumentsHistory as jest.MockedFunction<typeof getDocumentsHistory>;
const cloneDocumentMock = cloneDocument as jest.MockedFunction<typeof cloneDocument>;
const bulkDeleteDocumentsMock = bulkDeleteDocuments as jest.MockedFunction<typeof bulkDeleteDocuments>;
const getDocumentDetailMock = getDocumentDetail as jest.MockedFunction<typeof getDocumentDetail>;
const getDocumentVersionDetailMock = getDocumentVersionDetail as jest.MockedFunction<typeof getDocumentVersionDetail>;
const getDocumentVersionDiffMock = getDocumentVersionDiff as jest.MockedFunction<typeof getDocumentVersionDiff>;
const getDocumentVersionsMock = getDocumentVersions as jest.MockedFunction<typeof getDocumentVersions>;
const getDocumentProcessualCheckMock = getDocumentProcessualCheck as jest.MockedFunction<typeof getDocumentProcessualCheck>;
const bulkRepairProcessualDocumentsMock = bulkRepairProcessualDocuments as jest.MockedFunction<typeof bulkRepairProcessualDocuments>;
const repairProcessualDocumentMock = repairProcessualDocument as jest.MockedFunction<typeof repairProcessualDocument>;
const restoreDocumentVersionMock = restoreDocumentVersion as jest.MockedFunction<typeof restoreDocumentVersion>;
const submitToECourtMock = submitToECourt as jest.MockedFunction<typeof submitToECourt>;
const getECourtHistoryMock = getECourtHistory as jest.MockedFunction<typeof getECourtHistory>;

function makeHistoryResponse(
  overrides: Partial<Awaited<ReturnType<typeof getDocumentsHistory>>> = {}
): Awaited<ReturnType<typeof getDocumentsHistory>> {
  return {
    user_id: "demo-user",
    total: 1,
    page: 1,
    page_size: 10,
    pages: 1,
    sort_by: "created_at",
    sort_dir: "desc",
    query: null,
    doc_type: null,
    has_docx_export: null,
    has_pdf_export: null,
    items: [
      {
        id: "doc-1",
        document_type: "lawsuit_debt_loan",
        document_category: "judicial",
        generated_text: "Generated text",
        preview_text: "Preview text",
        ai_model: "gpt-4o-mini",
        used_ai: true,
        has_docx_export: false,
        has_pdf_export: false,
        last_exported_at: null,
        e_court_ready: true,
        filing_blockers: [],
        created_at: "2026-02-18T10:00:00Z"
      }
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
      created_at: "2026-02-18T09:00:00Z",
      updated_at: "2026-02-18T09:00:00Z"
    },
    ...overrides
  };
}

describe("DocumentsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getECourtHistoryMock.mockResolvedValue({
      total: 0,
      page: 1,
      page_size: 10,
      pages: 1,
      items: []
    });
    submitToECourtMock.mockResolvedValue({
      status: "submitted",
      submission: {
        id: "sub-1",
        document_id: "doc-1",
        provider: "court_gov_ua",
        external_submission_id: "EC-20260222-abc123",
        status: "submitted",
        court_name: "Kyiv district court",
        signer_method: "diia_sign",
        tracking_url: "https://court.gov.ua/tracking/EC-20260222-abc123",
        error_message: null,
        submitted_at: "2026-02-22T10:00:00Z",
        updated_at: "2026-02-22T10:00:00Z"
      }
    });
    repairProcessualDocumentMock.mockResolvedValue({
      status: "repaired",
      id: "doc-1",
      repaired: true,
      has_docx_export: false,
      has_pdf_export: false,
      pre_generation_gate_checks: [],
      processual_validation_checks: []
    });
    getDocumentProcessualCheckMock.mockResolvedValue({
      status: "ok",
      id: "doc-1",
      is_valid: true,
      blockers: [],
      pre_generation_gate_checks: [],
      processual_validation_checks: []
    });
    bulkRepairProcessualDocumentsMock.mockResolvedValue({
      status: "completed",
      requested: 1,
      processed: 1,
      repaired: 1,
      missing_ids: [],
      items: [{ id: "doc-1", status: "repaired", repaired: true, is_valid: true, blockers: [] }]
    });
  });

  it("loads history and paginates with server calls", async () => {
    getDocumentsHistoryMock
      .mockResolvedValueOnce(makeHistoryResponse({ pages: 2, page: 1 }))
      .mockResolvedValueOnce(
        makeHistoryResponse({
          page: 2,
          pages: 2,
          items: [
            {
              id: "doc-2",
              document_type: "contract_services",
              document_category: "contract",
              generated_text: "Second row text",
              preview_text: "Second preview",
              ai_model: null,
              used_ai: false,
              has_docx_export: false,
              has_pdf_export: false,
              last_exported_at: null,
              e_court_ready: true,
              filing_blockers: [],
              created_at: "2026-02-18T11:00:00Z"
            }
          ]
        })
      );
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));
    expect(getDocumentsHistoryMock.mock.calls[0]?.[0]).toMatchObject({ page: 1, page_size: 10 });

    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(2));
    expect(getDocumentsHistoryMock.mock.calls[1]?.[0]).toMatchObject({ page: 2 });
    expect(screen.getByText("contract_services")).toBeInTheDocument();
  });

  it("applies filters when searching history", async () => {
    getDocumentsHistoryMock.mockResolvedValue(makeHistoryResponse());
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.type(screen.getByLabelText("Search"), "loan");
    await user.type(screen.getByLabelText("Doc type"), "lawsuit_debt_loan");
    await user.selectOptions(screen.getByLabelText("Sort by"), "document_type");
    await user.selectOptions(screen.getByLabelText("Sort dir"), "asc");
    await user.selectOptions(screen.getByLabelText("Page size"), "20");
    await user.click(screen.getByRole("button", { name: "Apply filters" }));

    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));
    expect(getDocumentsHistoryMock.mock.calls[0]?.[0]).toMatchObject({
      page: 1,
      page_size: 20,
      query: "loan",
      doc_type: "lawsuit_debt_loan",
      sort_by: "document_type",
      sort_dir: "asc"
    });
  });

  it("clones a document and reloads history", async () => {
    getDocumentsHistoryMock
      .mockResolvedValueOnce(makeHistoryResponse())
      .mockResolvedValueOnce(makeHistoryResponse({ total: 2 }));
    cloneDocumentMock.mockResolvedValue({
      status: "created",
      source_id: "doc-1",
      document_id: "doc-2",
      created_at: "2026-02-18T12:00:00Z",
      usage: makeHistoryResponse().usage
    });
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Clone" }));
    await waitFor(() => expect(cloneDocumentMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(2));
    expect(cloneDocumentMock).toHaveBeenCalledWith("doc-1", "", "demo-user");
  });

  it("repairs document processual structure and reloads history", async () => {
    getDocumentsHistoryMock
      .mockResolvedValueOnce(makeHistoryResponse())
      .mockResolvedValueOnce(makeHistoryResponse());
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Repair processual" }));
    await waitFor(() => expect(repairProcessualDocumentMock).toHaveBeenCalledTimes(1));
    expect(repairProcessualDocumentMock).toHaveBeenCalledWith("doc-1", "", "demo-user");
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(2));
  });

  it("checks processual state and renders processual check panel", async () => {
    getDocumentsHistoryMock.mockResolvedValue(makeHistoryResponse());
    getDocumentProcessualCheckMock.mockResolvedValue({
      status: "ok",
      id: "doc-1",
      is_valid: false,
      blockers: ["Validation failure: min_words"],
      pre_generation_gate_checks: [],
      processual_validation_checks: [
        {
          code: "min_words",
          status: "fail",
          message: "Word count 10 (minimum required: 180)."
        }
      ]
    });
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Check processual" }));
    await waitFor(() => expect(getDocumentProcessualCheckMock).toHaveBeenCalledTimes(1));
    expect(getDocumentProcessualCheckMock).toHaveBeenCalledWith("doc-1", "", "demo-user");
    expect(screen.getByText("Processual Check")).toBeInTheDocument();
    expect(screen.getByText(/Validation failure: min_words/)).toBeInTheDocument();
  });

  it("bulk repairs selected documents and reloads history", async () => {
    getDocumentsHistoryMock
      .mockResolvedValueOnce(makeHistoryResponse())
      .mockResolvedValueOnce(makeHistoryResponse());
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByLabelText("Select all visible"));
    await user.click(screen.getByRole("button", { name: /Repair selected/ }));
    await waitFor(() => expect(bulkRepairProcessualDocumentsMock).toHaveBeenCalledTimes(1));
    expect(bulkRepairProcessualDocumentsMock).toHaveBeenCalledWith(["doc-1"], "", "demo-user");
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(2));
    confirmSpy.mockRestore();
  });

  it("bulk deletes selected documents and reloads history", async () => {
    getDocumentsHistoryMock
      .mockResolvedValueOnce(
        makeHistoryResponse({
          total: 2,
          items: [
            makeHistoryResponse().items[0],
            {
              ...makeHistoryResponse().items[0],
              id: "doc-2",
              document_type: "contract_services"
            }
          ]
        })
      )
      .mockResolvedValueOnce(makeHistoryResponse({ total: 0, items: [] }));
    bulkDeleteDocumentsMock.mockResolvedValue({
      status: "completed",
      requested: 2,
      deleted: 2,
      deleted_ids: ["doc-1", "doc-2"],
      missing_ids: []
    });
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByLabelText("Select all visible"));
    await user.click(screen.getByRole("button", { name: /Delete selected/ }));

    await waitFor(() => expect(bulkDeleteDocumentsMock).toHaveBeenCalledTimes(1));
    expect(bulkDeleteDocumentsMock.mock.calls[0]?.[0]).toEqual(["doc-1", "doc-2"]);
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(2));
    confirmSpy.mockRestore();
  });

  it("loads versions on edit and restores selected version", async () => {
    getDocumentsHistoryMock
      .mockResolvedValueOnce(makeHistoryResponse())
      .mockResolvedValueOnce(makeHistoryResponse());
    getDocumentDetailMock
      .mockResolvedValueOnce({
        id: "doc-1",
        document_type: "lawsuit_debt_loan",
        document_category: "judicial",
        form_data: {},
        generated_text: "Generated text",
        preview_text: "Preview",
        calculations: {},
        ai_model: "gpt-4o-mini",
        used_ai: true,
        ai_error: null,
        has_docx_export: false,
        has_pdf_export: false,
        last_exported_at: null,
        e_court_ready: true,
        filing_blockers: [],
        created_at: "2026-02-18T10:00:00Z"
      })
      .mockResolvedValueOnce({
        id: "doc-1",
        document_type: "lawsuit_debt_loan",
        document_category: "judicial",
        form_data: {},
        generated_text: "Restored text",
        preview_text: "Preview",
        calculations: {},
        ai_model: "gpt-4o-mini",
        used_ai: true,
        ai_error: null,
        has_docx_export: false,
        has_pdf_export: false,
        last_exported_at: null,
        e_court_ready: true,
        filing_blockers: [],
        created_at: "2026-02-18T10:00:00Z"
      });
    getDocumentVersionsMock
      .mockResolvedValueOnce({
        document_id: "doc-1",
        total: 2,
        page: 1,
        page_size: 20,
        pages: 1,
        items: [
          { id: "ver-2", document_id: "doc-1", version_number: 2, action: "update", created_at: "2026-02-18T10:05:00Z" },
          { id: "ver-1", document_id: "doc-1", version_number: 1, action: "generate", created_at: "2026-02-18T10:00:00Z" }
        ]
      })
      .mockResolvedValueOnce({
        document_id: "doc-1",
        total: 4,
        page: 1,
        page_size: 20,
        pages: 1,
        items: [
          { id: "ver-4", document_id: "doc-1", version_number: 4, action: "restore", created_at: "2026-02-18T10:07:00Z" },
          { id: "ver-3", document_id: "doc-1", version_number: 3, action: "snapshot_before_restore", created_at: "2026-02-18T10:06:00Z" },
          { id: "ver-2", document_id: "doc-1", version_number: 2, action: "update", created_at: "2026-02-18T10:05:00Z" },
          { id: "ver-1", document_id: "doc-1", version_number: 1, action: "generate", created_at: "2026-02-18T10:00:00Z" }
        ]
      });
    getDocumentVersionDetailMock.mockResolvedValue({
      id: "ver-1",
      document_id: "doc-1",
      version_number: 1,
      action: "generate",
      generated_text: "Version text",
      created_at: "2026-02-18T10:00:00Z"
    });
    getDocumentVersionDiffMock.mockResolvedValue({
      document_id: "doc-1",
      target_version_id: "ver-1",
      target_version_number: 1,
      against: "current",
      against_version_number: null,
      diff_text: "--- against\n+++ version_1\n@@ -1 +1 @@\n-current\n+version",
      added_lines: 1,
      removed_lines: 1
    });
    restoreDocumentVersionMock.mockResolvedValue({
      status: "restored",
      id: "doc-1",
      restored_from_version_id: "ver-1",
      restored_to_version_number: 4,
      has_docx_export: false,
      has_pdf_export: false
    });
    const confirmSpy = jest.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Edit" }));
    await waitFor(() => expect(getDocumentDetailMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentVersionsMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Versions")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText("Compare against"), "ver-2");
    await user.click(screen.getAllByRole("button", { name: "Preview" })[0]);
    await waitFor(() => expect(getDocumentVersionDetailMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentVersionDiffMock).toHaveBeenCalledTimes(1));
    expect(getDocumentVersionDiffMock).toHaveBeenCalledWith("doc-1", "ver-2", "ver-2", "", "demo-user");
    expect(screen.getByDisplayValue("Version text")).toBeInTheDocument();
    expect(screen.getByText(/Diff vs/)).toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: "Restore" })[0]);
    await waitFor(() => expect(restoreDocumentVersionMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getDocumentDetailMock).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(getDocumentVersionsMock).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(2));
    confirmSpy.mockRestore();
  });

  it("submits selected document to e-court for PRO_PLUS plan", async () => {
    getDocumentsHistoryMock.mockResolvedValue(
      makeHistoryResponse({
        usage: {
          ...makeHistoryResponse().usage,
          plan: "PRO_PLUS",
          status: "active"
        }
      })
    );
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getECourtHistoryMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Submit e-Court" }));
    await user.type(screen.getByLabelText("Court name"), "Kyiv district court");
    await user.click(screen.getByRole("button", { name: "Submit to E-Court" }));

    await waitFor(() => expect(submitToECourtMock).toHaveBeenCalledTimes(1));
    expect(submitToECourtMock.mock.calls[0]?.[0]).toMatchObject({
      document_id: "doc-1",
      court_name: "Kyiv district court",
      signer_method: "diia_sign"
    });
  });

  it("applies hard-stop and disables e-court submit button for blocked document", async () => {
    getDocumentsHistoryMock.mockResolvedValue(
      makeHistoryResponse({
        items: [
          {
            ...makeHistoryResponse().items[0],
            id: "doc-blocked",
            e_court_ready: false,
            filing_blockers: ["Required deadline appeal_deadline is urgent (2026-03-05)."]
          }
        ],
        usage: {
          ...makeHistoryResponse().usage,
          plan: "PRO_PLUS",
          status: "active"
        }
      })
    );
    const user = userEvent.setup();

    render(<DocumentsPage />);
    await user.click(screen.getByRole("button", { name: "Load history" }));
    await waitFor(() => expect(getDocumentsHistoryMock).toHaveBeenCalledTimes(1));

    await user.type(screen.getByLabelText("Document ID"), "doc-blocked");
    await user.type(screen.getByLabelText("Court name"), "Kyiv district court");
    expect(screen.getByText(/Hard-stop:/)).toBeInTheDocument();
    expect(screen.getByText(/appeal_deadline is urgent/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit to E-Court" })).toBeDisabled();
    expect(submitToECourtMock).not.toHaveBeenCalled();
  });
});
