#!/bin/bash
set -e

if [ "$DB_TOOL_MODE" = "migrator" ]; then
  echo "Running migrator mode..."
  if [ "$1" = "custom" ]; then
    echo "Running custom command: ${@:2}"
    exec "${@:2}"
  else
    exec alembic upgrade head
  fi
elif [ "$DB_TOOL_MODE" = "dumper" ]; then
  echo "Running dumper mode..."
  if [ "$1" = "custom" ]; then
    echo "Running custom command: ${@:2}"
    exec "${@:2}"
  else
    exec python dump.py
  fi
else
  echo "Error: Unknown mode '$DB_TOOL_MODE'. Valid modes are 'migrator' or 'dumper'."
  exit 1
fi