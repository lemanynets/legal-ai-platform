import { request } from "./http-client";

export type AuthLoginResponse = {
  access_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name?: string | null;
    role?: string;
    plan?: string;
  };
};

export async function login(payload: { email: string; password: string }) {
  return request<AuthLoginResponse>("/api/auth/login", {
    method: "POST",
    body: payload,
  });
}

export async function register(payload: { email: string; password: string; full_name?: string }) {
  return request<AuthLoginResponse>("/api/auth/register", {
    method: "POST",
    body: payload,
  });
}

export async function getMe(token?: string, demoUser?: string) {
  return request<{ id: string; email: string; full_name?: string | null; role?: string }>("/api/auth/me", {
    token,
    demoUser,
  });
}
