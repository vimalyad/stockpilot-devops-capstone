#!/usr/bin/env bash
set -euo pipefail
# Deliberately destructive to the disposable demo namespace, never production.
if [[ "${ALLOW_FAULTS:-}" != stockpilot ]]; then
  echo 'For the disposable lab only: export ALLOW_FAULTS=stockpilot' >&2
  exit 2
fi
case "${1:-}" in
  image) kubectl -n stockpilot set image deployment/backend backend=ghcr.io/vimalyad/stockpilot-devops-capstone-backend:deliberately-missing ;;
  selector) kubectl -n stockpilot patch service/backend -p '{"spec":{"selector":{"app.kubernetes.io/component":"backned"}}}' ;;
  readiness) kubectl -n stockpilot patch deployment/backend --type=json -p '[{"op":"replace","path":"/spec/template/spec/containers/0/readinessProbe/httpGet/path","value":"/missing-health"}]' ;;
  memory) kubectl -n stockpilot set resources deployment/backend --requests=memory=8Mi --limits=memory=8Mi ;;
  cpu) kubectl -n stockpilot set resources deployment/backend --requests=cpu=100 --limits=cpu=100 ;;
  database) kubectl -n stockpilot set env deployment/backend DATABASE_URL=postgresql+psycopg://stockpilot:deliberately-wrong@postgres:5432/stockpilot ;;
  ingress) kubectl -n stockpilot patch ingress/stockpilot --type=json -p '[{"op":"replace","path":"/spec/rules/0/http/paths/0/backend/service/name","value":"backned"}]' ;;
  *) echo 'Usage: challenge.sh image|selector|readiness|memory|cpu|database|ingress' >&2; exit 2 ;;
esac
