#!/bin/bash
set -e

if [ "$DB_TOOL_MODE" = "migrator" ]; then
  echo "Running migrator mode..."
  exec alembic upgrade head
elif [ "$DB_TOOL_MODE" = "dumper" ]; then
  echo "Running dumper mode..."
  exec python dump.py
else
  echo "Error: Unknown mode '$DB_TOOL_MODE'. Valid modes are 'migrator' or 'dumper'."
  exit 1
fi