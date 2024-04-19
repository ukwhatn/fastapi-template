ENV ?= "dev"

ifeq ($(ENV), prod)
	COMPOSE_YML := compose.prod.yml
else
	COMPOSE_YML := compose.dev.yml
endif

build:
	docker compose -f ../$(COMPOSE_YML) build front $(ARGS)

up:
	docker compose -f ../$(COMPOSE_YML) up -d front

down:
	docker compose -f ../$(COMPOSE_YML) down

logs:
	docker compose -f ../$(COMPOSE_YML) logs -f
