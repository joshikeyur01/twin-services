# Style

Inherits from the `twin-*` portfolio-wide conventions in
[`twin-arch`](https://github.com/joshikeyur01/twin-arch/blob/main/docs/style.md)
and from `twin-hello`. Only deltas and specifics are documented here.

## Workspace

- One uv workspace, six members: `contracts`, `bridge`, four services. The
  root `pyproject.toml` owns tool config and dev deps; members own their
  runtime deps. `.python-version` pins 3.12 — do not rely on
  `requires-python` alone (uv will happily pick 3.14).
- A service's dependency list is an architecture statement: only
  telemetry-svc may depend on the Influx client, only state-svc on numpy,
  and viz-svc must have no MQTT dependency at all.

## Contracts

- Every payload crossing MQTT, REST, or gRPC imports from `contracts/`.
  A `BaseModel` subclass inside `services/` fails CI.
- Topic strings are built by `contracts` helpers, never by hand.
- Evolution rules are ADR-0003 and they are not suggestions.

## Python

- Target 3.12, `mypy --strict`, ruff with the shared select list.
- Pydantic v2 for JSON contracts; frozen slotted dataclasses for config.
- Async for I/O; each service is one process, one `asyncio.TaskGroup`,
  fail-fast (ADR-0004). Expected failures are handled inside tasks.
- Structured logging via structlog, JSON renderer, event names like
  `mqtt_disconnected` — greppable, not prose.

## gRPC

- Proto packages are versioned (`twin.state.v1`); breaking changes mean a
  new package alongside, never mutation.
- Servicer method names come from the proto; the `noqa: N802` pair in
  `grpc_server.py` is the only sanctioned one.
- Streams drop, never buffer. A lagging client is the client's problem.

## MQTT

- Topic scheme: `twin/<asset>/joint/<joint>/<field>` for telemetry,
  `twin/<asset>/cmd/joints` for commands.
- QoS 0 for telemetry (a lost sample is noise), QoS 1 for commands (a lost
  setpoint is a missing motion; setpoints are idempotent so at-least-once
  is safe).

## Metrics and health

- Prometheus metric names start `twin_`; every service exports
  `twin_service_ready{service=...}`.
- `/healthz/live` and `/healthz/ready` on every service, same JSON shape.
  Readiness lists every dependency by name.

## Frontend (viz-svc only)

- Strict TypeScript, React 18 + react-three-fiber. One scene, one robot,
  camera orbit; no state-management libraries, no routing.
- The WebSocket frame shape mirrors `viz_svc/stream.py:to_frame` — the
  Python function is the source of truth, say so in a comment when you
  mirror it.

## Tests

- pytest + pytest-asyncio auto mode. Unit tests import no broker, no
  database, no ROS. `slow` marks stack-dependent integration tests (they
  skip when the stack is down); `chaos` marks container-killing tests.
- Literal status codes and values in test asserts are fine (per-file
  PLR2004 ignore) — that is what tests are for.

## Commits and branches

- Conventional Commits. Scope is the member or service:
  `feat(state-svc): ...`, `fix(contracts): ...`, `chore(deploy): ...`.
- Schema changes: `contracts` commit first, adopters after (ADR-0003).
- Trunk-based; squash merges; tag `v0.x.y`.
