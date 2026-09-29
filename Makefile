.PHONY: help env up down restart build logs ps api-logs worker-logs frontend-logs \
        api-shell worker-shell db-shell migrate migrate-autogenerate seed \
        qdrant-setup clean

COMPOSE := docker compose

help:
	@echo "NotebookLMC - Makefile targets"
	@echo "  make env                    Copy .env.example to .env (if missing)"
	@echo "  make up                     Build and start the full stack"
	@echo "  make down                   Stop the stack"
	@echo "  make restart                Restart the stack"
	@echo "  make build                  Build all images"
	@echo "  make logs                   Tail logs for all services"
	@echo "  make ps                     Show container status"
	@echo "  make api-logs                Tail api logs"
	@echo "  make worker-logs             Tail worker logs"
	@echo "  make frontend-logs           Tail frontend logs"
	@echo "  make api-shell                Open a shell in the api container"
	@echo "  make worker-shell             Open a shell in the worker container"
	@echo "  make db-shell                 Open a psql shell in postgres"
	@echo "  make migrate                  Run Alembic migrations (upgrade head)"
	@echo "  make migrate-autogenerate     Autogenerate a new Alembic revision"
	@echo "  make seed                     Seed the demo user/notebook"
	@echo "  make qdrant-setup             Create the Qdrant collection"
	@echo "  make clean                    Remove containers and volumes (DESTRUCTIVE)"

env:
	@test -f .env || cp .env.example .env
	@echo ".env ready. Fill in LANGDOCK_API_KEY and model ids before starting."

up: env
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart: down up

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

api-logs:
	$(COMPOSE) logs -f api

worker-logs:
	$(COMPOSE) logs -f worker

frontend-logs:
	$(COMPOSE) logs -f frontend

api-shell:
	$(COMPOSE) exec api /bin/sh

worker-shell:
	$(COMPOSE) exec worker /bin/sh

db-shell:
	$(COMPOSE) exec postgres psql -U $${POSTGRES_USER:-notebook} -d $${POSTGRES_DB:-notebook}

migrate:
	$(COMPOSE) exec api alembic upgrade head

migrate-autogenerate:
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(msg)"

seed:
	$(COMPOSE) exec api python -m app.scripts.seed_demo

qdrant-setup:
	$(COMPOSE) exec api python -m app.qdrant.client

clean:
	$(COMPOSE) down -v --remove-orphans
