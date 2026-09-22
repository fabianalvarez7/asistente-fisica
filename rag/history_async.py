"""Async boundaries and best-effort ordered writes for conversation history."""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
from dataclasses import dataclass
from typing import Any, Callable

from rag.history import HistoryUnavailableError, _is_programming_defect

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 1000
MAX_ATTEMPTS = 5
DEFAULT_HISTORY_TIMEOUT_SECONDS = 5.0
_TURSO_URL_ENV = "TURSO_DATABASE_URL"
_TURSO_TOKEN_ENV = "TURSO_AUTH_TOKEN"


class HistoryCallTimeout(HistoryUnavailableError):
    """A history call exceeded its budget before its worker returned."""


class _ChildCallError(Exception):
    """Fallback error when a child exception cannot cross the process pipe."""


def uses_cancellable_boundary() -> bool:
    """Return whether history is configured to use the remote Turso backend."""
    return bool(os.getenv(_TURSO_URL_ENV) and os.getenv(_TURSO_TOKEN_ENV))


def _run_in_child(connection, fn: Callable[..., Any], args: tuple[Any, ...]) -> None:
    """Execute one synchronous call in an isolated process."""
    try:
        connection.send(("ok", fn(*args)))
    except BaseException as exc:  # noqa: BLE001 - report every child failure
        try:
            connection.send(("error", exc))
        except Exception:
            connection.send(("error", _ChildCallError(type(exc).__name__)))
    finally:
        connection.close()


def _stop_child(process) -> None:
    """Terminate a timed-out child without waiting indefinitely for the driver."""
    if not process.is_alive():
        process.join()
        return

    process.terminate()
    process.join(0.2)
    if process.is_alive():
        process.kill()
        process.join(0.2)
    if process.is_alive():
        logger.error(
            "history_child_cleanup_failed: child process remained alive after "
            "terminate and kill attempts"
        )


async def _bounded_process_call(
    fn: Callable[..., Any], args: tuple[Any, ...], timeout: float
) -> Any:
    """Run a synchronous remote-driver call where timeout can kill the caller."""
    context = multiprocessing.get_context("spawn")
    parent_connection, child_connection = context.Pipe(duplex=False)
    process = context.Process(target=_run_in_child, args=(child_connection, fn, args))
    process.daemon = True
    started = False

    try:
        process.start()
        started = True
        child_connection.close()
        deadline = asyncio.get_running_loop().time() + timeout

        while True:
            if parent_connection.poll():
                status, value = parent_connection.recv()
                if status == "ok":
                    return value
                raise value

            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                logger.error(
                    "history_call_timeout (operation=%s, timeout=%s)",
                    getattr(fn, "__name__", type(fn).__name__),
                    timeout,
                )
                raise HistoryCallTimeout("persistence call exceeded timeout")

            if not process.is_alive():
                raise HistoryUnavailableError("history worker process exited")
            await asyncio.sleep(min(0.01, remaining))
    finally:
        if started:
            _stop_child(process)
        else:
            child_connection.close()
        parent_connection.close()


async def bounded_call(fn: Callable[..., Any], /, *args: Any, timeout: float) -> Any:
    """Run a synchronous history call off-loop and convert expiry to degradation.

    Turso calls run in a short-lived child process so a stalled synchronous
    driver call can be terminated. Local SQLite keeps the lighter thread
    boundary used for development.
    """
    if timeout <= 0:
        raise HistoryUnavailableError("history budget exhausted")
    if uses_cancellable_boundary():
        return await _bounded_process_call(fn, args, timeout)
    try:
        return await asyncio.wait_for(asyncio.to_thread(fn, *args), timeout)
    except asyncio.TimeoutError as exc:
        logger.error(
            "history_call_timeout (operation=%s, timeout=%s)",
            getattr(fn, "__name__", type(fn).__name__),
            timeout,
        )
        raise HistoryCallTimeout("persistence call exceeded timeout") from exc


class Deadline:
    """Monotonic request budget shared by sequential persistence observations."""

    def __init__(self, budget: float):
        self.budget = max(0.0, float(budget))
        self._started_at: float | None = None

    def start(self) -> "Deadline":
        self._started_at = asyncio.get_running_loop().time()
        return self

    @property
    def left(self) -> float:
        if self._started_at is None:
            return self.budget
        return max(0.0, self.budget - (asyncio.get_running_loop().time() - self._started_at))


@dataclass
class _WriteItem:
    fn: Callable[..., Any]
    args: tuple[Any, ...]
    pending: "PendingWrite"
    attempt: int = 0


