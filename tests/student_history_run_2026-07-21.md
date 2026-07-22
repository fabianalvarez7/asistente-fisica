# Student History & Identification — Manual Test Run — 2026-07-21

**Status**: pending review
**Branch**: `feat/student-history`
**Reference**: `openspec/changes/student-history/design.md` §"Test Plan" (lines 390-403)

**Instructions**:
- For each test, follow the "Reproducible steps" block. Each step has a command or UI action that can be re-run.
- Mark the checkbox as PASS only when the actual result matches the "Expected" exactly. When the result does not match, mark FAIL and describe the discrepancy in "Notes".
- Use the SQLite verification commands at the end of each test to confirm DB state independently of the UI.
- Estimated total time: 15-20 minutes.

**Prerequisites**:
- Backend running in dev mode: `uvicorn app.main:app --reload` (terminal 1).
- Frontend served by the same backend: open `http://127.0.0.1:8000/`.
- Browser DevTools open (Console + Network tabs) for API call inspection.
- For DB inspection, a separate terminal with `sqlite3 data/historial.db`.

---

## Test 1 — Fresh visit shows name gate

**Spec scenario**: Student visits for the first time; chat must be locked behind a name input.

**Reproducible steps**:
1. Open `http://127.0.0.1:8000/` in a private/incognito window.
2. Observe the page layout before any interaction.

**Expected**:
- `#name-area` is visible with a text input and submit button.
- The chat input (`#chat-input`) and send button are disabled.
- No history messages are rendered in the chat area.

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 2 — Name submission enables chat and persists in localStorage

**Spec scenario**: After typing a name, the student enters the chat and the name is remembered across reloads.

**Reproducible steps**:
1. In the same private window, type `Ana` in the name input.
2. Click `Entrar` (or press Enter).
3. Open DevTools → Application → Local Storage → `http://127.0.0.1:8000`.

**Expected**:
- `#name-area` is hidden.
- Chat input is enabled.
- `localStorage.student_name === "Ana"`.

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 3 — History renders on page load from SQLite

**Spec scenario**: A returning student sees their previous conversation immediately on page load.

**Reproducible steps**:
1. With backend running, pre-seed SQLite with 3 messages for "Ana" (one user, one assistant, one user):
   ```bash
   sqlite3 data/historial.db <<'SQL'
   INSERT INTO students (display_name) VALUES ('Ana');
   INSERT INTO messages (student_id, role, content)
     SELECT id, 'user',      'Hola' FROM students WHERE display_name = 'Ana';
   INSERT INTO messages (student_id, role, content)
     SELECT id, 'assistant', '¿En qué te ayudo?' FROM students WHERE display_name = 'Ana';
   INSERT INTO messages (student_id, role, content)
     SELECT id, 'user',      'Necesito ayuda con cinemática' FROM students WHERE display_name = 'Ana';
   SQL
   ```
2. Reload the page (private window from Test 2 still has `localStorage.student_name = "Ana"`).
3. Observe the chat area.

**Expected**:
- 3 messages render in chronological order before any new user action.
- Each user message has a `×` delete button.
- Each assistant message has a `×` delete button.

**DB verification**:
```bash
sqlite3 data/historial.db "SELECT id, role, substr(content, 1, 40) FROM messages ORDER BY created_at ASC, id ASC;"
```

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 4 — Multi-turn chat references prior turn

**Spec scenario**: The model sees the prior conversation; the second response depends on the first turn.

**Reproducible steps**:
1. With Ana's history loaded, send a first message: `¿Qué es la aceleración?`
2. Wait for the assistant response.
3. Send a second message: `¿Y cómo se calcula?`
4. Watch the server console (terminal running `uvicorn`) for the dev-mode `[MSG NN]` dump.

