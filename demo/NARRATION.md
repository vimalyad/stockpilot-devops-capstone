# StockPilot narration

Synthetic English voice; original explanatory diagrams. This is not a live browser or cloud recording.

## 01 — Inventory, engineered for operations.

Welcome to StockPilot, a multi warehouse inventory and procurement platform, built as an original DevOps capstone. The product follows a physical item from a supplier purchase through receiving, reservation, transfer and fulfilment. Around that product is a delivery platform using containers, Kubernetes, automated security gates, monitoring and infrastructure as code. This presentation explains the implemented design and the available verification. The diagrams are original illustrations, not screenshots of a live cluster. The audio is synthetic English narration.

Source: `README.md; backend/app/models.py; docs/DELIVERY.md`

## 02 — One stock count. Many competing decisions.

Inventory management is a demanding domain because several workflows compete for the same stock. A sales reservation promises units to a customer. A transfer moves those units between warehouses. A purchase order brings more units into the business. A simple counter is not enough. StockPilot keeps the available quantity separate from the physical quantity, makes transfers atomic, and records stock movement history. The architecture is designed to support multiple replicas, but no production capacity or load test result is claimed here.

Source: `backend/app/inventory.py; backend/app/orders.py; backend/app/models.py`

## 03 — A different stack for each responsibility.

The platform deliberately uses several technology stacks with clear responsibilities. React and TypeScript provide the operational interface. FastAPI, SQLAlchemy and Alembic handle validated requests, database access and schema evolution. PostgreSQL owns durable inventory records. Redis and Celery support background report generation, rather than owning authoritative stock. Docker and Helm package the runtime. GitHub Actions defines delivery gates, Argo CD reconciles desired state, and Terraform describes the cloud infrastructure. Each technology serves an identifiable part of the workflow.

Source: `frontend/package.json; backend/app; docker-compose.yml; helm; terraform; .github/workflows`

## 04 — Two paths: serve requests and refresh reports.

The request path starts in the browser and reaches the FastAPI service through the frontend proxy or ingress. The API reads and writes PostgreSQL. Reporting is a separate path. A request or the Celery beat scheduler queues report generation through Redis. A worker reads the authoritative database and caches a report with a timestamp and expiry. This separation allows report workers and API replicas to scale independently. If the report cache is unavailable, the report endpoint reports that failure while the live dashboard still reads the database.

Source: `backend/app/main.py; backend/app/tasks.py; backend/app/reporting.py; frontend/nginx.conf`

## 05 — Model the relationships before the screens.

The core model connects suppliers, products and warehouses. A balance belongs to one product and one warehouse, with a unique constraint on that pair. Database checks require nonnegative stock and prevent the reserved count from exceeding the on hand count. Movements record receipts, issues and transfers. Reservations record customer commitments. Purchase orders contain supplier-linked lines and a controlled lifecycle. Foreign keys preserve important relationships, so deleting a catalogue record cannot silently erase the meaning of historical stock records.

Source: `backend/app/models.py; backend/app/catalog.py`

## 06 — A practical operations workspace.

The frontend organizes the application around operational tasks. The overview explains stock value, warehouse distribution and low stock. The catalogue connects products to suppliers and reorder thresholds. Inventory and movement screens handle receiving, issuing and transferring units. Reservation controls separate a customer promise from fulfilment. Procurement connects supplier selection to purchase order lines and receiving. Forms expose validation and recoverable error states. This slide is a source-based feature map, not a browser screenshot; the environment's browser restriction is documented in the evidence register.

Source: `frontend/src/App.tsx; frontend/src/styles.css; docs/evidence.md`

## 07 — A transfer is one transaction, not two edits.

Consider an illustrative transfer of twenty keyboards. Delhi begins with one hundred units, ten already reserved. Bengaluru begins with forty. After the transfer, Delhi holds eighty and Bengaluru sixty. The combined total is unchanged. The API locks the relevant product, checks available stock, updates both balances and appends the movement before committing. A repeated request with the same idempotency key returns the existing movement. Reusing the key for different data produces a conflict. This protects normal client retries from duplicating stock changes.

Source: `backend/app/inventory.py: apply_movement, duplicate, lock_products`

## 08 — A reservation changes availability first.

Reservations change what can be promised without immediately changing what is physically present. Available stock is the on hand count minus the reserved count. Releasing an active reservation returns those units to availability. Fulfilling it reduces the reserved count and creates a corresponding issue movement in the same transaction. Repeating the same completion action returns the existing final state. Attempting a different action after closure returns a conflict. These rules are more important than a screen that merely lets a user edit a stock number.

Source: `backend/app/inventory.py: reserve, finish_reservation; backend/app/models.py: Balance`

## 09 — Receiving closes the procurement loop.

A purchase order begins as a draft containing a supplier, destination warehouse and product lines. Every line must belong to the selected supplier. Drafts can be edited before they are ordered. Receiving is allowed only after ordering, and it creates the receipt movements for all lines in one database transaction. Deterministic receipt keys prevent double counting if the same receive operation is retried. The current implementation receives whole orders. Partial deliveries, invoice matching and multi currency accounting are useful extensions rather than claimed features.

Source: `backend/app/orders.py; backend/app/schemas.py`

