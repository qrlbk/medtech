"use client";

export interface FilterState {
  city: string;
  sort: string;
  maxPrice: string;
  minRating: string;
  onlineBooking: boolean;
}

export function Filters({
  cities,
  value,
  onChange,
  onLocate,
  hasLocation,
}: {
  cities: string[];
  value: FilterState;
  onChange: (v: FilterState) => void;
  onLocate: () => void;
  hasLocation: boolean;
}) {
  const set = (patch: Partial<FilterState>) => onChange({ ...value, ...patch });

  const control =
    "h-11 rounded-xl border border-line bg-surface px-3.5 text-sm text-ink outline-none transition focus:border-brand-500 focus:shadow-focus";

  return (
    <div className="card flex flex-wrap items-center gap-2.5 p-4 text-sm">
      <select
        value={value.city}
        onChange={(e) => set({ city: e.target.value })}
        className={control}
        aria-label="Город"
      >
        <option value="">Все города</option>
        {cities.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

      <select
        value={value.sort}
        onChange={(e) => set({ sort: e.target.value })}
        className={control}
        aria-label="Сортировка"
      >
        <option value="price_asc">Сначала дешёвые</option>
        <option value="price_desc">Сначала дорогие</option>
        <option value="updated">Недавно обновлённые</option>
        <option value="distance" disabled={!hasLocation}>По расстоянию</option>
      </select>

      <input
        type="number"
        placeholder="Цена до, ₸"
        value={value.maxPrice}
        onChange={(e) => set({ maxPrice: e.target.value })}
        className={`${control} w-32 placeholder:text-ink-muted`}
        aria-label="Максимальная цена"
      />

      <select
        value={value.minRating}
        onChange={(e) => set({ minRating: e.target.value })}
        className={control}
        aria-label="Минимальный рейтинг"
      >
        <option value="">Любой рейтинг</option>
        <option value="4">4.0+</option>
        <option value="4.5">4.5+</option>
      </select>

      <label className={`${control} flex cursor-pointer items-center gap-2`}>
        <input
          type="checkbox"
          checked={value.onlineBooking}
          onChange={(e) => set({ onlineBooking: e.target.checked })}
          className="accent-brand-500"
        />
        Онлайн-запись
      </label>

      <button
        onClick={onLocate}
        className={`h-11 rounded-xl border px-4 text-sm font-medium transition ${
          hasLocation
            ? "border-brand-500 bg-brand-50 text-brand-700"
            : "border-line bg-surface text-ink-secondary hover:border-brand-300 hover:text-brand-700"
        }`}
      >
        {hasLocation ? "Геолокация вкл." : "Рядом со мной"}
      </button>
    </div>
  );
}
