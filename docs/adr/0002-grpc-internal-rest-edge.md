# 2. gRPC between services, REST at the edge

Date: 2026-07-17
Status: Accepted

## Context

Decomposing the twin creates two kinds of interface. state-svc serves derived
state to other *programs* (viz-svc today, anomaly-svc in `twin-anomaly`) that
want a continuous typed stream. command-svc serves *anyone* — including a
human with `curl` — who wants to poke the robot once.

Candidates per interface: REST+JSON, gRPC+protobuf, MQTT request/response,
WebSocket+JSON.

## Decision

- **state-svc speaks gRPC** (`GetState` unary, `StreamState` server-streaming),
  defined in `contracts/proto/state.proto`.
- **command-svc speaks REST** (`POST /command`), typed by the contracts
  Pydantic models.
- Nothing else grows an inter-service API without a new ADR.

## Measured, not vibes

On the running stack (same host, same uvicorn machinery for the REST side,
300 calls after warmup):

| Interface                        | p50     | p95     |
| -------------------------------- | ------- | ------- |
| gRPC `GetState` (typed TwinState)| 1.38 ms | 2.30 ms |
| REST GET returning JSON          | 1.88 ms | 2.88 ms |

Latency is a wash at this scale (~0.5 ms). **Latency is therefore not the
argument for gRPC here, and this ADR does not claim it is.** The argument is:

1. **Server-streaming with typed messages.** `StreamState` gives every
   consumer the same decimated, drop-don't-buffer stream with generated
   client code. A REST equivalent is polling or hand-rolled SSE/WebSocket
   with hand-rolled parsing.
2. **The contract is compiler-checked on both sides** — protobuf field
   numbers + generated stubs, versus JSON discipline enforced only by tests.
3. Conversely at the edge: gRPC's tooling burden (`grpcurl`, generated
   clients) is wrong for a surface whose DoD is literally a `curl` one-liner.
   A human-facing 202/422/503 REST contract is the boring correct choice.

## Consequences

Positive:
- viz-svc's browser feed is a thin proxy over the same gRPC contract as any
  other client — no private side channel.
- `twin-anomaly`'s scoring service can consume `StreamState` with zero new
  interface work.

Negative:
- Two interface styles to document and test instead of one.
- Generated stubs must be kept fresh (mitigated: `just gen` + CI staleness
  gate, see ADR-0003).
- gRPC's reconnect backoff needed explicit capping for honest fast recovery
  (see ADR-0004).

## Alternatives considered

- **REST everywhere:** rejected — polling for 50 Hz state is wasteful and
  the typed-stream benefit is exactly where the thesis argument lives.
- **gRPC everywhere:** rejected — hostile to the curl-a-command DoD and to
  casual inspection of the command path.
- **MQTT request/response for commands:** rejected — a queue in front of a
  robot command hides failures; a synchronous 503 is honest (ADR-0004).

## Dependency notes

New runtime dependencies introduced by this decomposition, recorded here per
AGENTS.md rule:

- `grpcio` + `protobuf` (via `contracts`) — the gRPC interface above.
- `numpy` (state-svc) — forward kinematics.
- `influxdb-client[async]` (telemetry-svc) — replaces Telegraf so that L4
  code, not rented config, enforces the contract on the persistence path.
- `prometheus-client` (all services) — see ADR-0004.
- `aiomqtt`, `fastapi`, `uvicorn`, `structlog` — inherited from twin-hello.
