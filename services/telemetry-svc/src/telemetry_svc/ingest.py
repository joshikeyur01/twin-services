"""MQTT → contract validation → InfluxDB.

The loop is the service: subscribe to the telemetry wildcard, validate every
payload against contracts, write points. Invalid input is counted and dropped
— never written, never fatal. Broker loss flips readiness and retries forever;
recovery needs no manual step (the chaos demo depends on this).
"""

from __future__ import annotations

import asyncio

import aiomqtt
import structlog
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from influxdb_client.client.write.point import Point
from influxdb_client.domain.write_precision import WritePrecision
from prometheus_client import Counter
from pydantic import ValidationError

from contracts import JointTelemetry, parse_telemetry_topic, telemetry_wildcard
from telemetry_svc.config import TelemetryConfig

log = structlog.get_logger()

MESSAGES = Counter("twin_telemetry_messages_total", "Telemetry messages received from MQTT.")
REJECTED = Counter(
    "twin_telemetry_rejected_total",
    "Messages dropped for failing the contract.",
    ["reason"],  # "topic" | "payload"
)
WRITE_FAILURES = Counter("twin_influx_write_failures_total", "InfluxDB writes that raised.")

RECONNECT_DELAY_S = 2.0


class Ingestor:
    """Owns the MQTT→InfluxDB loop and reports its readiness."""

    def __init__(self, config: TelemetryConfig) -> None:
        self._config = config
        self._mqtt_connected = False
        self._influx_ok = False

    def readiness(self) -> dict[str, bool]:
        return {"mqtt": self._mqtt_connected, "influxdb": self._influx_ok}

    async def run(self) -> None:
        """Consume telemetry forever; reconnect with a fixed delay on broker loss."""
        while True:
            try:
                await self._consume()
            except aiomqtt.MqttError as exc:
                self._mqtt_connected = False
                log.warning("mqtt_disconnected", error=str(exc), retry_in_s=RECONNECT_DELAY_S)
                await asyncio.sleep(RECONNECT_DELAY_S)

    async def _consume(self) -> None:
        cfg = self._config
        async with (
            InfluxDBClientAsync(
                url=cfg.influx_url, token=cfg.influx_token, org=cfg.influx_org
            ) as influx,
            aiomqtt.Client(cfg.mqtt_host, cfg.mqtt_port) as mqtt,
        ):
            self._mqtt_connected = True
            self._influx_ok = await influx.ping()
            write_api = influx.write_api()
            topic_filter = telemetry_wildcard(cfg.asset_name)
            await mqtt.subscribe(topic_filter)
            log.info("consuming", topic=topic_filter, influx=cfg.influx_url)

            async for message in mqtt.messages:
                MESSAGES.inc()
                raw = message.payload
                if not isinstance(raw, bytes | str):
                    REJECTED.labels(reason="payload").inc()
                    continue
                point = _to_point(str(message.topic), raw)
                if point is None:
                    continue
                try:
                    await write_api.write(bucket=cfg.influx_bucket, record=point)
                    self._influx_ok = True
                # The influx client raises many types; a write must never kill ingest.
                except Exception as exc:
                    WRITE_FAILURES.inc()
                    self._influx_ok = False
                    log.warning("influx_write_failed", error=str(exc))


def _to_point(topic: str, payload: bytes | str) -> Point | None:
    """One validated telemetry message becomes one point; anything else, None."""
    try:
        asset, joint, field = parse_telemetry_topic(topic)
    except ValueError:
        REJECTED.labels(reason="topic").inc()
        return None
    try:
        sample = JointTelemetry.model_validate_json(payload)
    except ValidationError:
        REJECTED.labels(reason="payload").inc()
        return None
    point: Point = (
        Point("joint_telemetry")
        .tag("asset", asset)
        .tag("joint", joint)
        .tag("metric", field.value)
        .field("value", sample.value)
        .time(sample.stamp_ns, WritePrecision.NS)
    )
    return point
