# What I learned

Genuine lessons from building and breaking this repo, in the order the
stack taught them to me.

## Observability lies by omission unless you design against it

The first version of the Grafana status row showed a **dead service as
green**. When a Prometheus target dies, its gauges go *stale* (empty) rather
than zero, the naive `up * ready` product goes empty too, and `lastNotNull`
happily reaches back to the last pre-death value. The fix —
`min(up) * (min(twin_service_ready) or vector(1))` — is three tokens that
are the difference between a dashboard and a decoration. Found by killing a
container and *watching*, which is the entire argument for `just chaos`.

## `docker kill` does not trigger `restart: unless-stopped`

Docker treats CLI kills and stops as operator intent and does not restart
the container. My mental model ("restart policy = auto-recovery in the kill
demo") was simply wrong; the chaos script now owns the restart step, which
is also the more honest simulation of an orchestrator.

## gRPC's defaults assume patience the demo doesn't have

A dependency outage pushes the channel's reconnect backoff toward two
minutes. Next to a 2-second scrape interval that reads as "viz-svc is
stuck", when it's actually behaving as documented. Capping
(`grpc.max_reconnect_backoff_ms=3000`) made recovery visibly snappy. The
general lesson: every retry/backoff default encodes someone else's SLO.

## The benchmark said latency doesn't matter — that IS the result

gRPC `GetState` p50 1.38 ms vs REST JSON p50 1.88 ms on the same host. Half
a millisecond justifies nothing. The real reasons to pick gRPC internally
are typed server-streaming and compiler-checked contracts; the real reason
to pick REST at the edge is `curl`. Writing ADR-0002 around measured
irrelevance felt better than writing it around imagined speed.

## Contracts-first works, but only with teeth

"Shared schema package" is a platitude until CI greps for `BaseModel` in
`services/`, diffs the generated stubs, and a unit test pins every proto
field number. Each of those tripwires exists because I could feel where the
shortcut would happen. Also real: protoc's generated gRPC stub still emits
top-level imports that break inside a package (`just gen` rewrites them),
and checked-in stubs are noisy diffs — the price of not needing protoc in
four Docker builds.

## uv workspaces are excellent and sharp-edged

One lockfile, editable members, per-service dependency isolation that doubles
as architecture enforcement — genuinely good. But `requires-python: ">=3.12"`
let uv silently build the venv on Python 3.14 (pin with `.python-version`),
and an editable install of a member whose `src/` didn't exist yet "succeeds"
as an empty package.

## The environment is part of the system

Two hours of "editable installs randomly vanish" turned out to be macOS
iCloud (`fileproviderd`) asynchronously setting the hidden flag on `.venv`
— and CPython ≥3.12 skips hidden `.pth` files as a security measure. The
failure appears minutes after a successful sync, which incriminates
everything except the actual culprit. Fix is one `chflags` in the justfile;
the lesson is that "nondeterministic" usually means "asynchronous cause".

## Duplication is a decision, not a sin

Four near-identical `health.py` modules (readiness genuinely differs;
boilerplate is ~20 lines) beat a shared library whose interface would churn.
The one real cost surfaced immediately: a shared Prometheus gauge name
collides when tests import several services into one process. The guard is
five lines. Revisit at `twin-fleet` scale, per ADR-0004.

## Compose names are a shared global namespace

Hardcoded `container_name: twin-mosquitto` in two sibling repos means their
stacks can never coexist on one machine. Dropping `container_name` and
letting the compose project prefix do its job costs nothing and fixed it
permanently — `twin-hello` still has the trap.
