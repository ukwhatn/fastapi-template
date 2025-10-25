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
ifeq ($(POSTGRES_HOST), db)
	PROFILE_ARGS := --profile local-db
else ifeq ($(POSTGRES_HOST), localhost)
	PROFILE_ARGS := --profile local-db
endif

COMPOSE_CMD := docker compose -f $(COMPOSE_FILE) $(PROFILE_ARGS)

# 共通変数
ALEMBIC_DIR := app/infrastructure/database/alembic

# ==== 環境セットアップ ====
env:
	@cp .env.example .env
	@echo ".env file created. Please edit it with your configuration."

dev\:setup:
	@echo "プロジェクト名を入力してください（空欄でスキップ）："
	@read project_name; \
	if [ -n "$$project_name" ]; then \
		$(MAKE) project:rename NAME="$$project_name"; \
	fi
	@uv sync
	@$(MAKE) env
	@$(MAKE) pre-commit:install

project\:rename:
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required"; \
		echo "Usage: make project:init NAME=\"Your Project Name\""; \
		exit 1; \
	fi
	@UNIX_NAME=$$(echo "$(NAME)" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g' | sed -E 's/^-|-$$//g'); \
	echo "Initializing project with name: $(NAME) (unix name: $$UNIX_NAME)"; \
	find . -type f -not -path "*/\.*" -not -path "*/Makefile" -not -path "*/__pycache__/*" -not -path "*/node_modules/*" -not -path "*/venv/*" -exec grep -l "fastapi-template" {} \; | xargs -I{} sed -i '' 's/fastapi-template/'$$UNIX_NAME'/g' {}; \
	find . -type f -not -path "*/\.*" -not -path "*/Makefile" -not -path "*/__pycache__/*" -not -path "*/node_modules/*" -not -path "*/venv/*" -exec grep -l "FastAPI Template" {} \; | xargs -I{} sed -i '' 's/FastAPI Template/$(NAME)/g' {}; \
	git add .; \
	git commit -m "chore: initialize project with name: $(NAME)"; \
	git switch -c develop

# ==== パッケージ管理 ====
uv\:add:
	@uv add $(packages)
	@$(MAKE) uv:lock

uv\:add\:dev:
	@uv add $(packages) --dev
	@$(MAKE) uv:lock

uv\:lock:
	@uv lock

uv\:update:
	@uv lock --upgrade-package $(packages)

uv\:update\:all:
	@uv lock --upgrade

# ==== 開発ツール ====
openapi\:generate:
	@uv run python -c "from app.main import app; import json; from fastapi.openapi.utils import get_openapi; openapi = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes); print(json.dumps(openapi, indent=2, ensure_ascii=False))" > docs/openapi.json

# ==== コード品質チェック ====
test:
	@uv run --active pytest tests/ -v

test\:cov:
	@uv run --active pytest tests/ -v --cov=app --cov-report=html

lint:
	@uv run --active ruff check ./app ./tests

lint\:fix:
	@uv run --active ruff check --fix ./app ./tests

format:
	@uv run --active ruff format ./app ./tests

format\:check:
	@uv run --active ruff format --check ./app ./tests

type-check:
	@uv run --active mypy app tests

security\:scan:
	@$(MAKE) security:scan:code
	@$(MAKE) security:scan:sast

security\:scan\:code:
	@uv run --active bandit -r app/ -x tests/,app/db/dump.py

security\:scan\:code\:critical:
	@uv run --active bandit -r app/ -x tests/,app/db/dump.py -ll

security\:scan\:sast:
	@uv run --active semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten

security\:scan\:sast\:critical:
	@uv run --active semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten --severity ERROR --error

security\:scan\:trivy:
	@trivy config --exit-code 1 --severity CRITICAL ./docker/server.Dockerfile

# ==== Pre-commit ====
pre-commit\:install:
	@uv run pre-commit install
	@uv run pre-commit install --hook-type pre-push

pre-commit\:run:
	@uv run pre-commit run --all-files

pre-commit\:update:
	@uv run pre-commit autoupdate

# ==== DBマイグレーション ====
db\:revision\:create:
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required"; \
		echo "Usage: make db:revision:create NAME=\"description\""; \
		exit 1; \
	fi
	@cd $(ALEMBIC_DIR) && uv run alembic revision --autogenerate -m "$(NAME)"

db\:migrate:
	@uv run python -c "from app.infrastructure.database.migration import run_migrations; run_migrations()"

db\:downgrade:
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV is required"; \
		echo "Usage: make db:downgrade REV=-1  # or specific revision"; \
		exit 1; \
	fi
	@cd $(ALEMBIC_DIR) && uv run alembic downgrade $(REV)

db\:current:
	@cd $(ALEMBIC_DIR) && uv run alembic current

db\:history:
	@cd $(ALEMBIC_DIR) && uv run alembic history

# ==== DBバックアップ ====
db\:backup\:oneshot:
	@uv run python -m app.utils.backup_cli oneshot

db\:backup\:list:
	@uv run python -m app.utils.backup_cli list

db\:backup\:list\:remote:
	@uv run python -m app.utils.backup_cli list --remote

db\:backup\:restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:restore FILE=\"backup_20250101_120000.dump\""; \
		exit 1; \
	fi
	@uv run python -m app.utils.backup_cli restore $(FILE)

db\:backup\:restore\:s3:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:restore:s3 FILE=\"backup_20250101_120000.dump\""; \
		exit 1; \
	fi
	@uv run python -m app.utils.backup_cli restore $(FILE) --from-s3

# ==== Docker Compose操作 ====
compose\:up:
	@$(COMPOSE_CMD) up -d

compose\:down:
	@$(COMPOSE_CMD) down

compose\:down\:v:
	@$(COMPOSE_CMD) down -v

compose\:logs:
	@$(COMPOSE_CMD) logs -f

compose\:ps:
	@$(COMPOSE_CMD) ps

compose\:ps\:json:
	@$(COMPOSE_CMD) ps --format json

compose\:pull:
	@$(COMPOSE_CMD) pull

compose\:restart:
	@$(COMPOSE_CMD) restart

compose\:build:
	@$(COMPOSE_CMD) up --build -d

# ==== local環境操作 ====
local\:up:
	@ENV=local $(MAKE) compose:up

local\:down:
	@ENV=local $(MAKE) compose:down

local\:down\:v:
	@ENV=local $(MAKE) compose:down:v

local\:logs:
	@ENV=local $(MAKE) compose:logs

local\:ps:
	@ENV=local $(MAKE) compose:ps

local\:serve:
	@uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000

# ==== dev環境操作 ====
dev\:deploy:
	@./scripts/deploy-dev.sh

dev\:logs:
	@ENV=dev $(MAKE) compose:logs

dev\:ps:
	@ENV=dev $(MAKE) compose:ps

dev\:down:
	@ENV=dev $(MAKE) compose:down

# ==== prod環境操作 ====
prod\:deploy:
	@./scripts/deploy-prod.sh

prod\:logs:
	@ENV=prod $(MAKE) compose:logs

prod\:ps:
	@ENV=prod $(MAKE) compose:ps

prod\:down:
	@ENV=prod $(MAKE) compose:down

# ==== Watchtower管理コマンド ====
watchtower\:setup:
	@./scripts/setup-watchtower.sh

watchtower\:logs:
	@docker logs watchtower -f

watchtower\:status:
	@docker ps --filter "name=watchtower"

watchtower\:restart:
	@docker restart watchtower

# ==== 秘密情報管理コマンド ====
secrets\:encrypt\:dev:
	@if [ ! -f .env.dev ]; then \
		echo "Error: .env.dev not found. Create it first."; \
		exit 1; \
	fi
	@sops -e .env.dev > .env.dev.enc
	@echo "✅ .env.dev encrypted to .env.dev.enc"

secrets\:encrypt\:prod:
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found. Create it first."; \
		exit 1; \
	fi
	@sops -e .env.prod > .env.prod.enc
	@echo "✅ .env.prod encrypted to .env.prod.enc"

secrets\:decrypt\:dev:
	@if [ ! -f .env.dev.enc ]; then \
		echo "Error: .env.dev.enc not found"; \
		exit 1; \
	fi
	@sops -d .env.dev.enc > .env.dev
	@echo "✅ .env.dev.enc decrypted to .env.dev"

secrets\:decrypt\:prod:
	@if [ ! -f .env.prod.enc ]; then \
		echo "Error: .env.prod.enc not found"; \
		exit 1; \
	fi
	@sops -d .env.prod.enc > .env.prod
	@echo "✅ .env.prod.enc decrypted to .env.prod"

secrets\:edit\:dev:
	@if [ ! -f .env.dev.enc ]; then \
		echo "Error: .env.dev.enc not found"; \
		exit 1; \
	fi
	@sops .env.dev.enc

secrets\:edit\:prod:
	@if [ ! -f .env.prod.enc ]; then \
		echo "Error: .env.prod.enc not found"; \
		exit 1; \
	fi
	@sops .env.prod.enc

# ==== テンプレート適用コマンド ====
template\:list:
	@if ! git remote | grep -q "template"; then \
		git remote add template git@github.com:ukwhatn/fastapi-template.git; \
		echo "Added template remote"; \
	fi
	@git fetch template
	@echo "テンプレートの最新コミット一覧："
	@git log template/main -n 10 --oneline

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
	@git fetch template
	@echo "適用したいコミットのハッシュを入力してください："
	@read commit_hash; \
	git checkout $$commit_hash -- . && \
	echo "テンプレートの変更が強制的に適用されました。変更を確認しgit add/commitしてください。"

.PHONY: build build\:no-cache up down reload reset logs logs\:once ps pr\:create deploy\:prod uv\:add uv\:add\:dev uv\:lock uv\:update uv\:update\:all dev\:setup lint lint\:fix format format\:check type-check security\:scan security\:scan\:code security\:scan\:code\:critical security\:scan\:sast security\:scan\:sast\:critical security\:scan\:trivy test test\:cov db\:revision\:create db\:migrate db\:downgrade db\:current db\:history db\:backup\:oneshot db\:backup\:list db\:backup\:list\:remote db\:backup\:restore db\:backup\:restore\:s3 env openapi\:generate compose\:up compose\:down compose\:down\:v compose\:logs compose\:ps compose\:pull compose\:restart compose\:build local\:up local\:down local\:down\:v local\:logs local\:ps local\:serve dev\:deploy dev\:logs dev\:ps dev\:down prod\:deploy prod\:logs prod\:ps prod\:down watchtower\:setup watchtower\:logs watchtower\:status watchtower\:restart secrets\:encrypt\:dev secrets\:encrypt\:prod secrets\:decrypt\:dev secrets\:decrypt\:prod secrets\:edit\:dev secrets\:edit\:prod project\:rename project\:init template\:list template\:apply template\:apply\:range template\:apply\:force pre-commit\:install pre-commit\:run pre-commit\:update
