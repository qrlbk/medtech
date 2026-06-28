export type Category = "laboratory" | "doctor_visit" | "diagnostics" | "procedure";

export interface ServiceSuggestion {
  id: string;
  name: string;
  category: Category;
}

export interface ClinicBrief {
  id: string;
  name: string;
  city: string;
  address: string | null;
  phone: string | null;
  working_hours: string | null;
  website: string | null;
  rating: number | null;
  has_online_booking: boolean;
  lat: number | null;
  lon: number | null;
}

export interface PriceOffer {
  price_id: string;
  price_kzt: number;
  duration_days: number | null;
  parsed_at: string | null;
  is_fresh: boolean;
  confidence: number;
  source_url: string | null;
  clinic: ClinicBrief;
  distance_m: number | null;
}

export interface Analytics {
  min_price: number | null;
  avg_price: number | null;
  max_price: number | null;
  clinic_count: number;
}

export interface SearchResponse {
  service: { id: string; name: string; category: Category };
  count: number;
  results: PriceOffer[];
  analytics: Analytics;
}

export interface ClinicCard {
  id: string;
  name: string;
  city: string;
  address: string | null;
  phone: string | null;
  working_hours: string | null;
  website: string | null;
  rating: number | null;
  has_online_booking: boolean;
  services: {
    service_id: string;
    name: string;
    category: Category;
    price_kzt: number;
    duration_days: number | null;
    parsed_at: string | null;
  }[];
}

export interface PricePoint {
  price_kzt: number;
  date: string | null;
  is_active: boolean;
}

export interface Stats {
  services: number;
  synonyms: number;
  clinics: number;
  cities: number;
  active_prices: number;
  sources: number;
  unmatched: number;
}

export const CATEGORY_LABELS: Record<Category, string> = {
  laboratory: "Лаборатория",
  doctor_visit: "Приём врача",
  diagnostics: "Диагностика",
  procedure: "Процедура",
};
