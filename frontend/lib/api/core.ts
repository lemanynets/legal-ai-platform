type RequestOptions = {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  token?: string;
  demoUser?: string;
};

type ApiClientErrorInit = {
  status?: number;
  detail?: string;
  raw?: string;
  isNetwork?: boolean;
};

class ApiClientError extends Error {
  status?: number;
  detail?: string;
  raw?: string;
  isNetwork: boolean;

  constructor(message: string, init: ApiClientErrorInit = {}) {
    super(message);
    this.name = "ApiClientError";
    this.status = init.status;
    this.detail = init.detail;
    this.raw = init.raw;
    this.isNetwork = Boolean(init.isNetwork);
  }

  override toString(): string {
    return this.message;
  }
}

function resolveApiBase(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (explicit) {
    const base = explicit.replace(/\/+$/, "");
    if (typeof window === "undefined" && (base.includes("localhost") || base.includes("127.0.0.1"))) {
      return base.replace(/localhost|127\.0\.0\.1/, "backend");
    }
    return base;
  }

  if (typeof window !== "undefined") {
    const host = window.location.hostname.toLowerCase();
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://localhost:8000";
    }
  }

  if (typeof window === "undefined") {
    return "http://backend:8000";
  }

  return "https://backend-production-0e53.up.railway.app";
}

export const API_BASE = resolveApiBase();

function stringifyDetail(detail: unknown): string {
  if (typeof detail === "string") return detail.trim();

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item.trim();
        if (item && typeof item === "object") {
          const record = item as Record<string, unknown>;
          const msg = typeof record.msg === "string" ? record.msg.trim() : "";
          const loc = Array.isArray(record.loc) ? record.loc.map((chunk) => String(chunk)).join(".") : "";
          return [loc, msg].filter(Boolean).join(": ");
        }
        return "";
      })
      .filter(Boolean);
    return parts.join("; ").trim();
  }

  if (detail && typeof detail === "object") {
    const record = detail as Record<string, unknown>;
    if (typeof record.message === "string" && record.message.trim()) {
      return record.message.trim();
    }
    try {
      return JSON.stringify(detail);
    } catch {
      return "";
    }
  }

  return "";
}

function localizeApiMessage(params: {
  status?: number;
  detail?: string;
  raw?: string;
  isNetwork?: boolean;
}): string {
  const status = params.status;
  const detail = (params.detail || "").trim();
  const raw = (params.raw || "").trim();
  const text = `${detail} ${raw}`.toLowerCase();

  if (params.isNetwork) {
    if (text.includes("iso-8859-1") || text.includes("headers") || text.includes("requestinit")) {
      return "Помилка заголовків запиту. Перезавантаж сторінку і спробуй ще раз.";
    }
    return "Не вдалося підключитися до сервера. Перевір з'єднання або стан backend.";
  }

  if (text.includes("insufficient_quota") || text.includes("analysis limit reached") || status === 402) {
    return "Ліміт тарифу або AI-квота вичерпано. Онови план або спробуй пізніше.";
  }
  if (text.includes("недостатньо тексту") || text.includes("not enough text")) {
    return "Недостатньо тексту для аналізу документа. Додай більш змістовний файл.";
  }
  if (text.includes("incorrect email or password") || text.includes("невірний email") || text.includes("неправильний email")) {
    return "Невірний email або пароль.";
  }
  if (text.includes("string contains non iso-8859-1 code point")) {
    return "Запит містить неприпустимі символи в заголовках. Очисть сесію і повтори.";
  }

  if (status === 401) return "Сесія завершилась або недійсна. Увійди знову.";
  if (status === 403) return "Немає доступу до цієї дії.";
  if (status === 404) return "Ресурс не знайдено.";
  if (status === 409) return "Конфлікт даних. Онови сторінку і повтори дію.";
  if (status === 422) return detail || "Помилка валідації даних. Перевір поля форми.";
  if (status === 429) return "Забагато запитів. Спробуй через хвилину.";
  if (typeof status === "number" && status >= 500) return "Сервер тимчасово недоступний. Спробуй пізніше.";

  if (detail) return detail;
  if (raw) return raw;
  if (status) return `API ${status}`;
  return "Невідома помилка запиту.";
}

export function buildAuthHeaders(token?: string, demoUser?: string): Record<string, string> {
  const headers: Record<string, string> = {};
  const normalizedToken = token?.trim();
  const normalizedDemoUser = demoUser?.trim();

  if (normalizedToken) {
    headers.Authorization = `Bearer ${normalizedToken}`;
  }

  if (!normalizedToken && normalizedDemoUser && /^[\x00-\x7F]+$/.test(normalizedDemoUser)) {
    headers["X-Demo-User"] = normalizedDemoUser;
  }
  return headers;
}

function buildHeaders(token?: string, demoUser?: string): HeadersInit {
  const headers = buildAuthHeaders(token, demoUser);
  headers["Content-Type"] = "application/json";
  return headers;
}

export async function buildApiError(response: Response): Promise<Error> {
  const text = await response.text();
  let detail = "";

  try {
    const payload = JSON.parse(text) as { detail?: unknown };
    if (payload && "detail" in payload) {
      detail = stringifyDetail(payload.detail);
    }
  } catch {
    // Fallback to raw response text.
  }

  const message = localizeApiMessage({
    status: response.status,
    detail,
    raw: text,
    isNetwork: false,
  });
  return new ApiClientError(message, { status: response.status, detail, raw: text });
}

function buildNetworkError(error: unknown): Error {
  const raw = error instanceof Error ? error.message : String(error ?? "");
  const message = localizeApiMessage({ raw, isNetwork: true });
  return new ApiClientError(message, { raw, isNetwork: true });
}

export async function safeFetch(input: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init);
  } catch (error) {
    throw buildNetworkError(error);
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (typeof error === "string" && error.trim()) return error.trim();
  return "Невідома помилка.";
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const response = await safeFetch(`${API_BASE}${path}`, {
    method: options.method ?? "GET",
    headers: buildHeaders(options.token, options.demoUser),
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });

  if (!response.ok) {
    throw await buildApiError(response);
  }
  return (await response.json()) as T;
}
