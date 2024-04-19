ENV ?= "dev"

ifeq ($(ENV), prod)
	COMPOSE_YML := compose.prod.yml
else
	COMPOSE_YML := compose.dev.yml
endif

poetry\:install:
	poetry install --with db

poetry\:install\:dev:
	poetry install --with db,dev

build:
	docker compose -f ../$(COMPOSE_YML) build db-migrator $(ARGS)

up:
	docker compose -f ../$(COMPOSE_YML) up -d db-migrator

down:
	docker compose -f ../$(COMPOSE_YML) down

logs:
	docker compose -f ../$(COMPOSE_YML) logs -f
