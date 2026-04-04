import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";
const allowDevAuth = process.env.NEXT_PUBLIC_ALLOW_DEV_AUTH === "true";
const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://localhost:8000";

export const supabase = supabaseUrl && supabaseAnonKey ? createClient(supabaseUrl, supabaseAnonKey) : null;

const isDevAuthEnabled = allowDevAuth || !supabase;
const SESSION_KEY = "legal_ai_session";
const PRO_PLUS_EMAILS = new Set(["lemaninets1985@gmail.com"]);
const PRO_PLUS_USER_IDS = new Set(["dev-lemaninets1985"]);

export interface UserSession {
  user_id: string;
  email: string;
  name: string;
  plan: string;
  token: string;
}

let cachedSession: UserSession | null = null;

function derivePlan(email: string, userId: string, fallback: string): string {
  const safeEmail = (email || "").trim().toLowerCase();
  const safeUserId = (userId || "").trim().toLowerCase();
  if (PRO_PLUS_EMAILS.has(safeEmail) || PRO_PLUS_USER_IDS.has(safeUserId)) {
    return "PRO_PLUS";
  }
  return fallback;
}

function readStoredSession(): UserSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<UserSession>;
    if (
      typeof parsed.user_id === "string" &&
      typeof parsed.email === "string" &&
      typeof parsed.name === "string" &&
      typeof parsed.plan === "string" &&
      typeof parsed.token === "string"
    ) {
      return {
        user_id: parsed.user_id,
        email: parsed.email,
        name: parsed.name,
        plan: parsed.plan,
        token: parsed.token,
      };
    }
  } catch {
    // Ignore invalid local storage data.
  }
  return null;
}

function persistSession(session: UserSession | null): void {
  if (typeof window === "undefined") return;
  if (!session) {
    localStorage.removeItem(SESSION_KEY);
    return;
  }
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

function hydrateCachedSession(): UserSession | null {
  if (cachedSession) return cachedSession;
  const stored = readStoredSession();
  if (stored) {
    cachedSession = stored;
  }
  return cachedSession;
}

function buildSession(params: {
  userId: string;
  email: string;
  name: string;
  token: string;
  fallbackPlan: string;
}): UserSession {
  return {
    user_id: params.userId,
    email: params.email,
    name: params.name,
    plan: derivePlan(params.email, params.userId, params.fallbackPlan),
    token: params.token,
  };
}

function decodeTokenPayload(token: string): Record<string, unknown> {
  const base64Url = token.split(".")[1] || "";
  const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  const jsonPayload = decodeURIComponent(
    atob(base64)
      .split("")
      .map((char) => `%${(`00${char.charCodeAt(0).toString(16)}`).slice(-2)}`)
      .join(""),
  );
  return JSON.parse(jsonPayload) as Record<string, unknown>;
}

async function readAuthErrorMessage(response: Response, fallbackMessage: string): Promise<string> {
  const contentType = response.headers.get("content-type") || "";

  try {
    if (contentType.includes("application/json")) {
      const errorData = await response.json();
      const detail = typeof errorData?.detail === "string" ? errorData.detail.trim() : "";
      if (detail) return detail;
    } else {
      const text = (await response.text()).trim();
      if (text) return text;
    }
  } catch {
    // Ignore malformed backend payloads.
  }

  if (response.status >= 500) {
    return "Сервер тимчасово недоступний. Спробуйте ще раз трохи пізніше.";
  }
  return fallbackMessage;
}

async function performAuthRequest(
  path: string,
  payload: Record<string, unknown>,
  fallbackMessage: string,
): Promise<{ access_token: string; token_type: string }> {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  } catch {
    throw new Error("Не вдалося з'єднатися з сервером. Перевірте, чи запущено бекенд на localhost:8000.");
  }

  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response, fallbackMessage));
  }

  return response.json();
}

export async function initAuth(): Promise<void> {
  if (typeof window === "undefined") return;

  hydrateCachedSession();

  if (supabase) {
    const {
      data: { session },
    } = await supabase.auth.getSession();

    if (session) {
      cachedSession = buildSession({
        userId: session.user.id,
        email: session.user.email || "",
        name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "User",
        token: session.access_token,
        fallbackPlan: "PRO",
      });
      persistSession(cachedSession);
    }
  }

  if (!cachedSession && isDevAuthEnabled) {
    cachedSession = readStoredSession();
  }

  if (supabase) {
    supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        cachedSession = buildSession({
          userId: session.user.id,
          email: session.user.email || "",
          name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "User",
          token: session.access_token,
          fallbackPlan: "PRO",
        });
        persistSession(cachedSession);
      } else if (!isDevAuthEnabled) {
        cachedSession = null;
        persistSession(null);
      }
    });
  }
}

export function getSession(): UserSession | null {
  return hydrateCachedSession();
}

export function getToken(): string {
  return hydrateCachedSession()?.token ?? "";
}

export function getUserId(): string {
  return hydrateCachedSession()?.user_id ?? "demo-user";
}

export async function login(email: string, password: string): Promise<UserSession> {
  const data = await performAuthRequest(
    "/api/auth/login",
    { email, password },
    "Не вдалося увійти. Перевірте email і пароль.",
  );
  const token = data.access_token;
  const payload = decodeTokenPayload(token);
  const userId =
    String(payload.sub || "").trim() || email.split("@")[0].replace(/[^a-z0-9]/gi, "-");

  const session = buildSession({
    userId,
    email,
    name: String(payload.full_name || email.split("@")[0]),
    token,
    fallbackPlan: "PRO",
  });

  cachedSession = session;
  persistSession(session);
  return session;
}

export async function registerUser(email: string, password: string, fullName?: string): Promise<UserSession> {
  const data = await performAuthRequest(
    "/api/auth/register",
    { email, password, full_name: fullName },
    "Не вдалося зареєструватися. Перевірте дані та спробуйте ще раз.",
  );
  const token = data.access_token;
  const payload = decodeTokenPayload(token);
  const userId =
    String(payload.sub || "").trim() || email.split("@")[0].replace(/[^a-z0-9]/gi, "-");

  const session = buildSession({
    userId,
    email,
    name: fullName || email.split("@")[0],
    token,
    fallbackPlan: "PRO",
  });

  cachedSession = session;
  persistSession(session);
  return session;
}

export async function devLogin(email: string, password: string): Promise<UserSession> {
  await new Promise((resolve) => setTimeout(resolve, 400));
  if (!email || !password) {
    throw new Error("Введіть email і пароль.");
  }

  const userId = `dev-${email.split("@")[0].replace(/[^a-z0-9]/gi, "-")}`;
  const session = buildSession({
    userId,
    email,
    name: email.split("@")[0],
    token: `dev-token-${userId}`,
    fallbackPlan: "FREE",
  });

  cachedSession = session;
  persistSession(session);
  return session;
}

export async function logout(): Promise<void> {
  if (typeof window === "undefined") return;
  if (supabase) {
    await supabase.auth.signOut();
  }
  cachedSession = null;
  persistSession(null);
  window.location.href = "/login";
}

export function updateSessionPlan(plan: string): void {
  const session = hydrateCachedSession();
  if (!session) return;
  cachedSession = { ...session, plan };
  persistSession(cachedSession);
}
