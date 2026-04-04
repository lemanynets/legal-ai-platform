import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import MonitoringPage from "./page";
import {
  createRegistryWatchItem,
  getCurrentSubscription,
  getRegistryMonitorEvents,
  getRegistryMonitoringStatus,
  getRegistryWatchItems,
} from "@/lib/api";

jest.mock("@/lib/api", () => ({
  getCurrentSubscription: jest.fn(),
  getRegistryWatchItems: jest.fn(),
  getRegistryMonitorEvents: jest.fn(),
  getRegistryMonitoringStatus: jest.fn(),
  createRegistryWatchItem: jest.fn(),
  runRegistryCheckDue: jest.fn(),
  checkRegistryWatchItem: jest.fn(),
  deleteRegistryWatchItem: jest.fn(),
}));

const getCurrentSubscriptionMock = getCurrentSubscription as jest.MockedFunction<typeof getCurrentSubscription>;
const getRegistryWatchItemsMock = getRegistryWatchItems as jest.MockedFunction<typeof getRegistryWatchItems>;
const getRegistryMonitorEventsMock = getRegistryMonitorEvents as jest.MockedFunction<typeof getRegistryMonitorEvents>;
const getRegistryMonitoringStatusMock = getRegistryMonitoringStatus as jest.MockedFunction<typeof getRegistryMonitoringStatus>;
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
        updated_at: null,
      },
      limits: { analyses_limit: null, docs_limit: null },
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
          updated_at: "2026-02-22T09:00:00Z",
        },
      ],
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
          created_at: "2026-02-22T09:00:00Z",
        },
      ],
    });
    getRegistryMonitoringStatusMock.mockResolvedValue({
      total_watch_items: 1,
      active_watch_items: 1,
      due_watch_items: 0,
      warning_watch_items: 0,
      state_changed_events_24h: 0,
      last_event_at: "2026-02-22T09:00:00Z",
      by_status: { active: 1 },
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
        updated_at: "2026-02-22T09:10:00Z",
      },
    });
  });

  it("loads monitoring widgets and event feed for PRO_PLUS", async () => {
    render(<MonitoringPage />);

    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryWatchItemsMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryMonitorEventsMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryMonitoringStatusMock).toHaveBeenCalledTimes(1));

    expect(screen.getByText("Demo LLC")).toBeInTheDocument();
    expect(screen.getByText("Watch item created")).toBeInTheDocument();
  });

  it("creates watch item from form and refreshes monitoring data", async () => {
    const { container } = render(<MonitoringPage />);
    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(getRegistryWatchItemsMock).toHaveBeenCalledTimes(1));

    const form = container.querySelector("#add-form form") as HTMLFormElement;
    const inputs = form.querySelectorAll("input");
    expect(inputs.length).toBeGreaterThanOrEqual(2);

    fireEvent.change(inputs[0], { target: { value: "87654321" } });
    fireEvent.change(inputs[1], { target: { value: "Second LLC" } });
    fireEvent.submit(form);

    await waitFor(() => expect(createRegistryWatchItemMock).toHaveBeenCalledTimes(1));
    expect(createRegistryWatchItemMock.mock.calls[0]?.[0]).toMatchObject({
      registry_type: "edr",
      identifier: "87654321",
      entity_name: "Second LLC",
    });
    await waitFor(() => expect(getRegistryWatchItemsMock.mock.calls.length).toBeGreaterThanOrEqual(2));
    await waitFor(() => expect(getRegistryMonitorEventsMock.mock.calls.length).toBeGreaterThanOrEqual(2));
  });

  it("does not request monitoring feeds for insufficient plan", async () => {
    getCurrentSubscriptionMock.mockResolvedValueOnce({
      user_id: "demo-user",
      plan: "FREE",
      status: "active",
      usage: {
        id: "sub-1",
        user_id: "demo-user",
        plan: "FREE",
        status: "active",
        analyses_used: 0,
        analyses_limit: 1,
        docs_used: 0,
        docs_limit: 1,
        current_period_start: null,
        current_period_end: null,
        created_at: null,
        updated_at: null,
      },
      limits: { analyses_limit: 1, docs_limit: 1 },
    });

    render(<MonitoringPage />);
    await waitFor(() => expect(getCurrentSubscriptionMock).toHaveBeenCalledTimes(1));

    await waitFor(() => {
      expect(getRegistryWatchItemsMock).not.toHaveBeenCalled();
      expect(getRegistryMonitorEventsMock).not.toHaveBeenCalled();
      expect(getRegistryMonitoringStatusMock).not.toHaveBeenCalled();
    });
  });
});
