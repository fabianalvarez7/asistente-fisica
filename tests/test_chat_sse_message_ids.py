"""Regression tests for SSE persistence and history degraded mode.

The frontend needs the ids of the persisted user and assistant messages so it
can attach working delete buttons to newly streamed turns. This test mocks the
RAG generator and the SQLite helpers, then verifies that ``POST /chat`` emits
``event: user_message_id`` and ``event: assistant_message_id`` frames around the
existing token stream.
"""

import os
import sqlite3
import sys
import unittest
from unittest.mock import MagicMock, call, patch

# Boot assertions in app.main require GROQ_API_KEY and a non-empty ChromaDB
# collection. Set a dummy key and replace the retrievers module with a fake
# before importing app.main, so the test never calls Groq or loads embeddings.
os.environ.setdefault("GROQ_API_KEY", "test-key")

_fake_retrievers = MagicMock()
_fake_store_class = MagicMock()
_fake_store_class.return_value.count.return_value = 1
_fake_retrievers.VectorStore = _fake_store_class
_fake_retrievers.EmbeddingsModel = MagicMock
sys.modules["rag.retrievers"] = _fake_retrievers

from fastapi.testclient import TestClient  # noqa: E402
from rag import history as history_module  # noqa: E402
from rag.history import HistoryUnavailableError  # noqa: E402

with patch.object(history_module, "init_db"):
    from app.main import ERROR_FALLBACK, _log_history_failure, app  # noqa: E402


def _fake_generator(query, history=None):
    yield "data: Pensá en esto...\n\n"
    yield "data: [DONE]\n\n"


def _wrapped_history_error(cause: Exception) -> HistoryUnavailableError:
    error = HistoryUnavailableError(
        "History persistence remained unavailable after reconnect"
    )
    error.__cause__ = cause
    return error


def _sqlite_operational_error(code: int) -> sqlite3.OperationalError:
    error = sqlite3.OperationalError("sensitive driver detail")
    error.sqlite_errorcode = code
    return error


