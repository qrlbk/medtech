"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { AnalyticsBar } from "@/components/AnalyticsBar";
import { CompareTable } from "@/components/CompareTable";
import { Filters, type FilterState } from "@/components/Filters";
import { ResultsList } from "@/components/ResultsList";
import { SearchBar } from "@/components/SearchBar";
import { api } from "@/lib/api";
import type { SearchResponse, ServiceSuggestion, Stats } from "@/lib/types";

const ClinicMap = dynamic(() => import("@/components/ClinicMap"), { ssr: false });

const DEFAULT_FILTERS: FilterState = {
  city: "",
  sort: "price_asc",
  maxPrice: "",
  minRating: "",
  onlineBooking: false,
};

export default function HomePage() {
  const [service, setService] = useState<ServiceSuggestion | null>(null);
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [cities, setCities] = useState<string[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [compare, setCompare] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.cities().then(setCities).catch(() => {});
    api.stats().then(setStats).catch(() => {});
  }, []);

  useEffect(() => {
    if (!service) return;
    setLoading(true);
    setCompare(new Set());
    api
      .search({
        service_id: service.id,
        city: filters.city || undefined,
        max_price: filters.maxPrice ? Number(filters.maxPrice) : undefined,
        min_rating: filters.minRating ? Number(filters.minRating) : undefined,
        has_online_booking: filters.onlineBooking || undefined,
        sort: filters.sort,
        lat: coords?.lat,
        lon: coords?.lon,
      })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [service, filters, coords]);

  const cheapest = useMemo(() => {
    if (!data || data.results.length === 0) return null;
    return Math.min(...data.results.map((r) => r.price_kzt));
  }, [data]);

  const compareOffers = useMemo(
    () => (data ? data.results.filter((r) => compare.has(r.price_id)) : []),
    [data, compare]
  );

  const locate = () => {
    if (coords) {
      setCoords(null);
      return;
    }
    navigator.geolocation?.getCurrentPosition((pos) =>
      setCoords({ lat: pos.coords.latitude, lon: pos.coords.longitude })
    );
  };

  const toggleCompare = (id: string) => {
    setCompare((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="space-y-8">
      <section className="relative rounded-3xl bg-hero-teal p-8 text-white shadow-card sm:p-12">
        {/* Decorative blobs are clipped here so the section itself can let the
            search autocomplete dropdown overflow below the hero. */}
        <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-3xl">
          <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white/10 blur-2xl" />
          <div className="absolute -bottom-20 -left-10 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
        </div>
        <div className="relative max-w-2xl">
          <span className="badge bg-white/15 text-white backdrop-blur">
            Сравнение цен · Казахстан
          </span>
          <h1 className="mt-4 font-display text-3xl font-bold leading-tight tracking-heading sm:text-4xl">
            Сравните цены на медуслуги в Казахстане
          </h1>
          <p className="mt-3 max-w-xl text-base text-white/85">
            Анализы, приёмы врачей и диагностика из клиник — собрано в одном
            спокойном месте.
          </p>
          <div className="mt-6">
            <SearchBar onSelect={setService} />
          </div>
          {stats && (
            <div className="mt-5 flex flex-wrap gap-2">
              {[
                { v: stats.active_prices, l: "цен" },
                { v: stats.clinics, l: "клиник" },
                { v: stats.cities, l: "городов" },
                { v: stats.services, l: "услуг" },
              ].map((s) => (
                <span
                  key={s.l}
                  className="rounded-full bg-white/15 px-3 py-1.5 text-sm font-medium backdrop-blur"
                >
                  <b className="font-semibold">{s.v}</b> {s.l}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {service && (
        <section className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-2xl font-bold text-ink">{service.name}</h2>
            <button
              onClick={async () => {
                const token = localStorage.getItem("medprice_token");
                if (!token) {
                  alert("Войдите в систему (страница «Админка»), чтобы подписаться.");
                  return;
                }
                try {
                  await api.subscribe(token, service.id);
                  alert("Подписка оформлена: уведомим о снижении цены.");
                } catch {
                  alert("Не удалось оформить подписку.");
                }
              }}
              className="btn-ghost"
            >
              Подписаться на снижение цены
            </button>
          </div>

          <Filters
            cities={cities}
            value={filters}
            onChange={setFilters}
            onLocate={locate}
            hasLocation={coords != null}
          />

          {data && <AnalyticsBar analytics={data.analytics} />}

          <div className="grid gap-5 lg:grid-cols-3">
            <div className="lg:col-span-2">
              {loading ? (
                <div className="card p-10 text-center text-ink-muted">Загрузка…</div>
              ) : (
                <ResultsList
                  offers={data?.results ?? []}
                  cheapest={cheapest}
                  selected={compare}
                  onToggleCompare={toggleCompare}
                />
              )}
            </div>
            <div className="card h-80 overflow-hidden p-1.5 lg:h-auto">
              <ClinicMap offers={data?.results ?? []} />
            </div>
          </div>

          {compareOffers.length >= 2 && (
            <div className="space-y-3">
              <h3 className="font-display text-lg font-semibold text-ink">Сравнение клиник</h3>
              <CompareTable offers={compareOffers} />
            </div>
          )}
        </section>
      )}

      {!service && (
        <section className="card p-8 text-ink-secondary">
          <h3 className="font-display text-lg font-semibold text-ink">С чего начать</h3>
          <p className="mt-2 max-w-2xl leading-relaxed">
            Начните вводить название услуги выше — например{" "}
            <span className="font-medium text-navy">«ОАК»</span>,{" "}
            <span className="font-medium text-navy">«УЗИ брюшной полости»</span> или{" "}
            <span className="font-medium text-navy">«приём терапевта»</span>. Подсказки
            появятся автоматически.
          </p>
        </section>
      )}
    </div>
  );
}
