"use client";

import { useEffect, useRef, useState } from "react";
import { api, formatKzt, type UnmatchedItem } from "@/lib/api";
import type { ServiceSuggestion } from "@/lib/types";

export default function AdminPage() {
  const [token, setToken] = useState<string | null>(null);
  const [email, setEmail] = useState("admin@medprice.kz");
  const [password, setPassword] = useState("admin");
  const [error, setError] = useState("");
  const [items, setItems] = useState<UnmatchedItem[]>([]);
  const [services, setServices] = useState<ServiceSuggestion[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [source, setSource] = useState("");
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const [upClinic, setUpClinic] = useState("");
  const [upCity, setUpCity] = useState("");
  const [upFile, setUpFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressLabel, setProgressLabel] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current);
  }, []);

  useEffect(() => {
    const saved = localStorage.getItem("medprice_token");
    if (saved) setToken(saved);
  }, []);

  useEffect(() => {
    if (!token) return;
    api.services().then(setServices).catch(() => {});
    api.sources().then(setSources).catch(() => {});
    refresh();
  }, [token]);

  const refresh = () => {
    if (!token) return;
    api.unmatched(token).then(setItems).catch(() => setItems([]));
  };

  const login = async () => {
    setError("");
    try {
      const { access_token } = await api.login(email, password);
      localStorage.setItem("medprice_token", access_token);
      setToken(access_token);
    } catch {
      setError("Неверный email или пароль");
    }
  };

  const resolve = async (item: UnmatchedItem, reject: boolean) => {
    if (!token) return;
    const catalogId = reject ? null : choice[item.id] ?? item.suggested_catalog_id;
    if (!reject && !catalogId) {
      setMsg("Выберите услугу справочника или отклоните запись");
      return;
    }
    await api.resolve(token, item.id, catalogId);
    setItems((prev) => prev.filter((i) => i.id !== item.id));
  };

  const ingest = async () => {
    if (!token || ingesting) return;
    setMsg("");

    // Server-side baseline: parse-runs newer than this belong to our trigger.
    let baseline = "";
    try {
      const pre = await api.sourceRuns(1);
      baseline = pre[0]?.started_at ?? "";
    } catch {}

    const expected = Math.max(1, source ? 1 : sources.length);
    try {
      await api.triggerIngest(token, source || undefined);
    } catch {
      setMsg("Не удалось запустить парсинг.");
      return;
    }

    setIngesting(true);
    setProgress(6);
    setProgressLabel(`Парсинг запущен — 0 из ${expected} источников…`);
    const startedAt = Date.now();
    // Rough time estimate so the bar advances smoothly between real updates.
    const estTotalMs = expected * 1400 + 2000;

    pollRef.current = setInterval(async () => {
      let finishedCount = 0;
      let newOffers = 0;
      let errors = 0;
      try {
        const runs = await api.sourceRuns(80);
        const batch = runs.filter((r) => (r.started_at ?? "") > baseline);
        const done = batch.filter((r) => r.status !== "running");
        finishedCount = done.length;
        newOffers = done.reduce((s, r) => s + (r.offers_new ?? 0), 0);
        errors = done.filter((r) => r.status === "error").length;
      } catch {}

      const elapsed = Date.now() - startedAt;
      const creep = Math.min(90, Math.round((elapsed / estTotalMs) * 100));
      const real = Math.round((finishedCount / expected) * 100);
      setProgress((p) => Math.max(p, 6, creep, Math.min(95, real)));
      setProgressLabel(`Обработано ${Math.min(finishedCount, expected)} из ${expected} источников…`);

      const timedOut = elapsed > 90000;
      if (finishedCount >= expected || timedOut) {
        if (pollRef.current) clearInterval(pollRef.current);
        pollRef.current = null;
        setProgress(100);
        setProgressLabel(
          timedOut
            ? "Завершаем… (превышено ожидание)"
            : `Готово: источников ${finishedCount}, новых строк ${newOffers}` +
                (errors ? `, ошибок ${errors}` : "")
        );
        setTimeout(() => {
          setIngesting(false);
          setProgress(0);
          refresh();
        }, 1400);
      }
    }, 800);
  };

  const upload = async () => {
    if (!token || !upFile) return;
    if (!upClinic.trim() || !upCity.trim()) {
      setMsg("Укажите клинику и город для загружаемого файла.");
      return;
    }
    setUploading(true);
    setMsg("");
    try {
      const r = await api.uploadIngest(token, upFile, upClinic.trim(), upCity.trim());
      setMsg(
        `Файл «${r.filename}» (${r.format.toUpperCase()}): строк ${r.rows}, ` +
          `новых предложений ${r.offers_new}, привязано ${r.auto_matched}, ` +
          `в очереди ${r.unmatched}, обновлено цен ${r.prices_created}.`
      );
      setUpFile(null);
      refresh();
    } catch (e) {
      setMsg(`Ошибка загрузки: ${e instanceof Error ? e.message : "неизвестно"}`);
    } finally {
      setUploading(false);
    }
  };

  if (!token) {
    return (
      <div className="mx-auto max-w-sm card p-7">
        <h1 className="font-display text-xl font-bold text-ink">Вход в админку</h1>
        <p className="mt-1 text-sm text-ink-secondary">Ручная разметка непривязанных услуг.</p>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="email"
          className="field mt-5 w-full"
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          type="password"
          placeholder="пароль"
          className="field mt-3 w-full"
        />
        {error && <div className="mt-3 text-sm text-danger">{error}</div>}
        <button onClick={login} className="btn-primary mt-5 w-full">
          Войти
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-xl font-bold text-ink">
          Очередь ручной разметки ({items.length})
        </h1>
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            disabled={ingesting}
            className="h-10 rounded-xl border border-line bg-surface px-3 text-sm text-ink outline-none transition focus:border-brand-500 focus:shadow-focus disabled:opacity-50"
          >
            <option value="">Все источники</option>
            {sources.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          <button
            onClick={ingest}
            disabled={ingesting}
            className="btn-secondary h-10 px-4 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {ingesting ? "Парсинг…" : "Запустить парсинг"}
          </button>
          <button onClick={refresh} className="btn-ghost h-10 px-4">
            Обновить
          </button>
        </div>
      </div>

      {ingesting && (
        <div className="card p-4">
          <div className="flex items-center justify-between text-sm text-ink-secondary">
            <span>{progressLabel}</span>
            <span className="tabular-nums font-medium text-ink">{progress}%</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-subtle">
            <div
              className="h-full rounded-full bg-brand-500 transition-all duration-500 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}
      {msg && (
        <div className="rounded-xl bg-brand-50 px-4 py-3 text-sm text-brand-700">{msg}</div>
      )}

      <div className="card p-5">
        <h2 className="font-display text-base font-semibold text-ink">
          Загрузить прайс-лист с устройства
        </h2>
        <p className="mt-1 text-sm text-ink-secondary">
          Файл клиники в формате PDF, DOCX, XLSX или XLS. Система извлечёт услуги
          и цены и отправит их на нормализацию.
        </p>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <input
            value={upClinic}
            onChange={(e) => setUpClinic(e.target.value)}
            placeholder="Название клиники"
            className="field w-full"
          />
          <input
            value={upCity}
            onChange={(e) => setUpCity(e.target.value)}
            placeholder="Город"
            className="field w-full"
          />
          <input
            type="file"
            accept=".pdf,.docx,.xlsx,.xls"
            onChange={(e) => setUpFile(e.target.files?.[0] ?? null)}
            className="block w-full text-sm text-ink-secondary file:mr-3 file:rounded-lg file:border-0 file:bg-brand-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-brand-700 hover:file:bg-brand-100"
          />
          <button
            onClick={upload}
            disabled={!upFile || uploading}
            className="btn-primary h-10 px-4 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? "Загрузка…" : "Загрузить и распарсить"}
          </button>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-line bg-surface p-10 text-center text-ink-muted">
          Очередь пуста — все услуги нормализованы.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div key={item.id} className="card p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="font-medium text-ink">{item.service_name_raw}</div>
                  <div className="mt-1 text-xs text-ink-muted">
                    {item.source} · {item.clinic_raw} · {item.city} ·{" "}
                    {item.price_raw != null ? formatKzt(item.price_raw) : "—"}
                    {item.suggested_name && ` · подсказка: ${item.suggested_name} (${((item.score ?? 0) * 100).toFixed(0)}%)`}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={choice[item.id] ?? item.suggested_catalog_id ?? ""}
                    onChange={(e) => setChoice({ ...choice, [item.id]: e.target.value })}
                    className="h-10 rounded-xl border border-line bg-surface px-3 text-sm text-ink outline-none transition focus:border-brand-500 focus:shadow-focus"
                  >
                    <option value="">— выбрать услугу —</option>
                    {services.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => resolve(item, false)}
                    className="h-10 rounded-xl bg-success px-4 text-sm font-semibold text-white transition hover:brightness-95"
                  >
                    Привязать
                  </button>
                  <button
                    onClick={() => resolve(item, true)}
                    className="h-10 rounded-xl border border-line px-4 text-sm font-medium text-danger transition hover:bg-danger/5"
                  >
                    Отклонить
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
