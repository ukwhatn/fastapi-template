# CLAUDE.md

This file provides guidance for Claude Code when working with this repository.

## Project Overview

FastAPI production-ready template using Clean Architecture (4-layer), SQLAlchemy ORM, RDB-based encrypted session management, comprehensive Docker deployment, and Supabase support.

**Tech Stack:**
- FastAPI 0.120.0+ (Python 3.14+)
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

### Database Operations
```bash
make db:revision:create NAME="description"  # Create new migration
make db:migrate                             # Apply migrations
make db:current                             # Show current revision
make db:history                             # Show migration history
```

### Docker Operations
```bash
make up                     # Build and start containers
make down                   # Stop containers
make reload                 # Rebuild and restart containers
make logs                   # Follow container logs
make ps                     # Show running containers
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
- **Imports**: Use absolute imports (`from app.domain...`), not relative imports
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
- `DATABASE_URL` takes precedence over individual `POSTGRES_*` variables
- Supabase auto-detected if URL contains 'supabase.co'
- Application continues with DB features disabled if DATABASE_URL not set (with warning)

### Docker Profiles
- Use `INCLUDE_DB=true` to enable database services (db, adminer, db-migrator, db-dumper)
- Environments: `dev` (default), `stg`, `test`, `prod`
- Example: `make up ENV=prod INCLUDE_DB=true`

### Security
- Sentry integration for error tracking (production)
- New Relic APM monitoring (production)
- Security scanning via Bandit and Semgrep: `make security:scan`

## Repository Etiquette

- Main branch: `main`
- Development branch: `develop`
- Create PRs from feature branches to `develop`
- Use `make pr:create` to create PR (requires gh CLI)
- Run `make lint`, `make type-check`, and `make test` before committing
- Use conventional commits (e.g., `feat:`, `fix:`, `refactor:`)

## Documentation

- **README.md** - User-facing landing page (Japanese)
- **development.md** - Complete development guide (Japanese)
- **CLAUDE.md** - This file, for AI assistance

## Common Gotchas

- mypy requires paths without `./` prefix: use `mypy app tests` not `mypy ./app ./tests`
- Database migrations must be reviewed before applying (Alembic can miss some changes)
- Session encryption key must be 32 url-safe base64-encoded bytes
- Docker Compose profiles must be explicitly enabled via `INCLUDE_DB=true` for database services
