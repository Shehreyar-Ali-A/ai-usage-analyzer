#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_PG="ai-usage-analyzer-postgres-1"
STANDALONE_PG="ai-workspace-pg"

# Load env vars from .env
if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  source "$PROJECT_DIR/.env"
  set +a
fi

# Check if docker-compose Postgres is already running
if docker ps --format '{{.Names}}' | grep -q "^${COMPOSE_PG}$"; then
  echo "Using existing docker-compose Postgres container."
  PG_CONTAINER="$COMPOSE_PG"

# Check if standalone dev container is already running
elif docker ps --format '{{.Names}}' | grep -q "^${STANDALONE_PG}$"; then
  echo "Postgres already running."
  PG_CONTAINER="$STANDALONE_PG"

# Check if standalone exists but is stopped
elif docker ps -a --format '{{.Names}}' | grep -q "^${STANDALONE_PG}$"; then
  echo "Starting existing Postgres container..."
  docker start "$STANDALONE_PG"
  PG_CONTAINER="$STANDALONE_PG"

# Create a new standalone container
else
  echo "Creating Postgres container..."
  docker run -d --name "$STANDALONE_PG" \
    -e POSTGRES_USER=postgres \
    -e POSTGRES_PASSWORD=postgres \
    -e POSTGRES_DB=ai_workspace \
    -p 5433:5432 \
    -v ai_workspace_pgdata:/var/lib/postgresql/data \
    postgres:16-alpine
  PG_CONTAINER="$STANDALONE_PG"
fi

echo "Waiting for Postgres to be ready..."
until docker exec "$PG_CONTAINER" pg_isready -U postgres > /dev/null 2>&1; do
  sleep 1
done
echo "Postgres is ready."

# Run backend
cd "$PROJECT_DIR/backend"
export PYTHONPATH="$PROJECT_DIR/backend"

echo "Running migrations..."
alembic upgrade head

echo "Starting backend on port 8888..."
uvicorn app.main:app --reload --port 8888
