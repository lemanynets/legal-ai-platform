import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import MonitoringPage from "./page";
import {
  createRegistryWatchItem,
  getCurrentSubscription,
  getRegistryMonitorEvents,
  getRegistryMonitoringStatus,
  getRegistryWatchItems,
  runRegistryCheckDue
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  getCurrentSubscription: jest.fn(),
  getRegistryWatchItems: jest.fn(),
  getRegistryMonitorEvents: jest.fn(),
  getRegistryMonitoringStatus: jest.fn(),
  createRegistryWatchItem: jest.fn(),
  runRegistryCheckDue: jest.fn(),
  checkRegistryWatchItem: jest.fn(),
  deleteRegistryWatchItem: jest.fn()
}));

const getCurrentSubscriptionMock = getCurrentSubscription as jest.MockedFunction<typeof getCurrentSubscription>;
const getRegistryWatchItemsMock = getRegistryWatchItems as jest.MockedFunction<typeof getRegistryWatchItems>;
const getRegistryMonitorEventsMock = getRegistryMonitorEvents as jest.MockedFunction<typeof getRegistryMonitorEvents>;
const getRegistryMonitoringStatusMock = getRegistryMonitoringStatus as jest.MockedFunction<typeof getRegistryMonitoringStatus>;
const runRegistryCheckDueMock = runRegistryCheckDue as jest.MockedFunction<typeof runRegistryCheckDue>;
const createRegistryWatchItemMock = createRegistryWatchItem as jest.MockedFunction<typeof createRegistryWatchItem>;

describe("MonitoringPage", () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
    getRegistryWatchItemsMock.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
      items: [
        {
          id: "watch-1",
          user_id: "demo-user",
          source: "opendatabot",
          registry_type: "edr",
          identifier: "12345678",
          entity_name: "Demo LLC",
          status: "active",
          check_interval_hours: 24,
          last_checked_at: null,
          next_check_at: "2026-02-22T10:00:00Z",
          last_change_at: null,
          latest_snapshot: null,
          notes: null,
          created_at: "2026-02-22T09:00:00Z",
          updated_at: "2026-02-22T09:00:00Z"
        }
      ]
    });
    getRegistryMonitorEventsMock.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 20,
      pages: 1,
      items: [
        {
          id: "evt-1",
          watch_item_id: "watch-1",
          user_id: "demo-user",
          event_type: "watch_created",
          severity: "info",
          title: "Watch item created",
          details: {},
          observed_at: "2026-02-22T09:00:00Z",
          created_at: "2026-02-22T09:00:00Z"
        }
      ]
    });
    getRegistryMonitoringStatusMock.mockResolvedValue({
      total_watch_items: 1,
      active_watch_items: 1,
      due_watch_items: 0,
      warning_watch_items: 0,
      state_changed_events_24h: 0,
      last_event_at: "2026-02-22T09:00:00Z",
      by_status: { active: 1 }
    });
    createRegistryWatchItemMock.mockResolvedValue({
      status: "created",
      item: {
        id: "watch-2",
        user_id: "demo-user",
        source: "opendatabot",
        registry_type: "edr",
        identifier: "87654321",
        entity_name: "Second LLC",
        status: "active",
        check_interval_hours: 24,
        last_checked_at: null,
        next_check_at: "2026-02-22T10:00:00Z",
        last_change_at: null,
        latest_snapshot: null,
        notes: null,
        created_at: "2026-02-22T09:10:00Z",
        updated_at: "2026-02-22T09:10:00Z"
      }
    });
    runRegistryCheckDueMock.mockResolvedValue({
      status: "ok",
      scanned: 1,
      checked: 1,
      state_changed: 0
    });
  });

  it("loads monitoring data for PRO_PLUS user", async () => {
    render(<MonitoringPage />);

    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryWatchItemsMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryMonitorEventsMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryMonitoringStatusMock).toHaveBeenCalledTimes(1));
    expect(screen.getByText("Demo LLC")).toBeInTheDocument();
    expect(screen.getByText(/Watch item created/)).toBeInTheDocument();
    expect(screen.getAllByText(/Total watch items:/).length).toBeGreaterThan(0);
  });

  it("creates watch item and refreshes lists", async () => {
    const user = userEvent.setup();
    render(<MonitoringPage />);
    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalledTimes(1));

    await user.clear(screen.getByLabelText("Identifier (EDRPOU / case number)"));
    await user.type(screen.getByLabelText("Identifier (EDRPOU / case number)"), "87654321");
    await user.clear(screen.getByLabelText("Entity name"));
    await user.type(screen.getByLabelText("Entity name"), "Second LLC");
    await user.click(screen.getByRole("button", { name: "Create watch item" }));

    await waitFor(() => expect(createRegistryWatchItemMock).toHaveBeenCalledTimes(1));
    expect(createRegistryWatchItemMock.mock.calls[0]?.[0]).toMatchObject({
      registry_type: "edr",
      identifier: "87654321",
      entity_name: "Second LLC"
    });
    await waitFor(() => expect(getRegistryWatchItemsMock.mock.calls.length).toBeGreaterThanOrEqual(2));
    await waitFor(() => expect(getRegistryMonitorEventsMock.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it("runs due checks and refreshes status", async () => {
    const user = userEvent.setup();
    render(<MonitoringPage />);
    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("button", { name: "Run due checks" }));
    await waitFor(() => expect(runRegistryCheckDueMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryMonitoringStatusMock.mock.calls.length).toBeGreaterThanOrEqual(2));
  });
});
