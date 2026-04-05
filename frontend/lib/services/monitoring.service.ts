import { request } from "./http-client";

export type MonitoringWatchItem = {
  id: string;
  entity_type: string;
  entity_code: string;
  label: string;
  status: string;
  created_at: string;
};

export async function getMonitoringStatus(token?: string, demoUser?: string) {
  return request<{ status: string; active_items?: number; last_check_at?: string | null }>("/api/monitoring/status", {
    token,
    demoUser,
  });
}

export async function getMonitoringWatchItems(token?: string, demoUser?: string) {
  return request<{ items: MonitoringWatchItem[]; total?: number }>("/api/monitoring/watch-items", {
    token,
    demoUser,
  });
}

export async function runWatchItemCheck(itemId: string, token?: string, demoUser?: string) {
  return request<{ status: string; item_id: string }>(`/api/monitoring/watch-items/${itemId}/check`, {
    method: "POST",
    token,
    demoUser,
  });
}
