ENV ?= "dev"
POETRY_GROUPS = "server,db,dev"

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
	poetry lock

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

security\:scan:
	make security:scan:code
	make security:scan:sast

security\:scan\:code:
	poetry run bandit -r app/ -x tests/,app/db/dump.py

security\:scan\:sast:
	poetry run semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten

db\:revision\:create:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator custom alembic revision --autogenerate -m '${NAME}'

db\:migrate:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator custom alembic upgrade head

db\:downgrade:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator custom alembic downgrade $(REV)

db\:current:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator custom alembic current

db\:history:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator custom alembic history

# データベースダンプ関連コマンド
db\:dump:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm --build -e DB_TOOL_MODE=dumper -e DUMPER_MODE=interactive db-dumper custom python dump.py

db\:dump\:oneshot:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper custom python dump.py oneshot

db\:dump\:list:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper custom python dump.py list

db\:dump\:restore:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper custom python dump.py restore $(FILE)

db\:dump\:test:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper custom python dump.py test --confirm

db\:backup\:test: # 後方互換性のためにエイリアスを提供
	make db:dump:test

envs\:setup:
	cp envs/server.env.example envs/server.env
	cp envs/db.env.example envs/db.env
	cp envs/sentry.env.example envs/sentry.env
	cp envs/aws-s3.env.example envs/aws-s3.env

project\:init:
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required"; \
		echo "Usage: make project:init NAME=\"Your Project Name\""; \
		exit 1; \
	fi
	@UNIX_NAME=$$(echo "$(NAME)" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-|-$$//g'); \
	echo "Initializing project with name: $(NAME) (unix name: $$UNIX_NAME)"; \
	find . -type f -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/venv/*" -exec grep -l "fastapi-template" {} \; | xargs -I{} sed -i '' 's/fastapi-template/'$$UNIX_NAME'/g' {}; \
	find . -type f -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/venv/*" -exec grep -l "FastAPI Template" {} \; | xargs -I{} sed -i '' 's/FastAPI Template/$(NAME)/g' {}

	git add .
	git commit -m "chore: initialize project with name: $(NAME)"
	git switch -c develop

template\:update:
	@if ! git remote | grep -q "template"; then \
		git remote add template git@github.com:ukwhatn/fastapi-template.git; \
		echo "Added template remote"; \
	fi
	git fetch --all
	git merge template/main --squash --allow-unrelated-histories
	@echo "Template updates from ukwhatn/fastapi-template have been squash-merged."
	@echo "Review changes and commit them with: git commit -m \"your message\""

template\:update\:commit:
	git add . && git commit -m "chore: merge template updates from ukwhatn/fastapi-template"

.PHONY: build up down logs ps pr\:create deploy\:prod poetry\:install poetry\:add poetry\:lock poetry\:update poetry\:reset dev\:setup lint lint\:fix format security\:scan security\:scan\:code security\:scan\:sast test test\:cov test\:setup db\:revision\:create db\:migrate db\:downgrade db\:current db\:history db\:dump db\:backup\:test db\:dump\:oneshot db\:dump\:list db\:dump\:restore db\:dump\:test envs\:setup project\:init template\:update template\:update\:commit