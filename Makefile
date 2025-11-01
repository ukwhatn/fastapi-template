# ==== Prepare ====

ENV ?= local

ifeq ($(ENV), prod)
	-include .env.prod
	export
	COMPOSE_FILE := compose.prod.yml
else ifeq ($(ENV), stg)
	-include .env.stg
	export
	COMPOSE_FILE := compose.stg.yml
else
	-include .env
	export
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
.PHONY: env
env:
	@cp .env.example .env
	@echo ".env file created. Please edit it with your configuration."

.PHONY: dev\:setup
dev\:setup:
	@echo "プロジェクト名を入力してください（空欄でスキップ）："
	@read project_name; \
	if [ -n "$$project_name" ]; then \
		$(MAKE) project:rename NAME="$$project_name"; \
	fi
	@uv sync
	@$(MAKE) env
	@$(MAKE) pre-commit:install

.PHONY: project\:rename
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
	git push; \
	git switch -c develop

# ==== パッケージ管理 ====
.PHONY: uv\:add
uv\:add:
	@uv add $(packages)
	@$(MAKE) uv:lock

.PHONY: uv\:add\:dev
uv\:add\:dev:
	@uv add $(packages) --dev
	@$(MAKE) uv:lock

.PHONY: uv\:lock
uv\:lock:
	@uv lock

.PHONY: uv\:update
uv\:update:
	@uv lock --upgrade-package $(packages)

.PHONY: uv\:update\:all
uv\:update\:all:
	@uv lock --upgrade

# ==== 開発ツール ====
.PHONY: openapi\:generate
openapi\:generate:
	@uv run python -c "from app.main import app; import json; from fastapi.openapi.utils import get_openapi; openapi = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes); print(json.dumps(openapi, indent=2, ensure_ascii=False))" > openapi.json

# ==== コード品質チェック ====
.PHONY: test
test:
	@uv run --active pytest tests/ -v

.PHONY: test\:cov
test\:cov:
	@uv run --active pytest tests/ -v --cov=app --cov-report=html

.PHONY: lint
lint:
	@uv run --active ruff check ./app ./tests

.PHONY: lint\:fix
lint\:fix:
	@uv run --active ruff check --fix ./app ./tests

.PHONY: format
format:
	@uv run --active ruff format ./app ./tests

.PHONY: format\:check
format\:check:
	@uv run --active ruff format --check ./app ./tests

.PHONY: type-check
type-check:
	@uv run --active mypy app tests

.PHONY: security\:scan
security\:scan:
	@$(MAKE) security:scan:code
	@$(MAKE) security:scan:sast

.PHONY: security\:scan\:code
security\:scan\:code:
	@uv run --active bandit -r app/ -x tests/,app/db/dump.py

.PHONY: security\:scan\:code\:critical
security\:scan\:code\:critical:
	@uv run --active bandit -r app/ -x tests/,app/db/dump.py -ll

.PHONY: security\:scan\:sast
security\:scan\:sast:
	@uv run --active semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten

.PHONY: security\:scan\:sast\:critical
security\:scan\:sast\:critical:
	@uv run --active semgrep scan --config=p/python --config=p/security-audit --config=p/owasp-top-ten --severity ERROR --error

.PHONY: security\:scan\:trivy
security\:scan\:trivy:
	@trivy config --exit-code 1 --severity CRITICAL Dockerfile

# ==== Pre-commit ====
.PHONY: pre-commit\:install
pre-commit\:install:
	@uv run pre-commit install
	@uv run pre-commit install --hook-type pre-push

.PHONY: pre-commit\:run
pre-commit\:run:
	@uv run pre-commit run --all-files

.PHONY: pre-commit\:update
pre-commit\:update:
	@uv run pre-commit autoupdate

# ==== DBマイグレーション ====
.PHONY: db\:revision\:create
db\:revision\:create:
	@if [ -z "$(NAME)" ]; then \
		echo "Error: NAME is required"; \
		echo "Usage: make db:revision:create NAME=\"description\""; \
		exit 1; \
	fi
	@cd $(ALEMBIC_DIR) && uv run alembic revision --autogenerate -m "$(NAME)"

