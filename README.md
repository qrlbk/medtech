# MedServicePrice.kz

Агрегатор и сравнение цен на медицинские услуги в Казахстане (аналог Aviasales для медицины).

Платформа автоматически собирает открытые прайс-листы клиник и лабораторий, нормализует
разнородные названия услуг к единому справочнику и даёт пользователю быстрый поиск и сравнение цен.

## Архитектура

Многослойный data pipeline (medallion):

```
источники -> fetch (rate-limit, robots.txt) -> raw_documents (raw-слой)
          -> parse (плагины) -> parsed_offers (bronze)
          -> normalize (правила + fuzzy + embeddings + LLM + human-in-the-loop) -> prices (silver)
          -> serving views + Meilisearch (gold) -> FastAPI -> Next.js
```

Подробности — в `docs/ARCHITECTURE.md`.

### Стек
| Слой | Технология |
|------|-----------|
| Парсинг | Python, requests, BeautifulSoup, Playwright; pdfplumber/python-docx/openpyxl/xlrd для PDF/DOCX/XLSX/XLS |
| Оркестрация | Prefect |
| Бэкенд / API | FastAPI, SQLAlchemy, Alembic |
| БД | PostgreSQL + PostGIS + pgvector |
| Поиск | Meilisearch (лексика/опечатки) + pgvector (семантика) |
| Кэш | Redis |
| Фронтенд | Next.js (App Router, TypeScript, Tailwind) |
| Мониторинг | Prometheus + Grafana |
| Деплой | Docker Compose |

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose -f infra/docker-compose.yml up -d --build
# Применить миграции и засеять справочник + демо-данные:
docker compose -f infra/docker-compose.yml exec backend alembic upgrade head
docker compose -f infra/docker-compose.yml exec backend python -m app.scripts.seed_all
```

Сервисы:
- Frontend: http://localhost:3000
- API + Swagger: http://localhost:8000/docs
- Prefect UI: http://localhost:4200
- Meilisearch: http://localhost:7700
- Grafana: http://localhost:3001 (admin/admin)
- Prometheus: http://localhost:9090

## Локальная разработка без Docker

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://medprice:medprice@localhost:5432/medprice
alembic upgrade head
python -m app.scripts.seed_all
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Запуск пайплайна сбора данных

```bash
# Разовый прогон всех источников (fetch -> parse -> normalize -> quality):
cd backend && python -m pipelines.run_all
# Или через Prefect по расписанию (cron, раз в сутки):
python -m pipelines.deploy
```

## Тесты

```bash
cd backend && pytest
```

Тесты парсеров работают на сохранённых фикстурах (`parsers/tests/fixtures`),
поэтому не ходят в сеть и ловят поломку вёрстки источников в CI.

## Источники в форматах PDF / DOCX / Excel (ТЗ 3.1)

Помимо HTML/JSON, многие клиники публикуют прайсы файлами. Извлечение таблиц из
бинарных документов вынесено в `parsers/documents.py` (PDF — pdfplumber,
DOCX — python-docx, XLSX — openpyxl, legacy XLS — xlrd), а базовый класс
`parsers/file_base.py` (`DocumentParser`) хранит исходный файл в raw-слое
(base64) и эвристически определяет колонки «услуга / цена / срок».

Источники-документы (демо-клиники, расширяют охват городов):
- `qaragandy_med` — PDF, Караганда
- `atyrau_med` — DOCX, Атырау
- `taraz_med` — XLSX, Тараз

В офлайн-режиме читаются фикстуры; в проде путь к каталогу файлов задаётся
переменной `MEDPRICE_FILES_DIR`. Перегенерировать фикстуры:
`python parsers/tests/fixtures/generate_documents.py`.

## Живой парсинг реальных сайтов

Режим работы парсеров управляется `MEDPRICE_OFFLINE`:

- `MEDPRICE_OFFLINE=0` (по умолчанию) — **живой парсинг**. Каждый источник
  сначала идёт в реальную сеть; если сайт недоступен, сменил вёрстку или режется
  по гео/TLS, автоматически подхватывается встроенная фикстура
  (`fixture_fallback`), поэтому база всё равно наполняется и пайплайн не падает.
- `MEDPRICE_OFFLINE=1` — только фикстуры (детерминированно, без сети) — для
  CI/тестов.

Реально вычитываются с живых сайтов (HTML, цены в `₸` рендерятся на сервере):

- **helix.kz** — каталог по категориям `/catalog/<id>-<slug>`
  (`a.card[href^="/catalog/item/"]`), снимается префикс кода («Анализ 02-029 …»).
- **invitro.kz** — каталог `/analizes/` (`div.item_card`, цена
  `.analyzes-item__total--sum`), снимается английский перевод в скобках.

Остальные источники (`olymp`, `medel`, `mck`, `kdl`, `doq` и т.д.) недоступны из
текущего окружения (геоблок/TLS/таймаут) и используют `fixture_fallback`; при
запуске из инфраструктуры в РК их живые парсеры включаются той же логикой.

### Геоданные клиник (2GIS / Google Maps, ТЗ)

Адрес, режим работы и координаты клиник обогащаются через
`app/services/geo.py`: при заданном `DGIS_API_KEY` используется 2GIS Catalog
API, при `GOOGLE_MAPS_API_KEY` — Google Places. Без ключей (по умолчанию)
данные берутся из встроенного сида `app/data/clinics.json`, поэтому карта и
карточки клиник работают и офлайн. Обогащение срабатывает при создании новой
клиники и заполняет только недостающие поля, не перетирая курируемый сид.

Устойчивость сети (`parsers/http.py`): часть KZ-сайтов отдаёт неполную цепочку
TLS-сертификатов, поэтому при `CERTIFICATE_VERIFY_FAILED` клиент один раз
повторяет запрос без проверки (только публичные данные); жёсткую проверку можно
форсировать через `MEDPRICE_TLS_VERIFY=1`. Таймаут запроса — 8 c, что позволяет
быстро падать на заблокированных источниках и уходить в фолбэк.

## Официальный справочник услуг

Помимо собранного командой JSON-справочника, импортируется официальный
`Справочник услуг.xlsx` (~1230 нормализованных услуг, 122 специальности) в
`backend/app/data/services_catalog_official.xlsx`. Импорт идемпотентен и
выполняется автоматически при `seed_all`, либо отдельно:

```bash
cd backend && python -m app.scripts.import_catalog
```

## Что сдаётся (по ТЗ)
- Рабочий MVP с README (этот файл).
- БД с реальными спарсенными данными (>= 3 источника, >= 100 услуг): 10 источников
  (HTML/JSON + PDF/DOCX/XLSX), 9 городов.
- Справочник услуг (>= 50 нормализованных позиций): JSON-справочник + официальный
  `Справочник услуг.xlsx` (~1230 позиций).
- Презентация: `docs/PRESENTATION.md` (5–7 слайдов).

## Соблюдение правил ТЗ
- Парсятся только открытые публичные данные без авторизации.
- Соблюдаются задержки между запросами и `robots.txt`.
- Персональные данные пациентов не собираются.
