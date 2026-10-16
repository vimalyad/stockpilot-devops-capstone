# Observability

Install the Prometheus Operator before enabling chart monitoring. This setup creates real scrape targets, eight Grafana panels, and API availability/error/latency plus worker-availability alerts. Request metrics come from the API; pod/volume panels require kubelet and kube-state-metrics from kube-prometheus-stack. Low-traffic series may be empty until traffic is generated.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
kubectl create namespace monitoring
kubectl -n monitoring create secret generic grafana-admin --from-literal=admin-user=admin --from-literal=admin-password="$(openssl rand -hex 24)"
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring -f monitoring/kube-prometheus-stack-values.yaml
helm upgrade --install stockpilot helm/stockpilot -n stockpilot -f gitops/release.yaml --set monitoring.enabled=true
kubectl -n monitoring port-forward svc/monitoring-grafana 3001:80
kubectl -n monitoring port-forward svc/monitoring-kube-prometheus-prometheus 9090:9090
```

Retrieve the generated Grafana password locally using `kubectl get secret`; do not record it in screenshots. Generate requests with `python scripts/load-test.py --url http://localhost:3000/api/dashboard --requests 1000 --workers 8`. Read application JSON logs using `kubectl -n stockpilot logs deploy/backend`. Alertmanager has no outbound notification destination by default; add one before production operation.

This directory contains configuration, not evidence of a live monitoring deployment.
