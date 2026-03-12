# Observability — Morocco Spatial Dashboard

Logging, health checks, metrics, and optional monitoring.

## Logging

The backend uses Python `logging`. The log level is controlled by the `LOG_LEVEL` environment variable (see [.env.example](../.env.example) and [DEPLOYMENT.md](DEPLOYMENT.md)). Set it to `debug` for verbose output during development; use `info` or `warning` in production.

Structured logs (e.g. JSON) and shipping to a log aggregator (Loki, Elasticsearch, etc.) can be added later by configuring the logging handler in the application or in the deployment environment.

## Health endpoints

The API exposes:

- **GET /health** — Liveness: returns 200 and `{"status": "ok"}`. Use for orchestrators (Docker, Kubernetes) to check that the process is running.
- **GET /ready** — Readiness: returns 200 if the application can connect to the database, 503 otherwise. Use to avoid sending traffic to the backend before it is ready.

Configure your load balancer or ingress to use `/ready` for readiness probes and `/health` for liveness.

## Metrics (Prometheus)

The backend exposes Prometheus metrics at **GET /metrics**. Scrape this endpoint for dashboards and alerting.

- **URL:** `http://<backend-host>:8000/metrics`
- **Format:** Prometheus text exposition format (e.g. `# TYPE http_requests_total counter`).

Example Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: morocco-dashboard-backend
    static_configs:
      - targets: ["backend:8000"]
    metrics_path: /metrics
```

Use Grafana or another tool to build dashboards from these metrics.

## Future

- **Distributed tracing:** Optional OpenTelemetry (or similar) for request traces across services.
- **Alerting:** Define Prometheus alerting rules (e.g. high error rate, readiness failures) and route them to your notification channel (Slack, PagerDuty, etc.).
