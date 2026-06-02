.PHONY: format lint test check

format:
	uv run ruff format .
	uv run ruff check . --fix

lint:
	uv run ruff format --check .
	uv run ruff check .

test:
	uv run pytest

check: lint test
