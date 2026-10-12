"""Persistence coverage for theory, exercise, and legacy message scopes."""

import os
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from rag import history


class HistoryScopingTests(unittest.TestCase):
    def test_checkpoint_advance_is_compare_and_set_under_concurrent_submissions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "history.db")
            with patch.dict(os.environ, {"SQLITE_PATH": db_path}, clear=False):
                os.environ.pop("TURSO_DATABASE_URL", None)
                os.environ.pop("TURSO_AUTH_TOKEN", None)
                history._reset_connection()
                try:
                    history.init_db(db_path)
                    student_id = history.get_or_create_student("Ana")

                    def submit_once(_):
                        return history.advance_exercise_progress(
                            student_id,
                            "cinematica-1d-ejercicio-02",
                            0,
                            1,
                        )

                    with ThreadPoolExecutor(max_workers=2) as executor:
                        results = list(executor.map(submit_once, range(2)))
                    canonical = history.get_exercise_progress(
                        student_id, "cinematica-1d-ejercicio-02"
                    )
                finally:
                    history._reset_connection()

        self.assertEqual(sorted(result[0] for result in results), [1, 1])
        self.assertEqual(sorted(result[1] for result in results), [False, True])
        self.assertEqual(canonical, 1)

    def test_progress_isolated_by_typed_name_not_an_authentication_boundary(self):
        """Display-name identity is intentionally not authentication."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "history.db")
            with patch.dict(os.environ, {"SQLITE_PATH": db_path}, clear=False):
                os.environ.pop("TURSO_DATABASE_URL", None)
                os.environ.pop("TURSO_AUTH_TOKEN", None)
                history._reset_connection()
                try:
                    history.init_db(db_path)
                    ana_id = history.get_or_create_student("Ana")
                    same_name_id = history.get_or_create_student("Ana")
                    another_name_id = history.get_or_create_student("Lucía")
                    history.advance_exercise_progress(
                        ana_id, "cinematica-1d-ejercicio-02", 0, 1
                    )
                    ana_progress = history.get_exercise_progress(
                        same_name_id, "cinematica-1d-ejercicio-02"
                    )
                    other_progress = history.get_exercise_progress(
                        another_name_id, "cinematica-1d-ejercicio-02"
                    )
                finally:
                    history._reset_connection()

        self.assertEqual(ana_id, same_name_id)
        self.assertNotEqual(ana_id, another_name_id)
        self.assertEqual(ana_progress, 1)
        self.assertEqual(other_progress, 0)

    def test_theory_and_exercise_history_are_separate(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "history.db")
            with patch.dict(os.environ, {"SQLITE_PATH": db_path}, clear=False):
                os.environ.pop("TURSO_DATABASE_URL", None)
                os.environ.pop("TURSO_AUTH_TOKEN", None)
                history._reset_connection()
                try:
                    history.init_db(db_path)
                    student_id = history.get_or_create_student("Ana")
                    theory_id = history.save_message(
                        student_id, "user", "pregunta de teoría"
                    )
                    exercise_id = history.save_message(
                        student_id,
                        "user",
                        "pregunta del ejercicio",
                        "cinematica-1d-ejercicio-02",
                    )

                    theory_messages = history.get_history(student_id)
                    exercise_messages = history.get_history(
                        student_id,
                        exercise_id="cinematica-1d-ejercicio-02",
                    )
                finally:
                    history._reset_connection()

            self.assertEqual([message["id"] for message in theory_messages], [theory_id])
            self.assertEqual(
                [message["id"] for message in exercise_messages], [exercise_id]
            )

    def test_nullable_legacy_rows_migrate_into_theory_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "legacy.db")
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    display_name TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                INSERT INTO students (display_name, created_at)
                VALUES ('Ana', '2026-01-01T00:00:00Z');
                INSERT INTO messages (student_id, role, content, created_at)
                VALUES (1, 'user', 'mensaje legado', '2026-01-01T00:00:01Z');
                """
            )
            connection.commit()
            connection.close()

            with patch.dict(os.environ, {"SQLITE_PATH": db_path}, clear=False):
                os.environ.pop("TURSO_DATABASE_URL", None)
                os.environ.pop("TURSO_AUTH_TOKEN", None)
                history._reset_connection()
                try:
                    history.init_db(db_path)
                    theory_messages = history.get_history(1)
                    exercise_messages = history.get_history(
                        1, exercise_id="cinematica-1d-ejercicio-02"
                    )
                finally:
                    history._reset_connection()

            self.assertEqual([message["content"] for message in theory_messages], ["mensaje legado"])
            self.assertEqual(exercise_messages, [])


if __name__ == "__main__":
    unittest.main()
