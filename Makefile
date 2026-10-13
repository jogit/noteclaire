.PHONY: install dev-backend dev-frontend test lint check coverage unused format up down logs

# Développement hors Docker : la base est dans ./data
LOCAL_ENV = DATABASE_URL=sqlite:///../data/app.db DATA_DIR=../data BACKUP_DIR=../backups CHATGPT_REDIRECT_PORT=5173

install:
	cd backend && uv sync --frozen
	cd frontend && npm ci

dev-backend:
	cd backend && $(LOCAL_ENV) uv run alembic upgrade head
	cd backend && $(LOCAL_ENV) uv run uvicorn --factory app.main:create_app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -q
	cd frontend && npm test

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app tests
	cd frontend && npm run lint && npm run typecheck

# Avant de proposer un changement : tout ce qui doit être vert.
check: lint test

# Couverture des tests (indicatif : environ 95 % côté serveur, 85 % côté interface).
coverage:
	cd backend && uv run pytest -q --cov=app --cov-report=term-missing:skip-covered
	cd frontend && npm run coverage

# Code mort : fonctions, méthodes, classes et imports jamais utilisés, dépendances inutiles. Les
# « variables » signalées à 60 % sont des champs Pydantic ou de dataclasses, sérialisés sans être
# lus : bruit connu, filtré.
unused:
	cd backend && ! uv run vulture app --min-confidence 60 --ignore-decorators "@router.*,@callback_router.*,@app.*,@field_validator,@model_validator,@classmethod,@asynccontextmanager,@event.*,@cache" --ignore-names "cls,model_config,MESSAGES,lifespan,create_app,Base" | grep -E "unused (function|method|class|import|property)"
	cd frontend && npx knip --no-progress

format:
	cd backend && uv run ruff check --fix . && uv run ruff format .
	cd frontend && npm run format

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f
