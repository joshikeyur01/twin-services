"""Shared contracts for twin-services.

The single source of truth for every cross-service payload: Pydantic models
for MQTT/REST (``contracts.models``) and generated protobuf/gRPC stubs
(``contracts.gen``). Services import shapes from here and never define their
own — CI enforces it.
"""

from contracts.models import (
    SCHEMA_VERSION,
    UR5_JOINT_NAMES,
    CommandKind,
    CommandReceipt,
    JointCommand,
    JointField,
    JointTelemetry,
    command_topic,
    parse_telemetry_topic,
    telemetry_topic,
    telemetry_wildcard,
)

__all__ = [
    "SCHEMA_VERSION",
    "UR5_JOINT_NAMES",
    "CommandKind",
    "CommandReceipt",
    "JointCommand",
    "JointField",
    "JointTelemetry",
    "command_topic",
    "parse_telemetry_topic",
    "telemetry_topic",
    "telemetry_wildcard",
]
