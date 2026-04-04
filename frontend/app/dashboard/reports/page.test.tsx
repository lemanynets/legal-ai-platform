import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import ReportsPage from "./page";
import { exportFullLawyerPreflightHistoryReport, getFullLawyerPreflightHistory } from "@/lib/api";

jest.mock("@/lib/api", () => ({
  getFullLawyerPreflightHistory: jest.fn(),
  exportFullLawyerPreflightHistoryReport: jest.fn(),
}));

const getFullLawyerPreflightHistoryMock = getFullLawyerPreflightHistory as jest.MockedFunction<typeof getFullLawyerPreflightHistory>;
const exportFullLawyerPreflightHistoryReportMock =
  exportFullLawyerPreflightHistoryReport as jest.MockedFunction<typeof exportFullLawyerPreflightHistoryReport>;

describe("ReportsPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
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

    getFullLawyerPreflightHistoryMock.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
      event: "all",
      items: [
        {
          id: "audit-1",
          event_type: "upload",
          source_file_name: "sample.txt",
          extracted_chars: 1234,
          status: "ok",
          final_submission_gate_status: "blocked",
          consume_quota: false,
          format: null,
          has_report_snapshot: true,
          created_at: "2026-03-02T10:00:00Z",
        },
      ],
    });
    exportFullLawyerPreflightHistoryReportMock.mockResolvedValue(new Blob(["test"], { type: "application/pdf" }));
  });

  it("loads report history and downloads a snapshot", async () => {
    render(<ReportsPage />);

    await waitFor(() => expect(getFullLawyerPreflightHistoryMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("sample.txt")).toBeInTheDocument();
    expect(screen.getByText("1 / 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "PDF" }));

    await waitFor(() => expect(exportFullLawyerPreflightHistoryReportMock).toHaveBeenCalledTimes(1));
    expect(exportFullLawyerPreflightHistoryReportMock.mock.calls[0]?.[0]).toBe("audit-1");
    expect(exportFullLawyerPreflightHistoryReportMock.mock.calls[0]?.[1]).toBe("pdf");
  });
});