class ChatSseMessageIdTests(unittest.TestCase):
    """POST /chat yields message-id events before and after the assistant text."""

    def setUp(self):
        self.client = TestClient(app)

    def test_sse_stream_exposes_user_and_assistant_message_ids(self):
        with (
            patch("app.main.generate_response", _fake_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch("app.main.save_message", side_effect=[101, 202]) as mock_save,
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")

        self.assertEqual(
            body,
            "event: user_message_id\ndata: 101\n\n"
            "data: Pensá en esto...\n\n"
            "event: assistant_message_id\ndata: 202\n\n"
            "data: [DONE]\n\n",
        )

        # save_message is called once for the user turn and once for the assistant.
        self.assertEqual(mock_save.call_count, 2)

    def test_chat_generates_without_student_persistence(self):
        generator = MagicMock(side_effect=_fake_generator)
        with (
            patch("app.main.generate_response", generator),
            patch(
                "app.main.get_or_create_student",
                side_effect=HistoryUnavailableError,
            ),
            patch("app.main.save_message") as mock_save,
            patch("app.main.get_history") as mock_history,
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("data: Pensá en esto...\n\n", body)
        self.assertIn("data: [DONE]\n\n", body)
        self.assertNotIn("event: user_message_id", body)
        generator.assert_called_once_with("test", history=[])
        mock_save.assert_not_called()
        mock_history.assert_not_called()

    def test_chat_generates_when_user_message_persistence_fails(self):
        generator = MagicMock(side_effect=_fake_generator)
        with (
            patch("app.main.generate_response", generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch(
                "app.main.save_message",
                side_effect=[HistoryUnavailableError(), 202],
            ),
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("data: Pensá en esto...\n\n", body)
        self.assertIn("data: [DONE]\n\n", body)
        self.assertNotIn("event: user_message_id", body)
        self.assertIn("event: assistant_message_id\ndata: 202\n\n", body)
        generator.assert_called_once_with("test", history=[])

    def test_chat_uses_empty_history_when_history_read_fails(self):
        generator = MagicMock(side_effect=_fake_generator)
        with (
            patch("app.main.generate_response", generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", side_effect=HistoryUnavailableError),
            patch("app.main.save_message", side_effect=[101, 202]),
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data: Pensá en esto...\n\n", response.text)
        generator.assert_called_once_with("test", history=[])

    def test_assistant_output_survives_persistence_failure(self):
        with (
            patch("app.main.generate_response", _fake_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch(
                "app.main.save_message",
                side_effect=[101, HistoryUnavailableError()],
            ),
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.content.decode("utf-8")
        self.assertIn("data: Pensá en esto...\n\n", body)
        self.assertIn("data: [DONE]\n\n", body)
        self.assertNotIn("event: error", body)
        self.assertNotIn("event: assistant_message_id", body)

    def _assert_history_degrades(
        self,
        *,
        lookup_result=None,
        lookup_error=None,
        create_error=None,
        welcome_error=None,
        read_error=None,
    ):
        with (
            patch(
                "app.main.get_student_by_name",
                return_value=lookup_result,
                side_effect=lookup_error,
            ),
            patch(
                "app.main.get_or_create_student",
                return_value=1,
                side_effect=create_error,
            ),
            patch(
                "app.main.save_message",
                return_value=10,
                side_effect=welcome_error,
            ),
            patch(
                "app.main.get_history",
                return_value=[],
                side_effect=read_error,
            ),
        ):
            response = self.client.get(
                "/history",
                params={"student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"messages": []})

    def test_history_endpoint_degrades_when_lookup_fails(self):
        self._assert_history_degrades(lookup_error=HistoryUnavailableError())

    def test_history_endpoint_degrades_when_create_fails(self):
        self._assert_history_degrades(create_error=HistoryUnavailableError())

    def test_history_endpoint_degrades_when_welcome_save_fails(self):
        self._assert_history_degrades(welcome_error=HistoryUnavailableError())

    def test_history_endpoint_degrades_when_final_read_fails(self):
        self._assert_history_degrades(
            lookup_result=1,
            read_error=HistoryUnavailableError(),
        )

    def test_chat_does_not_swallow_non_history_exception(self):
        with patch(
            "app.main.get_or_create_student",
            side_effect=RuntimeError("programming defect"),
        ):
            with self.assertRaisesRegex(RuntimeError, "programming defect"):
                self.client.post(
                    "/chat",
                    json={"query": "test", "student_name": "Ana"},
                )

    def test_history_endpoint_does_not_swallow_non_history_exception(self):
        with patch(
            "app.main.get_student_by_name",
            side_effect=RuntimeError("programming defect"),
        ):
            with self.assertRaisesRegex(RuntimeError, "programming defect"):
                self.client.get(
                    "/history",
                    params={"student_name": "Ana"},
                )

    def test_log_uses_root_cause_class_without_sensitive_exception_text(self):
        cause = _sqlite_operational_error(sqlite3.SQLITE_BUSY)
        error = _wrapped_history_error(cause)

        with patch("app.main.logger.error") as error_log:
            _log_history_failure("read_recent_history", error)

        error_log.assert_called_once_with(
            "History unavailable; continuing in degraded mode "
            "(operation=%s, wrapper_type=%s, root_cause_type=%s)",
            "read_recent_history",
            "HistoryUnavailableError",
            "OperationalError",
        )
        rendered_log = error_log.call_args.args[0] % error_log.call_args.args[1:]
        self.assertNotIn(str(cause), rendered_log)

    def test_yielded_generation_error_persists_fallback_once_in_sse_order(self):
        def yielded_error_generator(query, history=None):
            yield "data: Respuesta parcial\n\n"
            yield f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            yield "data: [DONE]\n\n"

        with (
            patch("app.main.generate_response", yielded_error_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch("app.main.save_message", side_effect=[101, 202]) as mock_save,
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(
            response.text,
            "event: user_message_id\ndata: 101\n\n"
            "data: Respuesta parcial\n\n"
            "event: assistant_message_id\ndata: 202\n\n"
            f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            "data: [DONE]\n\n",
        )
        self.assertEqual(
            mock_save.call_args_list,
            [
                call(1, "user", "test"),
                call(1, "assistant", ERROR_FALLBACK),
            ],
        )

    def test_distinct_yielded_error_is_forwarded_after_persisted_fallback(self):
        distinct_error = "Fallo específico del generador"

        def yielded_error_generator(query, history=None):
            yield f"event: error\ndata: {distinct_error}\n\n"
            yield "data: [DONE]\n\n"

        with (
            patch("app.main.generate_response", yielded_error_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch("app.main.save_message", side_effect=[101, 202]) as mock_save,
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertNotEqual(distinct_error, ERROR_FALLBACK)
        self.assertEqual(
            response.text,
            "event: user_message_id\ndata: 101\n\n"
            "event: assistant_message_id\ndata: 202\n\n"
            f"event: error\ndata: {distinct_error}\n\n"
            "data: [DONE]\n\n",
        )
        self.assertEqual(
            mock_save.call_args_list,
            [
                call(1, "user", "test"),
                call(1, "assistant", ERROR_FALLBACK),
            ],
        )

    def test_yielded_error_then_raise_persists_fallback_at_most_once(self):
        distinct_error = "Fallo específico antes de excepción"

        def yielded_error_then_raise(query, history=None):
            yield f"event: error\ndata: {distinct_error}\n\n"
            raise RuntimeError("generation failed after yielded error")

        with (
            patch("app.main.generate_response", yielded_error_then_raise),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch(
                "app.main.save_message",
                side_effect=[101, 202, 303],
            ) as mock_save,
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(
            response.text,
            "event: user_message_id\ndata: 101\n\n"
            "event: assistant_message_id\ndata: 202\n\n"
            f"event: error\ndata: {distinct_error}\n\n"
            f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            "data: [DONE]\n\n",
        )
        self.assertEqual(
            mock_save.call_args_list,
            [
                call(1, "user", "test"),
                call(1, "assistant", ERROR_FALLBACK),
            ],
        )

    def test_yielded_generation_error_survives_fallback_persistence_failure(self):
        def yielded_error_generator(query, history=None):
            yield "data: Respuesta parcial\n\n"
            yield f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            yield "data: [DONE]\n\n"

        persistence_error = _wrapped_history_error(
            _sqlite_operational_error(sqlite3.SQLITE_BUSY)
        )
        with (
            patch("app.main.generate_response", yielded_error_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch(
                "app.main.save_message",
                side_effect=[101, persistence_error],
            ) as mock_save,
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(
            response.text,
            "event: user_message_id\ndata: 101\n\n"
            "data: Respuesta parcial\n\n"
            f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            "data: [DONE]\n\n",
        )
        self.assertEqual(
            mock_save.call_args_list,
            [
                call(1, "user", "test"),
                call(1, "assistant", ERROR_FALLBACK),
            ],
        )

    def test_generation_failure_before_first_token_terminates_after_fallback(self):
        def failing_generator(query, history=None):
            raise RuntimeError("generation failed")
            yield  # pragma: no cover - makes this a generator

        persistence_error = _wrapped_history_error(
            _sqlite_operational_error(sqlite3.SQLITE_BUSY)
        )
        with (
            patch("app.main.generate_response", failing_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch("app.main.save_message", side_effect=[101, persistence_error]),
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(
            response.text,
            "event: user_message_id\ndata: 101\n\n"
            f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            "data: [DONE]\n\n",
        )

    def test_mid_stream_generation_failure_terminates_after_fallback(self):
        def failing_generator(query, history=None):
            yield "data: Respuesta parcial\n\n"
            raise RuntimeError("generation failed")

        persistence_error = _wrapped_history_error(
            _sqlite_operational_error(sqlite3.SQLITE_BUSY)
        )
        with (
            patch("app.main.generate_response", failing_generator),
            patch("app.main.get_or_create_student", return_value=1),
            patch("app.main.get_history", return_value=[]),
            patch("app.main.save_message", side_effect=[101, persistence_error]),
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(
            response.text,
            "event: user_message_id\ndata: 101\n\n"
            "data: Respuesta parcial\n\n"
            f"event: error\ndata: {ERROR_FALLBACK}\n\n"
            "data: [DONE]\n\n",
        )


class HistoryPersistenceBoundaryTests(unittest.TestCase):
    def test_repeated_sqlite_availability_error_is_translated_with_cause(self):
        attempts = []

        @history_module._reconnect_on_failure
        def unavailable_operation():
            error = _sqlite_operational_error(sqlite3.SQLITE_BUSY)
            attempts.append(error)
            raise error

        with patch.object(history_module, "_reset_connection") as reset:
            with self.assertRaises(HistoryUnavailableError) as raised:
                unavailable_operation()

        self.assertEqual(len(attempts), 2)
        self.assertIs(raised.exception.__cause__, attempts[-1])
        reset.assert_called_once_with()

    def test_unrelated_exception_propagates_unchanged(self):
        defect = ValueError("programming defect")

        @history_module._reconnect_on_failure
        def broken_operation():
            raise defect

        with patch.object(history_module, "_reset_connection") as reset:
            with self.assertRaises(ValueError) as raised:
                broken_operation()

        self.assertIs(raised.exception, defect)
        reset.assert_not_called()

    def test_sqlite_sql_and_schema_errors_are_not_translated(self):
        connection = sqlite3.connect(":memory:")
        try:
            for statement in ("SELEC 1", "SELECT * FROM missing_table"):
                with self.subTest(statement=statement):
                    attempts = 0

                    @history_module._reconnect_on_failure
                    def defective_operation():
                        nonlocal attempts
                        attempts += 1
                        connection.execute(statement)

                    with patch.object(history_module, "_reset_connection") as reset:
                        with self.assertRaises(sqlite3.OperationalError):
                            defective_operation()

                    self.assertEqual(attempts, 1)
                    reset.assert_not_called()
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
