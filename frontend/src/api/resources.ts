import { ApiError, apiFetch } from "./client";
import { getApiBaseUrl } from "./client";

export type Entity = { id: string } & Record<string, unknown>;

type ListResponse = {
  count?: number;
  next?: string | null;
  previous?: string | null;
  results?: Entity[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function toApiPath(next: string): string {
  const parsed = new URL(next, window.location.origin);
  const base = new URL(getApiBaseUrl(), window.location.origin).pathname.replace(/\/$/, "");
  let pathname = parsed.pathname;
  if (base && pathname.startsWith(`${base}/`)) pathname = pathname.slice(base.length);
  return `${pathname}${parsed.search}`;
}

export async function apiFetchList<T extends Entity>(path: string): Promise<T[]> {
  const collected: T[] = [];
  const seen = new Set<string>();
  let cursor: string | null = path;

  while (cursor && !seen.has(cursor) && collected.length < 500) {
    seen.add(cursor);
    const data = await apiFetch<unknown>(cursor);
    if (Array.isArray(data)) return [...collected, ...(data as T[])];
    if (isRecord(data) && Array.isArray(data.results)) {
      const page = data as ListResponse;
      collected.push(...((page.results || []) as T[]));
      cursor = typeof page.next === "string" ? toApiPath(page.next) : null;
      continue;
    }
    break;
  }
  return collected;
}

export function apiPost<T>(path: string, body: Record<string, unknown> = {}): Promise<T> {
  return apiFetch<T>(path, { method: "POST", body: JSON.stringify(body) });
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export function text(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number" || typeof value === "string") return String(value);
  if (Array.isArray(value)) return value.map((item) => text(item, "")).filter(Boolean).join(", ") || fallback;
  return JSON.stringify(value);
}

export function shortDate(value: unknown): string {
  const raw = text(value, "");
  return raw.includes("T") ? raw.slice(0, 10) : raw;
}

export function optionLabel(item: Entity): string {
  return text(item.name) + (item.code ? ` (${text(item.code)})` : "");
}

export function numberValue(value: string): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}
