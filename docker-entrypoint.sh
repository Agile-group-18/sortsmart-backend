#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h db -U sortsmart 2>/dev/null; do
  sleep 1
done

echo "Running migrations..."
alembic upgrade head

echo "Starting app..."
exec "$@"
