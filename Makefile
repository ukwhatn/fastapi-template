ENV ?= "dev"
POETRY_GROUPS = "server,db,dev,dumper,test"

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

test\:setup:
	poetry install --with test

test: test\:setup
	poetry run pytest

test\:cov: test\:setup
	poetry run pytest --cov=app --cov-report=term-missing

db\:revision\:create:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic revision --autogenerate -m '${NAME}'"

db\:migrate:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic upgrade head"

db\:downgrade:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic downgrade $(REV)"

db\:current:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic current"

db\:history:
	docker compose -f $(COMPOSE_YML) build db-migrator
	docker compose -f $(COMPOSE_YML) run --rm db-migrator /bin/bash -c "alembic history"

# データベースダンプ関連コマンド
db\:dump:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm --build --name db-dumper-interactive -e DB_TOOL_MODE=dumper -e DUMPER_MODE=interactive db-dumper

# 後方互換性のためにエイリアスを提供
db\:backup\:test:
	make db:dump:test

db\:dump\:oneshot:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper python -m app.db.dump oneshot

db\:dump\:list:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper python -m app.db.dump list

db\:dump\:restore:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper python -m app.db.dump restore $(FILE)

db\:dump\:test:
	docker compose -f $(COMPOSE_YML) build
	docker compose -f $(COMPOSE_YML) run --rm db-dumper python -m app.db.dump test --confirm

envs\:setup:
	cp envs/server.env.example envs/server.env
	cp envs/db.env.example envs/db.env
	cp envs/sentry.env.example envs/sentry.env
	cp envs/aws-s3.env.example envs/aws-s3.env

# アプリケーション名を変更するターゲット
# 使用法: make app:rename NEW_NAME="my-app-name"
app\:rename:
	@if [ -z "$(NEW_NAME)" ]; then \
		echo "エラー: アプリケーション名が指定されていません"; \
		echo "使用法: make app:rename NEW_NAME=\"my-app-name\""; \
		exit 1; \
	fi
	@echo "アプリケーション名を 'fastapi-template' から '$(NEW_NAME)' に変更しています..."
	@# pyproject.tomlの名前を変更
	@sed -i.bak 's/name = "fastapi-template"/name = "$(NEW_NAME)"/' pyproject.toml && rm pyproject.toml.bak
	@# READMEのタイトルと説明を変更
	@sed -i.bak '1s/# FastAPI Template/# $(NEW_NAME)/' README.md && rm README.md.bak
	@sed -i.bak 's/FastAPIアプリケーションのためのテンプレートリポジトリ。/$(NEW_NAME)アプリケーション/' README.md && rm README.md.bak
	@# docker-composeのコンテナプレフィックスを変更
	@for file in compose.*.yml; do \
		sed -i.bak "s/container_name: fastapi-template-/container_name: $(NEW_NAME)-/g" $$file && rm $$file.bak; \
	done
	@# NewRelicのアプリケーション名を変更
	@sed -i.bak 's/NEW_RELIC_APP_NAME="FastAPI Template"/NEW_RELIC_APP_NAME="$(NEW_NAME)"/' envs/server.env.example && rm envs/server.env.example.bak
	@if [ -f envs/server.env ]; then \
		sed -i.bak 's/NEW_RELIC_APP_NAME="FastAPI Template"/NEW_RELIC_APP_NAME="$(NEW_NAME)"/' envs/server.env && rm envs/server.env.bak; \
	fi
	@echo "アプリケーション '$(NEW_NAME)' の設定が完了しました！"
	@echo "注意: もし元のリポジトリから複製して使用する場合は、以下のコマンドを実行してください:"
	@echo "  rm -rf .git && git init && git add . && git commit -m \"initial commit: $(NEW_NAME)\""

# 新規プロジェクトセットアップのためのターゲット
# 使用法: make project:init NEW_NAME="my-app-name"
project\:init: app\:rename envs\:setup
	@echo "プロジェクト '$(NEW_NAME)' を初期化しています..."
	@if [ -d .git ]; then \
		echo "既存のGitリポジトリを削除しています..."; \
		rm -rf .git; \
	fi
	@git init
	@git add .
	@git commit -m "initial commit: $(NEW_NAME)"
	@echo "プロジェクト '$(NEW_NAME)' の初期化が完了しました！"

PHONY: build up down logs ps pr\:create deploy\:prod poetry\:install poetry\:add poetry\:lock poetry\:update poetry\:reset dev\:setup lint lint\:fix format test test\:cov db\:revision\:create db\:migrate db\:downgrade db\:current db\:history db\:dump db\:backup\:test db\:dump\:oneshot db\:dump\:list db\:dump\:restore db\:dump\:test envs\:setup app\:rename project\:init