Generic single-database configuration with Alembic.

## Commands

Generate a new migration:
```
alembic revision --autogenerate -m "Migration message"
```

Run migrations:
```
alembic upgrade head
```

Downgrade to a specific revision:
```
alembic downgrade <revision>
```

Get current revision:
```
alembic current
```

History:
```
alembic history
```