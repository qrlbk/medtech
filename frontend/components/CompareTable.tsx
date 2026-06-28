"use client";

import { formatKzt } from "@/lib/api";
import type { PriceOffer } from "@/lib/types";

export function CompareTable({ offers }: { offers: PriceOffer[] }) {
  if (offers.length < 2) return null;
  const rows: { label: string; render: (o: PriceOffer) => string }[] = [
    { label: "Цена", render: (o) => formatKzt(o.price_kzt) },
    { label: "Город", render: (o) => o.clinic.city },
    { label: "Адрес", render: (o) => o.clinic.address ?? "—" },
    { label: "Телефон", render: (o) => o.clinic.phone ?? "—" },
    { label: "Часы", render: (o) => o.clinic.working_hours ?? "—" },
    { label: "Рейтинг", render: (o) => (o.clinic.rating != null ? o.clinic.rating.toFixed(1) : "—") },
    { label: "Онлайн-запись", render: (o) => (o.clinic.has_online_booking ? "да" : "нет") },
    { label: "Срок", render: (o) => (o.duration_days != null ? `${o.duration_days} дн.` : "—") },
  ];
  return (
    <div className="overflow-x-auto rounded-2xl border border-line bg-surface shadow-card">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-line bg-subtle">
            <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-ink-muted">Параметр</th>
            {offers.map((o) => (
              <th key={o.price_id} className="px-4 py-3 text-left font-display font-semibold text-ink">
                {o.clinic.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.label} className="border-b border-line-light last:border-0">
              <td className="px-4 py-3 text-ink-muted">{r.label}</td>
              {offers.map((o) => (
                <td key={o.price_id} className="px-4 py-3 text-ink-secondary">{r.render(o)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
