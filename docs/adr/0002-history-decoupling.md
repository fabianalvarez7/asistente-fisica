# ADR 0002: Decouple chat availability from history persistence

- **Status**: Accepted
- **Date**: 2026-09-21
- **Change**: `history-decoupling`

## Decision

Keep the chat stream available when Turso is unavailable or hangs by separating
the request path from history persistence:

1. Awaited history reads and startup initialization use a bounded child-process
   boundary when Turso is configured. A timed-out synchronous libSQL call is
   terminated with its process. The local SQLite fallback keeps the lighter
   `asyncio.to_thread` plus `asyncio.wait_for` boundary for development.
2. `HISTORY_TIMEOUT_SECONDS` controls that budget and defaults to 5 seconds.
   Invalid or non-positive values fall back to the default.
3. Writes enter a bounded FIFO `asyncio.Queue` managed by one worker. The
   queue holds at most 1,000 items, never blocks a request, and preserves
   chronological order.
4. Availability failures retry in place up to five attempts with exponential
   backoff of 1, 2, 4, and 8 seconds (capped at 30 seconds). Queue overflow,
   retry exhaustion, shutdown, and terminal timeouts are logged as drops.
5. A timeout is terminal for that write. Retrying after an abandoned
   synchronous call could duplicate an insert if the database operation
   completes after its caller stops waiting.
6. The worker starts eagerly during application lifespan startup and lazily on
   the first enqueue as a test/development fallback. Remaining work is logged
   and dropped at process shutdown.

The SSE event names, frame order, `[DONE]` marker, `/history` JSON shape, and
existing amber degraded banner remain unchanged.

## Context

The `libsql-experimental` 0.0.55 driver is synchronous and has no usable
timeout. A silent network stall therefore blocks indefinitely. The previous
fail-open handling classified raised exceptions but could not classify a call
that never returned. In addition, `/chat` awaited persistence before streaming,
so a history outage also became a chat outage.

The keepalive workflow previously called `/history?student_name=_keepalive`.
That woke the Space but also performed database work and created or reused a
synthetic student. It now calls the bounded, read-only `/health` endpoint so
the schedule warms the Space and verifies persistence without changing data.

## Contracts

### Availability and durability

- On a healthy Turso connection, every accepted chat message is persisted
  immediately or by the queue before normal recovery completes.
- During an outage or hang, the assistant may deliver the response while a
  write remains queued. If persistence recovers during the process lifetime,
  queued writes drain in order.
- A prolonged outage, queue overflow, terminal timeout, or process shutdown
  may lose queued messages. Each loss is logged; the amber banner discloses
  that history may not survive a reload.
- The queue is intentionally process-local. It is not a durable broker and is
  not expected to survive an HF Space restart or sleep/wake cycle.

### Defect visibility

The old synchronous request path exposed some programming defects as HTTP 500
responses. With asynchronous writes, a defect can surface after the request
has returned. Defects detectable at enqueue time still propagate to the
request. Defects raised by the worker are logged at `ERROR` with the
`history_write_defect` classification and are never converted into an
availability/degraded signal. Availability failures are the only failures
eligible for retry or degraded signaling.

## Abandoned synchronous calls

For Turso, a timed-out synchronous driver call runs in a child process that is
terminated before the timeout is reported. No abandoned driver thread remains
in the application process, and timed-out writes are not retried to avoid
duplicate inserts. The local SQLite fallback still uses `to_thread`; that
development-only path retains Python's inability to cancel an already-running
synchronous call.

The request entry phase uses one deadline for its sequential history
observations. A later assistant-write observation can add another timeout in
the mixed-failure case, so `[DONE]` may approach two timeout budgets. The
normal healthy path is faster because writes no longer gate generation.

## Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| One `asyncio.create_task` per write | Request-scoped tasks can be cancelled at lifespan end and can grow without a bounded queue. |
| A decorator around `rag/history.py` | The driver boundary is synchronous; an explicit wrapper selects the cancellable child-process boundary for Turso, preserves the local SQLite thread fallback, and keeps tests that patch `app.main` callables. |
| Retrying timed-out writes | The abandoned thread may still commit; retrying can create duplicate rows. |
| Retiring the keepalive workflow | It would lose the warm-Space benefit without solving history availability. `/health` keeps the wake-up and verifies persistence without synthetic database writes. |
| SQLite-only production history | Container-local SQLite is lost when the Space sleeps or restarts. |
| Supabase, Neon, or a paid Turso plan | Changing providers does not remove the prototype's need for bounded calls and would add cost or operational scope. |

## Rollback and consequences

There is no schema migration, feature flag, or new required secret. Reverting
the implementation change restores the previous fail-open behavior. Reverting
also restores the old persistence coupling and the old keepalive side effect,
so the operational documentation must be reverted with the implementation.

The main positive consequence is that a hung Turso history service cannot hold
the SSE stream forever or accumulate abandoned driver threads in the app
process. The accepted costs are best-effort durability during outages,
process-local queue loss on shutdown, child-process startup overhead, and more
operational logging to monitor worker-side defects and drops.
