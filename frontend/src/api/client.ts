const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1").replace(/\/$/, "");

export const UNAUTHORIZED_EVENT = "school-erp:unauthorized";

type JsonRecord = Record<string, unknown>;

export class ApiError extends Error {
  readonly status: number;
  readonly path: string;
  readonly payload: unknown;

  constructor(message: string, status: number, path: string, payload: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.path = path;
    this.payload = payload;
  }
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function flattenMessages(value: unknown): string {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(flattenMessages).filter(Boolean).join(" ");
  if (isRecord(value)) {
    return Object.entries(value)
      .map(([key, item]) => {
        const label = key.replace(/_/g, " ");
        const message = flattenMessages(item);
        return message ? `${label}: ${message}` : "";
      })
      .filter(Boolean)
      .join(" ");
  }
  return value == null ? "" : String(value);
}

function messageFromPayload(payload: unknown, status: number): string {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (isRecord(payload)) {
    const errors = payload.errors ?? payload;
    if (typeof errors === "string" && errors.trim()) return errors;
    if (isRecord(errors)) {
      const detail = errors.detail ?? errors.non_field_errors ?? payload.detail;
      const detailMessage = flattenMessages(detail);
      if (detailMessage) return detailMessage;
      const fieldMessage = flattenMessages(errors);
      if (fieldMessage) return fieldMessage;
    }
    const direct = flattenMessages(payload);
    if (direct) return direct;
  }
  return `Request failed (${status})`;
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(^|;\\s*)" + name + "=([^;]*)"));
  return match ? decodeURIComponent(match[2]) : null;
}

function buildUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${suffix}`;
}

function buildHeaders(init: RequestInit): Headers {
  const headers = new Headers(init.headers || {});
  const method = (init.method || "GET").toUpperCase();
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    const csrf = getCookie("csrftoken");
    if (csrf) headers.set("X-CSRFToken", csrf);
  }
  return headers;
}

async function parsePayload(res: Response): Promise<unknown> {
  const contentType = res.headers.get("content-type") || "";
  try {
    if (contentType.includes("application/json")) return await res.json();
    const text = await res.text();
    return text || null;
  } catch {
    return null;
  }
}

async function request(path: string, init: RequestInit): Promise<Response> {
  const res = await fetch(buildUrl(path), {
    credentials: "include",
    ...init,
    headers: buildHeaders(init),
  });
  if (!res.ok) {
    if (res.status === 401 && !path.startsWith("/auth/")) {
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT, { detail: { path } }));
    }
    const payload = await parsePayload(res);
    throw new ApiError(messageFromPayload(payload, res.status), res.status, path, payload);
  }
  return res;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await request(path, init);
  if (res.status === 204) return undefined as T;
  const data = await parsePayload(res);
  return data as T;
}

export async function apiFetchBlob(path: string, fallbackName: string): Promise<{ blob: Blob; filename: string }> {
  const res = await request(path, {});
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") || "";
  const match = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/i);
  const raw = match?.[1] || match?.[2];
  const filename = raw ? decodeURIComponent(raw.trim().replace(/^"|"$/g, "")) : fallbackName;
  return { blob, filename };
}

export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

export async function getCsrf(): Promise<{ csrfToken: string }> {
  return apiFetch<{ csrfToken: string }>("/auth/csrf/");
}

export function getApiBaseUrl(): string {
  return API_BASE_URL;
}
