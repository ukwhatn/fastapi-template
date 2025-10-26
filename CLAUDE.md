# CLAUDE.md

This file provides guidance for Claude Code when working with this repository.

## Project Overview

FastAPI production-ready template using Clean Architecture (4-layer), SQLAlchemy ORM, RDB-based encrypted session management, comprehensive Docker deployment, and Supabase support.

**Tech Stack:**
- FastAPI 0.120.0+ (Python 3.13+)
- SQLAlchemy 2.0+ with PostgreSQL
- Docker Compose (multi-profile setup)
- uv for dependency management
- Ruff for linting/formatting
- mypy for strict type checking
- pytest with coverage reporting

## Common Commands

### Essential Setup
```bash
make env                    # Create .env from .env.example
make dev:setup              # Install all dependencies with uv
make up INCLUDE_DB=true     # Start all containers with database
make db:migrate             # Apply database migrations
```

### Development Workflow
```bash
make lint                   # Check code quality with Ruff
make lint:fix               # Auto-fix linting issues
make format                 # Format code with Ruff
make type-check             # Run mypy type checking (strict mode)
make test                   # Run all tests
make test:cov               # Run tests with coverage report
```

### Pre-commit Hooks (Git Automation)
```bash
make pre-commit:install     # Install git hooks (one-time setup)
make pre-commit:run         # Run all hooks manually on all files
make pre-commit:update      # Update hook versions
```

### Database Operations
```bash
make db:revision:create NAME="description"  # Create new migration
make db:migrate                             # Apply migrations manually
make db:downgrade REV=-1                    # Rollback one migration
make db:current                             # Show current revision
make db:history                             # Show migration history
```

**Note**: Migrations run automatically on application startup (lifespan). `make db:migrate` is for manual execution only.

### Database Backup Operations
```bash
# Backup operations
make db:backup:oneshot                      # Create backup immediately
make db:backup:list                         # List local backups
make db:backup:list:remote                  # List S3 backups

# Diff operations
make db:backup:diff FILE="backup_xxx.backup.gz"        # Show diff with backup (local)
make db:backup:diff:s3 FILE="backup_xxx.backup.gz"     # Show diff with backup (S3)

# Restore operations
make db:backup:restore FILE="backup_xxx.backup.gz"     # Restore from backup (local)
make db:backup:restore:s3 FILE="backup_xxx.backup.gz"  # Restore from backup (S3)
make db:backup:restore:dry-run FILE="backup_xxx.backup.gz"  # Show diff only (no restore)
```

**Backup Format**:
- Uses psycopg2 directly (no pg_dump/pg_restore dependency)
- Format: Compressed JSON (gzip)
- Includes migration version and table data
- Auto-cleanup based on `BACKUP_RETENTION_DAYS` (default: 7 days)

**Restore Behavior**:
- Transaction-based (all-or-nothing)
- Automatically adjusts migration version
- Shows diff summary before restore
- Supports dry-run mode for preview

### Docker Operations
```bash
make up                     # Build and start containers (legacy)
make down                   # Stop containers
make reload                 # Rebuild and restart containers
make logs                   # Follow container logs
make ps                     # Show running containers
```

### Deployment (New)
```bash
# Local development (uv native + Docker DB)
docker compose -f compose.local.yml up -d
uv run fastapi dev app/main.py

# Dev environment (auto-deploy via GitHub Actions)
# Server setup (one-time): ./scripts/setup-server.sh dev
# Then push to develop branch for auto-deploy
make dev:logs               # View dev logs
make dev:ps                 # Check dev status

# Production environment (auto-deploy via GitHub Actions)
# Server setup (one-time): ./scripts/setup-server.sh prod
# Then push to main branch for auto-deploy
make prod:logs              # View production logs
make prod:ps                # Check production status

# Secrets management (SOPS + age)
make secrets:encrypt:dev    # Encrypt dev secrets
make secrets:encrypt:prod   # Encrypt prod secrets
make secrets:decrypt:dev    # Decrypt dev secrets
make secrets:decrypt:prod   # Decrypt prod secrets
```

