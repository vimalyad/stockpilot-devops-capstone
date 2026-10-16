# Local platform validation — 16 October 2026

`validation-summary.json` records commands and their real exit codes. Helm lint/render, Actionlint, Docker Compose configuration, Terraform formatting/cached initialization, shell syntax, Gitleaks and Trivy configuration checks passed. The chart renders 24 resources including monitoring; `manifest-security-audit.json` verifies non-root, read-only, privilege restrictions and bounded resources for application/stateful/migration/test workloads.

Terraform provider validation failed because this session cannot establish the provider IPC connection; the actual output is preserved. This is not a successful Terraform validation, plan or AWS deployment.

Trivy used its embedded configuration rules because checks could not be downloaded in the restricted session. The result has no unexcepted HIGH/CRITICAL findings, with two documented demo exceptions: restricted public EKS API (`AWS-0040`) and NAT-free public worker addressing (`AWS-0164`). No image vulnerability scan was run locally. Gitleaks inspected 12 commits at the time of this capture and found no secrets.

These are static checks. Docker builds/running containers, kind/EKS deployment, live monitoring, GitOps reconciliation, remote CI and GHCR publication remain unverified. CI contains the runtime checks for execution after publication.
