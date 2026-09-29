.PHONY: help install db-check migrate seed test lint typecheck run up down demo

PYTHON ?= python
UVICORN ?= uvicorn
ALEMBIC ?= alembic
PYTEST ?= pytest

help:
	@echo "ControlChaos Make Targets:"
	@echo "  make install    - Install backend dependencies"
	@echo "  make db-check   - Verify database connectivity, SSL status, and latency"
	@echo "  make migrate    - Run Alembic migrations against DATABASE_URL"
	@echo "  make seed       - Seed demo users, roles, entities, and accounts"
	@echo "  make test       - Run pytest test suite"
	@echo "  make lint       - Run ruff linter and formatting checks"
	@echo "  make typecheck  - Run mypy type checking"
	@echo "  make run        - Start FastAPI backend dev server"
	@echo "  make up         - Start docker-compose services"
	@echo "  make down       - Stop docker-compose services"

install:
	$(PYTHON) -m pip install -e "backend[dev]"

db-check:
	$(PYTHON) scripts/db_check.py

migrate:
	cd backend && $(ALEMBIC) upgrade head

seed:
	$(PYTHON) scripts/seed.py

test:
	cd backend && $(PYTEST) -v

lint:
	ruff check backend

typecheck:
	cd backend && mypy app

run:
	cd backend && $(UVICORN) app.main:app --host 0.0.0.0 --port 8000 --reload

up:
	docker-compose up -d --build

down:
	docker-compose down
