# Архитектура MedServicePrice.kz

## Принцип
Это не «сайт с парсером», а **платформа данных**. Главная ценность — качество и
прослеживаемость цен: для любой цены мы знаем источник, время сбора и исходный
«сырой» текст. UI — витрина над этим фундаментом.

## Слои данных (medallion)

```
источники ──► fetch (rate-limit, robots.txt, content-hash)
          ──► raw_documents        (RAW: HTML/JSON как есть, для переразбора и аудита)
          ──► parsed_offers        (BRONZE: строки «как на сайте»)
          ──► prices (versioned)   (SILVER: привязка к справочнику, KZT, confidence)
          ──► serving views + Meili (GOLD: денормализовано под поиск)
```

- **RAW** никогда не перезаписывается → можно переразобрать данные при изменении логики
  парсинга без повторного похода на сайт. Хранение ≥ 90 дней (аудит, ТЗ).
- **Versioned prices**: при изменении цены вставляется новая строка, старая помечается
  `is_active=False`. Бесплатно даёт историю цен и графики.

## Поток сбора (плагинная архитектура)

```
BaseParser (fetch/parse) ── registry ──► ingest_source (per-source isolation)
                                          │
                                          ├─ persist_raw_doc  (dedup по content_hash)
                                          └─ persist_offers   (dedup по dedup_hash)
```

Добавление источника = новый файл `parsers/sources/<name>.py` с `@register`.
Ядро не меняется (требование масштабируемости ТЗ). Падение одного источника не
останавливает остальные (изоляция на уровне Prefect task / try-except).

Реализованные форматы: HTML-таблицы (KDL, Helix, MCK), HTML-карточки (Invitro),
HTML-список (Medel), встроенный JSON (Olymp), JSON-агрегатор многих клиник (Doq).

## Нормализация (multi-stage matcher)
1. **Точный** матч по справочнику синонимов (`alias_norm`).
2. **Fuzzy** (rapidfuzz `token_set_ratio`), порог `NORMALIZE_FUZZY_THRESHOLD`.
3. **Семантический** — multilingual embeddings → ближайший вектор в pgvector,
   порог `NORMALIZE_MATCH_THRESHOLD`.
4. **LLM-арбитр** (опционально) для пограничных случаев.
5. Ниже порога → запись становится **suggestion** и уходит в `unmatched_queue`
   (human-in-the-loop). Решение оператора сохраняется как новый синоним —
   матчер «учится», и в следующий прогон такая услуга матчится автоматически.

## Контроль качества
- Валидация цен (диапазон, положительность), конвертация USD→KZT.
- Anomaly detection: скачок цены > 10× → понижение `confidence` и флаг в UI.
- Свежесть: цены старше `DATA_FRESH_DAYS` (30) не считаются актуальными.

## Поиск (гибридный)
- **Meilisearch** — автодополнение, опечатки, морфология ru/kk.
- **pgvector** — семантический матч запроса.
- **PostGIS** — сортировка по расстоянию.
- **Redis** — кэш горячих запросов.
- Все внешние сервисы имеют graceful-фоллбэк (Postgres trigram / без кэша), поэтому
  система не падает, если что-то из инфраструктуры недоступно.

## Сервисы (docker-compose)
postgres(+postgis+pgvector), redis, meilisearch, backend(FastAPI), prefect,
worker(расписание), telegram-bot, frontend(Next.js), prometheus, grafana.

## Наблюдаемость
- `/metrics` (Prometheus): свежесть данных, размер unmatched-очереди, запуски парсеров
  по статусу, RPS, латентность p95.
- Журнал `parse_runs`: статус/ошибка/счётчики по каждому запуску источника.
- Grafana-дашборд провижинится автоматически.