class PendingWrite:
    """Handle the first observation of a queued write without cancelling it."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.future: asyncio.Future[tuple[str, Any]] = loop.create_future()

    def _set_result(self, outcome: tuple[str, Any]) -> None:
        if not self.future.done():
            self.future.set_result(outcome)

    async def resolve(self, timeout: float) -> int | None:
        """Return the row id, or None for availability/observation failure."""
        try:
            outcome = await asyncio.wait_for(asyncio.shield(self.future), max(0.0, timeout))
        except asyncio.TimeoutError:
            return None

        status, value = outcome
        if status == "ok":
            return value
        if status == "defect":
            raise value
        return None


def _metadata(args: tuple[Any, ...]) -> tuple[Any, int]:
    role = args[1] if len(args) > 1 else "unknown"
    content = args[2] if len(args) > 2 else ""
    return role, len(content) if isinstance(content, str) else 0


class WriteWorker:
    """Single FIFO worker with bounded, retry-in-place persistence."""

    def __init__(
        self,
        maxsize: int = MAX_QUEUE_SIZE,
        max_attempts: int = MAX_ATTEMPTS,
        backoff_start: float = 1.0,
        backoff_cap: float = 30.0,
        call_timeout: float = DEFAULT_HISTORY_TIMEOUT_SECONDS,
    ):
        self.queue: asyncio.Queue[_WriteItem] = asyncio.Queue(maxsize=maxsize)
        self.max_attempts = max(1, max_attempts)
        self.backoff_start = max(0.0, backoff_start)
        self.backoff_cap = max(self.backoff_start, backoff_cap)
        self.call_timeout = call_timeout
        self._task: asyncio.Task[None] | None = None
        self._current: _WriteItem | None = None

    def ensure_running(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    def enqueue_write(self, fn: Callable[..., Any], /, *args: Any) -> PendingWrite:
        loop = asyncio.get_running_loop()
        pending = PendingWrite(loop)
        role, length = _metadata(args)
        if role != "unknown" and role not in ("user", "assistant"):
            raise ValueError(f"role must be one of ('user', 'assistant'), got {role!r}")

        item = _WriteItem(fn, tuple(args), pending)
        try:
            self.queue.put_nowait(item)
        except asyncio.QueueFull:
            pending._set_result(("unavailable", None))
            logger.error(
                "history_queue_overflow (queue_depth=%s, role=%s, content_length=%s)",
                self.queue.qsize(),
                role,
                length,
            )
            return pending
        self.ensure_running()
        return pending

    async def _run(self) -> None:
        while True:
            try:
                item = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            self._current = item
            await self._process(item)
            self._current = None

    async def _process(self, item: _WriteItem) -> None:
        role, length = _metadata(item.args)
        for attempt in range(1, self.max_attempts + 1):
            item.attempt = attempt
            try:
                result = await bounded_call(
                    item.fn, *item.args, timeout=self.call_timeout
                )
            except HistoryCallTimeout:
                item.pending._set_result(("timeout", None))
                logger.error(
                    "history_write_dropped (reason=timeout, attempt=%s, role=%s, "
                    "content_length=%s, queue_depth=%s)",
                    attempt,
                    role,
                    length,
                    self.queue.qsize(),
                )
                return
            except Exception as exc:
                if _is_programming_defect(exc):
                    item.pending._set_result(("defect", exc))
                    logger.error(
                        "history_write_defect (exc_type=%s, role=%s)",
                        type(exc).__name__,
                        role,
                    )
                    return
                if attempt == 1:
                    item.pending._set_result(("unavailable", exc))
                if attempt == self.max_attempts:
                    logger.error(
                        "history_write_dropped (reason=retry_exhausted, attempt=%s, "
                        "role=%s, content_length=%s, queue_depth=%s)",
                        attempt,
                        role,
                        length,
                        self.queue.qsize(),
                    )
                    return
                delay = min(self.backoff_cap, self.backoff_start * (2 ** (attempt - 1)))
                if delay:
                    await asyncio.sleep(delay)
                continue
            else:
                item.pending._set_result(("ok", result))
                return

    async def drain(self, timeout: float | None = None) -> bool:
        self.ensure_running()
        if self._task is None:
            return True
        try:
            waiter = asyncio.shield(self._task)
            if timeout is None:
                await waiter
            else:
                await asyncio.wait_for(waiter, timeout)
        except asyncio.TimeoutError:
            return False
        return self.queue.empty() and (self._task is None or self._task.done())

    def _drop_remaining(self, reason: str) -> None:
        while True:
            try:
                item = self.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            item.pending._set_result(("unavailable", None))
            role, length = _metadata(item.args)
            logger.error(
                "history_write_dropped (reason=%s, attempt=%s, role=%s, "
                "content_length=%s, queue_depth=%s)",
                reason,
                item.attempt,
                role,
                length,
                self.queue.qsize(),
            )
        if self._current is not None:
            self._current.pending._set_result(("unavailable", None))

    async def shutdown(self) -> None:
        self._drop_remaining("shutdown")
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._current = None


_worker_loop: asyncio.AbstractEventLoop | None = None
_worker: WriteWorker | None = None


def get_write_worker(*, call_timeout: float | None = None) -> WriteWorker:
    """Return the current-loop worker, updating its persistence timeout when set."""
    global _worker_loop, _worker
    loop = asyncio.get_running_loop()
    if _worker is None or _worker_loop is not loop:
        if _worker is not None:
            _worker._drop_remaining("loop_change")
        _worker_loop = loop
        _worker = WriteWorker(
            call_timeout=(
                DEFAULT_HISTORY_TIMEOUT_SECONDS
                if call_timeout is None
                else call_timeout
            )
        )
    elif call_timeout is not None:
        _worker.call_timeout = call_timeout
    return _worker


def enqueue_write(
    fn: Callable[..., Any], /, *args: Any, call_timeout: float | None = None
) -> PendingWrite:
    """Enqueue on the current loop's managed worker with an optional call budget."""
    return get_write_worker(call_timeout=call_timeout).enqueue_write(fn, *args)
