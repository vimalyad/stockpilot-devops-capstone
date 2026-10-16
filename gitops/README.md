# GitOps promotion

The repository URL is the intended standalone repository; publication and a successful CI run must happen before this Application can sync. `development` is deliberately an unpromoted tag, not a claim that images exist.

1. Publish the repository, run CI and ensure both SHA-tagged GHCR packages are readable by the cluster (make packages public or configure `imagePullSecrets`).
2. Create the `stockpilot` namespace and `stockpilot-secrets` using `scripts/create-secret.sh`.
3. Install Argo CD using its documented installation procedure, then apply `gitops/project.yaml` and `gitops/application.yaml`.
4. The CI promotion job updates only `gitops/release.yaml` on main after tests, scans and kind deployment succeed. Git tracks exactly which commit is released.
5. Argo CD syncs configuration, then stateful services, a single migration Job, then application replicas. HPA owns replica counts, and Argo CD ignores that field.
6. Revert a promotion commit to roll back images. Database downgrades are a separate reviewed operation; image rollback cannot undo incompatible schema changes.

Do not commit credentials. Keep the write APIs private until authentication is implemented.
