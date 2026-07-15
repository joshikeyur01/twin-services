# 4. Health checks: liveness vs readiness, and honest degradation

Date: 2026-07-17
Status: Accepted

## Context

The repo's success criterion is observable graceful degradation: kill any
one service and Grafana shows it, the rest survive, restart recovers. That
requires health reporting that can distinguish "process dead" from "process
alive but a dependency is gone" — twin-hello's single `/healthz` returning
`{"status": "ok"}` cannot.

## Decision

1. **Two endpoints per service.** `/healthz/live` answers 200 whenever the
   process serves HTTP. `/healthz/ready` answers 200 only when every
   dependency check passes, else 503 with per-dependency detail:
   `{"status": "degraded", "checks": {"mqtt": true, "influxdb": false}}`.
2. **Readiness is service-specific by nature**, so the health module is
   deliberately duplicated per service (≈50 lines) rather than shared:
   telemetry-svc checks MQTT + InfluxDB, state-svc checks MQTT, command-svc
   checks MQTT, viz-svc checks its gRPC channel to state-svc.
3. **Prometheus scrapes everything every 2 s** — the scrape interval is the
   demo's reaction time. Each service exports `twin_service_ready{service=}`
   refreshed on scrape. The Grafana status cell computes
   `min(up) * (min(twin_service_ready) or vector(1))`: `up` catches a dead
   container, the gauge catches alive-but-degraded, and the `or vector(1)`
   guard matters because a dead target's gauge goes *stale* (empty) — a bare
   product would go empty too and `lastNotNull` would resurrect the pre-death
   READY. Found live; the fix is load-bearing.
4. **Degradation policy is explicit per service.**
   - telemetry-svc / state-svc: flip readiness, retry forever (2 s), keep
     serving what they can. state-svc keeps answering `GetState` with the
     last known state while degraded — stale data is labelled by readiness,
     not hidden.
   - command-svc: **fail, don't buffer.** Broker down → `POST /command` is
     503. An accepted command that silently goes nowhere would be a lie.
   - viz-svc: closes WebSockets (1011) when the stream dies; the frontend
     owns reconnection and shows its status pill. gRPC reconnect backoff is
     capped (1 s initial / 3 s max) because the default grows toward two
     minutes, which reads as "stuck" next to a 2 s scrape interval.
5. **Crash policy: fail fast.** Every service runs its tasks in one
   `asyncio.TaskGroup`; an unexpected task death cancels the rest and exits
   nonzero, delegating recovery to the container restart policy. Expected
   failures (broker loss) are handled inside the task and never kill it.
6. **`docker kill` does not trigger `restart: unless-stopped`** — Docker
   treats CLI kills as manual stops. The chaos script therefore owns the
   restart step (`scripts/chaos.py`), mirroring what a real orchestrator
   would do. Discovered live; documented so nobody "fixes" the compose file
   chasing an auto-restart that cannot happen.

## Consequences

Positive:
- The kill demo is scripted and repeatable (`just chaos`), and passed for
  all four services including the expected state→viz cascade.
- Compose healthchecks, `just healthz`, Prometheus, and Grafana all consume
  the same readiness truth.

Negative:
- Four near-identical health modules to keep in sync by hand. Accepted: the
  divergence risk is lower than the coupling cost of a shared internal
  library at this scale (revisit in `twin-fleet`).
- A shared gauge name across services collides when several are imported
  into one process; only tests do this, guarded in `_service_ready_gauge()`.

## Alternatives considered

- **Single `/healthz` (twin-hello style):** rejected — cannot express
  alive-but-degraded, which is the entire demo.
- **Shared health library (sixth workspace member):** rejected for now —
  readiness logic is the part that differs; the shared part is ~20 lines.
- **Pushgateway / self-reported liveness:** rejected — Prometheus `up` from
  a failed scrape is the most honest death signal available.

## Dependency notes

- `prometheus-client` (all four services) — the `/metrics` endpoint and
  `twin_service_ready` gauge above.
- Prometheus (container, `prom/prometheus:v2.54.1`) — scraping; Grafana
  alone cannot scrape Prometheus-format endpoints.
