# 1. Record architecture decisions

Date: 2026-07-17
Status: Accepted

## Context

We need a lightweight way to capture non-obvious design choices as we make
them, so that six months from now — or when `twin-anomaly` and `twin-fleet`
fork this repo — the reasoning is recoverable.

## Decision

We will use Architecture Decision Records (ADRs) as described by Michael
Nygard. Each ADR is a short markdown file in `docs/adr/`, numbered in
sequence. Format: Context → Decision → Consequences.

Status is one of: Proposed, Accepted, Deprecated, Superseded by ADR-XXXX.

## Consequences

- Every meaningful design decision is discoverable via `ls docs/adr/`.
- PRs that introduce a new dependency or cross a layer boundary must include
  an ADR (or a dependency note inside an existing one).
- ADRs are append-only. Corrections happen via a new ADR that supersedes.
