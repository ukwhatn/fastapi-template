ENV ?= "dev"
POETRY_GROUPS = "server,db,dev,dumper"

ifeq ($(ENV), prod)
	COMPOSE_YML := compose.prod.yml
else ifeq ($(ENV), stg)
	COMPOSE_YML := compose.stg.yml
else ifeq ($(ENV), test)
	COMPOSE_YML := compose.test.yml
else
	COMPOSE_YML := compose.dev.yml
endif

build:
	docker compose -f $(COMPOSE_YML) build

build\:no-cache:
	docker compose -f $(COMPOSE_YML) build --no-cache

up:
	docker compose -f $(COMPOSE_YML) up --build -d

down:
	docker compose -f $(COMPOSE_YML) down

reload:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) down
	docker compose -f $(COMPOSE_YML) up -d

reset:
	docker compose -f $(COMPOSE_YML) down --volumes --remove-orphans --rmi all

logs:
	docker compose -f $(COMPOSE_YML) logs -f

logs\:once:
	docker compose -f $(COMPOSE_YML) logs

ps:
	docker compose -f $(COMPOSE_YML) ps

pr\:create:
	git switch develop
	git push
	gh pr create --base main --head $(shell git branch --show-current)
	gh pr view --web

deploy\:prod:
	make build ENV=prod
	make reload ENV=prod

poetry\:install:
	pip install poetry
	poetry install --with $(group)

poetry\:add:
	poetry add --group=$(group) $(packages)
	make poetry:lock

poetry\:lock:
	poetry lock --no-update

poetry\:update:
	poetry update --with $(group)

poetry\:update\:all:
	poetry update

poetry\:reset:
	poetry env remove $(which python)
	poetry install

dev\:setup:
	poetry install --with $(POETRY_GROUPS)

lint:
	poetry run ruff check .

lint\:fix:
	poetry run ruff check --fix .

format:
	poetry run ruff format .

db\:revision\:create:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic revision --autogenerate -m '${NAME}'"

db\:migrate:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic upgrade head"

db\:backup:
	docker compose -f compose.prod.yml up -d --build db-dumper
	docker compose -f compose.prod.yml exec db-dumper python dump.py oneshot

db\:backup\:test:
	docker compose -f $(COMPOSE_YML) exec db-dumper python dump.py test --confirm

db\:restore:
	docker compose -f compose.prod.yml up -d --build db-dumper
	docker compose -f compose.prod.yml exec db-dumper python dump.py restore

envs\:setup:
	cp envs/server.env.example envs/server.env
	cp envs/db.env.example envs/db.env
	cp envs/sentry.env.example envs/sentry.env

PHONY: build up down logs ps pr\:create deploy\:prod poetry\:install poetry\:add poetry\:lock poetry\:update poetry\:reset dev\:setup db\:revision\:create db\:migrate envs\:setup