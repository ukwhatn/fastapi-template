ENV ?= "dev"
INCLUDE_DB ?= false
PROD_PORT ?= 59999

# 環境別設定
ifeq ($(ENV), prod)
	ENV_MODE := production
	SERVER_PORT := 127.0.0.1:$(PROD_PORT)
	COMPOSE_PROFILES := prod
	COMPOSE_ENV_FILES := --env-file ./envs/sentry.env
else ifeq ($(ENV), stg)
	ENV_MODE := production
	SERVER_PORT := 127.0.0.1:8000
	COMPOSE_PROFILES := stg
	COMPOSE_ENV_FILES := 
else ifeq ($(ENV), test)
	ENV_MODE := production
	SERVER_PORT := 127.0.0.1:8000
	COMPOSE_PROFILES := test
	COMPOSE_ENV_FILES := 
else
	ENV_MODE := development
	SERVER_PORT := 127.0.0.1:8000
	COMPOSE_PROFILES := dev
	COMPOSE_ENV_FILES := 
endif

# プロファイル構築
PROFILES_LIST := $(COMPOSE_PROFILES)
ifeq ($(INCLUDE_DB), true)
	PROFILES_LIST := $(PROFILES_LIST) db
	# devの場合はdb-devも追加
	ifeq ($(ENV), prod)
		PROFILES_LIST := $(PROFILES_LIST) db-prod
	else ifeq ($(ENV), stg)
		PROFILES_LIST := $(PROFILES_LIST) db-stg
	else ifeq ($(ENV), test)
		PROFILES_LIST := $(PROFILES_LIST) db-test
	else
		PROFILES_LIST := $(PROFILES_LIST) db-dev
	endif
endif

# profile引数構築
PROFILE_ARGS := $(foreach profile,$(PROFILES_LIST),--profile $(profile))

# composeコマンド構築
COMPOSE_CMD := docker compose $(PROFILE_ARGS) $(COMPOSE_ENV_FILES)

# 環境変数
export ENV_MODE
export SERVER_PORT
export INCLUDE_DB

# 共通変数
DB_MIGRATOR_RUN := $(COMPOSE_CMD) build db-migrator && $(COMPOSE_CMD) run --rm db-migrator custom alembic
DB_DUMPER_RUN := $(COMPOSE_CMD) build && $(COMPOSE_CMD) run --rm db-dumper custom python dump.py

build:
	$(COMPOSE_CMD) build

build\:no-cache:
	$(COMPOSE_CMD) build --no-cache

up:
	$(COMPOSE_CMD) up --build -d

down:
	$(COMPOSE_CMD) down

reload:
	$(COMPOSE_CMD) build
	$(COMPOSE_CMD) down
	$(COMPOSE_CMD) up -d

reset:
	$(COMPOSE_CMD) down --volumes --remove-orphans --rmi all

logs:
	$(COMPOSE_CMD) logs -f

logs\:once:
	$(COMPOSE_CMD) logs

ps:
	$(COMPOSE_CMD) ps

pr\:create:
	git switch develop
	git push
	gh pr create --base main --head $(shell git branch --show-current)
	gh pr view --web

deploy\:prod:
	make build ENV=prod
	make reload ENV=prod

uv\:add:
	uv add $(packages)
	make uv:lock

uv\:add\:dev:
	uv add --group dev $(packages)
	make uv:lock

uv\:lock:
	uv lock

uv\:update:
	uv lock --upgrade-package $(packages)

uv\:update\:all:
	uv lock --upgrade

dev\:setup:
	uv sync

lint:
	uv run --active ruff check ./app ./versions ./tests

lint\:fix:
	uv run --active ruff check --fix ./app ./versions ./tests

format:
	uv run --active ruff format ./app ./versions ./tests

type-check:
	uv run --active mypy app versions tests

security\:scan:
	make security:scan:code
	make security:scan:sast

security\:scan\:code:
	uv run --active bandit -r app/ -x tests/,app/db/dump.py

security\:scan\:sast:
	uv run --active semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten

db\:revision\:create:
	$(DB_MIGRATOR_RUN) revision --autogenerate -m '${NAME}'

db\:migrate:
	$(DB_MIGRATOR_RUN) upgrade head

db\:downgrade:
	$(DB_MIGRATOR_RUN) downgrade $(REV)

db\:current:
	$(DB_MIGRATOR_RUN) current

db\:history:
	$(DB_MIGRATOR_RUN) history