## Important Guidelines

**ALWAYS use Makefile commands when available**:
- This project uses a comprehensive Makefile with predefined tasks for common operations
- Using `make` commands ensures consistency, proper environment setup, and adherence to project conventions
- Before running any direct command (e.g., `pytest`, `mypy`, `ruff`), check if a corresponding `make` target exists
- Examples:
  - Use `make test` instead of `uv run pytest tests/`
  - Use `make type-check` instead of `uv run mypy app versions tests`
  - Use `make lint` instead of `uv run ruff check ./app`
  - Use `make format` instead of `uv run ruff format ./app`

**When to use direct commands**:
- Only when no Makefile target exists for the specific operation
- When you need to pass special flags not covered by existing targets
- When explicitly requested by the user to run a command directly

## Architecture

IMPORTANT: This project follows Clean Architecture with strict layer separation. Always respect dependency rules.

### Layer Structure (4 layers)

**Domain Layer** (`app/domain/`)
- Core business logic, entities, value objects
- No dependencies on other layers
- Files: `exceptions/base.py`, `entities/`, `value_objects/`

**Application Layer** (`app/application/`)
- Use cases, DTOs, repository interfaces
- Depends only on Domain layer
- Files: `use_cases/`, `services/`, `interfaces/`, `dtos/`

**Infrastructure Layer** (`app/infrastructure/`)
- Database models, repositories, external services
- Implements interfaces from Application layer
- Files: `database/models/`, `repositories/`, `security/`, `external/`

**Presentation Layer** (`app/presentation/`)
- FastAPI routers, schemas, middleware, dependencies
- Files: `api/v1/`, `api/system/`, `schemas/`, `middleware/`

### Key Files

- `app/main.py` - Application entry point with middleware setup and auto-migration
- `app/core/config.py` - Settings management (Pydantic Settings)
- `app/infrastructure/database/connection.py` - Database connection management
- `app/infrastructure/database/models/base.py` - Base model with timestamp mixin
- `app/infrastructure/database/migration.py` - Programmatic Alembic migration runner
- `app/infrastructure/database/alembic/` - Alembic migration configuration and versions
- `app/infrastructure/repositories/session_repository.py` - Session service implementation
- `app/infrastructure/security/encryption.py` - Fernet encryption for sessions

## Code Style

IMPORTANT: Follow these conventions strictly:

- **Type hints**: Always use type hints. Project uses mypy strict mode
- **Imports**: Use relative imports within `app/` package (e.g., `from .domain import ...`). Use absolute imports from outside (e.g., tests: `from app.domain import ...`)
- **Async/await**: Use async for all database operations and API endpoints
- **Docstrings**: Not required for simple functions, but recommended for complex logic
- **Naming**:
  - Files: `snake_case.py`
  - Classes: `PascalCase`
  - Functions/variables: `snake_case`
  - Constants: `UPPER_SNAKE_CASE`

## Testing Guidelines

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use `test_` prefix for all test files and functions
- Leverage fixtures from `tests/conftest.py` (`client`, `db_session`)
- Run `make test` before committing

## Workflow for Common Tasks

### Adding a New API Endpoint

1. Create SQLAlchemy model in `app/infrastructure/database/models/`
2. Create Pydantic schema in `app/presentation/schemas/`
3. Create repository in `app/infrastructure/repositories/`
4. Create use case in `app/application/use_cases/` (if needed)
5. Create router in `app/presentation/api/v1/`
6. Register router in `app/presentation/api/v1/__init__.py`
7. Create migration: `make db:revision:create NAME="add_model"`
8. Apply migration: `make db:migrate`
9. Add tests in `tests/`
10. Run: `make lint && make type-check && make test`

### Adding Database Model

