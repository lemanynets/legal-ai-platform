import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import CaseLawPage from "./page";
import {
  generateCaseLawDigest,
  getCaseLawDigest,
  getCaseLawDigestDetail,
  getCaseLawDigestHistory,
  getCurrentSubscription,
  getCaseLawSyncStatus,
  searchCaseLaw
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  generateCaseLawDigest: jest.fn(),
  getCaseLawDigest: jest.fn(),
  getCaseLawDigestDetail: jest.fn(),
  getCaseLawDigestHistory: jest.fn(),
  getCurrentSubscription: jest.fn(),
  getCaseLawSyncStatus: jest.fn(),
  searchCaseLaw: jest.fn(),
  importCaseLaw: jest.fn(),
  syncCaseLaw: jest.fn()
}));

const generateCaseLawDigestMock = generateCaseLawDigest as jest.MockedFunction<typeof generateCaseLawDigest>;
const getCaseLawDigestMock = getCaseLawDigest as jest.MockedFunction<typeof getCaseLawDigest>;
const getCaseLawDigestDetailMock = getCaseLawDigestDetail as jest.MockedFunction<typeof getCaseLawDigestDetail>;
const getCaseLawDigestHistoryMock = getCaseLawDigestHistory as jest.MockedFunction<typeof getCaseLawDigestHistory>;
const getCurrentSubscriptionMock = getCurrentSubscription as jest.MockedFunction<typeof getCurrentSubscription>;
const getCaseLawSyncStatusMock = getCaseLawSyncStatus as jest.MockedFunction<typeof getCaseLawSyncStatus>;
const searchCaseLawMock = searchCaseLaw as jest.MockedFunction<typeof searchCaseLaw>;

function makeSyncStatusResponse(overrides: Partial<Awaited<ReturnType<typeof getCaseLawSyncStatus>>> = {}) {
  return {
    total_records: 10,
    sources: { opendatabot: 7, manual_seed: 3 },
    latest_decision_date: "2025-01-10",
    oldest_decision_date: "2024-01-10",
    last_sync_at: "2026-02-18T10:00:00+00:00",
    last_sync_action: "case_law_sync",
    last_sync_query: "debt",
    last_sync_limit: 50,
    last_sync_created: 5,
    last_sync_updated: 2,
    last_sync_total: 7,
    last_sync_sources: ["opendatabot", "json_feed"],
    last_sync_seed_fallback_used: false,
    ...overrides
  };
}

function makeSearchResponse(overrides: Partial<Awaited<ReturnType<typeof searchCaseLaw>>> = {}) {
  return {
    total: 1,
    page: 1,
    page_size: 20,
    pages: 1,
    sort_by: "decision_date",
    sort_dir: "desc" as const,
    items: [
      {
        id: "row-1",
        source: "manual",
        decision_id: "d-001",
        court_name: "Supreme Court",
        court_type: "civil",
        decision_date: "2025-01-10",
        case_number: "100/1/25",
        subject_categories: ["loan"],
        legal_positions: { "article 625": "3% and inflation losses recoverable." },
        summary: "Loan debt case",
        reference_count: 5
      }
    ],
    ...overrides
  };
}

function makeDigestResponse(overrides: Partial<Awaited<ReturnType<typeof getCaseLawDigest>>> = {}) {
  return {
    digest_id: null,
    saved: false,
    title: null,
    days: 7,
    limit: 10,
    total: 1,
    only_supreme: true,
    court_type: "civil",
    source: ["opendatabot"],
    generated_at: "2026-02-21T10:00:00+00:00",
    items: [
      {
        id: "row-1",
        source: "opendatabot",
        decision_id: "d-001",
        court_name: "Supreme Court",
        court_type: "civil",
        decision_date: "2025-01-10",
        case_number: "100/1/25",
        subject_categories: ["loan"],
        summary: "Loan debt case",
        legal_positions: { "article 625": "3% and inflation losses recoverable." },
        prompt_snippet: "[opendatabot] case 100/1/25. court: Supreme Court. summary: Loan debt case."
      }
    ],
    ...overrides
  };
}

