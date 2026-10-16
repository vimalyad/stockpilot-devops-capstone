#!/usr/bin/env bash
set -euo pipefail
: "${POSTGRES_PASSWORD:?Export a URL-safe PostgreSQL password}"
docker network inspect stockpilot >/dev/null 2>&1 || docker network create stockpilot
docker volume create stockpilot-postgres >/dev/null
docker build -t stockpilot-backend:local backend
docker build -t stockpilot-frontend:local frontend
docker run -d --name postgres --network stockpilot -e POSTGRES_USER=stockpilot -e POSTGRES_DB=stockpilot -e POSTGRES_PASSWORD -v stockpilot-postgres:/var/lib/postgresql/data postgres:17-alpine
until docker exec postgres pg_isready -U stockpilot; do sleep 2; done
docker run -d --name redis --network stockpilot redis:7.4-alpine
export DATABASE_URL="postgresql+psycopg://stockpilot:${POSTGRES_PASSWORD}@postgres:5432/stockpilot" REDIS_URL=redis://redis:6379/0
docker run --rm --network stockpilot -e DATABASE_URL stockpilot-backend:local sh -ec 'alembic upgrade head && python -m app.seed'
docker run -d --name backend --network stockpilot -e DATABASE_URL -e REDIS_URL -p 127.0.0.1:8000:8000 stockpilot-backend:local
docker run -d --name worker --network stockpilot -e DATABASE_URL -e REDIS_URL stockpilot-backend:local celery -A app.tasks:celery worker --loglevel=info
docker run -d --name scheduler --network stockpilot -e DATABASE_URL -e REDIS_URL stockpilot-backend:local celery -A app.tasks:celery beat --schedule=/tmp/celerybeat
docker run -d --name frontend --network stockpilot -p 127.0.0.1:3000:8080 stockpilot-frontend:local
