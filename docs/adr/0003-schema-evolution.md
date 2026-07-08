# 3. Schema evolution: additive-only, versioned envelopes, locked field numbers

Date: 2026-07-17
Status: Accepted

## Context

Four services and a bridge now share payload shapes. The moment two deployed
components disagree about a schema, the failure is silent data corruption or
a crash loop — the worst kinds. And this repo's schemas already have a
"legacy producer": the vendored twin-hello bridge wire format predates the
contracts package.

## Decision

One rule set for both dialects, enforced where possible by CI and tests:

1. **Additive-only.** Fields are added, never renamed, retyped, or removed.
   A breaking change is a new version living alongside the old one
   (`twin.state.v2` package, `/v2` route), never a mutation.
2. **Envelopes carry `schema_version`** with a default of 1, so payloads
   that predate the field (the twin-hello bridge) parse as version 1 forever.
3. **Consumers ignore unknown fields.** No Pydantic model in contracts sets
   `extra="forbid"`; tomorrow's producer must not break today's consumer.
4. **Protobuf field numbers are never reused.** Removed fields get a
   `reserved` statement. A unit test pins every TwinState field number so a
   renumber fails in CI, loudly, instead of corrupting old payloads quietly.
5. **Generated stubs are checked in** (`contracts.gen`) and regenerated only
   via `just gen`; CI fails if the checked-in stubs are stale.
6. **Schema changes land in `contracts/` first**, in their own commit with a
   CHANGELOG entry; service adoption follows. Never the reverse, never mixed.

## Consequences

Positive:
- "Yesterday's producer, today's consumer" and the reverse are both tested,
  not assumed (`contracts/tests/test_contracts.py`).
- Services never depend on a working `protoc` at build or runtime.
- The CI grep for `BaseModel` subclasses in `services/` keeps the single
  source of truth single.

Negative:
- Dead fields accumulate; the schema can only grow within a version. This is
  the accepted price of never corrupting a deployed peer.
- Checked-in generated code makes diffs noisier. Mitigated by generating in
  a dedicated directory that lint, mypy, and review treat as opaque.

## Alternatives considered

- **Schema registry (Confluent-style):** rejected — infrastructure heavier
  than the whole rest of the stack, for one repo's worth of schemas.
- **Forbid unknown fields for "safety":** rejected — it converts every
  additive producer change into a consumer outage, the opposite of safety.
- **Generate stubs at build time instead of checking in:** rejected — every
  image build and CI job would need protoc + plugins, and stub drift would
  be invisible in review.
