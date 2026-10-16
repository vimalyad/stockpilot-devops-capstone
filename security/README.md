# Security gates and boundaries

The pipeline runs Bandit and Semgrep SAST, pip-audit and npm dependency audits, full-history Gitleaks, Trivy infrastructure checks, and blocking HIGH/CRITICAL scans for both runtime images. Image findings are not hidden with `--ignore-unfixed`. Scanners and cluster tools use pinned versions; release binaries are verified with committed SHA-256 checksums. Scan reports remain CI artifacts, including failures.

Images run as non-root with read-only root filesystems. Kubernetes drops Linux capabilities, disallows privilege escalation, uses RuntimeDefault seccomp and disables automatic service-account tokens. PostgreSQL and Redis accept traffic only from application components under NetworkPolicy-aware CNIs. kind's default networking does not enforce NetworkPolicy; use Calico/Cilium to verify isolation.

Database credentials are external environment/Secret values. The CI-only database password cannot access any external service. Do not put real secrets in `.env.example`, Helm values, screenshots or Git. Rotate any real credential exposed before removing it from history.

This project has no authentication/RBAC or tenant isolation. Keep the demonstration private. API validation and transactional integrity do not provide authorization. TLS must be configured through Ingress before Internet exposure. PostgreSQL/Redis are durable single instances, not highly available managed services.

No successful remote scan or container deployment is claimed until an actual CI run is recorded. Base images and vulnerability databases change; a clean scan is specific to its run and does not establish permanent safety.

The sole IaC exception is `AWS-0040`: EKS retains a public control-plane endpoint for operator access, restricted to the required single IPv4 `/32`; private access also remains enabled. This is not an Internet-wide API rule. Production should use a private operator path and disable public access. No CVE/image exceptions are configured.
