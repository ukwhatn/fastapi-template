ENV ?= "dev"

ifeq ($(ENV), prod)
	COMPOSE_YML := compose.prod.yml
else
	COMPOSE_YML := compose.dev.yml
endif

build:
	docker compose -f $(COMPOSE_YML) build

up:
	docker compose -f $(COMPOSE_YML) up -d

down:
	docker compose -f $(COMPOSE_YML) down

reload:
	docker compose -f $(COMPOSE_YML) down
	docker compose -f $(COMPOSE_YML) up -d

reset:
	docker compose -f $(COMPOSE_YML) down --volumes --remove-orphans

ps:
	docker compose -f $(COMPOSE_YML) ps

logs:
	docker compose -f $(COMPOSE_YML) logs -f

revision:
	docker compose -f $(COMPOSE_YML) up -d server
	docker compose -f $(COMPOSE_YML) exec server /bin/bash -c "cd /db && alembic revision --autogenerate -m '${NAME}'"

migrate:
	docker compose -f $(COMPOSE_YML) up -d server
	docker compose -f $(COMPOSE_YML) exec server /bin/bash -c "cd /db && alembic upgrade head"

init:
	cp envs/bot.env.example envs/bot.env
	cp envs/db.env.example envs/db.env
	cp envs/sentry.env.example envs/sentry.env
	cp envs/server.env.example envs/server.env

install-local-requirements:
	find . -name requirements.txt -exec pip install -r {} \;

deploy:
	git switch develop
	git push
	gh pr create --base main --head $(shell git branch --show-current)
	gh pr view --web

PHONY: build up down reset ps logs revision migrate init install-local-requirements deploy