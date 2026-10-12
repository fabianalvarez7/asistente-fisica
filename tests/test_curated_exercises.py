"""Focused coverage for the published curated-exercise chat flow."""

import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, call, patch

os.environ.setdefault("GROQ_API_KEY", "test-key")

_fake_retrievers = MagicMock()
_fake_store_class = MagicMock()
_fake_store_class.return_value.count.return_value = 1
_fake_retrievers.VectorStore = _fake_store_class
_fake_retrievers.EmbeddingsModel = MagicMock
sys.modules["rag.retrievers"] = _fake_retrievers

from fastapi.testclient import TestClient  # noqa: E402

from rag import history as history_module  # noqa: E402
from rag.exercises import get_exercise  # noqa: E402

with patch.object(history_module, "init_db"):
    import app.main as main  # noqa: E402

from rag import chain  # noqa: E402


EXERCISE_ID = "cinematica-1d-ejercicio-02"


def _streaming_generator(query, history=None, *, exercise=None, checkpoint_index=None):
    del query, history, checkpoint_index
    assert exercise is not None
    yield "data: Pensá en esto...\n\n"
    yield "data: [DONE]\n\n"


class CuratedExerciseEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(main.app)

    def test_catalog_returns_only_student_safe_published_data(self):
        response = self.client.get("/api/exercises")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual([item["id"] for item in data], [EXERCISE_ID])
        self.assertTrue(all("teacher_key" not in item for item in data))
        self.assertNotIn("checkpoints", data[0])
        self.assertNotIn("guidance", data[0])
        self.assertNotIn("constant-acceleration", response.text)
        self.assertNotIn("correct_option_ids", response.text)
        for future_answer in (
            "x(10)=120 m",
            "x(20)=360 m",
            "aceleración constante",
        ):
            self.assertNotIn(future_answer, response.text)
        self.assertEqual(
            data[0]["title"],
            "Guía nº 2 Cinemática de la partícula en 1D - Ejercicio 2",
        )
        self.assertEqual(data[0]["graph_asset"], "/img/exercise-cinematica-1d-ejercicio-02.png")
        self.assertEqual(
            data[0]["starter_ideas"],
            [
                "Leé primero los ejes y sus unidades: t está en segundos y x en metros.",
                "Observá la forma de la curva x(t) antes de sacar conclusiones.",
            ],
        )

    def test_exercise_page_is_separate_from_theory_chat(self):
        response = self.client.get("/exercises")

        self.assertEqual(response.status_code, 200)
        self.assertIn('id="exercise-title"', response.text)
        self.assertNotIn('id="exercise-select"', response.text)

    def test_theory_chat_keeps_working_without_exercise_id(self):
        def theory_generator(query, history=None, *, exercise=None):
            del query, history
            assert exercise is None
            yield "data: Respuesta de teoría\n\n"
            yield "data: [DONE]\n\n"

        with (
            patch.object(main, "generate_response", side_effect=theory_generator) as generate,
            patch.object(
                main,
                "get_or_create_student",
                side_effect=main.HistoryUnavailableError,
            ),
        ):
            response = self.client.post(
                "/chat",
                json={"query": "test", "student_name": "Ana"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data: Respuesta de teoría\n\n", response.text)
        generate.assert_called_once_with("test", history=[], exercise=None)

    def test_chat_rejects_unknown_or_unpublished_exercise_id_with_400(self):
        response = self.client.post(
            "/chat",
            json={
                "query": "test",
                "student_name": "Ana",
                "exercise_id": "not-published",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"],
            "exercise_id must identify a published exercise",
        )

    def test_chat_rejects_whitespace_only_exercise_id_with_400(self):
        response = self.client.post(
            "/chat",
            json={"query": "test", "student_name": "Ana", "exercise_id": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "exercise_id cannot be empty")

    def test_history_rejects_whitespace_only_exercise_id_with_400(self):
        response = self.client.get(
            "/history",
            params={"student_name": "Ana", "exercise_id": "   "},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "exercise_id cannot be empty")

    def test_chat_passes_selected_exercise_to_generation(self):
        with (
            patch.object(main, "generate_response", side_effect=_streaming_generator) as generate,
            patch.object(main, "get_or_create_student", return_value=7),
            patch.object(main, "get_history", return_value=[]),
            patch.object(main, "get_exercise_progress", return_value=0),
            patch.object(main, "_enqueue_message") as enqueue_message,
        ):
            enqueue_message.return_value.resolve = AsyncMock(return_value=1)
            response = self.client.post(
                "/chat",
                json={
                    "query": "¿Qué representan los ejes?",
                    "student_name": "Ana",
                    "exercise_id": EXERCISE_ID,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn("data: Pensá en esto...\n\n", response.text)
        generate.assert_called_once()
        self.assertEqual(generate.call_args.args, ("¿Qué representan los ejes?",))
        self.assertEqual(generate.call_args.kwargs["history"], [])
        self.assertEqual(
            generate.call_args.kwargs["exercise"], get_exercise(EXERCISE_ID)
        )

    def test_exercise_chat_passes_canonical_progress_to_generation(self):
        def generator(query, history=None, *, exercise=None, checkpoint_index=0):
            del query, history, exercise
            assert checkpoint_index == 2
            yield "data: Pensá en el tercer checkpoint...\n\n"
            yield "data: [DONE]\n\n"

        pending = MagicMock()
        pending.resolve = AsyncMock(return_value=1)

        with (
            patch.object(main, "generate_response", side_effect=generator) as generate,
            patch.object(main, "get_or_create_student", return_value=7),
            patch.object(main, "get_history", return_value=[]),
            patch.object(main, "get_exercise_progress", return_value=2),
            patch.object(main, "_enqueue_message", return_value=pending),
        ):
            response = self.client.post(
                "/chat",
                json={
                    "query": "¿Qué sigue?",
                    "student_name": "Ana",
                    "exercise_id": EXERCISE_ID,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(generate.call_args.kwargs["checkpoint_index"], 2)

    def test_completed_exercise_chat_rejects_without_history_or_generation(self):
        exercise = get_exercise(EXERCISE_ID)
        sensitive_history = [
            {
                "role": "assistant",
                "content": "Respuesta tutor sensible: x(20)=360 m",
            },
        ]
        with (
            patch.object(main, "generate_response") as generate,
            patch.object(main, "get_or_create_student", return_value=7),
            patch.object(
                main,
                "get_exercise_progress",
                return_value=len(exercise.checkpoints),
            ),
            patch.object(main, "get_history", return_value=sensitive_history) as get_history,
            patch.object(main, "_enqueue_message") as enqueue_message,
        ):
            response = self.client.post(
                "/chat",
                json={
                    "query": "¿Podés darme otra pista?",
                    "student_name": "Ana",
                    "exercise_id": EXERCISE_ID,
                },
            )

        self.assertEqual(response.status_code, 409)
        detail = response.json()["detail"]
        self.assertEqual(detail["code"], "exercise_completed")
        self.assertFalse(detail["retryable"])
        self.assertIn("reseña de respuestas", detail["message"])
        self.assertNotIn(sensitive_history[0]["content"], response.text)
        get_history.assert_not_called()
        enqueue_message.assert_not_called()
        generate.assert_not_called()

    def test_exercise_chat_fails_closed_when_progress_read_fails(self):
        pending = MagicMock()
        pending.resolve = AsyncMock(return_value=1)

        with (
            patch.object(main, "generate_response") as generate,
            patch.object(main, "get_or_create_student", return_value=7),
            patch.object(main, "get_history", return_value=[]),
            patch.object(
                main,
                "get_exercise_progress",
                side_effect=main.HistoryUnavailableError("progress unavailable"),
            ),
            patch.object(main, "_enqueue_message", return_value=pending),
        ):
            response = self.client.post(
                "/chat",
                json={
                    "query": "¿Qué sigue?",
                    "student_name": "Ana",
                    "exercise_id": EXERCISE_ID,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(main.EXERCISE_PROGRESS_ERROR, response.text)
        generate.assert_not_called()

    def test_exercise_history_is_separate_and_has_no_theory_welcome(self):
        with (
            patch.object(main, "get_student_by_name", return_value=None),
            patch.object(main, "get_or_create_student", return_value=7),
            patch.object(main, "save_message") as save_message,
            patch.object(main, "get_history", return_value=[]) as get_history,
        ):
            response = self.client.get(
                "/history",
                params={"student_name": "Ana", "exercise_id": EXERCISE_ID},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"messages": [], "degraded": False})
        save_message.assert_not_called()
        get_history.assert_called_once_with(7, exercise_id=EXERCISE_ID)


class CuratedExerciseGenerationTests(unittest.TestCase):
    def test_exercise_generation_fails_closed_without_canonical_progress(self):
        exercise = get_exercise(EXERCISE_ID)
        with patch.object(
            chain._OPENAI_CLIENT.chat.completions,
            "create",
            return_value=[],
        ) as create:
            output = list(chain.generate_response("¿Qué sigue?", exercise=exercise))

        self.assertIn(chain.EXERCISE_PROGRESS_ERROR, "".join(output))
        self.assertIn("event: error", "".join(output))
        create.assert_not_called()

    def test_exercise_generation_does_not_use_global_course_retrieval(self):
        exercise = get_exercise(EXERCISE_ID)
        with (
            patch.object(
                chain._EMBEDDINGS,
                "embed_query",
            ) as embed_query,
            patch.object(
                chain._VECTOR_STORE, "similarity_search_with_scores"
            ) as retrieve,
            patch.object(
                chain._OPENAI_CLIENT.chat.completions,
                "create",
                return_value=[],
            ) as create,
        ):
            output = list(
                chain.generate_response(
                    "¿Qué miro primero?", exercise=exercise, checkpoint_index=0
                )
            )

        self.assertNotIn("No encuentro info sobre esto en los apuntes", "".join(output))
        embed_query.assert_not_called()
        retrieve.assert_not_called()
        create.assert_called_once()

    def test_generation_prompt_contains_selected_exercise_scope_and_checkpoint(self):
        exercise = get_exercise(EXERCISE_ID)
        with (
            patch.object(chain._EMBEDDINGS, "embed_query") as embed_query,
            patch.object(
                chain._VECTOR_STORE, "similarity_search_with_scores"
            ) as retrieve,
            patch.object(
                chain._OPENAI_CLIENT.chat.completions,
                "create",
                return_value=[],
            ) as create,
        ):
            list(
                chain.generate_response(
                    "¿Qué representan los ejes?", exercise=exercise, checkpoint_index=0
                )
            )

        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(exercise.statement, prompt)
        self.assertIn("position-time graph", prompt)
        self.assertIn(exercise.guidance[0].question, prompt)
        self.assertIn("No encuentro info sobre esto en los apuntes", prompt)
        self.assertNotIn("teacher_key", prompt)
        prompt_beyond_statement = prompt.replace(exercise.statement, "")
        starter_ideas = "\n".join(exercise.starter_ideas)
        for future_answer in (
            "x(10)=120 m",
            "x(20)=360 m",
            "aceleración constante",
        ):
            self.assertNotIn(future_answer, starter_ideas)
            self.assertNotIn(future_answer, prompt_beyond_statement)
        self.assertNotIn(exercise.guidance[1].question, prompt)
        embed_query.assert_not_called()
        retrieve.assert_not_called()

    def test_exercise_guidance_uses_canonical_progress_not_chat_message_count(self):
        exercise = get_exercise(EXERCISE_ID)
        with patch.object(
            chain._OPENAI_CLIENT.chat.completions,
            "create",
            return_value=[],
        ) as create:
            list(
                chain.generate_response(
                    "¿Qué sigue?",
                    history=[
                        {"role": "user", "content": f"mensaje {index}"}
                        for index in range(20)
                    ],
                    exercise=exercise,
                    checkpoint_index=2,
                )
            )

        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(exercise.guidance[2].question, prompt)
        self.assertNotIn(exercise.guidance[-1].question, prompt)

    def test_graph_guidance_uses_only_the_current_checkpoint(self):
        exercise = get_exercise(EXERCISE_ID)
        with patch.object(
            chain._OPENAI_CLIENT.chat.completions,
            "create",
            return_value=[],
        ) as create:
            list(
                chain.generate_response(
                    "¿Cómo reviso mi dibujo?",
                    exercise=exercise,
                    checkpoint_index=6,
                )
            )

        prompt = create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(exercise.checkpoints[6].prompt, prompt)
        self.assertIn(exercise.checkpoints[6].hint, prompt)
        self.assertNotIn(exercise.checkpoints[10].prompt, prompt)
        self.assertNotIn("acceleration-graph-correct", prompt)

    def test_few_shot_examples_are_only_in_theory_prompts(self):
        exercise = get_exercise(EXERCISE_ID)
        with patch.object(
            chain._OPENAI_CLIENT.chat.completions,
            "create",
            return_value=[],
        ) as exercise_create:
            list(
                chain.generate_response(
                    "¿Qué miro primero?", exercise=exercise, checkpoint_index=0
                )
            )

        exercise_messages = exercise_create.call_args.kwargs["messages"]
        exercise_content = "\n".join(message["content"] for message in exercise_messages)
        for example in chain._FEW_SHOT:
            self.assertNotIn(example["content"], exercise_content)

        document = MagicMock(
            page_content="Contenido de teoría",
            metadata={"source": "teoria.md"},
        )
        with (
            patch.object(chain._EMBEDDINGS, "embed_query", return_value=[0.1]),
            patch.object(
                chain._VECTOR_STORE,
                "similarity_search_with_scores",
                return_value=[(document, 0.1)],
            ),
            patch.object(
                chain._OPENAI_CLIENT.chat.completions,
                "create",
                return_value=[],
            ) as theory_create,
        ):
            list(chain.generate_response("¿Qué es la aceleración?"))

        theory_messages = theory_create.call_args.kwargs["messages"]
        theory_content = "\n".join(message["content"] for message in theory_messages)
        for example in chain._FEW_SHOT:
            self.assertIn(example["content"], theory_content)
