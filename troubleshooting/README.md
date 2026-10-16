# Seven deliberate operational failures

Use only an isolated lab and one experiment at a time. Suspend Argo CD auto-sync temporarily or it will correctly repair the fault before investigation. Each scenario below is an exercise definition, not a claim that it was executed.

```bash
export ALLOW_FAULTS=stockpilot
bash troubleshooting/challenge.sh image
kubectl -n stockpilot get pods
kubectl -n stockpilot describe pod <affected-pod>
kubectl -n stockpilot get events --sort-by=.metadata.creationTimestamp
kubectl -n stockpilot logs <affected-pod> --all-containers --previous
```

| Fault | Observable symptom | Investigation and root cause | Repair and verification |
|---|---|---|---|
| `image` | New replica remains ImagePullBackOff; old replicas may keep serving | Describe pod; registry cannot resolve deliberately missing tag | `kubectl -n stockpilot rollout undo deploy/backend`; wait for rollout and GET `/ready` |
| `selector` | Frontend API receives 502/504; API pods are healthy | Inspect Service selectors and EndpointSlices; selector says `backned` | Patch component selector to `backend`; verify endpoints return and API responds |
| `readiness` | New replica is Running but not Ready | Describe pod probe events; `/missing-health` returns404 | Roll back deployment; verify ready count and `/ready` |
| `memory` | New API replica OOMKilled or restarts | `describe pod`, previous logs and metrics;8Mi limit cannot fit Python process | Roll back deployment; verify restart count stabilizes |
| `cpu` | New replica remains Pending | Events say insufficient CPU; request100cores exceeds node capacity | Roll back deployment; confirm scheduling and availability |
| `database` | Init waits for schema, or API readiness503; rollout stalls | Inspect init container logs and Secret/env configuration; explicit env shadows correct Secret | `kubectl -n stockpilot set env deploy/backend DATABASE_URL-`; wait rollout and readiness |
| `ingress` | `/api` produces503 despite healthy pods and Service | Describe Ingress, then controller logs; backend Service name is misspelled | Patch first backend name to `backend`; curl host route again |

Service repair:

```bash
kubectl -n stockpilot patch svc/backend -p '{"spec":{"selector":{"app.kubernetes.io/component":"backend"}}}'
```

Ingress repair:

```bash
kubectl -n stockpilot patch ingress/stockpilot --type=json -p '[{"op":"replace","path":"/spec/rules/0/http/paths/0/backend/service/name","value":"backend"}]'
```

For rollout-based repairs, run `kubectl -n stockpilot rollout undo deployment/backend` immediately after the selected experiment, then `kubectl -n stockpilot rollout status deployment/backend`. A rollout undo requires the prior ReplicaSet history. Re-enable Argo CD reconciliation after recovery and verify Synced/Healthy.

Scaling exercise: install metrics-server, run `scripts/load-test.py`, and watch `kubectl -n stockpilot get hpa -w`. CPU HPA reacts to measured utilization, so the load must be sufficient and sustained. Capture actual scale-up and cooldown; an HPA manifest alone is not scaling evidence. Data durability exercise: create a product, restart the PostgreSQL pod while retaining its PVC, then verify the product survives. PostgreSQL is single-instance and will have a brief outage during this experiment.
