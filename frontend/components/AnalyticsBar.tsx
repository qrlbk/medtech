"use client";

import { formatKzt } from "@/lib/api";
import type { Analytics } from "@/lib/types";

export function AnalyticsBar({ analytics }: { analytics: Analytics }) {
  const items = [
    { label: "Минимум", value: analytics.min_price },
    { label: "Средняя", value: analytics.avg_price },
    { label: "Максимум", value: analytics.max_price },
  ];
  return (
    <div className="grid grid-cols-2 gap-3.5 sm:grid-cols-4">
      {items.map((i) => (
        <div key={i.label} className="rounded-2xl border border-line bg-surface p-4 shadow-soft">
          <div className="text-xs uppercase tracking-wide text-ink-muted">{i.label}</div>
          <div className="mt-1 font-display text-lg font-semibold text-navy">
            {i.value != null ? formatKzt(i.value) : "—"}
          </div>
        </div>
      ))}
      <div className="rounded-2xl border border-line bg-surface p-4 shadow-soft">
        <div className="text-xs uppercase tracking-wide text-ink-muted">Клиник</div>
        <div className="mt-1 font-display text-lg font-semibold text-navy">{analytics.clinic_count}</div>
      </div>
    </div>
  );
}
