# Roadmap

Six phases, two weeks total. Same rule as `twin-hello`: if a phase slips more
than two days, cut scope inside the phase — do not push the next phase. The
kill-a-container demo is the deliverable; everything else is negotiable.

## Phase 0 · Scaffold (days 1–2)

- [ ] Repo skeleton, licence, `.gitignore`, pre-commit, CI (lint + mypy + tests).
- [ ] `pyproject.toml` as a `uv` workspace: `contracts/` + one member per
      Python service.
- [ ] `docker-compose.yml` starts Mosquitto, InfluxDB, Grafana, Prometheus;
      service entries are stubs that build and answer `/healthz` with a
      hardcoded response.
- [ ] `justfile` with `up`, `down`, `healthz`, `lint`, `test`.

**DoD:** `just up && just healthz` shows four green infra containers and four
green service stubs on a fresh clone.

## Phase 1 · Contracts (day 3)

- [ ] Pydantic v2 models: `JointTelemetry`, `JointCommand`, envelope with
      `schema_version`.
- [ ] `contracts/proto/state.proto`: `GetState`, `StreamState`, `TwinState`
      message; generated stubs checked in under `contracts/gen/`.
- [ ] Round-trip tests: Pydantic → JSON → Pydantic, proto → bytes → proto,
      plus one "yesterday's producer, today's consumer" compatibility test.
- [ ] ADR-0003 (schema evolution) written — the rules exist *before* the
      first consumer does.

**DoD:** `just test` green; deleting any model field breaks a test.

## Phase 2 · Telemetry path (days 4–5)

- [ ] `telemetry-svc`: aiomqtt subscriber on `twin/ur5/#`, validates against
      `contracts`, writes to InfluxDB; real `/healthz` (liveness + readiness)
      and `/metrics`.
- [ ] Telegraf removed from the stack; Grafana joint traces work as in
      `twin-hello`, now fed by our code.
- [ ] Integration test: in-process broker, publish synthetic telemetry,
      assert the InfluxDB write call.

**DoD:** `just sim` (reused `twin-hello` sim + bridge) → Grafana traces move,
Telegraf container gone.

## Phase 3 · State + command (days 6–8)

- [ ] `state-svc`: rolling window over MQTT telemetry, UR5 forward kinematics
      for end-effector pose, per-joint velocity RMS; `GetState` and
      `StreamState` served on :50051.
- [ ] `command-svc`: `POST /command` (typed via `contracts`), publishes to
      `twin/ur5/cmd/joints`; bridge extended to forward `cmd` topics to ROS 2.
- [ ] ADR-0002 (gRPC internal, REST at the edge) written with a measured
      latency comparison, not vibes.
- [ ] Unit tests for FK against known UR5 poses; integration test for the
      command round-trip.

**DoD:** `curl -X POST :8003/command -d '{"kind":"home"}'` moves the Gazebo
arm, and `grpcurl :50051 GetState` reports the new pose.

## Phase 4 · Viz (days 9–10)

- [ ] `viz-svc`: FastAPI serving the built React + react-three-fiber bundle;
      WebSocket endpoint proxying `StreamState`.
- [ ] Browser shows the UR5 as a 3D arm tracking the live sim; no polling,
      no InfluxDB reads.
- [ ] Frontend kept deliberately thin: one scene, one robot, no controls
      beyond camera orbit. Command UI is a stretch goal, not a promise.

**DoD:** Open `:8004`, move the arm via `curl`, watch the 3D model follow.

## Phase 5 · Chaos + observability (days 11–12)

- [ ] Prometheus scrapes all four services; Grafana status row (four cells)
      provisioned from JSON next to the joint traces.
- [ ] ADR-0004 (health-check design) written: liveness vs readiness, and each
      service's documented degradation policy.
- [ ] The demo: `docker kill` each service in turn; assert the other three
      stay ready, the status cell goes red, and restart recovers with no
      manual step. Scripted as `just chaos`, recorded as the README GIF.
- [ ] `WHAT_I_LEARNED.md` filled in.

**DoD:** Fresh clone → `just up && just sim && just chaos` reproduces the
GIF: four kills, four graceful degradations, four recoveries.

## Explicit non-goals for this repo

- Semantic/information models (AAS, OPC-UA). Belongs in `twin-aas`.
- Anomaly detection, ML, notebooks. Belongs in `twin-anomaly`.
- More than one robot, load testing, namespacing. Belongs in `twin-fleet`.
- Kubernetes, mesh, mTLS, service discovery. Earliest honest home is
  `twin-fleet`, and maybe not even there.
