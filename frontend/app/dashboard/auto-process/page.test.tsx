import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import AutoProcessPage from "./page";
import { autoProcessDocument } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  autoProcessDocument: jest.fn(),
  exportDocument: jest.fn()
}));

const autoProcessDocumentMock = autoProcessDocument as jest.MockedFunction<typeof autoProcessDocument>;

describe("AutoProcessPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    autoProcessDocumentMock.mockResolvedValue({
      status: "ok",
      source_file_name: "sample.txt",
      extracted_chars: 1200,
      processual_only_mode: true,
      procedural_conclusions: ["Debt recovery indicators found."],
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

  it("uploads file and renders auto-processing result", async () => {
    const user = userEvent.setup();
    render(<AutoProcessPage />);

    const file = new File(["Debt under loan agreement 10000 UAH"], "sample.txt", { type: "text/plain" });
    await user.upload(screen.getByLabelText("Файл (txt/pdf/docx)"), file);
    await user.click(screen.getByRole("button", { name: "Запустити автообробку" }));

    await waitFor(() => expect(autoProcessDocumentMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText(/Згенеровано документів: 1/)).toBeInTheDocument();
    expect(screen.getAllByText(/lawsuit_debt_loan/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Debt recovery indicators found/)).toBeInTheDocument();
  });
});
