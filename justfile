# twin-services task runner. `just` for a listing.

set shell := ["bash", "-euo", "pipefail", "-c"]

# ─── setup ─────────────────────────────────────────────────────────────────

# Install dev dependencies for the whole workspace with uv.
install:
    uv sync --all-groups --all-packages
    # iCloud's fileproviderd asynchronously sets the macOS hidden flag on
    # dot-dirs; Python >= 3.12 skips hidden .pth files, silently breaking
    # editable installs (setuptools#4595). Clearing is idempotent.
    chflags -R nohidden .venv 2>/dev/null || true

# Regenerate protobuf stubs into contracts.gen (checked in — commit the diff).
gen:
    uv run python -m grpc_tools.protoc \
        --proto_path=contracts/proto \
        --python_out=contracts/src/contracts/gen \
        --grpc_python_out=contracts/src/contracts/gen \
        --mypy_out=contracts/src/contracts/gen \
        --mypy_grpc_out=contracts/src/contracts/gen \
        contracts/proto/state.proto
    # grpc_tools emits top-level imports; rewrite to package-relative so
    # the stubs work as contracts.gen.* (long-standing protoc quirk).
    uv run python -c "import pathlib; p = pathlib.Path('contracts/src/contracts/gen/state_pb2_grpc.py'); p.write_text(p.read_text().replace('import state_pb2 as', 'from . import state_pb2 as'))"

# ─── quality gates ─────────────────────────────────────────────────────────

# iCloud re-hides .pth files after every sync (see install); run before any
# uv-run recipe so editable imports never silently vanish.
_unhide:
    @chflags -R nohidden .venv 2>/dev/null || true

lint: _unhide
    uv run ruff check .
    uv run ruff format --check .

format: _unhide
    uv run ruff format .
    uv run ruff check --fix .

typecheck: _unhide
    uv run mypy contracts services bridge

test: _unhide
    uv run pytest

check: lint typecheck test

# ─── stack ─────────────────────────────────────────────────────────────────

# Build all four service images.
build:
    docker compose build

# Start infra + all four services.
up:
    docker compose up -d --build
    @echo "Grafana:    http://localhost:3000 (admin/admin)"
    @echo "Prometheus: http://localhost:9090"
    @echo "Viz:        http://localhost:8004"

down:
    docker compose down

logs svc="":
    docker compose logs -f {{svc}}

# ─── health ────────────────────────────────────────────────────────────────

_check name url:
    @curl -sf {{url}} >/dev/null && echo "{{name}} ✓" || echo "{{name}} ✗"

# Smoke check: infra and all four services answer.
healthz:
    @just _check grafana    http://localhost:3000/api/health
    @just _check influx     http://localhost:8086/health
    @just _check prometheus http://localhost:9090/-/healthy
    @just _check telemetry  http://localhost:8001/healthz/ready
    @just _check state      http://localhost:8002/healthz/ready
    @just _check command    http://localhost:8003/healthz/ready
    @just _check viz        http://localhost:8004/healthz/ready
    @docker compose exec -T mosquitto mosquitto_sub -t '$SYS/broker/uptime' -C 1 -W 2 >/dev/null 2>&1 \
        && echo "mqtt ✓" || echo "mqtt ✗"

# ─── sim + bridge (vendored from twin-hello) ───────────────────────────────

# Launch Gazebo with the UR5 world. Requires ROS 2 Jazzy sourced.
sim:
    ros2 launch sim/launch/ur5_demo.launch.py

# Run the DDS↔MQTT bridge locally (requires ROS 2 sourced and `just up`).
bridge:
    MQTT_HOST=localhost uv run python -m bridge.main

# ─── demo ──────────────────────────────────────────────────────────────────

# Kill each service in turn; assert the others stay ready and recovery is automatic.
chaos:
    uv run python scripts/chaos.py

# Record a 15s screencast for the README. Requires peek.
record:
    peek --start-timer 3 --duration 15 --output-format gif \
         --output docs/demo/twin-services.gif
