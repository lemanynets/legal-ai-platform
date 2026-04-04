import { request } from "./core";
import type { CaseLawSearchItem } from "../api";

export type Case = {
  id: string;
  user_id: string;
  title: string;
  description: string | null;
  case_number: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type CaseDetail = Case & {
  documents: Array<{
    id: string;
    document_type: string;
    document_category: string;
    created_at: string;
  }>;
  forum_posts: Array<{
    id: string;
    title: string;
    created_at: string;
  }>;
  case_law_items: CaseLawSearchItem[];
};

export type CaseDecisionSyncResponse = {
  status: string;
  case_id: string;
  case_number: string;
  records_in: number;
  created: number;
  updated: number;
  total: number;
};

export async function getCases(token?: string, demoUser?: string): Promise<Case[]> {
  return request<Case[]>("/api/cases", { token, demoUser });
}

export async function getCase(caseId: string, token?: string, demoUser?: string): Promise<CaseDetail> {
  return request<CaseDetail>(`/api/cases/${caseId}`, { token, demoUser });
}

export async function syncCaseDecisions(
  caseId: string,
  token?: string,
  demoUser?: string,
): Promise<CaseDecisionSyncResponse> {
  return request<CaseDecisionSyncResponse>(`/api/cases/${caseId}/sync-decisions`, {
    method: "POST",
    token,
    demoUser,
  });
}

export async function createCase(payload: Partial<Case>, token?: string, demoUser?: string): Promise<Case> {
  return request<Case>("/api/cases", { method: "POST", body: payload, token, demoUser });
}

export async function updateCase(
  caseId: string,
  payload: Partial<Case>,
  token?: string,
  demoUser?: string,
): Promise<Case> {
  return request<Case>(`/api/cases/${caseId}`, { method: "PATCH", body: payload, token, demoUser });
}

export async function deleteCase(caseId: string, token?: string, demoUser?: string): Promise<{ status: string }> {
  return request<{ status: string }>(`/api/cases/${caseId}`, { method: "DELETE", token, demoUser });
}
