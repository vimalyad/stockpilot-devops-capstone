# StockPilot chart

The chart deploys two API replicas, two frontend replicas, two Celery workers, one Celery beat scheduler, persistent PostgreSQL and Redis, a migration Job, Service routing, optional Ingress/HPA and optional Prometheus integration. Defaults are a capacity/scaling design, not a performance benchmark. Single-instance stateful dependencies remain an availability boundary.

```bash
kubectl apply -f k8s/namespace.yaml
export POSTGRES_PASSWORD="$(openssl rand -hex 24)"
bash scripts/create-secret.sh
helm lint helm/stockpilot
helm upgrade --install stockpilot helm/stockpilot -n stockpilot --wait --wait-for-jobs --timeout 8m \
  --set backend.image.tag=<tested-commit-sha> --set frontend.image.tag=<tested-commit-sha>
helm test stockpilot -n stockpilot --logs
kubectl -n stockpilot port-forward svc/frontend 3000:8080
```

On a local cluster, install an Ingress controller and metrics-server separately for hostname routing and HPA. Use `--set ingress.enabled=false --set autoscaling.enabled=false` for an initial minimal smoke run. Enable monitoring only after the Prometheus Operator CRDs exist. On EKS install the included StorageClass and pass `--set postgres.storageClass=stockpilot-gp3` (applies to both stateful services).

The migration runs once per Helm revision, with retries while the database starts. API/worker/scheduler init containers wait until database Alembic heads match the migrations packaged in that application image. Argo CD uses sync waves so config precedes stateful services, migration precedes application workloads, and a single beat scheduler avoids duplicate periodic tasks. Successful migration Jobs are retained for logs; prune old revision Jobs after retaining evidence.

The demo seed is idempotent and can be disabled with `--set seedDemo=false`. Supply `stockpilot-secrets` keys `POSTGRES_PASSWORD` and `DATABASE_URL`; Helm never embeds a default password. GHCR packages must be public or an imagePullSecret must be supplied. Release names are tracked by labels, but service names are fixed; install one StockPilot release per namespace.

Do not delete PVCs during ordinary redeployment. A Helm uninstall leaves StatefulSet-generated PVCs behind. Back up PostgreSQL before destructive schema changes, and review migration compatibility before rolling an API image back.
