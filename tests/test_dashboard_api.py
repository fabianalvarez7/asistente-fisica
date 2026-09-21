"""Contract tests for the anonymous FastAPI professor dashboard."""

from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-key")

_fake_retrievers = MagicMock()
_fake_store_class = MagicMock()
_fake_store_class.return_value.count.return_value = 1
_fake_retrievers.VectorStore = _fake_store_class
_fake_retrievers.EmbeddingsModel = MagicMock
sys.modules["rag.retrievers"] = _fake_retrievers

from fastapi.testclient import TestClient  # noqa: E402

from rag import history as history_module  # noqa: E402

with patch.object(history_module, "init_db"):
    from app.main import DASHBOARD_ERROR_MESSAGE, app  # noqa: E402


class PublicDashboardApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_page_is_served_by_fastapi(self):
        response = self.client.get("/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Panel de profesores", response.text)
        self.assertNotIn("streamlit", response.text.lower())

    def test_dashboard_returns_only_approved_aggregate_shape(self):
        kpis = {
            "total_queries": 12,
            "unique_students": 4,
            "last_activity": "hace 2h",
            "student_id": 99,
        }
        topic_counts = [
            {
                "number": "IV",
                "title": "Dinámica",
                "count": 7,
                "content": "¿Cómo calculo la fuerza?",
            }
        ]

        with (
            patch("app.main.get_kpis", return_value=kpis),
            patch("app.main.get_topic_counts", return_value=topic_counts),
        ):
            response = self.client.get("/api/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "total_questions": 12,
                "students_represented": 4,
                "latest_activity": "hace 2h",
                "topic_counts": [
                    {"number": "IV", "title": "Dinámica", "count": 7}
                ],
                "topic_counts_approximate": True,
            },
        )
        for forbidden in ("content", "student_id", "student_name", "message", "query"):
            self.assertNotIn(forbidden, response.json())
            self.assertNotIn(forbidden, response.text)

    def test_dashboard_hides_database_failure_details(self):
        with patch(
            "app.main.get_kpis",
            side_effect=RuntimeError("token=secret database credentials"),
        ):
            response = self.client.get("/api/dashboard")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {"detail": DASHBOARD_ERROR_MESSAGE})
        self.assertNotIn("secret", response.text)


if __name__ == "__main__":
    unittest.main()
