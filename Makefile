.PHONY: sync upstream gateway admin mongo token test lint

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
