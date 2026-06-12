# Common commands for SalesLoop AI. Backend tooling (test/lint) runs locally:
# create a venv with `make venv` first.

.PHONY: up down logs migrate makemigration test lint format venv

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f backend

migrate:
	docker compose exec backend alembic upgrade head

# Usage: make makemigration m="add some table"
makemigration:
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

# Loads .env so the test run targets the docker Postgres (host port 5433)
test:
	set -a && . ./.env && set +a && cd backend && \
	DATABASE_URL="postgresql+asyncpg://$$DB_USER:$$DB_PASSWORD@localhost:5433/$$DB_NAME" \
	.venv/bin/python -m pytest

lint:
	cd backend && .venv/bin/ruff check app tests && .venv/bin/ruff format --check app tests && .venv/bin/mypy app

format:
	cd backend && .venv/bin/ruff format app tests && .venv/bin/ruff check --fix app tests

venv:
	cd backend && uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -r requirements-dev.txt