.PHONY: db\:migrate
db\:migrate:
	@uv run python -c "from app.infrastructure.database.migration import run_migrations; run_migrations()"

.PHONY: db\:downgrade
db\:downgrade:
	@if [ -z "$(REV)" ]; then \
		echo "Error: REV is required"; \
		echo "Usage: make db:downgrade REV=-1  # or specific revision"; \
		exit 1; \
	fi
	@cd $(ALEMBIC_DIR) && uv run alembic downgrade $(REV)

.PHONY: db\:current
db\:current:
	@cd $(ALEMBIC_DIR) && uv run alembic current

.PHONY: db\:history
db\:history:
	@cd $(ALEMBIC_DIR) && uv run alembic history

# ==== DBバックアップ (Docker経由実行) ====
.PHONY: db\:backup\:oneshot
db\:backup\:oneshot:
	@echo "Running backup in Docker container..."
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli oneshot

.PHONY: db\:backup\:list
db\:backup\:list:
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli list

.PHONY: db\:backup\:list\:remote
db\:backup\:list\:remote:
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli list --remote

.PHONY: db\:backup\:diff
db\:backup\:diff:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:diff FILE=\"backup_20250101_120000.backup.gz\""; \
		exit 1; \
	fi
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli diff $(FILE)

.PHONY: db\:backup\:diff\:s3
db\:backup\:diff\:s3:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:diff:s3 FILE=\"backup_20250101_120000.backup.gz\""; \
		exit 1; \
	fi
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli diff $(FILE) --from-s3

.PHONY: db\:backup\:restore
db\:backup\:restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:restore FILE=\"backup_20250101_120000.backup.gz\""; \
		exit 1; \
	fi
	@echo "WARNING: This will restore the database from $(FILE)"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli restore $(FILE)

.PHONY: db\:backup\:restore\:s3
db\:backup\:restore\:s3:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:restore:s3 FILE=\"backup_20250101_120000.backup.gz\""; \
		exit 1; \
	fi
	@echo "WARNING: This will restore the database from S3: $(FILE)"
	@echo "Press Ctrl+C to cancel, or Enter to continue..."
	@read confirm
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli restore $(FILE) --from-s3

.PHONY: db\:backup\:restore\:dry-run
db\:backup\:restore\:dry-run:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: FILE is required"; \
		echo "Usage: make db:backup:restore:dry-run FILE=\"backup_20250101_120000.backup.gz\""; \
		exit 1; \
	fi
	@$(COMPOSE_CMD) exec -T server uv run --directory /app python -m app.utils.backup_cli restore $(FILE) --dry-run

# ==== Frontend操作 ====
.PHONY: frontend\:install
frontend\:install:
	@cd frontend && pnpm install

.PHONY: frontend\:build
frontend\:build:
	@cd frontend && pnpm build

.PHONY: frontend\:lint
frontend\:lint:
	@cd frontend && pnpm lint

.PHONY: frontend\:lint\:fix
frontend\:lint\:fix:
	@cd frontend && pnpm lint --fix

.PHONY: frontend\:type-check
frontend\:type-check:
	@cd frontend && pnpm exec tsc --noEmit

# ==== Docker Compose操作 ====
.PHONY: compose\:up
compose\:up:
	@$(COMPOSE_CMD) up -d

.PHONY: compose\:down
compose\:down:
	@$(COMPOSE_CMD) down --remove-orphans

.PHONY: compose\:down\:v
compose\:down\:v:
	@$(COMPOSE_CMD) down -v

.PHONY: compose\:logs
compose\:logs:
	@$(COMPOSE_CMD) logs -f

.PHONY: compose\:ps
compose\:ps:
	@$(COMPOSE_CMD) ps

.PHONY: compose\:ps\:json
compose\:ps\:json:
	@$(COMPOSE_CMD) ps --format json

.PHONY: compose\:pull
compose\:pull:
	@$(COMPOSE_CMD) pull

.PHONY: compose\:restart
compose\:restart:
	@$(COMPOSE_CMD) restart

.PHONY: compose\:build
compose\:build:
	@$(COMPOSE_CMD) up --build -d

# ==== local環境操作 ====
.PHONY: local\:up
local\:up:
	@ENV=local $(MAKE) compose:up

