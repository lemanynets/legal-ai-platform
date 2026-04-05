export type RequestOptions = {
  method?: string;
  body?: unknown;
  token?: string;
  demoUser?: string;
  headers?: Record<string, string>;
  cache?: RequestCache;
};

function resolveApiBase(): string {
  const envValue = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (envValue) {
    return envValue.replace(/\/$/, "");
  }
  if (typeof window !== "undefined") {
    return window.location.origin.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

export const API_BASE = resolveApiBase();

export class ApiClientError extends Error {
  status?: number;
  code?: string;
  details?: unknown;
  isNetwork?: boolean;

  constructor(message: string, opts?: { status?: number; code?: string; details?: unknown; isNetwork?: boolean }) {
    super(message);
    this.name = "ApiClientError";
    this.status = opts?.status;
    this.code = opts?.code;
    this.details = opts?.details;
    this.isNetwork = opts?.isNetwork;
  }
}

export function buildAuthHeaders(token?: string, demoUser?: string): Record<string, string> {
  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (demoUser) headers["X-Demo-User"] = demoUser;
  return headers;
}

async function buildApiError(response: Response): Promise<ApiClientError> {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    const payload = await response.json().catch(() => ({}));
    return new ApiClientError(payload?.message || payload?.detail || `HTTP ${response.status}`, {
      status: response.status,
      code: payload?.code,
      details: payload,
    });
  }
  const raw = await response.text().catch(() => "");
  return new ApiClientError(raw || `HTTP ${response.status}`, { status: response.status });
}

export async function safeFetch(input: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    throw new ApiClientError("Network error", { isNetwork: true, details: String(error) });
  }
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    ...buildAuthHeaders(options.token, options.demoUser),
    ...(options.headers || {}),
  };

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  const response = await safeFetch(`${API_BASE}${path}`, {
    method: options.method || "GET",
    headers,
    body,
    cache: options.cache || "no-store",
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
