"use client";

import { useEffect, useState } from "react";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { api, formatKzt } from "@/lib/api";
import type { PricePoint } from "@/lib/types";

export function PriceHistoryChart({
  clinicId,
  serviceId,
}: {
  clinicId: string;
  serviceId: string;
}) {
  const [points, setPoints] = useState<PricePoint[]>([]);

  useEffect(() => {
    api.history(clinicId, serviceId).then(setPoints).catch(() => setPoints([]));
  }, [clinicId, serviceId]);

  if (points.length < 2) {
    return (
      <p className="text-sm text-ink-muted">
        Недостаточно данных для графика истории цен (нужно минимум 2 точки).
      </p>
    );
  }

  const data = points.map((p) => ({
    date: p.date ? new Date(p.date).toLocaleDateString("ru-RU") : "",
    price: p.price_kzt,
  }));

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#EEF2F6" />
          <XAxis dataKey="date" fontSize={12} stroke="#8893A2" />
          <YAxis fontSize={12} stroke="#8893A2" tickFormatter={(v) => `${v / 1000}к`} />
          <Tooltip
            formatter={(v: number) => formatKzt(v)}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid #E5EBF2",
              boxShadow: "0 12px 36px rgba(25,42,70,0.08)",
            }}
          />
          <Line
            type="monotone"
            dataKey="price"
            stroke="#1FAFC1"
            strokeWidth={2.5}
            dot={{ r: 3, fill: "#1FAFC1" }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
