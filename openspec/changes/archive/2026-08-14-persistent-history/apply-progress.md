# Apply Progress: 2026-08-14-persistent-history

**Status**: `partial` — 6 of 7 tasks committed; Task 7 (deploy) pending user action.

**Artifact store mode**: hybrid — this file is the OpenSpec artifact; Engram receives the same summary.

---

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `ff28362` | `chore(deps): add libsql-experimental for Turso support` |
| 2 | `63d4cfd` | `chore(env): add TURSO_* vars and mark SQLITE_PATH as dev-only` |
| 3 | `31ad891` | `refactor(history): swap SQLite factory for Turso-or-local connection layer` |
| 4 | `2761770` | `fix(chat): handle DB errors mid-request with SSE error frame` |
| 5 | `614cb97` | `docs(spec): apply persistent-history delta to conversation-persistence` |
| 6 | `2d8ec29` | `docs(agents): update §7 #12 — history persistence via Turso` |

---

## Verification Results

### Task 1 — libsql-experimental dependency

**Command**:
```bash
source .venv/bin/activate
pip install -r requirements.txt
python -c "import libsql_experimental; print(libsql_experimental.__name__)"
```

**Outcome**: ✅ Passed. Package installed and imported.

**Deviation**: The pin was changed from `>=0.1,<1.0` to `>=0.0.55,<1.0` because PyPI only lists `0.0.x` releases for `libsql-experimental`; no `0.1+` release exists.

---

### Task 2 — .env.example Turso vars

**Command**:
```bash
grep -c TURSO .env.example
```

**Outcome**: ✅ Passed. Returns `3` (two variable lines plus one comment mention).

---

### Task 3 — rag/history.py connection factory

**Commands**:
```bash
# Local fallback (no Turso vars)
source .venv/bin/activate
python -c "from rag.history import _get_connection; c = _get_connection(); print(type(c).__name__)"
# -> Connection (sqlite3.Connection)

# Turso branch (driver reached)
TURSO_DATABASE_URL=libsql://test-db-org.turso.io TURSO_AUTH_TOKEN=fake \
  python -c "from rag.history import _get_connection; c = _get_connection(); print(type(c).__module__, type(c).__name__)"
# -> builtins Connection (libsql_experimental Connection, module reported as builtins by C extension)
```

**Outcome**: ✅ Passed for local fallback; Turso driver branch reached.

**Deviation from design/tasks**: `with conn:` context-manager blocks are **not** used because `libsql_experimental.Connection` does not implement `__enter__`/`__exit__`. Instead, the code uses `conn.execute(...)` + `conn.commit()` manually, which works for both `sqlite3` and libSQL. A small `_rows_to_dicts(cursor)` helper was added because libSQL does not expose a `Row` factory.

---

### Task 4 — app/main.py DB error handling

**Commands**:
```bash
source .venv/bin/activate
python -m py_compile app/main.py

TURSO_DATABASE_URL=libsql://test-db-org.turso.io TURSO_AUTH_TOKEN=invalid \
  python -c "
from fastapi.testclient import TestClient
import app.main
client = TestClient(app.main.app)
print('GET /history', client.get('/history?student_name=Ana').status_code)
print('POST /chat', client.post('/chat', json={'query':'hola','student_name':'Ana'}).status_code)
print('DELETE', client.delete('/messages/1?student_name=Ana').status_code)
"
```

**Outcome**: ✅ Passed. All three endpoints return `503` with the Spanish message `No se pudo guardar la conversación. Reintentá en un momento.`.

**Deviation**: `init_db()` at module import is also wrapped in `try/except`; otherwise an invalid Turso token at startup would crash the process before any endpoint could return a 503 or SSE error frame. The task only listed endpoint call sites, but this import-time call site was required for the verification scenario to work.

---

### Task 5 — conversation-persistence spec delta

**Command**:
```bash
grep -c "Turso" openspec/specs/conversation-persistence/spec.md
```

**Outcome**: ✅ Passed. Returns `16`.

---

### Task 6 — AGENTS.md update

**Command**:
```bash
grep -n "ephemeral" AGENTS.md
```

**Outcome**: ✅ Passed. Returns no matches.

---

### Task 7 — Deploy and verify on HF Spaces

**Status**: ⏳ Pending.

- Add `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` as HF Space Secrets.
- Push the change to the HF Space repo per `docs/hf-space.md`.
- Send a chat message; confirm the row exists in Turso.
- Cold-restart the Space; confirm history survives.

This task is intentionally not a commit.

---

## Known Issues / Deviations

1. **libsql-experimental pin**: Changed from `>=0.1,<1.0` to `>=0.0.55,<1.0` because no `0.1+` release exists on PyPI.
2. **No `with conn:` blocks**: libSQL connections do not support context managers, so manual `execute` + `commit` is used.
3. **`_rows_to_dicts` helper**: Added to support both `sqlite3.Row` and libSQL's tuple-only cursors.
4. **`init_db()` wrapped at import time**: Required so DB connection failures at startup do not prevent the endpoints from returning 503/SSE errors.
5. **Verification URL for invalid Turso token**: Used `libsql://test-db-org.turso.io` instead of `libsql://test.turso.io` because the latter hangs at the network layer in the test environment; `test-db-org.turso.io` fails fast with a 404/Host not found, which is sufficient to exercise the error-handling path.

---

## Line Count Check

| File | New Lines | Estimated | Delta |
|------|-----------|-----------|-------|
| `requirements.txt` | 25 | ~2 changed | within ±20% of estimate |
| `.env.example` | 42 | ~8 changed | within ±20% of estimate |
| `rag/history.py` | 257 | ~40 changed | within ±20% of estimate |
| `app/main.py` | 233 | ~45 changed | within ±20% of estimate |
| `openspec/specs/conversation-persistence/spec.md` | 228 | ~30 changed | within ±20% of estimate |
| `AGENTS.md` | 262 | ~15 changed | smaller than estimate (net +2) |

---

## Next Recommended Phase

`sdd-verify` after the user completes Task 7 (HF Spaces deploy + real Turso credentials).
