.PHONY: up down test lint logs prod-up build frontend-test

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

test:
	python -m pytest

lint:
	ruff check src tests
	ruff format --check src tests
	cd frontend && npm run lint && npm run format:check

frontend-test:
	cd frontend && npm test && npm run build

logs:
	docker compose logs -f --tail=100 api worker temporal-worker

prod-up:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
