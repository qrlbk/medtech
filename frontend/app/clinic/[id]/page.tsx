"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { PriceHistoryChart } from "@/components/PriceHistoryChart";
import { api, formatKzt } from "@/lib/api";
import { CATEGORY_LABELS, type ClinicCard } from "@/lib/types";

export default function ClinicPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [clinic, setClinic] = useState<ClinicCard | null>(null);
  const [openService, setOpenService] = useState<string | null>(null);

  useEffect(() => {
    api.clinic(id).then(setClinic).catch(() => setClinic(null));
  }, [id]);

  if (!clinic) {
    return <div className="card p-10 text-center text-ink-muted">Загрузка клиники…</div>;
  }

  return (
    <div className="space-y-6">
      <Link href="/" className="text-sm font-medium text-brand-600 transition hover:text-brand-700">
        ← Назад к поиску
      </Link>

      <div className="card p-6 sm:p-8">
        <h1 className="font-display text-2xl font-bold text-ink sm:text-3xl">{clinic.name}</h1>
        <div className="mt-3 grid gap-1.5 text-sm text-ink-secondary sm:grid-cols-2">
          <div>{clinic.city}{clinic.address ? `, ${clinic.address}` : ""}</div>
          {clinic.phone && <div>тел: {clinic.phone}</div>}
          {clinic.working_hours && <div>часы: {clinic.working_hours}</div>}
          {clinic.rating != null && (
            <div>рейтинг: <span className="font-medium text-warning">★ {clinic.rating.toFixed(1)}</span></div>
          )}
          {clinic.website && (
            <div>
              <a href={clinic.website} target="_blank" rel="noreferrer" className="text-brand-600 underline hover:text-brand-700">
                сайт клиники
              </a>
            </div>
          )}
          {clinic.has_online_booking && (
            <div>
              <span className="badge bg-brand-50 text-brand-700">онлайн-запись доступна</span>
            </div>
          )}
        </div>
      </div>

      <div>
        <h2 className="mb-3 font-display text-lg font-semibold text-ink">
          Услуги и цены ({clinic.services.length})
        </h2>
        <div className="divide-y divide-line-light overflow-hidden rounded-2xl border border-line bg-surface shadow-card">
          {clinic.services.map((s) => (
            <div key={s.service_id}>
              <button
                onClick={() => setOpenService(openService === s.service_id ? null : s.service_id)}
                className="flex w-full items-center justify-between px-5 py-4 text-left transition hover:bg-subtle"
              >
                <span>
                  <span className="font-medium text-ink">{s.name}</span>
                  <span className="badge ml-2 bg-subtle text-ink-secondary">
                    {CATEGORY_LABELS[s.category]}
                  </span>
                </span>
                <span className="font-display font-semibold text-navy">{formatKzt(s.price_kzt)}</span>
              </button>
              {openService === s.service_id && (
                <div className="border-t border-line-light bg-subtle px-5 py-4">
                  <PriceHistoryChart clinicId={clinic.id} serviceId={s.service_id} />
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
