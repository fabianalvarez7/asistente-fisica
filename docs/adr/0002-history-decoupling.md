# ADR 0002: Decouple chat availability from history persistence

- **Status**: Accepted
- **Date**: 2026-09-21
- **Change**: `history-decoupling`

## Decision

Keep the chat stream available when Turso is unavailable or hangs by separating
the request path from history persistence:

1. Awaited history reads and startup initialization run through a bounded
   `asyncio.to_thread` plus `asyncio.wait_for` boundary.
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
synthetic student. The warm-up concern is independent of history durability,
so the workflow now calls the read-only `/topics` endpoint instead.

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

`asyncio.wait_for` stops awaiting a timed-out `to_thread` call, but Python
cannot cancel the synchronous function already running in its executor
thread. Those abandoned calls can finish later. The queue is bounded, the
executor limits the number of concurrent abandoned threads, and timed-out
writes are not retried to avoid duplicate inserts. This is an accepted,
bounded prototype trade-off rather than a claim of cancellation safety.

The request entry phase uses one deadline for its sequential history
observations. A later assistant-write observation can add another timeout in
the mixed-failure case, so `[DONE]` may approach two timeout budgets. The
normal healthy path is faster because writes no longer gate generation.

## Rejected alternatives

| Alternative | Reason for rejection |
|---|---|
| One `asyncio.create_task` per write | Request-scoped tasks can be cancelled at lifespan end and can grow without a bounded queue. |
| A decorator around `rag/history.py` | The driver boundary is synchronous; an explicit wrapper makes the `to_thread`/timeout boundary visible and preserves tests that patch `app.main` callables. |
| Retrying timed-out writes | The abandoned thread may still commit; retrying can create duplicate rows. |
| Retiring the keepalive workflow | It would lose the warm-Space benefit without solving history availability. `/topics` keeps the wake-up and removes synthetic database writes. |
| SQLite-only production history | Container-local SQLite is lost when the Space sleeps or restarts. |
| Supabase, Neon, or a paid Turso plan | Changing providers does not remove the prototype's need for bounded calls and would add cost or operational scope. |

## Rollback and consequences

There is no schema migration, feature flag, or new required secret. Reverting
the implementation change restores the previous fail-open behavior. Reverting
also restores the old persistence coupling and the old keepalive side effect,
so the operational documentation must be reverted with the implementation.

The main positive consequence is that a hung history service cannot hold the
SSE stream forever. The accepted costs are best-effort durability during
outages, process-local queue loss on shutdown, possible executor threads that
finish after timeout, and more operational logging to monitor worker-side
defects and drops.
