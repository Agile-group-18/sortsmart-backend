#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until nc -z db 5432; do
  sleep 1
done
sleep 1

echo "PostgreSQL is ready!"
echo "Running migrations..."
alembic upgrade head

echo "Starting server..."
exec "$@"