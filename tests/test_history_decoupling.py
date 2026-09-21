import asyncio
import logging
import time
import unittest

import rag.history_async as history_async
from rag.history_async import Deadline, WriteWorker, bounded_call
from rag.history import HistoryUnavailableError


class HistoryAsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_bounded_call_converts_timeout(self):
        with self.assertRaises(HistoryUnavailableError):
            await bounded_call(lambda: time.sleep(0.1), timeout=0.01)

    async def test_deadline_reports_remaining_budget(self):
        deadline = Deadline(1).start()
        self.assertGreater(deadline.left, 0)
        self.assertLessEqual(deadline.left, 1)

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


if __name__ == "__main__":
    unittest.main()
