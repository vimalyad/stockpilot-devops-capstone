#!/usr/bin/env bash
set -euo pipefail
export PATH="$PWD/.tools/bin:$PATH"
: "${IMAGE_PREFIX:?}" "${IMAGE_TAG:?}"
cluster="stockpilot-${GITHUB_RUN_ID:-local}-${GITHUB_RUN_ATTEMPT:-1}"
mkdir -p reports
cleanup() {
  kubectl -n stockpilot get pods,jobs,svc,pvc,hpa -o wide > reports/resources.txt 2>&1 || true
  kubectl -n stockpilot get events --sort-by=.metadata.creationTimestamp > reports/events.txt 2>&1 || true
  kubectl -n stockpilot logs -l app.kubernetes.io/name=stockpilot --all-containers --prefix --tail=150 > reports/workloads.log 2>&1 || true
  kind delete cluster --name "$cluster"
}
trap cleanup EXIT
kind create cluster --name "$cluster" --wait 120s
docker load -i images.tar
kind load docker-image --name "$cluster" "$IMAGE_PREFIX-backend:$IMAGE_TAG" "$IMAGE_PREFIX-frontend:$IMAGE_TAG"
kubectl apply -f k8s/namespace.yaml
export POSTGRES_PASSWORD
POSTGRES_PASSWORD=$(openssl rand -hex 24)
bash scripts/create-secret.sh
helm upgrade --install stockpilot helm/stockpilot -n stockpilot --wait --wait-for-jobs --timeout 8m --set backend.image.repository="$IMAGE_PREFIX-backend" --set frontend.image.repository="$IMAGE_PREFIX-frontend" --set backend.image.tag="$IMAGE_TAG" --set frontend.image.tag="$IMAGE_TAG" --set ingress.enabled=false --set autoscaling.enabled=false
helm test stockpilot -n stockpilot --logs --timeout 120s | tee reports/helm-smoke.txt
kubectl -n stockpilot rollout status deployment/worker --timeout=120s
kubectl -n stockpilot exec deployment/backend -- python -c 'from app.tasks import refresh_report; task=refresh_report.delay(); result=task.get(timeout=30); assert "generated_at" in result; print("Background reporting completed:", result["generated_at"])' | tee reports/worker-smoke.txt
kubectl -n stockpilot exec deployment/backend -- python -c 'from app.tasks import redis_client; assert redis_client().get("stockpilot:inventory-report"); print("Redis report cache populated")' | tee reports/cache-smoke.txt