1. Create model class inheriting from `Base` in `app/infrastructure/database/models/`
2. Import in `app/infrastructure/database/models/__init__.py`
3. Import in `app/infrastructure/database/alembic/env.py` (for autogenerate detection)
4. Create corresponding Pydantic schema
5. Create repository implementation
6. Generate migration: `make db:revision:create NAME="description"`
7. Review migration file in `app/infrastructure/database/alembic/versions/`
8. Migrations apply automatically on next `uv run fastapi dev` or container restart
9. For manual apply: `make db:migrate`

### Modifying Environment Configuration

1. Add field to `Settings` class in `app/core/config.py`
2. Update `.env.example` with new variable
3. Update `.env` locally
4. Access via `get_settings()` dependency in endpoints

## Important Project Details

### Session Management
- Uses RDB-based sessions (NOT Redis)
- Fernet encryption for session data (requires `SESSION_ENCRYPTION_KEY` in .env)
- CSRF protection enabled
- Session fixation protection via User-Agent + IP fingerprinting

### Database Configuration
- Database URL is constructed from individual `POSTGRES_*` variables (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB)
- Supabase auto-detected if POSTGRES_HOST contains 'supabase.co'
- `POSTGRES_HOST` determines database location:
  - `POSTGRES_HOST=db` → local DB container starts (via --profile local-db)
  - `POSTGRES_HOST=db.xxx.supabase.co` → external DBaaS, no local container
- db-dumper ALWAYS runs, connecting to whichever DB is configured

### Database Migrations
- **Automatic execution**: Migrations run on application startup (FastAPI lifespan event)
- **Location**: `app/infrastructure/database/alembic/versions/`
- **Safety**: If migration fails, application startup stops (prevents data corruption)
- **Auto-deploy compatibility**: When GitHub Actions deploys new image, migrations run automatically
- **Idempotency**: Alembic ensures migrations only run once (safe to restart)
- **Manual rollback**: Use `make db:downgrade REV=-1` if needed

### Docker Profiles
- Use `--profile local-db` to enable local database container
- Deployment scripts auto-detect POSTGRES_HOST to determine if --profile local-db is needed
- db-dumper runs regardless of DB location (local or external)

### Security
- Sentry integration for error tracking (production)
- New Relic APM monitoring (production)
- Security scanning via Bandit and Semgrep: `make security:scan`

## Deployment Architecture

IMPORTANT: The project uses three distinct deployment environments with GitHub Actions auto-deploy.

### Environment Overview

| Environment | App Execution | Database | Proxy | Auto-Deploy | Compose File |
|-------------|--------------|----------|-------|-------------|--------------|
| **Local** | uv native (hot reload) | Docker (optional) | None | No | `compose.local.yml` |
| **Dev** | Docker (GHCR.io) | Docker PostgreSQL | Cloudflare Tunnels | GitHub Actions (develop) | `compose.dev.yml` |
| **Prod** | Docker (GHCR.io) | External (Supabase) | nginx + Cloudflare | GitHub Actions (main) | `compose.prod.yml` |

### Key Deployment Features

**Multi-platform builds**: GitHub Actions builds linux/amd64 and linux/arm64 images

**Tag strategy**:
- `main` branch → `latest` + `main` + `main-sha-xxx` tags
- `develop` branch → `develop` + `develop-sha-xxx` tags

**Automatic deployment**: GitHub Actions SSHs into server and deploys on push to develop/main

**Sparse checkout**: Server only clones necessary files (compose.yml, Makefile, etc.) to minimize disk usage

**Secrets management**: SOPS + age for encrypted environment files (`.env.dev.enc`, `.env.prod.enc`)

### Secrets Management (SOPS + age)

**Why**: Encrypted secrets can be safely committed to Git with full audit trail

**Setup**:
1. Install SOPS and age
2. Generate age key pair: `age-keygen -o ~/.config/sops/age/keys.txt`
3. Update `.sops.yaml` with public key
4. Encrypt: `sops -e .env.dev > .env.dev.enc`
5. Commit encrypted file to Git

**Deployment flow**:
1. GitHub Actions builds image and pushes to GHCR.io
2. GitHub Actions SSHs into server
3. Server runs `git pull` to get latest compose.yml
4. Server runs `docker compose pull` to get latest image
5. Server runs `docker compose up -d --force-recreate` to restart containers
6. Health check confirmation (60s timeout)

