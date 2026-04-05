import { request } from "./http-client";

export type DocumentType = {
  doc_type: string;
  title: string;
  category: string;
  procedure: string;
};

export type FormField = {
  key: string;
  label: string;
  type: string;
  required: boolean;
  placeholder?: string;
  options?: string[];
};

export type DocumentFormSchemaResponse = {
  doc_type: string;
  title: string;
  fields: Array<{
    name: string;
    label: string;
    type: string;
    required: boolean;
  }>;
};

export type AsyncJobEnqueueResponse = {
  status: "queued";
  job_id: string;
  task_id: string;
};

export type AsyncJobStatusResponse = {
  job_id: string;
  task_id: string;
  status: "queued" | "running" | "success" | "failed";
  progress: number;
  message?: string | null;
  result?: Record<string, unknown> | null;
  error?: string | null;
};

export async function getDocumentTypes(token?: string, demoUser?: string): Promise<DocumentType[]> {
  return request<DocumentType[]>("/api/documents/types", { token, demoUser });
}

export async function getDocumentFormSchema(docType: string, token?: string, demoUser?: string): Promise<DocumentFormSchemaResponse> {
  return request<DocumentFormSchemaResponse>(`/api/documents/form-schema/${docType}`, { token, demoUser });
}

export async function enqueueGenerateJob(
  docType: string,
  formData: Record<string, unknown>,
  tariff: string,
  token?: string,
  demoUser?: string,
  options?: { extra_prompt_context?: string }
): Promise<AsyncJobEnqueueResponse> {
  return request<AsyncJobEnqueueResponse>("/api/jobs/generate", {
    method: "POST",
    body: {
      doc_type: docType,
      form_data: formData,
      tariff,
      extra_prompt_context: options?.extra_prompt_context,
    },
    token,
    demoUser,
  });
}

export async function getAsyncJobStatus(jobId: string, token?: string, demoUser?: string): Promise<AsyncJobStatusResponse> {
  return request<AsyncJobStatusResponse>(`/api/jobs/${jobId}`, { token, demoUser });
}
