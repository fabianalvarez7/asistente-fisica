"""Lightweight fake Turso callables for history integration tests.

These callables are sent across the multiprocessing spawn boundary used by
``rag.history_async`` when ``TURSO_DATABASE_URL`` is set. They intentionally
avoid importing ``app.main`` (or any heavy dependency) so the child process can
import and execute them quickly on CI runners.
"""

import os
import time


def _record_fake_turso_event(event: str) -> int:
    path = os.environ["FAKE_TURSO_EVENTS_PATH"]
    with open(path, "a+", encoding="utf-8") as events:
        events.write(event + "\n")
        events.flush()
        events.seek(0)
        return len(events.readlines())


def fake_turso_init_db() -> None:
    _record_fake_turso_event("init")


def fake_turso_health_check() -> None:
    _record_fake_turso_event("health")
    if os.getenv("FAKE_TURSO_MODE") == "hang":
        while True:
            time.sleep(0.01)


def fake_turso_get_or_create_student(name: str) -> int:
    _record_fake_turso_event(f"student:{name}")
    return 1


def fake_turso_get_history(
    student_id: int, limit: int | None = None, exercise_id: str | None = None
) -> list:
    del student_id, limit, exercise_id
    _record_fake_turso_event("history")
    return []


def fake_turso_get_exercise_progress(student_id: int, exercise_id: str) -> int:
    del student_id, exercise_id
    _record_fake_turso_event("exercise-progress")
    return 0


def fake_turso_save_message(
    student_id: int, role: str, content: str, exercise_id: str | None = None
) -> int:
    del student_id
    scope = exercise_id or "theory"
    event_number = _record_fake_turso_event(f"save:{role}:{content}:{scope}")
    return event_number