**Reference**: See `docs/secrets-management.md` for detailed guide

### Deployment Workflow

**Local development**:
```bash
docker compose -f compose.local.yml up -d
uv run fastapi dev app/main.py
```

**Dev deployment** (initial):
```bash
# On server (one-time setup)
./scripts/setup-server.sh dev

# Configure GitHub Secrets (one-time):
# DEV_SSH_HOST, DEV_SSH_USER, DEV_SSH_PORT, DEV_SSH_PRIVATE_KEY
```

**Dev deployment** (subsequent):
```bash
git push origin develop        # GitHub Actions auto-deploys
```

**Production deployment** (initial):
```bash
# On server (one-time setup)
./scripts/setup-server.sh prod

# Configure GitHub Secrets (one-time):
# PROD_SSH_HOST, PROD_SSH_USER, PROD_SSH_PORT, PROD_SSH_PRIVATE_KEY
```

**Production deployment** (subsequent):
```bash
git push origin main           # GitHub Actions auto-deploys
```

### Important Deployment Notes

- **SSH managed by GitHub Actions**: Developers don't need server access
- **Downtime**: ~10-30 seconds during deploys (forced container recreation)
- **Branch isolation**: develop and main branches use different tags and servers
- **Rollback**: Use `git revert` and push, or manually checkout previous commit on server
- **Monitoring**: Check GitHub Actions logs and server logs with `ENV={dev|prod} make compose:logs`
- **Health checks**: Deployment fails if health check doesn't pass within 60 seconds

**Reference**: See `docs/deployment.md` for comprehensive deployment guide

## Repository Etiquette

- Main branch: `main`
- Development branch: `develop`
- Create PRs from feature branches to `develop`
- Use `make pr:create` to create PR (requires gh CLI)
- Pre-commit hooks automatically run format/lint on commit, tests on push
- Use conventional commits (e.g., `feat:`, `fix:`, `refactor:`)

## Documentation

- **README.md** - User-facing landing page (Japanese)
- **development.md** - Complete development guide (Japanese)
- **docs/deployment.md** - Deployment guide for local/dev/prod (Japanese)
- **docs/secrets-management.md** - SOPS + age secrets management guide (Japanese)
- **CLAUDE.md** - This file, for AI assistance

## Pre-commit Hooks

This project uses [pre-commit](https://pre-commit.com/) framework for automated code quality checks.

### What Gets Checked

**Pre-commit (on `git commit`)**:
- File validation (large files, YAML/TOML syntax, trailing whitespace)
- Ruff format (auto-format code)
- Ruff lint --fix (auto-fix linting issues)
- uv.lock synchronization
- OpenAPI spec generation (when `app/*.py` changes)

**Pre-push (on `git push`)**:
- Type checking (mypy)
- Unit tests (pytest)

### First-Time Setup

```bash
# Install git hooks (one-time)
make pre-commit:install
```

### Usage

Hooks run automatically on commit/push. To run manually:

```bash
# Run all hooks on all files
make pre-commit:run

# Run specific hook
uv run pre-commit run ruff --all-files

# Skip hooks (not recommended)
git commit --no-verify
```

### Performance Optimizations

- ✅ **Ruff**: 150-200x faster than traditional linters
- ✅ **Parallel execution**: Multiple files processed simultaneously
- ✅ **Selective execution**: Only changed files checked (except tests/type-check)
- ✅ **Caching**: Hook environments cached after first run

**Reference**: Configuration in `.pre-commit-config.yaml`

## Common Gotchas

- mypy requires paths without `./` prefix: use `mypy app tests` not `mypy ./app ./tests`
- Database migrations must be reviewed before applying (Alembic can miss some changes)
- Session encryption key must be 32 url-safe base64-encoded bytes
- Docker Compose profiles must be explicitly enabled via `INCLUDE_DB=true` for database services
- Pre-commit hooks can be skipped with `--no-verify` but this is not recommended
