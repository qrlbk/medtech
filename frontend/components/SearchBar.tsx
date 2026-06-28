"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, type ServiceSuggestion } from "@/lib/types";

export function SearchBar({
  onSelect,
  initialQuery = "",
}: {
  onSelect: (s: ServiceSuggestion) => void;
  initialQuery?: string;
}) {
  const [query, setQuery] = useState(initialQuery);
  const [suggestions, setSuggestions] = useState<ServiceSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length < 1) {
      setSuggestions([]);
      return;
    }
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        setSuggestions(await api.autocomplete(query.trim()));
        setOpen(true);
      } catch {
        setSuggestions([]);
      } finally {
        setLoading(false);
      }
    }, 180);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={boxRef} className="relative">
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocusCapture={() => suggestions.length && setOpen(true)}
        placeholder="Найдите услугу: ОАК, УЗИ, приём терапевта…"
        aria-label="Поиск медицинской услуги"
        className="h-14 w-full rounded-2xl border border-white/40 bg-white px-5 text-base text-ink shadow-card outline-none transition placeholder:text-ink-muted focus:border-brand-500 focus:shadow-focus"
      />
      {open && suggestions.length > 0 && (
        <ul className="absolute z-30 mt-2 max-h-80 w-full overflow-auto rounded-2xl border border-line bg-surface text-ink shadow-card-hover">
          {suggestions.map((s) => (
            <li key={s.id}>
              <button
                onClick={() => {
                  setQuery(s.name);
                  setOpen(false);
                  onSelect(s);
                }}
                className="flex w-full items-center justify-between px-5 py-3 text-left transition hover:bg-subtle"
              >
                <span className="font-medium">{s.name}</span>
                <span className="badge ml-3 bg-subtle text-ink-secondary">
                  {CATEGORY_LABELS[s.category]}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {loading && (
        <span className="absolute right-4 top-4 text-sm text-ink-muted">…</span>
      )}
    </div>
  );
}
