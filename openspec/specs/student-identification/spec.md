# student-identification Specification

## Purpose

Lightweight, passwordless student identification for the chat prototype. A student types a display name once; it is persisted in the browser's `localStorage` and sent as `student_name` on every chat request. The backend resolves the name to a student row in SQLite (creating it if absent). There is no password, no email, no token, no logout button. This satisfies AGENTS.md §3 ("History per student") and §9 (Student role) without the auth-strategy work deferred to month 3.

## Requirements

### Requirement: Chat is gated on a typed display name

The frontend SHALL disable the chat input until the student has typed at least one non-whitespace character into the name input and submitted it. Until then the chat input SHALL be marked disabled and `POST /chat` SHALL NOT be callable from the UI. The name input SHALL appear above the chat input on first visit.

#### Scenario: Fresh visit, empty name

- GIVEN the browser has no `student_name` in `localStorage`
- WHEN the page loads
- THEN the chat input is disabled and a name input is visible above it
- AND the chat send button (or Enter) does nothing

#### Scenario: Name typed and submitted

- GIVEN the name input is empty on a fresh visit
- WHEN the user types "Ana" and submits (Enter or a submit affordance)
- THEN the chat input becomes enabled
- AND "Ana" is stored in `localStorage` under the `student_name` key

#### Scenario: Whitespace-only name is rejected

- GIVEN the name input is visible
- WHEN the user types "   " (only spaces) and submits
- THEN the chat input stays disabled
- AND no `student_name` is written to `localStorage`

### Requirement: Name persists across reloads on the same device

Once a name is submitted, the frontend SHALL read `localStorage.student_name` on every subsequent page load and skip the name input. The student SHALL NOT be re-prompted as long as the value is present. There is no logout button; switching students requires clearing `localStorage` or using a different browser/device.

#### Scenario: Reload keeps the name

- GIVEN `localStorage.student_name` is "Ana" from a prior session
- WHEN the page reloads
- THEN the chat input is enabled on load
- AND the name input is not shown (or is hidden / pre-filled)

#### Scenario: Cleared localStorage re-prompts

- GIVEN `localStorage` is cleared
- WHEN the page reloads
- THEN the student is asked for a name again before chatting

### Requirement: `student_name` is sent on every chat request

Every `POST /chat` request SHALL include a `student_name` field in the JSON body whose value is the string currently in `localStorage`. The backend SHALL treat `student_name` as required; a missing or empty field SHALL be rejected with HTTP 400 or 422 before any model call.

#### Scenario: Request carries the name

- GIVEN `localStorage.student_name` is "Ana"
- WHEN the user submits a message "¿cómo resuelvo este problema?"
- THEN the request body contains `{"student_name": "Ana", "query": "..."}`

#### Scenario: Missing name is rejected

- GIVEN a `POST /chat` request without `student_name` (e.g., crafted client or stale tab)
- WHEN the request reaches the backend
- THEN the backend responds with 4xx and does not call Groq
- AND no message is persisted to SQLite

### Requirement: Backend resolves student by display name without unique constraint

On receiving a `student_name`, the backend SHALL look up the first `students` row whose `display_name` equals the supplied value (case-sensitive match). If none exists, it SHALL create one with `display_name` = value and `created_at` = now. The backend SHALL NOT enforce a unique constraint on `display_name`; names that collide (two different "Juan Pérez") SHALL share the same student row and therefore the same history. This is an accepted trade-off for the prototype (proposal §Risks).

#### Scenario: New name creates a student

- GIVEN no `students` row has `display_name = "Ana"`
- WHEN a `POST /chat` request arrives with `student_name = "Ana"`
- THEN a new `students` row is created with `display_name = "Ana"` and a non-null `created_at`
- AND the new student's `id` is used for the subsequent message persistence

#### Scenario: Returning name reuses the student

- GIVEN a `students` row with `display_name = "Ana"` exists
- WHEN another `POST /chat` request arrives with `student_name = "Ana"`
- THEN no new `students` row is inserted
- AND the existing row's `id` is used for message persistence

#### Scenario: Name collision merges histories

- GIVEN two different students both type "Ana" on different devices
- WHEN each sends messages via `POST /chat`
- THEN both sets of messages are persisted against the same `student_id`
- AND both students see the merged history when they load `/history?student_name=Ana`

### Requirement: Identification is limited to a typed display name

The identification flow SHALL NOT collect a password, email, token, or any credential. It SHALL NOT issue a session cookie or bearer token. The student name is the only identifier transmitted. Role distinctions beyond "student" (professor, Nair, dev) are out of scope for this change.

#### Scenario: No credentials transmitted

- GIVEN the identification flow is implemented
- WHEN a `POST /chat` request is inspected
- THEN the request body contains only `student_name` and the chat payload
- AND no `Authorization` header, cookie, or token is required for the request to succeed

### Requirement: Frontend loads history on identification

Once a student is identified (either by submitting a name now or by reading `localStorage` on load), the frontend SHALL fetch `GET /history?student_name=...` and render all returned messages in the chat UI before the student sends any new message. Until that fetch completes, the chat area SHALL show an empty or loading state, not a fabricated history.

#### Scenario: Returning student sees their history

- GIVEN `localStorage.student_name` is "Ana" and Ana has 6 prior messages in SQLite
- WHEN the page loads
- THEN the frontend issues `GET /history?student_name=Ana`
- AND renders the 6 messages in chronological order before any new chat is sent

#### Scenario: New student has empty history

- GIVEN a first-time student types "Lucía"
- WHEN the frontend fetches `GET /history?student_name=Lucía`
- THEN the backend returns an empty list
- AND the chat area renders an empty state (no fake messages)
