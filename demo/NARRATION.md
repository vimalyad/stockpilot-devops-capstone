# StockPilot narration

Synthetic English voice; original explanatory diagrams. This is not a live browser or cloud recording.

## 01 — Inventory, engineered for operations.

Welcome to StockPilot, a multi warehouse inventory and procurement platform, built as an original DevOps capstone. The product follows a physical item from a supplier purchase through receiving, reservation, transfer and fulfilment. Around that product is a delivery platform using containers, Kubernetes, automated security gates, monitoring and infrastructure as code. This presentation explains the implemented design and the available verification. The diagrams are original illustrations, not screenshots of a live cluster. The audio is synthetic English narration.

Source: `README.md; backend/app/models.py; docs/DELIVERY.md`

## 02 — One stock count. Many competing decisions.

Inventory management is a demanding domain because several workflows compete for the same stock. A sales reservation promises units to a customer. A transfer moves those units between warehouses. A purchase order brings more units into the business. A simple counter is not enough. StockPilot keeps the available quantity separate from the physical quantity, makes transfers atomic, and records stock movement history. The architecture is designed to support multiple replicas, but no production capacity or load test result is claimed here.

Source: `backend/app/inventory.py; backend/app/orders.py; backend/app/models.py`

## 03 — A different stack for each responsibility.

Stock Pilot combines several stacks with specific responsibilities. React and Type Script provide the interface. Fast A P I, SQL Alchemy and Alembic implement validated transactions and migrations. Postgres owns durable inventory. Redis and Celery handle asynchronous reports. Docker and Helm package the runtime, while GitHub Actions, Argo C D and Terraform define delivery and infrastructure.

Source: `frontend/package.json; backend/app; docker-compose.yml; helm; terraform; .github/workflows`

## 04 — Two paths: serve requests and refresh reports.

The browser reaches the A P I through a proxy or ingress, and the A P I reads and writes Postgres. Report requests and the scheduler enqueue work in Redis. Celery workers read the database and write timestamped reports into the cache. Workers and A P I replicas have separate responsibilities. Redis never owns authoritative stock.

Source: `backend/app/main.py; backend/app/tasks.py; backend/app/reporting.py; frontend/nginx.conf`

## 05 — Model the relationships before the screens.

Suppliers connect to products and purchase orders. Each balance belongs to one product and one warehouse. Database constraints require nonnegative stock and prevent reserved units from exceeding physical stock. Movements record receipts, issues and transfers. Reservations record commitments. Foreign keys preserve the meaning of inventory history when catalogue records are changed or removed.

Source: `backend/app/models.py; backend/app/catalog.py`

## 06 — A practical operations workspace.

Eight views organize the frontend: overview, inventory, movements, reservations, purchase orders, warehouses, suppliers and reports. Users can search products, export C S V data, manage catalogue records and perform stock workflows. Forms include validation and recoverable errors. Thirteen frontend tests exercise components and request payloads. This feature map is a diagram, not a browser screenshot.

Source: `frontend/src/App.tsx; frontend/src/styles.css; docs/evidence.md`

## 07 — A transfer is one transaction, not two edits.

In this illustrative transfer, twenty units move from Delhi to Bengaluru. Delhi falls from one hundred to eighty, while Bengaluru rises from forty to sixty. The total remains one hundred and forty. Both balances and the movement commit together. Available stock excludes reservations. An identical idempotent retry returns the existing movement instead of moving stock again.

Source: `backend/app/inventory.py: apply_movement, duplicate, lock_products`

## 08 — A reservation changes availability first.

Available stock equals on hand minus reserved. Releasing a reservation restores availability. Fulfilling creates the matching issue transaction. The same completion can be retried safely, while conflicting changes after closure are rejected. This preserves both physical stock and customer promises.

Source: `backend/app/inventory.py: reserve, finish_reservation; backend/app/models.py: Balance`

## 09 — Receiving closes the procurement loop.

Purchase orders move from draft to ordered to received. Lines must match the selected supplier. Receiving commits all receipt movements together, with deterministic keys preventing duplicate stock. Drafts are editable. Partial deliveries and invoice matching remain future work.

Source: `backend/app/orders.py; backend/app/schemas.py`

## 10 — Background work must not own the stock ledger.

The scheduler or report endpoint queues work in Redis. A Celery worker reads Postgres and caches a timestamped report for three minutes. The live dashboard uses its own database request, so report cache failures do not change authoritative inventory.

Source: `backend/app/tasks.py; backend/app/main.py; backend/app/reporting.py`

## 11 — Scale the API while protecting correctness.

Postgres row locks coordinate competing stock changes across replicas. Stable product ordering reduces deadlock risk, while request fingerprints protect retries. SQLite tests verify rules, not production locking. Concurrent Postgres tests and measured load tests are still required before capacity claims.

Source: `backend/app/inventory.py; backend/app/orders.py; helm/stockpilot`

## 12 — Turn a source change into a gated release.

The delivery workflow connects tests and security gates to image builds, scans and a temporary kind deployment. Commit S H A tags make releases traceable. Promotion updates Git only after its prerequisites pass. Hosted execution and registry publication require separate evidence.

Source: `.github/workflows; scripts; gitops`

## 13 — Kubernetes encodes operational expectations.

Kubernetes defines replicas, Services, Ingress, probes, storage and one migration job. Autoscaling, disruption budgets and resource limits express operational expectations. Readiness checks database access. A rendered chart validates configuration; actual rollout, persistence and scaling still need a running cluster.

Source: `helm/stockpilot/templates; kubernetes; backend/app/main.py`

## 14 — Security has both release and runtime boundaries.

Release checks cover source, dependencies, secrets, infrastructure and images. Runtime controls reduce privileges and restrict access. The product currently has no sign in or role based permissions, so demo write endpoints remain private. Scan results apply to their specific revision.

Source: `.github/workflows; security; backend/app/main.py; helm/stockpilot/templates`

## 15 — Observe requests, then explain failures.

Prometheus records request counts, errors and latency. Grafana panels and alerts organize those metrics, while structured logs support investigation. Argo C D reconciles the desired Helm release from Git. Live graphs and healthy synchronized status require real runtime evidence.

Source: `backend/app/main.py; monitoring; gitops`

## 16 — Cloud infrastructure is explicit and reviewable.

Terraform defines networking, E K S workers and storage. NAT is optional, with its tradeoffs documented. No cloud deployment is claimed without account access. Planning, applying, verification and teardown are separate milestones, and retained data requires deliberate cleanup decisions.

Source: `terraform; docs/operations-guide.md; docs/evidence.md`

## 17 — Evidence follows execution, not ambition.

The evidence register separates implementation from execution. Local tests and builds have captured results. Docker and Chromium are blocked in this environment, so this video shows architecture rather than a simulated live application. Hosted delivery and cloud deployment remain unclaimed.

Source: `docs/evidence.md; docs/presentation/verification.json; demo/README.md`

## 18 — A complete demo has a clear next action.

The live runbook starts with stock receiving, transfers, reservations and purchase orders, then demonstrates delivery, persistence, monitoring and GitOps. Capture each result only after execution. Thank you.

Source: `demo/RUNBOOK.md; docs/operations-guide.md`
