import asyncio
import logging
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rag import history
import rag.history_async as history_async
from rag.history_async import Deadline, HistoryCallTimeout, WriteWorker, bounded_call
from rag.history import HistoryUnavailableError


def _hung_driver_call():
    time.sleep(30)


def _healthy_driver_call():
    return "recovered"


class HistoryAsyncTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.local_boundary = patch.object(
            history_async, "uses_cancellable_boundary", return_value=False
        )
        self.local_boundary.start()
        self.addCleanup(self.local_boundary.stop)

    async def test_bounded_call_converts_timeout(self):
        with self.assertRaises(HistoryUnavailableError):
            await bounded_call(lambda: time.sleep(0.1), timeout=0.01)

    async def test_repeated_remote_timeouts_do_not_block_recovery(self):
        with patch.object(history_async, "uses_cancellable_boundary", return_value=True):
            for _ in range(3):
                with self.assertRaises(HistoryUnavailableError):
                    await bounded_call(_hung_driver_call, timeout=0.05)

            self.assertEqual(
                await bounded_call(_healthy_driver_call, timeout=1), "recovered"
            )

    async def test_deadline_reports_remaining_budget(self):
        deadline = Deadline(1).start()
        self.assertGreater(deadline.left, 0)
        self.assertLessEqual(deadline.left, 1)

    def test_stop_child_reports_process_still_alive_after_kill(self):
        process = Mock()
        process.is_alive.side_effect = [True, True, True]

        with self.assertLogs("rag.history_async", level=logging.ERROR) as logs:
            history_async._stop_child(process)

        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertTrue(
            any("history_child_cleanup_failed" in line for line in logs.output)
        )

    async def test_queue_overflow_is_dropped(self):
        worker = WriteWorker(maxsize=1)
        first = worker.enqueue_write(lambda *_: 1, 1, "user", "one")
        second = worker.enqueue_write(lambda *_: 2, 1, "assistant", "two")
        third = worker.enqueue_write(lambda *_: 3, 1, "user", "three")
        self.assertIsNone(await third.resolve(0.01))
        await worker.shutdown()
        self.assertIsNone(await first.resolve(0.01))
        self.assertIsNone(await second.resolve(0.01))

    async def test_retry_stays_in_place_before_next_write(self):
        calls = []

        def first(*args):
            calls.append(args[2])
            if len(calls) == 1:
                raise OSError("offline")
            return len(calls)

        worker = WriteWorker(max_attempts=2, backoff_start=0, call_timeout=1)
        first_pending = worker.enqueue_write(first, 1, "user", "first")
        second_pending = worker.enqueue_write(first, 1, "assistant", "second")
        await worker.drain(timeout=1)
        self.assertEqual(calls, ["first", "first", "second"])
        self.assertIsNone(await first_pending.resolve(0))
        self.assertEqual(await second_pending.resolve(0), 3)
        await worker.shutdown()

    async def test_write_timeout_is_terminal(self):
        worker = WriteWorker(call_timeout=0.01, backoff_start=0)
        pending = worker.enqueue_write(lambda *_: time.sleep(0.1), 1, "user", "x")
        with self.assertLogs("rag.history_async", level=logging.ERROR) as logs:
            await worker.drain(timeout=1)
        self.assertIsNone(await pending.resolve(0))
        self.assertTrue(any("reason=timeout" in line for line in logs.output))
        await worker.shutdown()

    async def test_managed_worker_uses_configured_call_timeout(self):
        worker = history_async.get_write_worker(call_timeout=0.01)
        pending = worker.enqueue_write(lambda *_: time.sleep(0.1), 1, "user", "x")

        with self.assertLogs("rag.history_async", level=logging.ERROR) as logs:
            await worker.drain(timeout=1)

        self.assertEqual(worker.call_timeout, 0.01)
        self.assertIsNone(await pending.resolve(0))
        self.assertTrue(any("reason=timeout" in line for line in logs.output))
        await worker.shutdown()

    async def test_programming_defect_is_visible(self):
        worker = WriteWorker()
        pending = worker.enqueue_write(lambda *_: (_ for _ in ()).throw(ValueError("bug")), 1, "user", "x")
        with self.assertLogs("rag.history_async", level=logging.ERROR) as logs:
            await worker.drain(timeout=1)
        with self.assertRaises(ValueError):
            await pending.resolve(0)
        self.assertTrue(any("history_write_defect" in line for line in logs.output))
        await worker.shutdown()

    async def test_shutdown_cancels_worker_and_resolves_queued_items(self):
        worker = WriteWorker(maxsize=2, call_timeout=60)
        item = worker.enqueue_write(lambda *_: time.sleep(0.1), 1, "user", "x")
        await asyncio.sleep(0)
        await worker.shutdown()
        self.assertIsNone(await item.resolve(0))
        self.assertIsNone(worker._task)


class HistoryPersistenceBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_turso_callable_is_terminated_and_joined_after_timeout(self):
        """A hung real history operation must not leave a child process behind."""
        with tempfile.TemporaryDirectory() as module_dir:
            module_path = Path(module_dir) / "libsql_experimental.py"
            marker_path = Path(module_dir) / "connected"
            module_path.write_text(
                """
import os
import time


class Error(Exception):
    pass


class _HangingClient:
    def execute(self, _sql):
        while True:
            time.sleep(0.01)


def connect(_url, auth_token=None):
    del auth_token
    with open(os.environ["FAKE_LIBSQL_MARKER"], "w") as marker:
        marker.write("connected")
    return _HangingClient()
""".lstrip()
            )

            original_path = sys.path[:]
            sys.path.insert(0, module_dir)
            history._reset_connection()
            stopped_processes = []
            original_stop_child = history_async._stop_child

            def stop_and_capture(process):
                stopped_processes.append(process)
                original_stop_child(process)

            try:
                with patch.dict(
                    os.environ,
                    {
                        "TURSO_DATABASE_URL": "libsql://test.invalid",
                        "TURSO_AUTH_TOKEN": "test-token",
                        "FAKE_LIBSQL_MARKER": str(marker_path),
                    },
                    clear=False,
                ), patch.object(
                    history_async, "_stop_child", side_effect=stop_and_capture
                ):
                    with self.assertRaises(HistoryCallTimeout):
                        await history_async.bounded_call(
                            history.check_history_health,
                            timeout=1,
                        )
            finally:
                history._reset_connection()
                sys.path[:] = original_path

            self.assertEqual(marker_path.read_text(), "connected")
            self.assertEqual(len(stopped_processes), 1)
            process = stopped_processes[0]
            self.assertFalse(process.is_alive())
            self.assertIsNotNone(process.exitcode)

    async def test_local_sqlite_fallback_uses_real_history_operations(self):
        """The development SQLite path remains usable through its thread boundary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "history.db")
            history._reset_connection()
            try:
                with patch.dict(
                    os.environ,
                    {"SQLITE_PATH": db_path},
                    clear=False,
                ):
                    os.environ.pop("TURSO_DATABASE_URL", None)
                    os.environ.pop("TURSO_AUTH_TOKEN", None)
                    self.assertFalse(history_async.uses_cancellable_boundary())
                    await history_async.bounded_call(history.init_db, timeout=1)
                    student_id = await history_async.bounded_call(
                        history.get_or_create_student,
                        "Ana",
                        timeout=1,
                    )
                    message_id = await history_async.bounded_call(
                        history.save_message,
                        student_id,
                        "user",
                        "test",
                        timeout=1,
                    )
                    messages = await history_async.bounded_call(
                        history.get_history,
                        student_id,
                        timeout=1,
                    )
            finally:
                history._reset_connection()

            self.assertEqual(message_id, messages[0]["id"])
            self.assertEqual(messages[0]["content"], "test")
            self.assertEqual(messages[0]["role"], "user")


if __name__ == "__main__":
    unittest.main()
