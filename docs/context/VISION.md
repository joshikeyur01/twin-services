# Vision

## Why this repo exists

`twin-hello` proved the loop — asset → transport → observation — inside what
is honestly one process and a docker-compose file. That was the point. But
every serious twin architecture in the literature is service-oriented, and
the thesis argues *about* that decomposition. I can't argue about it credibly
until I've paid its costs myself: contract management, partial failure,
inter-service latency, four Dockerfiles where one used to do.

This repo takes the same UR5 twin and splits it into four containerised
services with explicit, versioned contracts between them:

- **`telemetry-svc`** — ingests MQTT, writes to InfluxDB (owns L2→storage).
- **`state-svc`** — computes derived state (end-effector pose, velocity RMS),
  exposes it over gRPC (the first real L4 inhabitant).
- **`command-svc`** — accepts REST commands, publishes MQTT setpoints
  (closes the command path `twin-hello` deliberately left open).
- **`viz-svc`** — serves a React + react-three-fiber viewer of the live twin
  (an L5 that isn't Grafana).

The one-sentence version: **`twin-hello` was a pipe; this is an architecture.**

## What "done" looks like

- `just up` starts the broker, InfluxDB, Grafana, and all four services; every
  service answers `/healthz` and exposes `/metrics`, and a Grafana
  service-status row shows four green cells.
- **Killing any single service degrades gracefully and Grafana shows it.**
  `docker kill` on any one container: the other three stay healthy, the
  dashboard's status row flips the dead cell red within one scrape interval,
  and the service recovers with no manual intervention on restart.
- A `curl` to `command-svc` moves the simulated arm; `state-svc` reports the
  changed end-effector pose over gRPC; `viz-svc` renders the motion live in
  the browser.
- No service defines its own payload shape. Every cross-service message —
  Pydantic for MQTT/REST, protobuf for gRPC — imports from the top-level
  `contracts/` package, and CI fails if a service declares a schema locally.
- Three ADRs exist and say something falsifiable: (a) gRPC vs REST between
  services, (b) schema-evolution strategy, (c) health-check design.

## What "done" does not look like

- Semantic information models (AAS, OPC-UA). That's `twin-aas`.
- Anomaly detection or any ML. That's `twin-anomaly`.
- More than one robot. That's `twin-fleet`.
- Kubernetes or a service mesh. Compose can demonstrate partial failure just
  fine; real orchestration pressure doesn't appear until `twin-fleet`.
- Auth beyond localhost. mTLS between services is noted where it would go,
  not implemented.

Four services is already the maximum honest scope for one robot. A fifth
service is feature creep wearing an architecture diagram.

## Audience

Same three people as `twin-hello`, in order:

1. **Me, six months from now**, forking this for `twin-anomaly` and
   `twin-fleet` — both extend this stack, so its seams must be clean.
2. **A thesis examiner** who wants evidence that "service-oriented digital
   twin" in the text maps to running, observably-degradable services.
3. **A recruiter or PI** who watches the kill-a-container demo GIF and
   understands graceful degradation in fifteen seconds.

If a change doesn't help at least one of those three, it doesn't ship.
