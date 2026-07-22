"""Regression test for the SSE message-id handshake added in Task 4.

The frontend needs the ids of the persisted user and assistant messages so it
can attach working delete buttons to newly streamed turns. This test mocks the
RAG generator and the SQLite helpers, then verifies that ``POST /chat`` emits
``event: user_message_id`` and ``event: assistant_message_id`` frames around the
existing token stream.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

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
from app.main import app  # noqa: E402


def _fake_generator(query, history=None):
    yield "data: Pensá en esto...\n\n"
    yield "data: [DONE]\n\n"


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

        # User message is persisted before streaming and its id is announced first.
        self.assertIn("event: user_message_id\ndata: 101\n\n", body)
        # Assistant message is persisted on [DONE] and its id is announced before
        # the terminal frame reaches the client.
        self.assertIn("event: assistant_message_id\ndata: 202\n\n", body)
        # Existing token stream is preserved.
        self.assertIn("data: Pensá en esto...\n\n", body)
        self.assertIn("data: [DONE]\n\n", body)

        # save_message is called once for the user turn and once for the assistant.
        self.assertEqual(mock_save.call_count, 2)


if __name__ == "__main__":
    unittest.main()
