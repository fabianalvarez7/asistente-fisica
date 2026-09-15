"""Tests for the interactive topics endpoint and dashboard compatibility.

The frontend consumes ``GET /topics`` to render an accordion of Socratic
seed questions. These tests guard the response shape, the draft-marker
convention, the 500-character chat limit, and the dashboard aggregation
that still only reads ``numero`` and ``titulo``.
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

from rag import history as history_module  # noqa: E402
from rag.topics import _TOPICS, load_topics  # noqa: E402

with patch.object(history_module, "init_db"):
    from app.main import app  # noqa: E402

from dashboard.queries import get_topic_counts  # noqa: E402


class TopicDataTests(unittest.TestCase):
    """Invariants on the static topic list."""

    def test_load_topics_returns_preguntas_per_unit(self):
        unidades = load_topics()
        self.assertEqual(len(unidades), 12)
        for unidad in unidades:
            self.assertIn("numero", unidad)
            self.assertIn("titulo", unidad)
            self.assertIn("preguntas", unidad)
            preguntas = unidad["preguntas"]
            self.assertGreaterEqual(len(preguntas), 2)
            self.assertLessEqual(len(preguntas), 3)
            for pregunta in preguntas:
                self.assertTrue(pregunta.endswith("?"))

    def test_all_preguntas_are_marked_as_borrador_initially(self):
        expected_prefix = "[BORRADOR — falta validar con Nair]"
        for unidad in load_topics():
            for pregunta in unidad["preguntas"]:
                self.assertTrue(
                    pregunta.startswith(expected_prefix),
                    f"Prompt missing draft prefix: {pregunta!r}",
                )

    def test_all_preguntas_within_max_length(self):
        for unidad in load_topics():
            for pregunta in unidad["preguntas"]:
                self.assertLessEqual(
                    len(pregunta),
                    500,
                    f"Prompt exceeds 500 chars ({len(pregunta)}): {pregunta!r}",
                )


class TopicsEndpointTests(unittest.TestCase):
    """``GET /topics`` passes the new shape through unchanged."""

    def setUp(self):
        self.client = TestClient(app)

    def test_topics_endpoint_returns_preguntas_per_unit(self):
        response = self.client.get("/topics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("unidades", data)
        self.assertEqual(len(data["unidades"]), 12)
        for unidad in data["unidades"]:
            self.assertIn("numero", unidad)
            self.assertIn("titulo", unidad)
            self.assertIn("preguntas", unidad)
            self.assertGreaterEqual(len(unidad["preguntas"]), 2)
            self.assertLessEqual(len(unidad["preguntas"]), 3)

    def test_topics_endpoint_marks_all_preguntas_as_borrador(self):
        expected_prefix = "[BORRADOR — falta validar con Nair]"
        response = self.client.get("/topics")
        self.assertEqual(response.status_code, 200)
        for unidad in response.json()["unidades"]:
            for pregunta in unidad["preguntas"]:
                self.assertTrue(pregunta.startswith(expected_prefix))

    def test_topics_endpoint_prompts_within_maxlength(self):
        response = self.client.get("/topics")
        self.assertEqual(response.status_code, 200)
        for unidad in response.json()["unidades"]:
            for pregunta in unidad["preguntas"]:
                self.assertLessEqual(len(pregunta), 500)


class DashboardBackwardCompatTests(unittest.TestCase):
    """``get_topic_counts`` keeps working when units gain ``preguntas``."""

    def test_get_topic_counts_shape_unchanged(self):
        fake_conn = MagicMock()
        fake_conn.execute.return_value.fetchall.return_value = []
        with patch("dashboard.queries._get_connection", return_value=fake_conn):
            counts = get_topic_counts()

        self.assertEqual(len(counts), len(_TOPICS))
        for item, topic in zip(counts, _TOPICS):
            self.assertEqual(item, {
                "number": topic["numero"],
                "title": topic["titulo"],
                "count": 0,
            })


if __name__ == "__main__":
    unittest.main()
