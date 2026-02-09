/**
 * API client: base URL, Bearer token, 401 refresh retry, typed errors.
 */

import { getAccessToken, getRefreshToken, refresh, logout } from "./auth";
import type { APIErrorDetail } from "./types";

const BASE_URL =
  typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_URL
    ? process.env.NEXT_PUBLIC_API_URL
    : "http://localhost:8000/api/v1";

export class APIError extends Error {
  constructor(
    public status: number,
    public detail: string,
    public body?: unknown
  ) {
    super(detail);
    this.name = "APIError";
  }
}

async function getToken(): Promise<string | null> {
  return getAccessToken();
}

/**
 * Fetch with Authorization Bearer, 401 → refresh once and retry; on refresh failure → logout and redirect to /login.
 */
export async function apiFetch(
  path: string,
  options: RequestInit = {},
  retried = false
): Promise<Response> {
  const url = path.startsWith("http") ? path : `${BASE_URL.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;
  const token = await getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  let res = await fetch(url, { ...options, headers, credentials: "include" });

  if (res.status === 401 && !retried && getRefreshToken()) {
    try {
      await refresh(BASE_URL);
      const newToken = await getToken();
      if (newToken) {
        (headers as Record<string, string>)["Authorization"] = `Bearer ${newToken}`;
        res = await fetch(url, { ...options, headers, credentials: "include" });
      }
    } catch {
      logout(true);
      throw new APIError(401, "Session expired");
    }
  }

  return res;
}

/** Parse error body and return user-facing message. */
export function parseAPIError(res: Response, body: APIErrorDetail | unknown): string {
  if (typeof (body as APIErrorDetail)?.detail === "string") {
    return (body as APIErrorDetail).detail as string;
  }
  if (
    body &&
    typeof body === "object" &&
    "detail" in body &&
    typeof (body as { detail?: unknown }).detail === "object"
  ) {
    const d = (body as { detail: { message?: string; errors?: Array<{ message: string }> } }).detail;
    if (d?.message) return d.message;
    if (Array.isArray(d?.errors) && d.errors.length) return d.errors.map((e) => e.message).join("; ");
  }
  if (res.status === 400) return "Invalid request";
  if (res.status === 403) return "Not allowed";
  if (res.status === 404) return "Not found";
  if (res.status === 409) return "Conflict (e.g. invalid state transition)";
  if (res.status === 422) return "Validation error";
  if (res.status === 429) return "Too many requests";
  if (res.status >= 500) return "Server error";
  return "Request failed";
}

/** Throwing fetch: on !res.ok throws APIError and can trigger logout on 401 after refresh failure. */
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await apiFetch(path, options);
  let body: unknown;
  const text = await res.text();
  try {
    body = text ? JSON.parse(text) : undefined;
  } catch {
    body = { detail: text || "Unknown error" };
  }

  if (!res.ok) {
    const message = parseAPIError(res, body as APIErrorDetail);
    throw new APIError(res.status, message, body);
  }

  return (body ?? undefined) as T;
}

export { BASE_URL };
