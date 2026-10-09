# Load .env (KEY=VALUE lines) into every recipe's environment, if present.
-include .env
export

.PHONY: sync upstream gateway admin admin-keys admin-token mongo mongo-start mongo-stop shell token test lint

sync:
	uv sync

upstream:
	uv run python -m upstream.server

gateway:
	uv run python -m gateway.server

# usage: make token USER=alice
token:
	uv run python scripts/mint_jwt.py $(USER)

test:
	uv run pytest

lint:
	uv run ruff check . && uv run ruff format --check .

admin:
	uv run python -m admin.app

mongo:
	docker compose up -d mongo

mongo-start:
	uv run python scripts/mongo.py start

mongo-stop:
	uv run python scripts/mongo.py stop

shell:
	uv run python scripts/mongo.py shell

admin-keys:
	uv run python scripts/admin_keys.py genkeys

admin-token:
	uv run python scripts/admin_keys.py token
