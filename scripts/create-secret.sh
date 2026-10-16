#!/usr/bin/env bash
set -euo pipefail
: "${POSTGRES_PASSWORD:?Export a URL-safe PostgreSQL password}"
namespace=${NAMESPACE:-stockpilot}
kubectl create secret generic stockpilot-secrets --namespace "$namespace" --from-literal="POSTGRES_PASSWORD=$POSTGRES_PASSWORD" --from-literal="DATABASE_URL=postgresql+psycopg://stockpilot:$POSTGRES_PASSWORD@postgres:5432/stockpilot" --dry-run=client -o yaml | kubectl apply -f -
