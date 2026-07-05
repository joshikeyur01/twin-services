# Project context & conventions

Read this before touching code. It sets the architecture, conventions, and
guardrails for any work in this repository.

## Mission

The service-oriented digital twin: the `twin-hello` UR5 twin decomposed into
four containerised services (`telemetry-svc`, `state-svc`, `command-svc`,
`viz-svc`) with shared, versioned contracts.

Success criterion: `docker kill` on any single service degrades gracefully —
the other three stay ready, Grafana's status row shows the outage, restart
recovers without manual steps. Captured as the README GIF via `just chaos`.

## Stack

Python 3.12 · ROS 2 Jazzy · Gazebo Harmonic · Mosquitto (MQTT) · InfluxDB 2 ·
Grafana · Prometheus · gRPC/protobuf · React + react-three-fiber ·
Docker Compose · `uv` (workspace) · `just`.

## Non-negotiable conventions

- Type hints everywhere; `mypy --strict` passes.
- **Contracts-first:** every cross-service payload imports from `contracts/`
  — Pydantic v2 for MQTT/REST, protobuf for gRPC. A service that declares a
  payload shape locally is a bug, even if it works.
- Protobuf stubs are generated into `contracts/gen/` and checked in; never
  hand-edit generated code.
- Every service has its own Dockerfile and exposes `/healthz` (liveness and
  readiness, distinctly) and `/metrics` (Prometheus format).
- `ruff` for lint and format; no `# noqa` without a justification comment.
- Tests colocated: `pytest` + `pytest-asyncio`; each service has at least one
  integration test.
- Conventional Commits: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`.
- No new runtime dependency without a note in `docs/adr/`.

## Architecture rules

Follow the 5-layer stack in [`docs/context/ARCHITECTURE.md`](docs/context/ARCHITECTURE.md).
Service responsibilities are exclusive — do **not** cross them:

- `telemetry-svc` ingests and persists. It does not compute derived state.
- `state-svc` computes and serves state. It does not persist anything.
- `command-svc` accepts and publishes commands. It does not read state; a
  command needing current state is a client-side composition, not a new
  coupling.
- `viz-svc` consumes `state-svc`'s gRPC stream only. The browser never
  touches MQTT or InfluxDB.
- Grafana queries InfluxDB and Prometheus. It does not talk to MQTT or to
  services directly.
- The DDS↔MQTT bridge stays dumb L2 plumbing — no validation logic beyond
  what `twin-hello` shipped, no business rules.

If a change would blur these boundaries, propose an ADR instead of writing
the code.

## When you touch code

1. Read the relevant ADRs in `docs/adr/` — especially 0002 (gRPC/REST),
   0003 (schema evolution), 0004 (health checks).
2. Schema changes land in `contracts/` first (with a CHANGELOG entry and
   regenerated stubs), then in services — never the reverse, and never in the
   same commit as service logic.
3. Update tests in the same commit as the code.
4. If you add a public interface (MQTT topic, HTTP route, gRPC method,
   config key), document it in `docs/`.
5. Prefer editing existing files over creating new ones.
6. Keep functions under ~40 lines and modules under ~200 lines. If they grow,
   split by responsibility, not by file size.

## What to refuse

- A fifth service. Whatever it is, it belongs in an existing service or a
  later repo.
- Kubernetes, service mesh, mTLS, service discovery. Earliest honest home is
  `twin-fleet`.
- ML models or anomaly detection. Belongs in `twin-anomaly`.
- AAS, OPC-UA, or any semantic modelling. Belongs in `twin-aas`.
- Message brokers other than Mosquitto, databases other than InfluxDB.
- Frontend scope growth in `viz-svc` (state management libraries, routing,
  design systems). One scene, one robot, camera orbit.

This repo demonstrates decomposition, not scale. Keep it four services.