## 10 — Background work must not own the stock ledger.

Background reporting adds a separate Python worker stack to the application. The report endpoint queues a task, and the scheduler can request refreshes every sixty seconds. A worker reads a database snapshot and stores the result in Redis for one hundred and eighty seconds, including its generation time. This makes staleness visible and keeps the cache disposable. Redis is not the source of inventory truth. A worker or cache outage is reported explicitly. The live dashboard follows its own database-backed path. Service execution evidence is tracked separately from the implementation.

Source: `backend/app/tasks.py; backend/app/main.py; backend/app/reporting.py`

## 11 — Scale the API while protecting correctness.

The design supports scaling without placing shared stock state in an application process. PostgreSQL row locks coordinate updates across replicas. Product locks are acquired in a stable order, reducing the risk of deadlocks when an order contains several products. Idempotency keys and request fingerprints protect retries. Frontend, API and worker workloads have distinct scaling responsibilities. There is an important verification boundary: SQLite-based tests do not validate PostgreSQL row locking. Concurrent PostgreSQL tests, load tests and failure recovery exercises are still needed before claiming a measured production scale.

Source: `backend/app/inventory.py; backend/app/orders.py; helm/stockpilot`

## 12 — Turn a source change into a gated release.

The delivery workflow links source validation to deployment. It defines backend checks, a frontend build, source and dependency security gates, container image builds and vulnerability scanning. A temporary kind cluster provides a place to install the Helm chart and smoke test it. Promotion updates the desired image revision only after its prerequisites succeed. Commit SHA image tags connect a release to a specific source version. These are implementation details in the workflow. A successful hosted run, published image and deployment must each be demonstrated separately before they are reported as verified.

Source: `.github/workflows; scripts; gitops`

## 13 — Kubernetes encodes operational expectations.

The Helm chart expresses more than how to start a container. Deployments and services connect the frontend and API. Probes separate startup, process health and database readiness. Resource requests, limits, autoscaling and disruption budgets describe operational expectations. PostgreSQL uses persistent storage, while a migration job prepares the schema before the application rollout. Runtime security settings reduce container privileges. These controls are designed in configuration. Actual rollout behaviour, storage persistence, scaling and failover need a Kubernetes environment and captured execution evidence.

Source: `helm/stockpilot/templates; kubernetes; backend/app/main.py`

## 14 — Security has both release and runtime boundaries.

Security operates before release and during execution. The repository defines checks for source code, dependencies, secrets, container images and infrastructure. Runtime controls reduce privileges and make credentials and network boundaries explicit. These measures do not add user authentication by themselves. The current application has no sign in or role based permissions, so write APIs should remain private in a demo environment. A passing scan also applies to one source revision and vulnerability database. It should never be translated into a blanket claim that the platform is secure.

Source: `.github/workflows; security; backend/app/main.py; helm/stockpilot/templates`

## 15 — Observe requests, then explain failures.

The API exports Prometheus counters and request duration histograms, with method, route and status labels. Structured request logs include the elapsed time. The repository also contains monitoring configuration that connects metrics to dashboards and alerts. GitOps addresses a different concern: Argo CD compares the cluster with the desired Helm configuration in Git and reconciles drift. Monitoring explains what the system is doing, while GitOps manages what it should be running. Live graphs and a healthy synchronized application status require their own runtime evidence.

Source: `backend/app/main.py; monitoring; gitops`

## 16 — Cloud infrastructure is explicit and reviewable.

Terraform describes a possible AWS deployment with a virtual private cloud, public and private subnets, EKS workers and storage integration. Network access, node sizing and NAT choices should be reviewed before applying it. The user does not currently have AWS access, and this session does not claim a cloud deployment. Infrastructure definitions, a successful plan, an apply and a verified running application are different milestones. A complete cloud demonstration also includes teardown, so the presenter should capture the result and then remove resources that are no longer needed.

Source: `terraform; docs/operations-guide.md; docs/evidence.md`

## 17 — Evidence follows execution, not ambition.

This register separates implementation from execution. The application code and delivery configuration are present. The evidence guide records the exact local checks that completed, with their scope and logs. Local container deployment is blocked because the Docker socket is unavailable. Chromium startup is also denied by the current sandbox, so this recording uses explanatory slides rather than pretending to show a browser walkthrough. Hosted continuous integration, registry publication and AWS deployment are not claimed without successful execution. This boundary makes the submission reviewable and honest.

Source: `docs/evidence.md; docs/presentation/verification.json; demo/README.md`

## 18 — A complete demo has a clear next action.

For the live presentation, start with the dashboard and catalogue. Receive stock, transfer it, reserve units, then demonstrate release and fulfilment. Create a purchase order and receive it to close the procurement loop. Next, show the checks, container deployment, persistent data, monitoring and GitOps evidence. The remaining environment-dependent captures are listed in the runbook. Chhavi Ahlawat's OpsPulse repository informed the organization of evidence and presentation material; the StockPilot domain, implementation and diagrams are original. Thank you for exploring how product rules and delivery engineering work together.

Source: `demo/RUNBOOK.md; docs/operations-guide.md; https://github.com/Chhavi07-arch/OpsPulse-devops-platform`
