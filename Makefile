# ==== Prepare ====
-include .env
export

ENV ?= local

ifeq ($(ENV), prod)
	COMPOSE_FILE := compose.prod.yml
else ifeq ($(ENV), dev)
	COMPOSE_FILE := compose.dev.yml
else
	COMPOSE_FILE := compose.local.yml
endif

# POSTGRES_HOSTに基づくprofile自動判定（local環境以外）
PROFILE_ARGS :=
ifneq ($(ENV), local)
	ifeq ($(POSTGRES_HOST), db)
		PROFILE_ARGS := --profile local-db
	else ifeq ($(POSTGRES_HOST), localhost)
		PROFILE_ARGS := --profile local-db
	endif
endif

COMPOSE_CMD := docker compose -f $(COMPOSE_FILE) $(PROFILE_ARGS)

# 共通変数
DB_MIGRATOR_RUN := $(COMPOSE_CMD) run --rm db-migrator custom alembic
DB_DUMPER_RUN := $(COMPOSE_CMD) run --rm db-dumper custom python dump.py

# ==== 環境セットアップ ====
env:
	@cp .env.example .env
	@echo ".env file created. Please edit it with your configuration."

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

dev\:setup:
	uv sync

# ==== パッケージ管理系 ====
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

# ==== 開発ツール ====
openapi\:generate:
	PYTHONPATH=app uv run python -c "from main import app; import json; from fastapi.openapi.utils import get_openapi; openapi = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes); print(json.dumps(openapi, indent=2, ensure_ascii=False))" > docs/openapi.json

# ==== コード品質チェック系 ====
test:
	PYTHONPATH=app uv run --active pytest tests/ -v

test\:cov:
	PYTHONPATH=app uv run --active pytest tests/ -v --cov=. --cov-report=html


lint:
	uv run --active ruff check ./app ./versions ./tests

lint\:fix:
	uv run --active ruff check --fix ./app ./versions ./tests

format:
	uv run --active ruff format ./app ./versions ./tests

type-check:
	PYTHONPATH=app uv run --active mypy app versions tests

security\:scan:
	make security:scan:code
	make security:scan:sast

security\:scan\:code:
	uv run --active bandit -r app/ -x tests/,app/db/dump.py

security\:scan\:sast:
	uv run --active semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten

# ==== DBマイグレーション系 ====
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

# ==== DBバックアップ系 ====
db\:dump:
	$(COMPOSE_CMD) run --rm --build -e DB_TOOL_MODE=dumper -e DUMPER_MODE=interactive db-dumper custom python dump.py

db\:dump\:oneshot:
	$(DB_DUMPER_RUN) oneshot

db\:dump\:list:
	$(DB_DUMPER_RUN) list

db\:dump\:restore:
	$(DB_DUMPER_RUN) restore $(FILE)

db\:dump\:test:
	$(DB_DUMPER_RUN) test --confirm


# 汎用Docker Composeコマンド
compose\:up:
	$(COMPOSE_CMD) up -d

compose\:down:
	$(COMPOSE_CMD) down

compose\:logs:
	$(COMPOSE_CMD) logs -f

compose\:ps:
	$(COMPOSE_CMD) ps

compose\:pull:
	$(COMPOSE_CMD) pull

compose\:restart:
	$(COMPOSE_CMD) restart

compose\:build:
	$(COMPOSE_CMD) up --build -d

# ローカル開発環境（uv native + Docker DB）
local\:up:
	ENV=local $(MAKE) compose:up

local\:down:
	ENV=local $(MAKE) compose:down

local\:logs:
	ENV=local $(MAKE) compose:logs

local\:ps:
	ENV=local $(MAKE) compose:ps

local\:serve:
	cd app && uv run fastapi dev main.py --host 0.0.0.0 --port 8000

# Dev環境（Watchtower自動デプロイ）
dev\:deploy:
	./scripts/deploy-dev.sh

dev\:logs:
	ENV=dev $(MAKE) compose:logs

dev\:ps:
	ENV=dev $(MAKE) compose:ps

dev\:down:
	ENV=dev $(MAKE) compose:down

# Prod環境（Watchtower自動デプロイ）
prod\:deploy:
	./scripts/deploy-prod.sh

prod\:logs:
	ENV=prod $(MAKE) compose:logs

prod\:ps:
	ENV=prod $(MAKE) compose:ps

prod\:down:
	ENV=prod $(MAKE) compose:down

# Watchtower管理
watchtower\:setup:
	./scripts/setup-watchtower.sh

watchtower\:logs:
	docker logs watchtower -f

watchtower\:status:
	docker ps --filter "name=watchtower"

watchtower\:restart:
	docker restart watchtower

# シークレット管理（SOPS + age）
secrets\:encrypt\:dev:
	@if [ ! -f .env.dev ]; then \
		echo "Error: .env.dev not found. Create it first."; \
		exit 1; \
	fi
	sops -e .env.dev > .env.dev.enc
	@echo "✅ .env.dev encrypted to .env.dev.enc"

secrets\:encrypt\:prod:
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found. Create it first."; \
		exit 1; \
	fi
	sops -e .env.prod > .env.prod.enc
	@echo "✅ .env.prod encrypted to .env.prod.enc"

secrets\:decrypt\:dev:
	@if [ ! -f .env.dev.enc ]; then \
		echo "Error: .env.dev.enc not found"; \
		exit 1; \
	fi
	sops -d .env.dev.enc > .env.dev
	@echo "✅ .env.dev.enc decrypted to .env.dev"

secrets\:decrypt\:prod:
	@if [ ! -f .env.prod.enc ]; then \
		echo "Error: .env.prod.enc not found"; \
		exit 1; \
	fi
	sops -d .env.prod.enc > .env.prod
	@echo "✅ .env.prod.enc decrypted to .env.prod"

secrets\:edit\:dev:
	@if [ ! -f .env.dev.enc ]; then \
		echo "Error: .env.dev.enc not found"; \
		exit 1; \
	fi
	sops .env.dev.enc

secrets\:edit\:prod:
	@if [ ! -f .env.prod.enc ]; then \
		echo "Error: .env.prod.enc not found"; \
		exit 1; \
	fi
	sops .env.prod.enc


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

.PHONY: build build\:no-cache up down reload reset logs logs\:once ps pr\:create deploy\:prod uv\:add uv\:add\:dev uv\:lock uv\:update uv\:update\:all dev\:setup lint lint\:fix format type-check security\:scan security\:scan\:code security\:scan\:sast test test\:cov db\:revision\:create db\:migrate db\:downgrade db\:current db\:history db\:dump db\:dump\:oneshot db\:dump\:list db\:dump\:restore db\:dump\:test env openapi\:generate compose\:up compose\:down compose\:logs compose\:ps compose\:pull compose\:restart compose\:build local\:up local\:down local\:logs local\:ps local\:serve dev\:deploy dev\:logs dev\:ps dev\:down prod\:deploy prod\:logs prod\:ps prod\:down watchtower\:setup watchtower\:logs watchtower\:status watchtower\:restart secrets\:encrypt\:dev secrets\:encrypt\:prod secrets\:decrypt\:dev secrets\:decrypt\:prod secrets\:edit\:dev secrets\:edit\:prod project\:init template\:list template\:apply template\:apply\:range template\:apply\:force
