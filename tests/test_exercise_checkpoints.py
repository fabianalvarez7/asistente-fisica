"""Deterministic checkpoint validation and exercise-tutor API contracts."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("GROQ_API_KEY", "test-key")

_fake_retrievers = MagicMock()
_fake_store_class = MagicMock()
_fake_store_class.return_value.count.return_value = 1
_fake_retrievers.VectorStore = _fake_store_class
_fake_retrievers.EmbeddingsModel = MagicMock
sys.modules["rag.retrievers"] = _fake_retrievers

from fastapi.testclient import TestClient  # noqa: E402

from rag.exercises import (  # noqa: E402
    evaluate_checkpoint,
    get_exercise,
    serialize_progress,
    serialize_for_student,
)
from rag import history as history_module  # noqa: E402
from tests.test_exercise_frontend import _run_node_contract  # noqa: E402

with patch.object(history_module, "init_db"):
    import app.main as main  # noqa: E402


EXERCISE_ID = "cinematica-1d-ejercicio-02"


class CheckpointDomainTests(unittest.TestCase):
    def setUp(self):
        self.exercise = get_exercise(EXERCISE_ID)

    def test_catalog_exposes_metadata_and_progress_exposes_current_options(self):
        catalog = serialize_for_student(self.exercise)
        self.assertNotIn("teacher_key", catalog)
        self.assertNotIn("checkpoints", catalog)
        self.assertNotIn("guidance", catalog)
        self.assertNotIn("correct_option_ids", str(catalog))

        progress = serialize_progress(self.exercise, 0)
        self.assertEqual(
            [option["id"] for option in progress["current_checkpoint"]["options"]],
            ["time-position-meters-seconds", "time-velocity-meters-seconds", "position-time-seconds-meters"],
        )
        self.assertNotIn("constant-acceleration", str(progress))
        self.assertNotIn("teacher_key", str(progress))

    def test_checkpoint_parts_follow_the_curated_exercise_sections(self):
        self.assertEqual(
            [checkpoint.part for checkpoint in self.exercise.checkpoints[:5]],
            ["a"] * 5,
        )
        self.assertEqual(
            [checkpoint.part for checkpoint in self.exercise.checkpoints[5:]],
            ["b"] * (len(self.exercise.checkpoints) - 5),
        )
        self.assertEqual(serialize_progress(self.exercise, 0)["current_checkpoint"]["part"], "a")
        self.assertEqual(serialize_progress(self.exercise, 5)["current_checkpoint"]["part"], "b")

    def test_graph_checkpoints_expose_only_current_safe_descriptors(self):
        for index, checkpoint_id, absent_ids in (
            (
                6,
                "velocity-graph-shape",
                ("acceleration-graph-shape", "acceleration-graph-correct"),
            ),
            (
                10,
                "acceleration-graph-shape",
                ("final-verification", "velocity-graph-correct"),
            ),
        ):
            with self.subTest(checkpoint_id=checkpoint_id):
                progress = serialize_progress(self.exercise, index)
                current = progress["current_checkpoint"]
                self.assertEqual(current["id"], checkpoint_id)
                self.assertEqual(current["presentation"], "graph")
                self.assertTrue(all(option["graph"] for option in current["options"]))
                for absent_id in absent_ids:
                    self.assertNotIn(absent_id, str(progress))
                self.assertNotIn("correct_option_ids", str(progress))
                self.assertNotIn("teacher_key", str(progress))

    def test_graph_checkpoint_correct_and_wrong_domain_branches(self):
        for checkpoint_id, correct_id, wrong_id in (
            ("velocity-graph-shape", "velocity-graph-correct", "velocity-graph-horizontal"),
            ("acceleration-graph-shape", "acceleration-graph-correct", "acceleration-graph-zero"),
        ):
            with self.subTest(checkpoint_id=checkpoint_id):
                correct = evaluate_checkpoint(self.exercise, checkpoint_id, [correct_id])
                wrong = evaluate_checkpoint(self.exercise, checkpoint_id, [wrong_id])
                self.assertEqual(correct["result"], "correct")
                self.assertTrue(correct["advanced"])
                self.assertEqual(wrong["result"], "incorrect")
                self.assertFalse(wrong["advanced"])

    def test_graph_checkpoints_reject_unknown_and_mixed_option_ids(self):
        for checkpoint_id, correct_id in (
            ("velocity-graph-shape", "velocity-graph-correct"),
            ("acceleration-graph-shape", "acceleration-graph-correct"),
        ):
            for answer_ids in (["not-a-graph-option"], [correct_id, "not-a-graph-option"]):
                with self.subTest(checkpoint_id=checkpoint_id, answer_ids=answer_ids):
                    result = evaluate_checkpoint(self.exercise, checkpoint_id, answer_ids)

                self.assertEqual(result["result"], "unknown")
                self.assertFalse(result["advanced"])

    def test_every_checkpoint_accepts_its_curated_answer(self):
        for checkpoint in self.exercise.checkpoints:
            result = evaluate_checkpoint(
                self.exercise,
                checkpoint.id,
                list(checkpoint.correct_option_ids),
            )
            self.assertEqual(result["result"], "correct", checkpoint.id)
            self.assertTrue(result["advanced"], checkpoint.id)

    def test_wrong_partial_and_unknown_answers_do_not_advance(self):
        multi = next(
            checkpoint
            for checkpoint in self.exercise.checkpoints
            if checkpoint.input_type == "multi_select"
        )
        partial = evaluate_checkpoint(
            self.exercise,
            multi.id,
            [multi.correct_option_ids[0]],
        )
        self.assertEqual(partial["result"], "partially_correct")
        self.assertFalse(partial["advanced"])

        wrong = evaluate_checkpoint(self.exercise, multi.id, ["not-an-option"])
        self.assertEqual(wrong["result"], "unknown")
        self.assertFalse(wrong["advanced"])

        hint = evaluate_checkpoint(self.exercise, multi.id, [], action="help")
        self.assertEqual(hint["result"], "unknown")
        self.assertFalse(hint["advanced"])
        self.assertNotIn("teacher_key", str(hint))


class CheckpointApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_wrong_answer_does_not_advance(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=0),
            patch.object(main, "advance_exercise_progress") as advance_progress,
            patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock),
        ):
            response = self.client.post(
                f"/api/exercises/{EXERCISE_ID}/checkpoint",
                json={
                    "student_name": "Ana",
                    "checkpoint_id": "read-axes-units",
                    "answer_ids": ["position-time-seconds-meters"],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "incorrect")
        self.assertFalse(response.json()["advanced"])
        advance_progress.assert_not_called()

    def test_correct_answer_advances_and_returns_only_next_public_checkpoint(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=0),
            patch.object(main, "advance_exercise_progress", return_value=(1, True)),
            patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock),
        ):
            response = self.client.post(
                f"/api/exercises/{EXERCISE_ID}/checkpoint",
                json={
                    "student_name": "Ana",
                    "checkpoint_id": "read-axes-units",
                    "answer_ids": ["time-position-meters-seconds"],
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["result"], "correct")
        self.assertTrue(body["advanced"])
        self.assertEqual(body["progress"]["current_index"], 1)
        self.assertNotIn("teacher_key", str(body))
        self.assertNotIn("correct_option_ids", str(body))

    def test_graph_checkpoint_correct_and_wrong_api_branches(self):
        graph_checkpoints = (
            (6, "velocity-graph-shape", "velocity-graph-correct", "velocity-graph-horizontal"),
            (10, "acceleration-graph-shape", "acceleration-graph-correct", "acceleration-graph-zero"),
        )
        for index, checkpoint_id, correct_id, wrong_id in graph_checkpoints:
            with self.subTest(checkpoint_id=checkpoint_id, branch="wrong"):
                with (
                    patch.object(main, "get_or_create_student", return_value=1),
                    patch.object(main, "get_exercise_progress", return_value=index),
                    patch.object(main, "advance_exercise_progress") as advance_progress,
                    patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock),
                ):
                    response = self.client.post(
                        f"/api/exercises/{EXERCISE_ID}/checkpoint",
                        json={
                            "student_name": "Ana",
                            "checkpoint_id": checkpoint_id,
                            "answer_ids": [wrong_id],
                        },
                    )
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["result"], "incorrect")
                self.assertFalse(response.json()["advanced"])
                advance_progress.assert_not_called()

            with self.subTest(checkpoint_id=checkpoint_id, branch="correct"):
                with (
                    patch.object(main, "get_or_create_student", return_value=1),
                    patch.object(main, "get_exercise_progress", return_value=index),
                    patch.object(main, "advance_exercise_progress", return_value=(index + 1, True)),
                    patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock),
                ):
                    response = self.client.post(
                        f"/api/exercises/{EXERCISE_ID}/checkpoint",
                        json={
                            "student_name": "Ana",
                            "checkpoint_id": checkpoint_id,
                            "answer_ids": [correct_id],
                        },
                    )
                body = response.json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(body["result"], "correct")
                self.assertTrue(body["advanced"])
                self.assertEqual(body["progress"]["current_index"], index + 1)
                self.assertNotIn("correct_option_ids", response.text)

    def test_graph_checkpoint_rejects_unknown_and_mixed_option_ids_without_advancing(self):
        graph_checkpoints = (
            (6, "velocity-graph-shape", "velocity-graph-correct"),
            (10, "acceleration-graph-shape", "acceleration-graph-correct"),
        )
        for index, checkpoint_id, correct_id in graph_checkpoints:
            for answer_ids in (["not-a-graph-option"], [correct_id, "not-a-graph-option"]):
                with self.subTest(checkpoint_id=checkpoint_id, answer_ids=answer_ids):
                    with (
                        patch.object(main, "get_or_create_student", return_value=1),
                        patch.object(main, "get_exercise_progress", return_value=index),
                        patch.object(main, "advance_exercise_progress") as advance_progress,
                        patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock),
                    ):
                        response = self.client.post(
                            f"/api/exercises/{EXERCISE_ID}/checkpoint",
                            json={
                                "student_name": "Ana",
                                "checkpoint_id": checkpoint_id,
                                "answer_ids": answer_ids,
                            },
                        )

                    body = response.json()
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(body["result"], "unknown")
                    self.assertFalse(body["advanced"])
                    self.assertEqual(body["progress"]["current_index"], index)
                    advance_progress.assert_not_called()

    def test_hint_does_not_advance_or_expose_teacher_key(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=0),
            patch.object(main, "advance_exercise_progress") as advance_progress,
            patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock),
        ):
            response = self.client.post(
                f"/api/exercises/{EXERCISE_ID}/checkpoint",
                json={
                    "student_name": "Ana",
                    "checkpoint_id": "read-axes-units",
                    "action": "hint",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "unknown")
        self.assertFalse(response.json()["advanced"])
        self.assertNotIn("teacher_key", response.text)
        advance_progress.assert_not_called()

    def test_checkpoint_id_cannot_jump_ahead(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=0),
        ):
            response = self.client.post(
                f"/api/exercises/{EXERCISE_ID}/checkpoint",
                json={
                    "student_name": "Ana",
                    "checkpoint_id": "motion-model",
                    "answer_ids": ["constant-acceleration"],
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["progress"]["current_index"], 0)

    def test_progress_reload_returns_only_the_canonical_current_checkpoint(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=1),
        ):
            response = self.client.get(
                f"/api/exercises/{EXERCISE_ID}/progress",
                params={"student_name": "Ana"},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["current_index"], 1)
        self.assertEqual(body["current_checkpoint"]["id"], "motion-model")
        self.assertIn("constant-acceleration", str(body))
        self.assertNotIn("initial-position-zero", str(body))
        self.assertNotIn("correct_option_ids", str(body))

    def test_incomplete_progress_does_not_include_completed_review(self):
        exercise = get_exercise(EXERCISE_ID)
        progress = serialize_progress(exercise, 0)

        self.assertNotIn("completed_review", progress)
        self.assertNotIn("x(10)=120 m", str(progress))

    def test_completed_progress_contains_checkpoint_questions_and_correct_answers(self):
        exercise = get_exercise(EXERCISE_ID)
        progress = serialize_progress(exercise, len(exercise.checkpoints))

        self.assertTrue(progress["complete"])
        self.assertEqual(len(progress["completed_review"]), len(exercise.checkpoints))
        first = progress["completed_review"][0]
        self.assertEqual(first["question"], exercise.checkpoints[0].prompt)
        self.assertEqual(
            first["correct_answers"][0]["label"],
            "t en segundos y x en metros",
        )
        self.assertEqual(
            first["correct_answers"][0]["value"],
            "time-position-meters-seconds",
        )
        self.assertNotIn("teacher_key", str(progress))

    def test_completed_progress_api_exposes_review_only_at_completion(self):
        exercise = get_exercise(EXERCISE_ID)
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(
                main,
                "get_exercise_progress",
                return_value=len(exercise.checkpoints),
            ),
        ):
            response = self.client.get(
                f"/api/exercises/{EXERCISE_ID}/progress",
                params={"student_name": "Ana"},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(body["complete"])
        self.assertEqual(len(body["completed_review"]), len(exercise.checkpoints))
        self.assertNotIn("teacher_key", response.text)

    def test_graph_progress_api_returns_only_current_graph_options(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=6),
        ):
            response = self.client.get(
                f"/api/exercises/{EXERCISE_ID}/progress",
                params={"student_name": "Ana"},
            )

        body = response.json()
        current = body["current_checkpoint"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(current["id"], "velocity-graph-shape")
        self.assertEqual(
            [option["id"] for option in current["options"]],
            [
                "velocity-graph-correct",
                "velocity-graph-horizontal",
                "velocity-graph-decreasing",
                "velocity-graph-curve",
            ],
        )
        self.assertTrue(all(option["graph"] for option in current["options"]))
        self.assertNotIn("acceleration-graph-correct", response.text)
        self.assertNotIn("teacher_key", response.text)

    def test_progress_rejects_empty_typed_name(self):
        response = self.client.get(
            f"/api/exercises/{EXERCISE_ID}/progress",
            params={"student_name": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "student_name cannot be empty")

    def test_exercise_history_review_filters_teacher_only_assistant_content(self):
        persisted_messages = [
            {
                "id": 1,
                "role": "user",
                "content": "Respuesta: t en segundos y x en metros",
                "created_at": "2026-01-01T00:00:00Z",
            },
            {
                "id": 2,
                "role": "assistant",
                "content": "Leemos una posición x medida en metros en función del tiempo t medido en segundos.",
                "created_at": "2026-01-01T00:00:01Z",
            },
            {
                "id": 3,
                "role": "assistant",
                "content": "teacher_key: x(t) = 6t + 0.6t²; future answer: x(20)=360 m",
                "created_at": "2026-01-01T00:00:02Z",
            },
            {
                "id": 4,
                "role": "user",
                "content": "¿Cuál es la solución completa?",
                "created_at": "2026-01-01T00:00:03Z",
            },
        ]
        with (
            patch.object(main, "get_student_by_name", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=0),
            patch.object(main, "get_history", return_value=persisted_messages),
        ):
            response = self.client.get(
                "/history",
                params={"student_name": "Ana", "exercise_id": EXERCISE_ID},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["messages"], persisted_messages[:2])
        self.assertNotIn("teacher_key", response.text)
        self.assertNotIn("x(20)=360 m", response.text)

    def test_completed_exercise_history_returns_only_canonical_review(self):
        exercise = get_exercise(EXERCISE_ID)
        persisted_messages = [
            {"role": "user", "content": "Pedí una pista"},
            {"role": "assistant", "content": exercise.checkpoints[0].hint},
            {"role": "user", "content": "Necesité ayuda"},
            {"role": "assistant", "content": "Todavía no. Revisá la idea y volvé a intentarlo."},
            {"role": "user", "content": "Respuesta: intento anterior"},
            {"role": "assistant", "content": "feedback de retry"},
        ]
        with (
            patch.object(main, "get_student_by_name", return_value=1),
            patch.object(
                main,
                "get_exercise_progress",
                return_value=len(exercise.checkpoints),
            ),
            patch.object(main, "get_history", return_value=persisted_messages) as get_history,
        ):
            response = self.client.get(
                "/history",
                params={"student_name": "Ana", "exercise_id": EXERCISE_ID},
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["messages"], [])
        self.assertEqual(
            body["completed_review"],
            serialize_progress(exercise, len(exercise.checkpoints))["completed_review"],
        )
        self.assertNotIn("Pedí una pista", response.text)
        self.assertNotIn("Necesité ayuda", response.text)
        self.assertNotIn("Todavía no", response.text)
        self.assertNotIn("feedback de retry", response.text)
        self.assertNotIn("teacher_key", response.text)
        get_history.assert_not_called()

    def test_stale_submission_returns_canonical_progress(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(main, "get_exercise_progress", return_value=1),
        ):
            response = self.client.post(
                f"/api/exercises/{EXERCISE_ID}/checkpoint",
                json={
                    "student_name": "Ana",
                    "checkpoint_id": "read-axes-units",
                    "answer_ids": ["time-position-meters-seconds"],
                },
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["progress"]["current_index"], 1)

    def test_checkpoint_submission_returns_retryable_503_when_progress_read_fails(self):
        with (
            patch.object(main, "get_or_create_student", return_value=1),
            patch.object(
                main,
                "get_exercise_progress",
                side_effect=main.HistoryUnavailableError("progress unavailable"),
            ),
            patch.object(main, "advance_exercise_progress") as advance_progress,
            patch.object(main, "_save_checkpoint_turn", new_callable=AsyncMock) as save_turn,
        ):
            response = self.client.post(
                f"/api/exercises/{EXERCISE_ID}/checkpoint",
                json={
                    "student_name": "Ana",
                    "checkpoint_id": "read-axes-units",
                    "answer_ids": ["time-position-meters-seconds"],
                },
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json()["detail"],
            {
                "code": "exercise_progress_unavailable",
                "message": main.EXERCISE_PROGRESS_ERROR,
                "retryable": True,
            },
        )
        advance_progress.assert_not_called()
        save_turn.assert_not_awaited()

    def test_exercise_progress_endpoints_return_retryable_503_when_student_lookup_fails(self):
        exercise = get_exercise(EXERCISE_ID)
        for method in ("get", "post"):
            with self.subTest(method=method):
                with patch.object(
                    main,
                    "get_or_create_student",
                    side_effect=main.HistoryUnavailableError("student lookup unavailable"),
                ):
                    if method == "get":
                        response = self.client.get(
                            f"/api/exercises/{EXERCISE_ID}/progress",
                            params={"student_name": "Ana"},
                        )
                    else:
                        response = self.client.post(
                            f"/api/exercises/{EXERCISE_ID}/checkpoint",
                            json={
                                "student_name": "Ana",
                                "checkpoint_id": exercise.checkpoints[0].id,
                                "answer_ids": [],
                            },
                        )

                self.assertEqual(response.status_code, 503)
                if method == "get":
                    self.assertEqual(response.json()["detail"], main.EXERCISE_PROGRESS_ERROR)
                else:
                    self.assertEqual(
                        response.json()["detail"],
                        {
                            "code": "exercise_progress_unavailable",
                            "message": main.EXERCISE_PROGRESS_ERROR,
                            "retryable": True,
                        },
                    )


class CheckpointPersistenceIntegrationTests(unittest.TestCase):
    def test_completed_checkpoint_turns_survive_scoped_reload_review(self):
        previous_sqlite_path = os.environ.get("SQLITE_PATH")
        previous_turso_url = os.environ.get("TURSO_DATABASE_URL")
        previous_turso_token = os.environ.get("TURSO_AUTH_TOKEN")

        def restore_history_environment():
            history_module._reset_connection()
            if previous_sqlite_path is None:
                os.environ.pop("SQLITE_PATH", None)
            else:
                os.environ["SQLITE_PATH"] = previous_sqlite_path
            for key, value in (
                ("TURSO_DATABASE_URL", previous_turso_url),
                ("TURSO_AUTH_TOKEN", previous_turso_token),
            ):
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.addCleanup(restore_history_environment)

        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["SQLITE_PATH"] = str(Path(temp_dir) / "history.db")
            os.environ.pop("TURSO_DATABASE_URL", None)
            os.environ.pop("TURSO_AUTH_TOKEN", None)
            history_module._reset_connection()
            history_module.init_db()

            exercise = get_exercise(EXERCISE_ID)
            with TestClient(main.app) as client:
                boundary_response = None
                for index, checkpoint in enumerate(exercise.checkpoints):
                    response = client.post(
                        f"/api/exercises/{EXERCISE_ID}/checkpoint",
                        json={
                            "student_name": "Persisted Ana",
                            "checkpoint_id": checkpoint.id,
                            "answer_ids": list(checkpoint.correct_option_ids),
                        },
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    if index == 4:
                        boundary_response = response

                self.assertIsNotNone(boundary_response)
                self.assertEqual(boundary_response.json()["progress"]["current_index"], 5)
                self.assertEqual(
                    boundary_response.json()["progress"]["current_checkpoint"]["part"],
                    "b",
                )
                self.assertTrue(response.json()["progress"]["complete"])

                student_id = history_module.get_student_by_name("Persisted Ana")
                self.assertIsNotNone(student_id)
                history_module.save_message(
                    student_id,
                    "user",
                    "Theory chat must stay outside exercise review",
                )
                scoped_history = history_module.get_history(
                    student_id,
                    exercise_id=EXERCISE_ID,
                )
                self.assertEqual(len(scoped_history), len(exercise.checkpoints) * 2)
                self.assertEqual(scoped_history[0]["role"], "user")
                self.assertEqual(scoped_history[1]["role"], "assistant")
                self.assertIn("Respuesta:", scoped_history[0]["content"])
                self.assertIn(
                    "Respuesta: 120 = 10v₀ + 50a, 360 = 20v₀ + 200a, "
                    "Al resolver: v₀ = 6 m/s y a = 1,2 m/s²",
                    [message["content"] for message in scoped_history],
                )

                reload_response = client.get(
                    "/history",
                    params={
                        "student_name": "Persisted Ana",
                        "exercise_id": EXERCISE_ID,
                    },
                )
                self.assertEqual(reload_response.status_code, 200)
                reload_body = reload_response.json()
                self.assertEqual(reload_body["messages"], [])
                self.assertEqual(
                    reload_body["completed_review"],
                    serialize_progress(
                        exercise, len(exercise.checkpoints)
                    )["completed_review"],
                )
                self.assertNotIn("Theory chat", reload_response.text)

                persisted_review = reload_body["messages"]
                node_result = _run_node_contract(
                """
elements['student-name'].value = 'Persisted Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
    assert.strictEqual(elements['exercise-review'].hidden, false);
    assert.strictEqual(
      elements['exercise-review-list'].children.length,
      completedReview.length,
);
assert.strictEqual(
  fetchCalls.filter((call) => call.url.endsWith('/checkpoint')).length,
  0,
);
    assert.ok(
      elements['exercise-review-list'].children.some(
        (item) => item.children[2].children.some(
          (answer) => answer.textContent.includes('x(10)=120 m'),
        ),
      ),
    );
""",
                completed=True,
                history_messages=persisted_review,
                completed_review=serialize_progress(
                    exercise, len(exercise.checkpoints)
                )["completed_review"],
            )
            self.assertEqual(node_result.returncode, 0, node_result.stderr)


if __name__ == "__main__":
    unittest.main()
