# twin-services

> The service-oriented digital twin: the same UR5, decomposed into four
> containerised services with versioned contracts — and a kill switch to
> prove the decomposition earns its keep. Second rung of the
> [`twin-*`](https://github.com/joshikeyur01?tab=repositories&q=twin-)
> portfolio.

![demo](docs/demo/twin-services.gif)

## What this is

`twin-hello` proved the loop; this repo proves the architecture. Four
services — **telemetry** (MQTT→InfluxDB), **state** (derived pose/RMS over
gRPC), **command** (REST→MQTT setpoints), **viz** (React + three.js viewer)
— share one `contracts/` package and degrade honestly when any one of them
is killed. Grafana shows the outage within one 2-second scrape; restart
recovers with no manual step. `just chaos` runs that as a scripted,
assertable demo.

Deliberately does **not** include: semantic models (`twin-aas`), anomaly
detection (`twin-anomaly`), more than one robot (`twin-fleet`), or
Kubernetes (nowhere, yet).

## Architecture (5-layer stack)

| Layer | Component |
|-------|-----------|
| L5 Application | Grafana · viz-svc (React + react-three-fiber) |
| L4 Services | telemetry-svc · state-svc · command-svc |
| L3 Information model | *(none — raw topics; added in `twin-aas`)* |
| L2 Transport | ROS 2 DDS ↔ MQTT bridge · gRPC (svc↔svc) |
| L1 Physical / simulated | UR5 in Gazebo Harmonic |

See [`docs/context/ARCHITECTURE.md`](docs/context/ARCHITECTURE.md) and the
ADRs in [`docs/adr/`](docs/adr/).

## Quick start

Prerequisites: Docker, Docker Compose, [`just`](https://github.com/casey/just),
[`uv`](https://docs.astral.sh/uv/). ROS 2 Jazzy + Gazebo only for the real sim.

```bash
just up          # build + start broker, InfluxDB, Prometheus, Grafana, 4 services
just healthz     # 8 green checks
just chaos       # kill each service in turn; assert graceful degradation
```

Move the arm without ROS (synthetic telemetry straight to the broker):

```bash
curl -X POST localhost:8003/command -H 'content-type: application/json' \
     -d '{"kind":"home"}'          # 202 + receipt; watch it on the wire
```

Then open <http://localhost:3000> (Grafana: status row + joint traces) and
<http://localhost:8004> (live 3D twin). With ROS 2 sourced: `just sim`,
`just bridge`, and the command above physically moves the Gazebo arm.

## Repo layout

```
contracts/            # THE source of truth: Pydantic models + proto + stubs
bridge/               # DDS↔MQTT plumbing (vendored from twin-hello + cmd path)
services/
  telemetry-svc/      # MQTT → validate → InfluxDB (replaces Telegraf)
  state-svc/          # window → forward kinematics → gRPC GetState/StreamState
  command-svc/        # POST /command → MQTT setpoint (fail, don't buffer)
  viz-svc/            # serves the viewer; StreamState → WebSocket
deploy/               # mosquitto, prometheus, grafana provisioning + dashboard
scripts/chaos.py      # the kill demo, scripted and assertable
sim/                  # Gazebo assets (shared work with twin-hello)
tests/integration/    # end-to-end against the compose stack
docs/context/         # vision, architecture, style, roadmap
docs/adr/             # decisions with evidence, not vibes
```

## What I learned

The honest list lives in [`WHAT_I_LEARNED.md`](WHAT_I_LEARNED.md) —
including the Grafana staleness trap, why `docker kill` doesn't trigger
restart policies, and what a latency benchmark said about the gRPC-vs-REST
choice (nothing — that's the finding).

## Licence

Apache-2.0 — see [`LICENSE`](LICENSE).
