COMPOSE = docker compose -f infra/docker-compose.yml

.PHONY: up down logs migrate seed pipeline test fe-build lint

up:            ## Build and start the full stack
	$(COMPOSE) up -d --build

down:          ## Stop the stack
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=100

migrate:       ## Apply DB migrations
	$(COMPOSE) exec backend alembic upgrade head

seed:          ## Seed catalog + admin + offline demo data
	$(COMPOSE) exec backend python -m app.scripts.seed_all

pipeline:      ## Run the ingest -> normalize -> index pipeline once
	$(COMPOSE) exec backend python -m pipelines.run_all

test:          ## Run backend tests (offline, fixtures-based)
	cd backend && MEDPRICE_OFFLINE=1 pytest -q

fe-build:      ## Build the frontend
	cd frontend && npm install && npm run build

lint:
	cd backend && ruff check app parsers pipelines
