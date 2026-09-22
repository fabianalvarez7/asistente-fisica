"""Application integration coverage for the history availability boundary."""

from __future__ import annotations

import os
import sys
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
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
    from rag import history  # noqa: E402
    from rag.history import HistoryUnavailableError  # noqa: E402


def _fake_generator(query, history=None):
    yield "data: Pensá en esto...\n\n"
    yield "data: [DONE]\n\n"


@contextmanager
def _fake_turso_environment():
    """Configure fake remote callables and state shared by spawned workers."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        events_path = temp_path / "turso-events.log"
        original_sys_path = sys.path[:]
        sys.path.insert(0, temp_dir)
        pythonpath = os.pathsep.join(
            path for path in (temp_dir, os.getenv("PYTHONPATH", "")) if path
        )

        with patch.dict(
            os.environ,
            {
                "TURSO_DATABASE_URL": "libsql://fake.test",
                "TURSO_AUTH_TOKEN": "fake-token",
                "FAKE_TURSO_EVENTS_PATH": str(events_path),
                "FAKE_TURSO_MODE": "healthy",
                "PYTHONPATH": pythonpath,
            },
            clear=False,
        ):
            history._reset_connection()
            try:
                yield events_path
            finally:
                history._reset_connection()
                sys.path[:] = original_sys_path


def _record_fake_turso_event(event):
    path = os.environ["FAKE_TURSO_EVENTS_PATH"]
    with open(path, "a+", encoding="utf-8") as events:
        events.write(event + "\n")
        events.flush()
        events.seek(0)
        return len(events.readlines())


def _fake_turso_init_db():
    _record_fake_turso_event("init")


def _fake_turso_health_check():
    _record_fake_turso_event("health")
    if os.getenv("FAKE_TURSO_MODE") == "hang":
        while True:
            time.sleep(0.01)


def _fake_turso_get_or_create_student(name):
    _record_fake_turso_event(f"student:{name}")
    return 1


def _fake_turso_get_history(student_id, limit=None):
    del student_id, limit
    _record_fake_turso_event("history")
    return []


def _fake_turso_save_message(student_id, role, content):
    del student_id
    event_number = _record_fake_turso_event(f"save:{role}:{content}")
    return event_number


class RemoteHistoryApplicationIntegrationTests(unittest.TestCase):
    def test_lifespan_and_health_use_spawned_turso_boundary(self):
        with _fake_turso_environment() as events_path:
            with (
                patch.object(main, "HISTORY_TIMEOUT_SECONDS", 2),
                patch.object(main, "init_db", _fake_turso_init_db),
                patch.object(main, "check_history_health", _fake_turso_health_check),
            ):
                self.assertTrue(main.history_async.uses_cancellable_boundary())
                with TestClient(main.app) as client:
                    response = client.get("/health")
                events = events_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "history": "ok"})
        self.assertIn("init", events)
        self.assertIn("health", events)

    def test_turso_health_timeout_recovers_without_restart(self):
        with _fake_turso_environment():
            with (
                patch.object(main, "HISTORY_TIMEOUT_SECONDS", 2),
                patch.object(main, "init_db", _fake_turso_init_db),
                patch.object(main, "check_history_health", _fake_turso_health_check),
            ):
                with TestClient(main.app) as client:
                    os.environ["FAKE_TURSO_MODE"] = "hang"
                    degraded = client.get("/health")
                    os.environ["FAKE_TURSO_MODE"] = "healthy"
                    recovered = client.get("/health")

        self.assertEqual(degraded.status_code, 503)
        self.assertEqual(recovered.status_code, 200)

    def test_chat_queues_remote_writes_with_history_callable(self):
        with _fake_turso_environment() as events_path:
            with (
                patch.object(main, "HISTORY_TIMEOUT_SECONDS", 2),
                patch.object(main, "init_db", _fake_turso_init_db),
                patch.object(
                    main, "get_or_create_student", _fake_turso_get_or_create_student
                ),
                patch.object(main, "get_history", _fake_turso_get_history),
                patch.object(main, "save_message", _fake_turso_save_message),
                patch.object(main, "generate_response", _fake_generator),
            ):
                with TestClient(main.app) as client:
                    response = client.post(
                        "/chat", json={"query": "test", "student_name": "Ana"}
                    )
                events = events_path.read_text(encoding="utf-8").splitlines()

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("event: history_status", response.text)
        self.assertIn("event: user_message_id", response.text)
        self.assertIn("event: assistant_message_id", response.text)
        roles = [
            event.split(":", 2)[1]
            for event in events
            if event.startswith("save:")
        ]
        self.assertEqual(roles, ["user", "assistant"])


class RemoteHistoryCallableTests(unittest.TestCase):
    def test_remote_enqueue_remaps_transport_callable_for_spawn(self):
        pending = MagicMock()
        with (
            patch.object(
                main.history_async, "uses_cancellable_boundary", return_value=True
            ),
            patch.object(main, "enqueue_write", return_value=pending) as enqueue,
        ):
            result = main._enqueue_history_write(
                main._queued_save_message, 1, "user", "message"
            )

        self.assertIs(result, pending)
        self.assertIs(enqueue.call_args.args[0], main.save_message)


class HistoryApplicationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.timeout = patch.object(main, "HISTORY_TIMEOUT_SECONDS", 0.05)
        self.timeout.start()
        self.local_boundary = patch.object(
            main.history_async, "uses_cancellable_boundary", return_value=False
        )
        self.local_boundary.start()
        self.client = TestClient(main.app)

    def tearDown(self):
        self.local_boundary.stop()
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

    def test_chat_recovers_after_degraded_request_without_restart(self):
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

        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_history", return_value=[]),
            patch.object(main, "save_message", side_effect=[101, 202]),
            patch.object(main, "generate_response", _fake_generator),
        ):
            recovered = self.client.post(
                "/chat", json={"query": "test", "student_name": "Ana"}
            )

        self.assertIn("event: history_status\ndata: degraded\n\n", degraded.text)
        self.assertNotIn("event: history_status", recovered.text)
        self.assertIn("data: [DONE]\n\n", recovered.text)

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

    def test_lifespan_checks_history_after_initialize_timeout(self):
        release = threading.Event()

        try:
            with (
                patch.object(main, "init_db", side_effect=lambda: release.wait()),
                patch.object(main, "check_history_health") as health_check,
            ):
                with TestClient(main.app) as client:
                    release.set()
                    self.assertEqual(client.get("/topics").status_code, 200)
        finally:
            release.set()

        health_check.assert_called_once()

    def test_health_endpoint_reports_persistence_and_recovers_without_restart(self):
        with patch.object(main, "check_history_health") as health_check:
            healthy = self.client.get("/health")

        with patch.object(
            main,
            "check_history_health",
            side_effect=HistoryUnavailableError("offline"),
        ):
            degraded = self.client.get("/health")

        with patch.object(main, "check_history_health") as health_check:
            recovered = self.client.get("/health")

        self.assertEqual(healthy.status_code, 200)
        self.assertEqual(healthy.json(), {"status": "ok", "history": "ok"})
        self.assertEqual(degraded.status_code, 503)
        self.assertEqual(recovered.status_code, 200)
        health_check.assert_called_once()

    def test_keepalive_uses_read_only_history_health_probe(self):
        workflow = (
            Path(__file__).resolve().parents[1] / ".github/workflows/keepalive.yml"
        ).read_text()
        self.assertIn('"${SPACE_URL}/health"', workflow)
        self.assertNotIn('"${SPACE_URL}/topics"', workflow)


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
