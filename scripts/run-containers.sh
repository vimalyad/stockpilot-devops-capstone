#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
network=stockpilot-manual
containers=(stockpilot-manual-frontend stockpilot-manual-scheduler stockpilot-manual-worker stockpilot-manual-backend stockpilot-manual-redis stockpilot-manual-postgres)
if [[ "${1:-up}" == down ]]; then
  for container in "${containers[@]}"; do
    if docker container inspect "$container" >/dev/null 2>&1; then docker rm -f "$container"; fi
  done
  if docker network inspect "$network" >/dev/null 2>&1; then docker network rm "$network"; fi
  echo 'Stopped StockPilot manual containers. Database volume retained: stockpilot-manual-postgres'
  exit 0
fi
if [[ "${1:-up}" != up ]]; then echo 'Usage: run-containers.sh up|down' >&2; exit 2; fi
: "${POSTGRES_PASSWORD:?Export a URL-safe PostgreSQL password}"
for container in "${containers[@]}"; do
  if docker container inspect "$container" >/dev/null 2>&1; then
    echo "$container already exists; use this script with down before restarting" >&2
    exit 2
  fi
done
docker network inspect "$network" >/dev/null 2>&1 || docker network create "$network"
docker volume create stockpilot-manual-postgres >/dev/null
docker build -t stockpilot-backend:local backend
docker build -t stockpilot-frontend:local frontend
docker run -d --name stockpilot-manual-postgres --network "$network" --network-alias postgres -e POSTGRES_USER=stockpilot -e POSTGRES_DB=stockpilot -e POSTGRES_PASSWORD -v stockpilot-manual-postgres:/var/lib/postgresql/data postgres:17-alpine
ready=false
for attempt in $(seq 1 60); do
  if docker exec stockpilot-manual-postgres pg_isready -U stockpilot -d stockpilot; then ready=true; break; fi
  sleep 2
done
if [[ "$ready" != true ]]; then echo 'PostgreSQL did not become ready within 120 seconds' >&2; exit 1; fi
docker run -d --name stockpilot-manual-redis --network "$network" --network-alias redis redis:7.4-alpine
export DATABASE_URL="postgresql+psycopg://stockpilot:${POSTGRES_PASSWORD}@postgres:5432/stockpilot" REDIS_URL=redis://redis:6379/0
docker run --rm --network "$network" -e DATABASE_URL stockpilot-backend:local sh -ec 'alembic upgrade head && python -m app.seed'
docker run -d --name stockpilot-manual-backend --network "$network" --network-alias backend -e DATABASE_URL -e REDIS_URL -p 127.0.0.1:8000:8000 stockpilot-backend:local
ready=false
for attempt in $(seq 1 60); do
  if docker exec stockpilot-manual-backend python -c 'import urllib.request; urllib.request.urlopen("http://localhost:8000/ready",timeout=2)' >/dev/null 2>&1; then ready=true; break; fi
  sleep 2
done
if [[ "$ready" != true ]]; then echo 'API did not become ready within 120 seconds' >&2; exit 1; fi
docker run -d --name stockpilot-manual-worker --network "$network" -e DATABASE_URL -e REDIS_URL stockpilot-backend:local celery -A app.tasks:celery worker --loglevel=info
docker run -d --name stockpilot-manual-scheduler --network "$network" -e DATABASE_URL -e REDIS_URL stockpilot-backend:local celery -A app.tasks:celery beat --schedule=/tmp/celerybeat
docker run -d --name stockpilot-manual-frontend --network "$network" -p 127.0.0.1:3000:8080 stockpilot-frontend:local
echo 'StockPilot: http://localhost:3000 · API docs: http://localhost:8000/docs'
