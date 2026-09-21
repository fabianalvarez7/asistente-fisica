"""Application integration coverage for the history availability boundary."""

from __future__ import annotations

import os
import sys
import threading
import time
import unittest
from contextlib import contextmanager
from unittest.mock import ANY, MagicMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-key")

_fake_retrievers = MagicMock()
_fake_store_class = MagicMock()
_fake_store_class.return_value.count.return_value = 1
_fake_retrievers.VectorStore = _fake_store_class
_fake_retrievers.EmbeddingsModel = MagicMock


@contextmanager
def _temporary_retrievers_module():
    missing = object()
    previous = sys.modules.get("rag.retrievers", missing)
    sys.modules["rag.retrievers"] = _fake_retrievers
    try:
        yield
    finally:
        if previous is missing:
            sys.modules.pop("rag.retrievers", None)
        else:
            sys.modules["rag.retrievers"] = previous


with _temporary_retrievers_module():
    from fastapi.testclient import TestClient  # noqa: E402

    import app.main as main  # noqa: E402
    from rag.history import HistoryUnavailableError  # noqa: E402


def _fake_generator(query, history=None):
    yield "data: Pensá en esto...\n\n"
    yield "data: [DONE]\n\n"


class HistoryApplicationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.timeout = patch.object(main, "HISTORY_TIMEOUT_SECONDS", 0.05)
        self.timeout.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.timeout.stop()

    def test_chat_degrades_when_history_call_hangs(self):
        release = threading.Event()

        def hung_lookup(name):
            release.wait()

        try:
            with (
                patch.object(main, "get_or_create_student", side_effect=hung_lookup),
                patch.object(main, "generate_response", _fake_generator),
            ):
                started = time.monotonic()
                with TestClient(main.app) as client:
                    response = client.post(
                        "/chat", json={"query": "test", "student_name": "Ana"}
                    )
                    release.set()
                elapsed = time.monotonic() - started
        finally:
            release.set()

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1)
        self.assertTrue(
            response.text.startswith("event: history_status\ndata: degraded\n\n")
        )
        self.assertIn("data: [DONE]\n\n", response.text)

    def test_chat_stream_is_independent_from_a_hung_write(self):
        release = threading.Event()

        def hung_save(*args):
            release.wait()

        try:
            with (
                patch.object(main, "get_or_create_student", return_value=1),
                patch.object(main, "get_history", return_value=[]),
                patch.object(main, "save_message", side_effect=hung_save),
                patch.object(main, "generate_response", _fake_generator),
            ):
                started = time.monotonic()
                with TestClient(main.app) as client:
                    response = client.post(
                        "/chat", json={"query": "test", "student_name": "Ana"}
                    )
                    release.set()
                elapsed = time.monotonic() - started
        finally:
            release.set()

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1)
        self.assertIn("data: Pensá en esto...\n\n", response.text)
        self.assertIn("data: [DONE]\n\n", response.text)

    def test_banner_is_absent_on_healthy_chat_and_present_on_degraded_chat(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_history", return_value=[]),
            patch.object(main, "save_message", side_effect=[101, 202]),
            patch.object(main, "generate_response", _fake_generator),
        ):
            healthy = self.client.post(
                "/chat", json={"query": "test", "student_name": "Ana"}
            )

        with (
            patch.object(
                main,
                "get_or_create_student",
                side_effect=HistoryUnavailableError("offline"),
            ),
            patch.object(main, "generate_response", _fake_generator),
        ):
            degraded = self.client.post(
                "/chat", json={"query": "test", "student_name": "Ana"}
            )

        self.assertNotIn("event: history_status", healthy.text)
        self.assertIn("event: history_status\ndata: degraded\n\n", degraded.text)

    def test_history_timeout_has_no_creation_or_welcome_side_effect(self):
        with (
            patch.object(
                main,
                "get_student_by_name",
                side_effect=HistoryUnavailableError("offline"),
            ),
            patch.object(main, "get_or_create_student") as create_student,
            patch.object(main, "save_message") as save_message,
        ):
            response = self.client.get("/history", params={"student_name": "Ana"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"messages": [], "degraded": True})
        create_student.assert_not_called()
        save_message.assert_not_called()

    def test_history_returns_synced_messages_after_recovery(self):
        with patch.object(
            main,
            "get_student_by_name",
            side_effect=HistoryUnavailableError("offline"),
        ):
            degraded = self.client.get(
                "/history", params={"student_name": "Ana"}
            )

        messages = [{"id": 1, "role": "user", "content": "test"}]
        with (
            patch.object(main, "get_student_by_name", return_value=1),
            patch.object(main, "get_history", return_value=messages),
        ):
            recovered = self.client.get(
                "/history", params={"student_name": "Ana"}
            )

        self.assertEqual(degraded.json(), {"messages": [], "degraded": True})
        self.assertEqual(
            recovered.json(), {"messages": messages, "degraded": False}
        )

    def test_delete_timeout_preserves_503_contract(self):
        release = threading.Event()

        def hung_owner(message_id):
            release.wait()

        try:
            with patch.object(
                main, "get_message_owner", side_effect=hung_owner
            ):
                with TestClient(main.app) as client:
                    response = client.delete(
                        "/messages/1", params={"student_name": "Ana"}
                    )
                    release.set()
        finally:
            release.set()

        self.assertEqual(response.status_code, 503)

    def test_lifespan_bootstrap_is_bounded(self):
        release = threading.Event()

        try:
            with patch.object(main, "init_db", side_effect=lambda: release.wait()):
                started = time.monotonic()
                with TestClient(main.app) as client:
                    response = client.get("/topics")
                    release.set()
                elapsed = time.monotonic() - started
        finally:
            release.set()

        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 1)


class HistoryTimeoutConfigurationTests(unittest.TestCase):
    def test_timeout_parser_uses_safe_default(self):
        self.assertEqual(main._parse_history_timeout(None), 5)
        self.assertEqual(main._parse_history_timeout("abc"), 5)
        self.assertEqual(main._parse_history_timeout("0"), 5)
        self.assertEqual(main._parse_history_timeout("2"), 2)

    def test_app_write_enqueue_uses_configured_timeout(self):
        with (
            patch.object(main, "HISTORY_TIMEOUT_SECONDS", 0.25),
            patch.object(main, "enqueue_write", return_value=MagicMock()) as enqueue,
        ):
            main._enqueue_history_write(lambda *_: 1, 1, "user", "message")

        enqueue.assert_called_once_with(
            ANY,
            1,
            "user",
            "message",
            call_timeout=0.25,
        )


if __name__ == "__main__":
    unittest.main()
