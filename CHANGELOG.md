# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Repo scaffold as a uv workspace: `contracts` + `bridge` + four services.
- `contracts/`: Pydantic models, topic helpers, `state.proto`, checked-in
  generated stubs, evolution tests including a proto field-number lock.
- telemetry-svc (MQTT→InfluxDB, replaces Telegraf), state-svc (rolling
  window + UR5 FK + gRPC), command-svc (REST→MQTT, fail-don't-buffer),
  viz-svc (React + react-three-fiber viewer over a StreamState WebSocket).
- Bridge vendored from twin-hello, extended with the cmd→ROS 2 path and
  rewired to the contracts wire format.
- Compose stack with per-service healthchecks; Prometheus + Grafana
  provisioning with a staleness-proof service-status row.
- `scripts/chaos.py`: scripted kill demo (passes for all four services).
- 48 unit tests + 3 stack integration tests; CI with contracts-freshness
  and no-local-schemas gates.
- ADRs 0001–0004 (decision records with measured evidence).