# データベースダンプ関連コマンド
db\:dump:
	$(COMPOSE_CMD) run --rm --build -e DB_TOOL_MODE=dumper -e DUMPER_MODE=interactive db-dumper custom python dump.py

db\:dump\:oneshot:
	$(DB_DUMPER_RUN) oneshot

db\:dump\:list:
	$(DB_DUMPER_RUN) list

db\:dump\:restore:
	$(DB_DUMPER_RUN) restore $(FILE)

db\:dump\:test:
	@if [ "$(INCLUDE_DB)" != "true" ]; then \
		echo "Skipping database dump test: INCLUDE_DB is not set to true"; \
	else \
		$(DB_DUMPER_RUN) test --confirm; \
	fi

env:
	cp .env.example .env
	@echo ".env file created. Please edit it with your configuration."

test:
	uv run --active pytest tests/ -v

test\:cov:
	uv run --active pytest tests/ -v --cov=app --cov-report=html

openapi\:generate:
	$(COMPOSE_CMD) exec server python -c "from main import app; import json; from fastapi.openapi.utils import get_openapi; openapi = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes); print(json.dumps(openapi, indent=2, ensure_ascii=False))" > docs/openapi.json

project\:init:
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required"; \
		echo "Usage: make project:init NAME=\"Your Project Name\""; \
		exit 1; \
	fi
	@UNIX_NAME=$$(echo "$(NAME)" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-|-$$//g'); \
	echo "Initializing project with name: $(NAME) (unix name: $$UNIX_NAME)"; \
	find . -type f -not -path "*/\.*" -not -path "*/Makefile" -not -path "*/__pycache__/*" -not -path "*/node_modules/*" -not -path "*/venv/*" -exec grep -l "fastapi-template" {} \; | xargs -I{} sed -i '' 's/fastapi-template/'$$UNIX_NAME'/g' {}; \
	find . -type f -not -path "*/\.*" -not -path "*/Makefile" -not -path "*/__pycache__/*" -not -path "*/node_modules/*" -not -path "*/venv/*" -exec grep -l "FastAPI Template" {} \; | xargs -I{} sed -i '' 's/FastAPI Template/$(NAME)/g' {}

	git add .
	git commit -m "chore: initialize project with name: $(NAME)"
	git switch -c develop

# テンプレート更新関連コマンド
template\:list:
	@if ! git remote | grep -q "template"; then \
		git remote add template git@github.com:ukwhatn/fastapi-template.git; \
		echo "Added template remote"; \
	fi
	git fetch template
	@echo "テンプレートの最新コミット一覧："
	git log template/main -n 10 --oneline

template\:apply:
	@echo "適用したいコミットのハッシュを入力してください（複数の場合はスペース区切り）："
	@read commit_hashes; \
	for hash in $$commit_hashes; do \
		git cherry-pick -X theirs $$hash || { \
			echo "自動マージできないコンフリクトが発生しました。手動で解決してください。"; \
			echo "解決後、git cherry-pick --continue を実行してください。"; \
			exit 1; \
		}; \
	done

template\:apply\:range:
	@echo "開始コミットハッシュを入力してください（古い方）："
	@read start_hash; \
	echo "終了コミットハッシュを入力してください（新しい方）："; \
	read end_hash; \
	git cherry-pick -X theirs $$start_hash^..$$end_hash || { \
		echo "自動マージできないコンフリクトが発生しました。手動で解決してください。"; \
		echo "解決後、git cherry-pick --continue を実行してください。"; \
		exit 1; \
	}

template\:apply\:force:
	@if ! git remote | grep -q "template"; then \
		git remote add template git@github.com:ukwhatn/fastapi-template.git; \
		echo "Added template remote"; \
	fi
	git fetch template
	@echo "適用したいコミットのハッシュを入力してください："
	@read commit_hash; \
	git checkout $$commit_hash -- . && \
	echo "テンプレートの変更が強制的に適用されました。変更を確認しgit add/commitしてください。"

.PHONY: build build\:no-cache up down reload reset logs logs\:once ps pr\:create deploy\:prod uv\:add uv\:add\:dev uv\:lock uv\:update uv\:update\:all dev\:setup lint lint\:fix format type-check security\:scan security\:scan\:code security\:scan\:sast test test\:cov db\:revision\:create db\:migrate db\:downgrade db\:current db\:history db\:dump db\:dump\:oneshot db\:dump\:list db\:dump\:restore db\:dump\:test env openapi\:generate project\:init template\:list template\:apply template\:apply\:range template\:apply\:force
