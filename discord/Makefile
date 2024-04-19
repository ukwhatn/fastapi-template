ENV ?= "dev"

ifeq ($(ENV), prod)
	COMPOSE_YML := compose.prod.yml
else
	COMPOSE_YML := compose.dev.yml
endif

poetry\:install:
	poetry install --with discord,db

poetry\:install\:dev:
	poetry install --with discord,dev

build:
	docker compose -f ../$(COMPOSE_YML) build discord $(ARGS)

up:
	docker compose -f ../$(COMPOSE_YML) up -d discord

down:
	docker compose -f ../$(COMPOSE_YML) down

logs:
	docker compose -f ../$(COMPOSE_YML) logs -f
