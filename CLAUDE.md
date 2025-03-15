# FASTAPI-TEMPLATE DEVELOPMENT GUIDE

## Build Commands
- `make build` - Build Docker containers
- `make up` - Start Docker containers with auto-build
- `make down` - Stop running containers
- `make reload` - Rebuild and restart containers

## Lint/Format Commands
- `make lint` - Run Ruff linter
- `make lint:fix` - Run Ruff with auto-fixing
- `make format` - Format code with Ruff
- `make security:scan` - Run security scans (Bandit, Semgrep)

## Database Commands
- `make db:migrate` - Run database migrations
- `make db:revision:create NAME="message"` - Create new migration

## Code Style Guidelines
- **Imports**: Group in order: standard lib, third-party, app-specific. Alphabetize each.
- **Naming**: snake_case for functions/variables, PascalCase for classes, singular nouns for models
- **Types**: Use type hints everywhere. Pydantic for validation, SQLAlchemy Mapped[] types for ORM
- **Errors**: Extend APIError base class, use middleware for global handling, use Sentry in prod
- **API Structure**: Router-based organization, version endpoints properly (/api/v1/...)
- **Documentation**: Use docstrings for classes/functions, document API endpoints clearly

## Project Structure
- `app/api/` - Routes and endpoints
- `app/core/` - Core application functionality
- `app/db/` - Database models, schemas, and CRUD operations
- `app/utils/` - Utility functions and helpers