"use client";

import Link from "next/link";
import { formatKzt } from "@/lib/api";
import type { PriceOffer } from "@/lib/types";

export function ResultsList({
  offers,
  cheapest,
  selected,
  onToggleCompare,
}: {
  offers: PriceOffer[];
  cheapest: number | null;
  selected: Set<string>;
  onToggleCompare: (priceId: string) => void;
}) {
  if (offers.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-line bg-surface p-10 text-center text-ink-muted">
        Ничего не найдено по заданным фильтрам.
      </div>
    );
  }

  return (
    <div className="space-y-3.5">
      {offers.map((o) => {
        const isCheapest = cheapest != null && o.price_kzt === cheapest;
        return (
          <div
            key={o.price_id}
            className={`flex flex-col gap-3 rounded-2xl border bg-surface p-5 shadow-card transition duration-200 hover:shadow-card-hover sm:flex-row sm:items-center sm:justify-between ${
              isCheapest ? "border-brand-300 ring-1 ring-brand-200" : "border-line"
            }`}
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  href={`/clinic/${o.clinic.id}`}
                  className="font-display font-semibold text-ink transition hover:text-brand-700"
                >
                  {o.clinic.name}
                </Link>
                {isCheapest && (
                  <span className="badge bg-[#E8FAEE] text-[#24A148]">
                    Лучшая цена
                  </span>
                )}
                {o.clinic.has_online_booking && (
                  <span className="badge bg-brand-50 text-brand-700">
                    Онлайн-запись
                  </span>
                )}
              </div>
              <div className="mt-1.5 text-sm text-ink-secondary">
                {o.clinic.city}
                {o.clinic.address ? `, ${o.clinic.address}` : ""}
                {o.clinic.working_hours ? ` · ${o.clinic.working_hours}` : ""}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-ink-muted">
                {o.clinic.rating != null && (
                  <span className="font-medium text-warning">★ {o.clinic.rating.toFixed(1)}</span>
                )}
                {o.duration_days != null && <span>срок {o.duration_days} дн.</span>}
                {o.distance_m != null && <span>{(o.distance_m / 1000).toFixed(1)} км</span>}
                <span className={o.is_fresh ? "text-success" : "text-warning"}>
                  {o.is_fresh ? "актуально" : "данные устарели"}
                  {o.parsed_at ? ` · ${new Date(o.parsed_at).toLocaleDateString("ru-RU")}` : ""}
                </span>
                {o.source_url && (
                  <a href={o.source_url} target="_blank" rel="noreferrer" className="text-brand-600 underline hover:text-brand-700">
                    источник
                  </a>
                )}
              </div>
            </div>
            <div className="flex items-center gap-4 border-t border-line pt-3 sm:border-0 sm:pt-0">
              <label className="flex cursor-pointer items-center gap-1.5 text-xs text-ink-secondary">
                <input
                  type="checkbox"
                  checked={selected.has(o.price_id)}
                  onChange={() => onToggleCompare(o.price_id)}
                  className="accent-brand-500"
                />
                сравнить
              </label>
              <div className="text-right">
                <div className="font-display text-xl font-bold text-navy">{formatKzt(o.price_kzt)}</div>
                {o.confidence < 0.7 && (
                  <div className="text-xs text-warning">требует проверки</div>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