**Expected**:
- Second response from the assistant references acceleration (the model saw the first turn in its context).
- Server console shows the assembled messages list with prior turns injected:
  - `[MSG 00] system | ...`
  - few-shot entries (`[MSG 01]` ... `[MSG NN]`)
  - history entries (Ana + the assistant's previous reply)
  - current query last
- No `localStorage` change for the student name.

**DB verification** (after both turns complete):
```bash
sqlite3 data/historial.db "SELECT COUNT(*) FROM messages m JOIN students s ON s.id = m.student_id WHERE s.display_name = 'Ana';"
```
Expected: `5` (3 pre-seeded + 2 new user messages; assistant messages also saved during streaming).

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:
La capa socrática está funcionando porque agrega preguntas a modo de guía, pero la primera respuesta ya incluye la fórmula, es decir, no se ven los tres niveles de ayuda que habíamos establecido.

---

## Test 5 — Delete own user message

**Spec scenario**: A student can remove a user message they sent; the row is gone from SQLite and the UI.

**Reproducible steps**:
1. Click the `×` button on the first pre-seeded user message (`Hola`).
2. Observe the chat area.
3. Inspect SQLite.

**Expected**:
- The `Hola` message bubble disappears from the UI.
- No console errors in DevTools.

**DB verification**:
```bash
sqlite3 data/historial.db "SELECT COUNT(*) FROM messages WHERE content = 'Hola';"
```
Expected: `0`

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 6 — Delete assistant message

**Spec scenario**: A student can also remove an assistant message; the bubble disappears and the UI reflows (standard chat UX).

**Reproducible steps**:
1. Click the `×` button on the assistant message (`¿En qué te ayudo?`).
2. Observe the chat area.

**Expected**:
- The assistant message bubble disappears.
- The UI reflows: messages below slide up to fill the space (standard chat-UX behavior, matches Slack/WhatsApp/etc.). Design.md was updated from the original "gap visible" wording to match this implementation; the deviation is accepted.

**DB verification**:
```bash
sqlite3 data/historial.db "SELECT COUNT(*) FROM messages WHERE content = '¿En qué te ayudo?';"
```
Expected: `0`

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:

---

## Test 7 — Cross-student delete returns 403

**Spec scenario**: A student cannot delete another student's messages; the API rejects with 403 and the DB row is preserved.

**Reproducible steps**:
1. In the same private window, change `localStorage.student_name` to `Beto` (DevTools → Application → Local Storage → edit value → reload).
2. After reload, Ana's history should NOT be visible (Beto has no messages yet).
3. Pick a known message id of Ana from the DB:
   ```bash
   sqlite3 data/historial.db "SELECT id, content FROM messages m JOIN students s ON s.id = m.student_id WHERE s.display_name = 'Ana' LIMIT 1;"
   ```
4. From DevTools Console, run:
   ```js
   fetch('/messages/<id-from-step-3>?student_name=Beto', { method: 'DELETE' })
     .then(r => r.status)
     .then(console.log);
   ```
5. Inspect SQLite again for the same message id.

**Expected**:
- Console logs `403`.
- The Ana message is still in the DB (row count unchanged).

**DB verification**:
```bash
sqlite3 data/historial.db "SELECT COUNT(*) FROM messages WHERE id = <id-from-step-3>;"
```
Expected: `1`

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 8 — Unknown name returns empty history

**Spec scenario**: A name that has never been used returns an empty list, not an error.

**Reproducible steps**:
1. From any terminal:
   ```bash
   curl -sS 'http://127.0.0.1:8000/history?student_name=Nobody'
   ```
2. Confirm HTTP status.

**Expected**:
- HTTP `200`.
- Body: `{"messages": []}`.

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 9 — History survives backend restart

**Spec scenario**: SQLite-backed history is durable; a backend restart does not lose it.

**Reproducible steps**:
1. With Ana's name set, send a new message: `Recordatorio de prueba`.
2. Wait for the assistant response.
3. Stop uvicorn (`Ctrl+C`).
4. Relaunch: `uvicorn app.main:app --reload`.
5. Reload the browser page.
6. Confirm the new messages are still visible.

**Expected**:
- After restart, Ana's full history (pre-seeded + new exchanges) is rendered on page load.
- No errors in server console at boot.

**DB verification** (after restart):
```bash
sqlite3 data/historial.db "SELECT COUNT(*) FROM messages m JOIN students s ON s.id = m.student_id WHERE s.display_name = 'Ana';"
```
Expected: `>= 3` (depends on which messages were deleted in Tests 5-6).

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Test 10 — `HISTORY_WINDOW=0` disables injection

**Spec scenario**: Setting the env var to 0 restores the single-turn message list, with no history entries injected.

**Reproducible steps**:
1. Stop uvicorn.
2. In the `.env` file (or export in the shell), set `HISTORY_WINDOW=0`.
3. Relaunch: `uvicorn app.main:app --reload`.
4. Send a new query from Ana.
5. Watch the server console for the `[MSG NN]` dump.

**Expected**:
- The assembled messages list contains: system, few-shot, current query — no history entries.
- The query still produces an answer (no error from the chain).
- After the response, the new user message is still saved to SQLite (the env var only affects injection, not persistence).

**DB verification**:
```bash
sqlite3 data/historial.db "SELECT COUNT(*) FROM messages m JOIN students s ON s.id = m.student_id WHERE s.display_name = 'Ana';"
```
Expected: `> 0` (persistence still works, even though injection is off).

**Cleanup**: restore `HISTORY_WINDOW=10` (or remove the line) and restart before continuing.

**Pass/Fail**: [x] PASS  [ ] FAIL

**Notes**:


---

## Summary

| # | Test | Result |
|---|------|--------|
| 1 | Fresh visit shows name gate | [x] PASS [ ] FAIL |
| 2 | Name submission enables chat | [x] PASS [ ] FAIL |
| 3 | History renders on page load | [x] PASS [ ] FAIL |
| 4 | Multi-turn chat references prior turn | [x] PASS [ ] FAIL |
| 5 | Delete own user message | [x] PASS [ ] FAIL |
| 6 | Delete assistant message | [x] PASS [ ] FAIL |
| 7 | Cross-student delete returns 403 | [x] PASS [ ] FAIL |
| 8 | Unknown name returns empty history | [x] PASS [ ] FAIL |
| 9 | History survives backend restart | [x] PASS [ ] FAIL |
| 10 | `HISTORY_WINDOW=0` disables injection | [x] PASS [ ] FAIL |

**Overall**: [x] ALL PASS  [ ] SOME FAIL (see notes above)

**Next step after this run**: `sdd-verify` to validate the change against specs, design, and tasks.
