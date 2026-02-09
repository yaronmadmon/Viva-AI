/**
 * Auth layer: token storage, login, logout, refresh.
 * Uses localStorage (client-only). Tokens attached to API requests via api.ts.
 */

import type { TokenResponse, UserResponse } from "./types";

const ACCESS_KEY = "viva_access_token";
const REFRESH_KEY = "viva_refresh_token";
const USER_KEY = "viva_user";

function isClient(): boolean {
  return typeof window !== "undefined";
}

export function getAccessToken(): string | null {
  if (!isClient()) return null;
  return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
  if (!isClient()) return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function getUser(): UserResponse | null {
  if (!isClient()) return null;
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as UserResponse;
  } catch {
    return null;
  }
}

const AUTH_COOKIE = "viva_authenticated";

export function setTokens(data: TokenResponse): void {
  if (!isClient()) return;
  localStorage.setItem(ACCESS_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(data.user));
  document.cookie = `${AUTH_COOKIE}=1; path=/; max-age=${60 * 60 * 24 * 7}; SameSite=Lax`;
}

export function clearAuth(): void {
  if (!isClient()) return;
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  document.cookie = `${AUTH_COOKIE}=; path=/; max-age=0`;
}

export function setUser(user: UserResponse): void {
  if (!isClient()) return;
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

/** Call after login/register; stores tokens and user. */
export function login(data: TokenResponse): void {
  setTokens(data);
}

/** Clear local tokens; optionally call backend /auth/logout first. */
export function logout(redirectToLogin = true): void {
  clearAuth();
  if (redirectToLogin && isClient()) {
    window.location.href = "/login";
  }
}

/**
 * Refresh access token using refresh token.
 * Returns new TokenResponse on success; throws on failure.
 */
export async function refresh(baseUrl: string): Promise<TokenResponse> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    throw new Error("No refresh token");
  }
  const res = await fetch(`${baseUrl}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!res.ok) {
    const text = await res.text();
    let detail = "Refresh failed";
    try {
      const j = JSON.parse(text) as { detail?: string };
      if (j.detail) detail = typeof j.detail === "string" ? j.detail : String(j.detail);
    } catch {
      detail = text || detail;
    }
    throw new Error(detail);
  }
  const data = (await res.json()) as TokenResponse;
  setTokens(data);
  return data;
}
