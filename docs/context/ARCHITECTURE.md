# Architecture

## The 5-layer stack

Same vocabulary as every `twin-*` repo. This repo's contribution is a real
L4 — three backend services plus a non-Grafana L5 — while L3 stays
deliberately empty until `twin-aas`.

```
┌────────────────────────────────────────────────────────────────────┐
│ L5  Application         Grafana dashboards · viz-svc (React + r3f) │
├────────────────────────────────────────────────────────────────────┤
│ L4  Services            telemetry-svc · state-svc · command-svc    │
├────────────────────────────────────────────────────────────────────┤
│ L3  Information model   (none — raw topics; added in twin-aas)     │
├────────────────────────────────────────────────────────────────────┤
│ L2  Transport           ROS 2 DDS ─bridge─▶ MQTT · gRPC (svc↔svc)  │
├────────────────────────────────────────────────────────────────────┤
│ L1  Physical asset      UR5 in Gazebo Harmonic                     │
└────────────────────────────────────────────────────────────────────┘
```

## Service topology

```
                 browser
                ▲       ▲
      WebSocket │       │ HTTP (dashboards)
        ┌───────┴──┐  ┌─┴───────┐     ┌────────────┐
        │ viz-svc  │  │ Grafana │◀────│ Prometheus  │──scrapes /metrics──▶ all svcs
        └───────┬──┘  └─┬───────┘     └────────────┘
           gRPC │       │ Flux
        ┌───────▼──┐  ┌─▼────────┐
        │state-svc │  │ InfluxDB │
        └───────┬──┘  └─▲────────┘
           MQTT │       │ writes
                │  ┌────┴──────────┐        ┌─────────────┐
                └──│ telemetry-svc │        │ command-svc │◀── REST (curl / UI)
                   └────▲──────────┘        └──────┬──────┘
                        │ MQTT telemetry           │ MQTT setpoints
                   ┌────┴──────────────────────────▼──────┐
                   │            Mosquitto                 │
                   └────▲──────────────────────────┬──────┘
                        │ publish            cmd   │
                   ┌────┴──────────────────────────▼──────┐
                   │   DDS↔MQTT bridge (from twin-hello)  │
                   └────▲──────────────────────────┬──────┘
                        │ /joint_states       /cmd │
                   ┌────┴──────────────────────────▼──────┐
                   │        UR5 in Gazebo Harmonic        │
                   └──────────────────────────────────────┘
```

## Data flows

**Telemetry (the `twin-hello` path, now owned by code):**

1. Gazebo publishes `sensor_msgs/JointState` at 50 Hz; the bridge republishes
   to `twin/ur5/joint/<name>/<field>` exactly as in `twin-hello`.
2. `telemetry-svc` subscribes to `twin/ur5/#`, validates each payload against
   the `contracts` Pydantic models, and writes points to InfluxDB. It replaces
   Telegraf: config we rented becomes code we own, because L4 needs one place
   that *enforces* contracts rather than merely parsing.

**Derived state:**

3. `state-svc` subscribes to the same MQTT telemetry, maintains a rolling
   window, and computes end-effector pose (forward kinematics from the UR5
   DH parameters) and per-joint velocity RMS.
4. It exposes `GetState` (unary) and `StreamState` (server-streaming) over
   gRPC on :50051, defined in `contracts/proto/state.proto`.

**Command (the path `twin-hello` deliberately left open):**

5. A client `POST`s a typed command to `command-svc` (e.g. `MoveJoints`,
   `Home`). The body is a `contracts` Pydantic model.
6. `command-svc` publishes a setpoint to `twin/ur5/cmd/joints`; the bridge
   forwards it to the ROS 2 side; Gazebo moves the arm.

**Visualisation:**

7. `viz-svc` serves the React + react-three-fiber bundle and proxies
   `StreamState` into a WebSocket the browser can consume. The 3D arm pose in
   the browser is therefore downstream of the same gRPC contract as any other
   client — no private side channel.

**Observability:**

8. Prometheus scrapes `/metrics` from all four services; Grafana shows a
   service-status row (up/down per service) next to the joint traces from
   InfluxDB. This is what makes the kill-a-container demo visible.

## Contracts

`contracts/` is a top-level package, versioned with the repo, imported by
every service. Two dialects, one source of truth:

- **Pydantic v2 models** for everything crossing MQTT or REST.
- **protobuf** for everything crossing gRPC, with generated stubs checked in
  under `contracts/gen/` so services never depend on a working `protoc` at
  runtime.

Rule (CI-enforced): a service that declares a payload shape locally fails
review. If a service needs a new field, the field lands in `contracts/` first.

## Ports

| Component     | Port  | Protocol            |
| ------------- | ----- | ------------------- |
| Mosquitto     | 1883  | MQTT                |
| InfluxDB      | 8086  | HTTP                |
| Grafana       | 3000  | HTTP                |
| Prometheus    | 9090  | HTTP                |
| telemetry-svc | 8001  | HTTP (healthz/metrics) |
| state-svc     | 8002 / 50051 | HTTP / gRPC  |
| command-svc   | 8003  | HTTP (REST + healthz/metrics) |
| viz-svc       | 8004  | HTTP + WebSocket    |

## Design decisions (summaries — the ADRs argue them)

### gRPC between services, REST at the edge — [ADR-0002](../adr/0002-grpc-internal-rest-edge.md)

`state-svc` serves gRPC because its consumers are programs that want a typed
stream. `command-svc` serves REST because its consumers include humans with
`curl`. The ADR records the latency and tooling evidence, not just taste.

### Schema evolution — [ADR-0003](../adr/0003-schema-evolution.md)

Additive-only changes, envelope carries `schema_version`, protobuf field
numbers are never reused, and `contracts/` CHANGELOG entries are mandatory.
The test suite includes a "yesterday's producer, today's consumer" round-trip.

### Health-check design — [ADR-0004](../adr/0004-health-check-design.md)

`/healthz` reports liveness *and* readiness distinctly (a service that lost
its MQTT connection is alive but not ready). Prometheus `up` plus a
service-reported readiness gauge drive the Grafana status row. Degradation
policy per service: what each one does when a dependency it needs is gone.

## What this repo intentionally omits

- **mTLS between services.** Noted at each boundary where it would attach;
  implementing it adds nothing to the decomposition argument.
- **Service discovery.** Compose DNS names are hardcoded config. Real
  discovery pressure arrives with N robots in `twin-fleet`.
- **Backpressure / replay.** Fire-and-forget MQTT survives at one robot ×
  50 Hz. `twin-fleet`'s load test will find the ceiling on purpose.
- **A semantic layer.** `state-svc` computes *values*; it does not model
  *meaning*. That distinction is the entire point of `twin-aas`.
