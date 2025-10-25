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
make db:migrate                             # Apply migrations
make db:current                             # Show current revision
make db:history                             # Show migration history
```

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

# Dev environment (auto-deploy via Watchtower)
make dev:deploy             # Deploy to dev environment
make dev:logs               # View dev logs
make dev:ps                 # Check dev status

# Production environment (auto-deploy via Watchtower)
make prod:deploy            # Deploy to production (with confirmation)
make prod:logs              # View production logs
make prod:ps                # Check production status

# Watchtower setup (one-time per server)
./scripts/setup-watchtower.sh

# Secrets management (SOPS + age)
make secrets:encrypt:dev    # Encrypt dev secrets
make secrets:encrypt:prod   # Encrypt prod secrets
make secrets:decrypt:dev    # Decrypt dev secrets
make secrets:decrypt:prod   # Decrypt prod secrets
```

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

- `app/main.py` - Application entry point with middleware setup
- `app/core/config.py` - Settings management (Pydantic Settings)
- `app/infrastructure/database/connection.py` - Database connection management
- `app/infrastructure/database/models/base.py` - Base model with timestamp mixin
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
3. Create corresponding Pydantic schema
4. Create repository implementation
5. Generate migration: `make db:revision:create NAME="description"`
6. Review migration file in `versions/`
7. Apply: `make db:migrate`

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
- db-migrator and db-dumper ALWAYS run, connecting to whichever DB is configured

### Docker Profiles
- Use `--profile local-db` to enable local database container
- Deployment scripts auto-detect POSTGRES_HOST to determine if --profile local-db is needed
- db-migrator and db-dumper run regardless of DB location (local or external)

### Security
- Sentry integration for error tracking (production)
- New Relic APM monitoring (production)
- Security scanning via Bandit and Semgrep: `make security:scan`

## Deployment Architecture

IMPORTANT: The project uses three distinct deployment environments with automatic updates.

### Environment Overview

| Environment | App Execution | Database | Proxy | Auto-Deploy | Compose File |
|-------------|--------------|----------|-------|-------------|--------------|
| **Local** | uv native (hot reload) | Docker (optional) | None | No | `compose.local.yml` |
| **Dev** | Docker (GHCR.io) | Docker PostgreSQL | Cloudflare Tunnels | Watchtower (develop) | `compose.dev.yml` |
| **Prod** | Docker (GHCR.io) | External (Supabase) | nginx + Cloudflare | Watchtower (latest) | `compose.prod.yml` |

### Key Deployment Features

**Multi-platform builds**: GitHub Actions builds linux/amd64 and linux/arm64 images

**Tag strategy**:
- `main` branch → `latest` + `main` + `main-sha-xxx` tags
- `develop` branch → `develop` + `develop-sha-xxx` tags

**Automatic deployment**: Watchtower monitors GHCR.io and auto-updates containers (10 min polling)

**Label-based control**: Only containers with `com.centurylinklabs.watchtower.enable=true` update

**Secrets management**: SOPS + age for encrypted environment files (`.env.dev.enc`, `.env.prod.enc`)

### Watchtower Setup

**One Watchtower per server** (not per project):
- Label-based control prevents unintended updates
- Weekly self-update via cron
- Discord/Slack notifications via Shoutrrr
- Setup: `./scripts/setup-watchtower.sh`

**Auto-update enabled for**:
- `server` container
- `db-dumper` container (from ukwhatn/postgres-tools)
- `db-migrator` container (from ukwhatn/postgres-tools)

**Auto-update disabled for**:
- `db` container (PostgreSQL)
- `cloudflared` container

### Secrets Management (SOPS + age)

**Why**: Encrypted secrets can be safely committed to Git with full audit trail

**Setup**:
1. Install SOPS and age
2. Generate age key pair: `age-keygen -o ~/.config/sops/age/keys.txt`
3. Update `.sops.yaml` with public key
4. Encrypt: `sops -e .env.dev > .env.dev.enc`
5. Commit encrypted file to Git

**Deployment flow**:
1. Deploy script decrypts `.env.dev.enc` → `.env`
2. Starts containers with decrypted secrets
3. Removes `.env` after deployment

**Reference**: See `docs/secrets-management.md` for detailed guide

### Deployment Workflow

**Local development**:
```bash
docker compose -f compose.local.yml up -d
uv run fastapi dev app/main.py
```

**Dev deployment** (initial):
```bash
./scripts/setup-watchtower.sh  # One-time per server
./scripts/deploy-dev.sh         # Deploy
```

**Dev deployment** (subsequent):
```bash
git push origin develop        # GitHub Actions builds and pushes
# Watchtower auto-updates within 10 minutes
```

**Production deployment** (initial):
```bash
./scripts/setup-watchtower.sh  # One-time per server
./scripts/deploy-prod.sh        # Deploy with confirmation
```

**Production deployment** (subsequent):
```bash
git push origin main           # GitHub Actions builds and pushes
# Watchtower auto-updates within 10 minutes
```

### Important Deployment Notes

- **No SSH required**: All deployments use GHCR.io pull + Watchtower
- **Downtime**: 10-30 seconds during auto-updates
- **Branch isolation**: develop and main branches use different tags (no cross-contamination)
- **Rollback**: Use SHA tags for specific version deployment
- **Monitoring**: Check Watchtower logs with `docker logs watchtower -f`
- **Health checks**: Containers have built-in health checks; Watchtower respects them

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
