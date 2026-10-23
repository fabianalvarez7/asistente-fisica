"""Delete leftover verification students from the production history database.

Verification runs against the deployed Space (to prove a deploy actually
works) create real students in the production history store, because the
checkpoint endpoint has no separate test namespace. Those rows are throwaway
but they are production data, so this script removes them explicitly.

Safety properties, in order of importance:

- Dry run by default. ``--apply`` is required to delete anything.
- Matches on an explicit ``--prefix`` that defaults to ``__verify``. Always
  pass a narrow prefix; a bare ``%`` would match real students.
- Refuses to run when ``PRAGMA foreign_keys`` is off. Messages and exercise
  progress cascade from ``students`` via ``ON DELETE CASCADE``, so with the
  pragma off the student row would be deleted and its history left orphaned.
- Reports affected row counts before deleting, and the remaining count after.
- Idempotent: a second run finds nothing to do and exits 0.

Usage:
    TURSO_DATABASE_URL=... TURSO_AUTH_TOKEN=... \\
        python scripts/limpiar_usuarios_verificacion.py --prefix __verify

    # actually delete (default is a dry run)
    python scripts/limpiar_usuarios_verificacion.py --prefix __verify --apply
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


DEFAULT_PREFIX = "__verify"


def _pipeline(statements: list[tuple[str, list]]) -> list:
    """Run statements through Turso's HTTP pipeline API and return responses."""

    url = os.environ["TURSO_DATABASE_URL"]
    token = os.environ["TURSO_AUTH_TOKEN"]
    body = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": args}}
            for sql, args in statements
        ]
    }
    request = urllib.request.Request(
        f"{url}/v2/pipeline",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["results"]


def _all_rows(statements: list[tuple[str, list]]) -> list[list]:
    """Run statements through Turso's pipeline API, one result set per statement.

    ``/v2/pipeline`` executes every statement in the batch and returns one
    result entry per statement, in order. Callers that batch several queries
    need all of them, so this returns the full list instead of just the first.
    """

    return [
        result["response"]["result"].get("rows") or []
        for result in _pipeline(statements)
    ]


def _rows(statements: list[tuple[str, list]]) -> list:
    """Run a single-statement batch and return its rows."""

    return _all_rows(statements)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix",
        default=DEFAULT_PREFIX,
        help=f"display_name prefix identifying verification students (default {DEFAULT_PREFIX!r})",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete; without this flag the script only reports",
    )
    args = parser.parse_args()

    missing = [
        name
        for name in ("TURSO_DATABASE_URL", "TURSO_AUTH_TOKEN")
        if not os.environ.get(name)
    ]
    if missing:
        print(f"Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        return 2

    if _rows([("PRAGMA foreign_keys", [])])[0][0] != 1:
        print(
            "Refusing to run: PRAGMA foreign_keys is off, so ON DELETE CASCADE\n"
            "would not remove messages and exercise_progress with the student.",
            file=sys.stderr,
        )
        return 1

    students = _rows(
        [
            (
                "SELECT id, display_name, created_at FROM students "
                "WHERE display_name LIKE ? ORDER BY id",
                [f"{args.prefix}%"],
            )
        ]
    )

    if not students:
        print(f"No students matching {args.prefix!r} found. Nothing to do.")
        return 0

    for student_id, display_name, created_at in students:
        counts = _all_rows(
            [
                ("SELECT COUNT(*) FROM messages WHERE student_id = ?", [student_id]),
                (
                    "SELECT COUNT(*) FROM exercise_progress WHERE student_id = ?",
                    [student_id],
                ),
            ]
        )
        print(
            f"  id={student_id} name={display_name!r} created={created_at} "
            f"messages={counts[0][0]} progress={counts[1][0]}"
        )

    if not args.apply:
        print(f"\nDry run. Re-run with --apply to delete {len(students)} student(s).")
        return 0

    _pipeline(
        [
            ("DELETE FROM students WHERE id = ?", [student_id])
            for student_id, _, _ in students
        ]
    )

    remaining = _rows(
        [
            (
                "SELECT COUNT(*) FROM students WHERE display_name LIKE ?",
                [f"{args.prefix}%"],
            )
        ]
    )[0][0]

    print(f"Deleted {len(students)} student(s). {remaining} matching remain.")
    return 0 if remaining == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())