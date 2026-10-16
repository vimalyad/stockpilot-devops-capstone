# Live demonstration runbook

Use an isolated demo environment. The application has no authentication or role-based authorization; keep write endpoints private. Seed data is illustrative, not real commercial inventory.

## Product walkthrough — approximately 6 minutes

1. Start the Compose stack from the root and open `http://localhost:3000`. Show the eight navigation views and the distinction between physical, reserved and available stock.
2. Search the product catalogue for `KB-104`. Explain its supplier, reorder point and the balances across Delhi and Bengaluru. Create and update a disposable product, then remove it before recording stock history.
3. Receive five units in Delhi with a descriptive reference. Verify the balance and newest movement. Transfer three units to Bengaluru and show the combined total remains unchanged.
4. Reserve two units in Delhi. Show that availability falls while on-hand stock is unchanged. Release the reservation; then create a second reservation and fulfil it. Verify the generated issue movement.
5. Demonstrate a rejected request that exceeds available stock. Explain the HTTP 409 response and show the count is unchanged.
6. Create a purchase order using a supplier's product, edit the draft, place the order and receive it. Show the updated stock and receipt reference. Explain whole-order receiving and the prevention of duplicate receiving.
7. Open Reports, request background generation, then retrieve the cached result. Explain its timestamp, expiry and the separate live database snapshot.
8. Resize the browser to show the responsive layout and export catalogue data to CSV.

## Delivery walkthrough — approximately 6 minutes

1. Show the repository map, meaningful Git history, test report, coverage and production frontend build output.
2. Show a real successful hosted workflow only after it has run. Explain source, dependency, secret, infrastructure and image gates; identify the commit SHA image tags.
3. Build and start Compose. Show all service health, the one-shot migration, worker and scheduler. Restart the stack without deleting volumes, then verify the earlier stock records remain.
4. Install the Helm release in a local cluster. Show API/frontend/worker replicas, readiness and liveness probes, Services, the database PVC and autoscaler configuration. Run `helm test`.
5. Show real Prometheus targets and a Grafana dashboard populated by requests. Trigger only the documented disposable-cluster troubleshooting exercises and verify recovery.
6. Show the Argo CD Application's actual revision, Healthy and Synced status. Make one authorized Git-tracked change and capture reconciliation.
7. Review Terraform. Run a real plan only with working AWS credentials. Any apply requires an authorized account and conscious cost review. Capture the result and perform the documented teardown.

## Recording and evidence

- Record the application browser and a separate clean demonstration terminal. Keep tokens, credentials and unrelated personal data outside the recording.
- Capture screenshots only after the operation actually succeeds; name each file with its scenario and record the environment and source revision in `screenshots/README.md`.
- Use the existing narrated architecture recording as a technical introduction; replace or supplement its limitation chapter when runtime evidence exists.
- The current repository does not claim Docker, Kubernetes, GitOps, hosted CI or AWS execution in this restricted session.
