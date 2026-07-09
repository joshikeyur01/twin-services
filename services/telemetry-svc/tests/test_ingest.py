"""Unit tests for the point conversion and readiness — no broker, no InfluxDB."""

from __future__ import annotations

from prometheus_client import REGISTRY

from telemetry_svc.config import TelemetryConfig
from telemetry_svc.ingest import Ingestor, _to_point


def _rejections(reason: str) -> float:
    value = REGISTRY.get_sample_value("twin_telemetry_rejected_total", {"reason": reason})
    return value or 0.0


class TestToPoint:
    def test_valid_message_becomes_point(self) -> None:
        point = _to_point("twin/ur5/joint/elbow_joint/position", '{"value": 1.57, "stamp_ns": 123}')
        assert point is not None
        line = point.to_line_protocol()  # type: ignore[no-untyped-call]  # influx client is untyped
        assert line == (
            "joint_telemetry,asset=ur5,joint=elbow_joint,metric=position value=1.57 123"
        )

    def test_non_telemetry_topic_dropped(self) -> None:
        before = _rejections("topic")
        assert _to_point("twin/ur5/cmd/joints", '{"value": 1, "stamp_ns": 1}') is None
        assert _rejections("topic") == before + 1

    def test_bad_payload_dropped(self) -> None:
        before = _rejections("payload")
        assert _to_point("twin/ur5/joint/elbow_joint/position", "not json") is None
        assert _to_point("twin/ur5/joint/elbow_joint/position", '{"value": "x"}') is None
        assert _rejections("payload") == before + 2

    def test_legacy_wire_format_accepted(self) -> None:
        # The twin-hello bridge payload: no schema_version.
        point = _to_point("twin/ur5/joint/elbow_joint/velocity", '{"value": 0.5, "stamp_ns": 42}')
        assert point is not None


class TestReadiness:
    def test_not_ready_before_connecting(self) -> None:
        ingestor = Ingestor(TelemetryConfig.from_env())
        assert ingestor.readiness() == {"mqtt": False, "influxdb": False}
