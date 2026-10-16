# Operations guide

## Local Python/Node development

Use Python 3.12+ and Node compatible with the frontend lockfile. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-dev.txt
cd backend
export DATABASE_URL=sqlite:///./stockpilot-dev.db
../.venv/bin/alembic upgrade head
../.venv/bin/python -m app.seed
../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

The Vite proxy forwards API requests to port 8000. SQLite is a development convenience; PostgreSQL is required to exercise production row locks. Background reports need Redis and a worker; use Compose for the complete service topology.

## Checks

```bash
.venv/bin/ruff check backend
PYTHONPATH=backend .venv/bin/pytest backend/tests --cov=backend/app --cov-report=term-missing
cd frontend
npm ci
npm run build
```

For PostgreSQL tests set `TEST_DATABASE_URL` to a dedicated disposable test database and `ALLOW_TEST_DATABASE_RESET=yes` as described in `backend/tests/conftest.py`. That opt-in permits schema resets; never point it at application data. SQLite skips the PostgreSQL concurrency case.

## Containers and persistence

```bash
cp .env.example .env
# Set a strong URL-safe password in .env.
docker compose config --quiet
docker compose up --build -d
docker compose ps
docker compose logs --tail=100 backend worker migrate
curl --fail http://127.0.0.1:8000/ready
```

Open `http://localhost:3000`. Create a movement, restart with `docker compose down` followed by `docker compose up -d`, and verify it persists. Volumes survive this sequence. Adding `-v` to `down` deletes data and should be reserved for an intentional disposable-demo reset.

```bash
docker compose exec -T postgres pg_dump -U stockpilot stockpilot > stockpilot-backup.sql
```

Restore into a deliberately selected recovery database and verify it. A backup is not proven until its restore is tested.

## Kubernetes

Publish images or load them into kind; set chart image repository/tag values to images the cluster can actually pull. Create the namespace and application Secret before installing:

```bash
kubectl apply -f k8s/namespace.yaml
# Export the URL-safe POSTGRES_PASSWORD used by the database.
bash scripts/create-secret.sh
helm lint helm/stockpilot
helm upgrade --install stockpilot helm/stockpilot -n stockpilot --wait --timeout 10m
helm test stockpilot -n stockpilot --logs
kubectl get pods,svc,pvc,hpa -n stockpilot
```

The migration job prepares the schema before application rollout. Inspect its logs if installation waits on migration. The example requires reachable images and an existing external Secret. [The CI deployment script](../scripts/ci-deploy.sh) is a concrete temporary-kind example. [Troubleshooting exercises](../troubleshooting/README.md) cover seven deliberate failures in disposable environments.

## Monitoring, GitOps and cloud

Follow [monitoring/README.md](../monitoring/README.md) to install Prometheus Operator and enable chart monitoring. Confirm actual scrape targets before interpreting graphs. Capture the timestamp, environment and source revision alongside screenshots.

Follow [gitops/README.md](../gitops/README.md) to configure repository access and Argo CD. Verify the actual revision and resource health; configuration alone does not prove a successful sync.

Follow [terraform/README.md](../terraform/README.md) with an authorized AWS account. Review the concrete plan before apply and verify current service versions, quotas and expected charges. Uninstall workloads and cloud load balancers before infrastructure teardown; deliberately handle retained database volumes. After destroy, check for remaining volumes, load balancers and logs.

Use [the live demo runbook](../demo/RUNBOOK.md) for the product/platform sequence and [the screenshot index](../screenshots/README.md) for provenance. Capture only operations actually performed.
