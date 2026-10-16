# Delivery checklist

Sources: [instructor README](https://github.com/Nency-Ravaliya/devops-heros/blob/main/session21-python/README.md), [grading rubric](https://github.com/Nency-Ravaliya/devops-heros/blob/main/session21-python/GRADING.md), and the Session 21 homework document.

## Application

- Original inventory-management domain: products, suppliers, warehouses, immutable stock movements, reservations, and purchase-order lifecycle.
- FastAPI, SQLAlchemy, Alembic, PostgreSQL, React/Vite/TypeScript and pytest.
- Redis/Celery for asynchronous inventory reports; the database remains authoritative.
- Health, database readiness, Prometheus metrics, Swagger and full CRUD.
- Responsive UI with search, filters, forms, loading states and recoverable errors.

## Delivery layers

- At least 10 meaningful development commits; no attribution trailers.
- Non-root backend and multi-stage frontend images; Docker Compose.
- GitHub Actions: tests, frontend build, SAST, SCA, history secret scan, both image scans, SHA-tagged GHCR publication, and temporary Kubernetes deployment.
- Helm, two frontend/backend replicas, ClusterIP Services, ConfigMap/Secret, Ingress, HPA, probes, persistent PostgreSQL, and one migration Job before application rollout.
- Prometheus Operator ServiceMonitor, Grafana dashboard, alerts and Argo CD promotion/self-heal.
- Terraform VPC, public/private subnets, optional NAT, EKS workers and EBS storage; teardown instructions.
- Broken-image and broken-Service labs plus database/persistence and GitOps recovery.
- Evidence index, architecture, operating instructions, recording and presentation.

## Verification boundary

Code, successful execution and submitted evidence are tracked separately. No screenshot, pipeline result, deployment or cloud apply is claimed before it happens.

The current session cannot access the Docker socket, and the user has no AWS access. Local Docker/Kubernetes and real AWS execution therefore need an accessible environment. The existing Typeahead project remains a separate capstone.

