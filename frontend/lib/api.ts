import type {
  Analytics, ClinicCard, PricePoint, SearchResponse, ServiceSuggestion, Stats,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000/api/v1";

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(BASE + path);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export interface SearchParams {
  service_id: string;
  city?: string;
  category?: string;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  has_online_booking?: boolean;
  sort?: string;
  lat?: number;
  lon?: number;
}

async function send<T>(method: string, path: string, body?: unknown, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(BASE + path, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
  return res.status === 204 ? (undefined as T) : (res.json() as Promise<T>);
}

export interface UnmatchedItem {
  id: string;
  parsed_offer_id: string;
  service_name_raw: string;
  source: string;
  clinic_raw: string | null;
  city: string | null;
  price_raw: number | null;
  suggested_catalog_id: string | null;
  suggested_name: string | null;
  score: number | null;
}

export const api = {
  autocomplete: (q: string) =>
    get<ServiceSuggestion[]>("/search/autocomplete", { q, limit: 8 }),
  search: (p: SearchParams) => get<SearchResponse>("/search", { ...p }),
  analytics: (serviceId: string, city?: string) =>
    get<Analytics>(`/services/${serviceId}/analytics`, { city }),
  clinic: (id: string) => get<ClinicCard>(`/clinics/${id}`),
  history: (clinicId: string, serviceId: string) =>
    get<PricePoint[]>("/prices/history", { clinic_id: clinicId, service_id: serviceId }),
  cities: () => get<string[]>("/cities"),
  categories: () => get<string[]>("/categories"),
  stats: () => get<Stats>("/stats"),
  services: () => get<ServiceSuggestion[]>("/services"),
  sources: () => get<string[]>("/sources"),
  sourceRuns: (limit = 60) => get<ParseRunInfo[]>("/sources/runs", { limit }),

  login: (email: string, password: string) =>
    send<{ access_token: string }>("POST", "/auth/login", { email, password }),
  register: (email: string, password: string) =>
    send<{ access_token: string }>("POST", "/auth/register", { email, password }),
  subscribe: (token: string, serviceId: string, clinicId?: string, target?: number) =>
    send("POST", "/subscriptions", {
      service_id: serviceId,
      clinic_id: clinicId,
      target_price_kzt: target,
    }, token),
  unmatched: (token: string) =>
    send<UnmatchedItem[]>("GET", "/admin/unmatched", undefined, token),
  resolve: (token: string, queueId: string, catalogId: string | null) =>
    send("POST", `/admin/unmatched/${queueId}/resolve`, {
      catalog_id: catalogId,
      add_as_synonym: true,
    }, token),
  triggerIngest: (token: string, source?: string) =>
    send<{ status: string; detail: string }>(
      "POST",
      source ? `/admin/ingest?source=${encodeURIComponent(source)}` : "/admin/ingest",
      {},
      token
    ),
  uploadIngest: async (
    token: string,
    file: File,
    clinic: string,
    city: string
  ): Promise<UploadResult> => {
    const form = new FormData();
    form.append("file", file);
    form.append("clinic", clinic);
    form.append("city", city);
    const res = await fetch(BASE + "/admin/ingest/upload", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text()}`);
    return res.json() as Promise<UploadResult>;
  },
};

export interface ParseRunInfo {
  source: string;
  status: string;
  offers_found: number | null;
  offers_new: number | null;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface UploadResult {
  filename: string;
  format: string;
  clinic: string;
  city: string;
  rows: number;
  offers_found: number;
  offers_new: number;
  auto_matched: number;
  unmatched: number;
  prices_created: number;
}

export function formatKzt(value: number): string {
  return new Intl.NumberFormat("ru-RU").format(Math.round(value)) + " ₸";
}
