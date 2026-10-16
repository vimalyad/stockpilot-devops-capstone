# Verification register

Implemented configuration, successful execution and environment-dependent work are separate. Status applies to local checks on **16 October 2026**; relevant checks must be rerun after later changes.

| Check | Evidence/result | Scope |
|---|---|---|
| Backend tests | [pytest log](../evidence/pytest.txt), [JUnit XML](../evidence/pytest.xml): **40 passed, 1 skipped; 97% coverage** | Isolated SQLite. PostgreSQL concurrency case skipped. |
| Ruff | [Output](../evidence/ruff.txt): passed | Backend source/test lint. |
| Bandit | [JSON report](../evidence/bandit.json): **0 findings** | Source analysis; not a general security guarantee. |
| API surface | [OpenAPI JSON](../evidence/openapi.json): 29 operations | Generated from the application. |
| Migration and seed | Upgrade/downgrade/upgrade and seed idempotence tests passed; [seeded inventory](../evidence/seeded-inventory.json) | 8 products, 2 suppliers, 2 warehouses, 16 receipts, 931 units. |
| Frontend | 13 component tests, TypeScript checking and production build passed | jsdom/React Testing Library; JS 190.25 kB (57.87 kB gzip), CSS 32.94 kB (8.05 kB gzip). No browser interaction capture. |
| Helm/Compose | Helm lint/render and Compose configuration passed | No images built, containers started or Kubernetes release installed. |
| IaC security | [Platform evidence](../evidence/platform/): Trivy 0 unexcepted HIGH/CRITICAL findings across 14 configuration files | Two documented EKS demo exceptions in `security/README.md`; scan is specific to these rules and source. |
| Secret history | [Final history validation](../evidence/platform/final-history-validation.json): Gitleaks 0 leaks across 20 history commits before the evidence update | Source history checked after cleanup; audit commit checked separately. |
| Workflow | actionlint passed | No hosted run or registry publication claimed. |
| Terraform | Formatting and provider initialization passed | Validate blocked by sandbox IPC/socket denial; no plan/apply. |
| Presentation | [18-slide editable PowerPoint](presentation/StockPilot-Capstone.pptx), [PDF](presentation/StockPilot-Capstone.pdf) | Speaker notes and original explanatory diagrams. |
| Video | [Narrated walkthrough](../demo/README.md) | Synthetic English narration; not a live browser or deployment recording. |

## Observed environment restrictions

- Local socket creation returns a permission error, preventing HTTP/database service startup.
- Docker's daemon socket is unavailable; static configuration cannot prove runtime deployment.
- Chromium exits at startup with `sandbox_host_linux.cc` / `shutdown: Operation not permitted`, including a file-only rendering attempt. No live UI screenshot was produced.
- No AWS account access is available. Hosted GitHub Actions and GHCR execution remain separate milestones.

## Remaining acceptance evidence

1. Run PostgreSQL concurrency tests and capture their result.
2. Capture UI CRUD, transfers, reservations, order receiving and rejected invalid transitions.
3. Start Compose; verify actual workers/cache reporting and restart persistence.
4. Execute hosted security gates and record source SHA, run URL and image tags.
5. Deploy Helm; verify probes, replicas, storage, scaling and smoke tests.
6. Capture actual Grafana data and Argo CD reconciliation/Healthy/Synced state.
7. Record deliberate disposable-cluster failure/recovery exercises.
8. With authorized AWS access, plan, deploy, verify, capture and tear down.

The [live demo runbook](../demo/RUNBOOK.md) provides the sequence. The [screenshot index](../screenshots/README.md) distinguishes illustrative diagrams from runtime evidence.