describe("CaseLawPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    localStorage.clear();
    getCurrentSubscriptionMock.mockResolvedValue({
      user_id: "demo-user",
      plan: "PRO_PLUS",
      status: "active",
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
        updated_at: null
      },
      limits: {
        analyses_limit: null,
        docs_limit: null
      }
    });
    getCaseLawSyncStatusMock.mockResolvedValue(makeSyncStatusResponse());
    getCaseLawDigestMock.mockResolvedValue(makeDigestResponse());
    generateCaseLawDigestMock.mockResolvedValue(makeDigestResponse({ digest_id: "digest-1", saved: true }));
    getCaseLawDigestDetailMock.mockResolvedValue(makeDigestResponse({ digest_id: "digest-1", saved: true }));
    getCaseLawDigestHistoryMock.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
      items: [
        {
          id: "digest-1",
          title: "Weekly SC digest",
          days: 7,
          limit: 10,
          total: 1,
          item_count: 1,
          only_supreme: true,
          court_type: "civil",
          source: ["opendatabot"],
          created_at: "2026-02-21T10:00:00+00:00"
        }
      ]
    });
  });

  it("runs search and renders table rows", async () => {
    searchCaseLawMock.mockResolvedValueOnce(makeSearchResponse());
    const user = userEvent.setup();

    render(<CaseLawPage />);
    await user.click(screen.getByRole("button", { name: "Search cache" }));

    await waitFor(() => expect(searchCaseLawMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Loan debt case")).toBeInTheDocument();
    expect(screen.getByText(/Found 1 records/)).toBeInTheDocument();
  });

  it("uses server-side pagination by calling page=2 on Next", async () => {
    searchCaseLawMock
      .mockResolvedValueOnce(makeSearchResponse({ page: 1, pages: 2 }))
      .mockResolvedValueOnce(
        makeSearchResponse({
          page: 2,
          pages: 2,
          items: [
            {
              id: "row-2",
              source: "manual",
              decision_id: "d-002",
              court_name: "Supreme Court",
              court_type: "civil",
              decision_date: "2025-01-09",
              case_number: "100/2/25",
              subject_categories: ["loan"],
              legal_positions: {},
              summary: "Second page row",
              reference_count: 2
            }
          ]
        })
      );
    const user = userEvent.setup();

    render(<CaseLawPage />);
    await user.click(screen.getByRole("button", { name: "Search cache" }));
    await waitFor(() => expect(searchCaseLawMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Next" }));
    await waitFor(() => expect(searchCaseLawMock).toHaveBeenCalledTimes(2));
    expect(searchCaseLawMock.mock.calls[1]?.[0]).toMatchObject({ page: 2 });
    expect(screen.getByText("Second page row")).toBeInTheDocument();
  });

  it("stores selected row into prompt context when clicking Use in prompt", async () => {
    searchCaseLawMock.mockResolvedValueOnce(makeSearchResponse());
    const user = userEvent.setup();

    render(<CaseLawPage />);
    await user.click(screen.getByRole("button", { name: "Search cache" }));
    await waitFor(() => expect(screen.getByText("Loan debt case")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Use in prompt" }));
    await waitFor(() => {
      const stored = localStorage.getItem("legal_ai_prompt_context") || "";
      expect(stored).toContain("Case: 100/1/25");
      expect(stored).toContain("Summary: Loan debt case");
    });
  });

  it("passes source/date/fresh filters to search endpoint", async () => {
    searchCaseLawMock.mockResolvedValueOnce(makeSearchResponse());
    const user = userEvent.setup();

    render(<CaseLawPage />);
    await user.type(screen.getByLabelText("Source (comma separated)"), "opendatabot");
    await user.type(screen.getByLabelText("Decision date from"), "2025-01-01");
    await user.type(screen.getByLabelText("Decision date to"), "2025-12-31");
    await user.type(screen.getByLabelText("Fresh days (optional)"), "365");
    await user.click(screen.getByRole("button", { name: "Search cache" }));

    await waitFor(() => expect(searchCaseLawMock).toHaveBeenCalledTimes(1));
    expect(searchCaseLawMock.mock.calls[0]?.[0]).toMatchObject({
      only_supreme: true,
      source: "opendatabot",
      date_from: "2025-01-01",
      date_to: "2025-12-31",
      fresh_days: 365
    });
  });

  it("loads digest and saves it into prompt context", async () => {
    const user = userEvent.setup();

    render(<CaseLawPage />);
    await user.click(screen.getByRole("button", { name: "Load digest" }));
    await waitFor(() => expect(getCaseLawDigestMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Use digest in prompt" }));
    await waitFor(() => {
      const stored = localStorage.getItem("legal_ai_prompt_context") || "";
      expect(stored).toContain("Weekly case-law digest");
      expect(stored).toContain("case 100/1/25");
    });
  });

  it("saves digest and refreshes history", async () => {
    const user = userEvent.setup();
    render(<CaseLawPage />);

    await user.type(screen.getByLabelText("Digest title (optional)"), "Weekly SC digest");
    await user.click(screen.getByRole("button", { name: "Save digest" }));
    await waitFor(() => expect(generateCaseLawDigestMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getCaseLawDigestHistoryMock).toHaveBeenCalled());
  });

  it("disables PRO/PRO_PLUS actions when plan is START", async () => {
    getCurrentSubscriptionMock.mockResolvedValueOnce({
      user_id: "demo-user",
      plan: "START",
      status: "active",
      usage: {
        id: "sub-1",
        user_id: "demo-user",
        plan: "START",
        status: "active",
        analyses_used: 0,
        analyses_limit: 10,
        docs_used: 0,
        docs_limit: 20,
        current_period_start: null,
        current_period_end: null,
        created_at: null,
        updated_at: null
      },
      limits: {
        analyses_limit: 10,
        docs_limit: 20
      }
    });

    render(<CaseLawPage />);
    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalled());

    expect(screen.getByRole("button", { name: "Save digest" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Refresh saved digests" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Run sync" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Import records" })).toBeDisabled();
    expect(screen.getAllByText(/Requires PRO_PLUS plan and active subscription/).length).toBeGreaterThan(0);
  });
});
