-include .env
.PHONY: help dev setup db api worker frontend up down logs lint format format-check fix typecheck check ci test test-x test-v test-s clean rag-phase-0 prompt-manager-serve sync-categories graph

# Output colors
CYAN := \033[36m
GREEN := \033[32m
RED := \033[31m
RESET := \033[0m

PY := $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; command -v python; fi)

##@ General
help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(CYAN)<command>$(RESET)\n"} /^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n%s\n", substr($$0, 5) } ' "$(CURDIR)/Makefile"


##@ Setup
setup: ## Create .venv and install dependencies
	uv venv
	uv pip install -e ".[dev]"

##@ Development
dev: ## Start LangGraph Studio
	uv run langgraph dev

migrations: ## Run all database migrations
	uv run python db/migrate.py

##@ Code Quality
# These commands check style and types, NOT logic.
# To test logic, use: make test
#
# Typical workflow:
#   make fix && make format   # Fix and format
#   make check                # Verify that everything is correct
#   git commit

lint: ## Find issues (imports, syntax) — does not modify files
	uv run ruff check .

format: ## Format code — MODIFIES files
	uv run ruff format .

format-check: ## Check formatting — does not modify files (for CI)
	uv run ruff format --check .

fix: ## Automatically fix issues — MODIFIES files
	uv run ruff check --fix .

typecheck: ## Check static types (pyright) — does not modify files
	uv run pyright src/

check: ## Check everything (lint + format + types) — does not modify files
	uv run ruff check . && uv run ruff format --check . && uv run pyright src/

ci: ## CI/CD: check everything and run tests — does not modify files
	uv run ruff check . && uv run ruff format --check . && uv run pyright src/ && uv run pytest

##@ Tests
test: ## Run all tests
	uv run pytest

test-x: ## Run tests and stop at the first failure
	uv run pytest -x

test-v: ## Run tests with verbose output
	uv run pytest -v

test-s: ## Run tests with added print() logs
	uv run pytest -v -s