.PHONY: local\:down
local\:down:
	@ENV=local $(MAKE) compose:down

.PHONY: local\:down\:v
local\:down\:v:
	@ENV=local $(MAKE) compose:down:v

.PHONY: local\:logs
local\:logs:
	@ENV=local $(MAKE) compose:logs

.PHONY: local\:ps
local\:ps:
	@ENV=local $(MAKE) compose:ps

.PHONY: local\:serve
local\:serve:
	@echo "Starting FastAPI and Frontend dev servers..."
	@cd frontend && pnpm dev & uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000 & wait

.PHONY: local\:serve\:backend
local\:serve\:backend:
	@uv run fastapi dev app/main.py --host 0.0.0.0 --port 8000

.PHONY: local\:serve\:frontend
local\:serve\:frontend:
	@cd frontend && pnpm dev

# ==== stg環境操作 ====
.PHONY: stg\:up
stg\:up:
	@ENV=stg $(MAKE) compose:up

.PHONY: stg\:logs
stg\:logs:
	@ENV=stg $(MAKE) compose:logs

.PHONY: stg\:ps
stg\:ps:
	@ENV=stg $(MAKE) compose:ps

.PHONY: stg\:down
stg\:down:
	@ENV=stg $(MAKE) compose:down

# ==== prod環境操作 ====
.PHONY: prod\:up
prod\:up:
	@ENV=prod $(MAKE) compose:up

.PHONY: prod\:logs
prod\:logs:
	@ENV=prod $(MAKE) compose:logs

.PHONY: prod\:ps
prod\:ps:
	@ENV=prod $(MAKE) compose:ps

.PHONY: prod\:down
prod\:down:
	@ENV=prod $(MAKE) compose:down

# ==== 秘密情報管理コマンド ====
.PHONY: secrets\:encrypt\:stg
secrets\:encrypt\:stg:
	@if [ ! -f .env.stg ]; then \
		echo "Error: .env.stg not found. Create it first."; \
		exit 1; \
	fi
	@sops -e .env.stg > .env.stg.enc
	@echo "✅ .env.stg encrypted to .env.stg.enc"

.PHONY: secrets\:encrypt\:prod
secrets\:encrypt\:prod:
	@if [ ! -f .env.prod ]; then \
		echo "Error: .env.prod not found. Create it first."; \
		exit 1; \
	fi
	@sops -e .env.prod > .env.prod.enc
	@echo "✅ .env.prod encrypted to .env.prod.enc"

.PHONY: secrets\:decrypt\:stg
secrets\:decrypt\:stg:
	@if [ ! -f .env.stg.enc ]; then \
		echo "Error: .env.stg.enc not found"; \
		exit 1; \
	fi
	@sops -d .env.stg.enc > .env.stg
	@echo "✅ .env.stg.enc decrypted to .env.stg"

.PHONY: secrets\:decrypt\:prod
secrets\:decrypt\:prod:
	@if [ ! -f .env.prod.enc ]; then \
		echo "Error: .env.prod.enc not found"; \
		exit 1; \
	fi
	@sops -d .env.prod.enc > .env.prod
	@echo "✅ .env.prod.enc decrypted to .env.prod"

.PHONY: secrets\:edit\:stg
secrets\:edit\:stg:
	@if [ ! -f .env.stg.enc ]; then \
		echo "Error: .env.stg.enc not found"; \
		exit 1; \
	fi
	@sops .env.stg.enc

.PHONY: secrets\:edit\:prod
secrets\:edit\:prod:
	@if [ ! -f .env.prod.enc ]; then \
		echo "Error: .env.prod.enc not found"; \
		exit 1; \
	fi
	@sops .env.prod.enc

# ==== テンプレート適用コマンド ====
.PHONY: template\:list
template\:list:
	@if ! git remote | grep -q "template"; then \
		git remote add template git@github.com:ukwhatn/fastapi-template.git; \
		echo "Added template remote"; \
	fi
	@git fetch template
	@echo "テンプレートの最新コミット一覧："
	@git log template/main -n 10 --oneline

.PHONY: template\:apply
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

.PHONY: template\:apply\:range
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

.PHONY: template\:apply\:force
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
