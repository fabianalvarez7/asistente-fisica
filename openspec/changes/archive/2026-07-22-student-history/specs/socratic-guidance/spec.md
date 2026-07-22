# Delta for socratic-guidance

## ADDED Requirements

### Requirement: History is visible to the model without breaking Socratic guidance

The Groq `messages` list SHALL include the student's recent conversation history (persisted and injected per the `conversation-persistence` capability) between `_FEW_SHOT` and the current query. The system prompt and `_FEW_SHOT` examples SHALL remain unchanged by this change. The Socratic pedagogy (question-based guidance, 3-level hint ladder, no final numerical answer, "señalar y repreguntar", off-topic refusal, voseo, LaTeX preservation) SHALL continue to hold in the presence of injected history. Multi-turn pedagogical adaptation — choosing hint levels based on what the student answered in prior turns — is out of scope for this change.

#### Scenario: Hint ladder is still single-turn-driven in the presence of history

- GIVEN the student has a 6-message history including a prior wrong answer
- WHEN the student's current query reaches the prompt layer
- THEN the assistant's hint level is decided from the current query's signal, NOT from escalating based on the prior wrong answer
- AND the response still ends with a guiding question

#### Scenario: System prompt and few-shot unchanged by history injection

- GIVEN history injection is enabled
- WHEN the assembled `messages` list is inspected
- THEN the `system` message content equals the existing Socratic system prompt byte-for-byte
- AND the `_FEW_SHOT` entries appear unchanged, in the same order, before any history entry

#### Scenario: Prior-turn reference now has context but no direct answer

- GIVEN the student writes "lo que te pregunté antes"
- WHEN the assistant can now see prior history
- THEN the assistant may use the prior turn as context to ask a more targeted guiding question
- AND still does not output the final numerical answer

## MODIFIED Requirements

### Requirement: Single-turn behaviour is enforced

The assistant SHALL NOT attempt true multi-turn Socratic scaffolding in this change. Hint-level escalation, error-flagging decisions, and refusal decisions SHALL be driven by the current query, not by adapting to the student's prior turns. The model SHALL now receive the last N persisted messages as context (injected between `_FEW_SHOT` and the current query per the `conversation-persistence` capability); this lifts the single-turn constraint at the infrastructure level — the model CAN see prior turns — but the pedagogical behaviour SHALL NOT exploit that visibility to escalate hints, hand out the answer, or skip rungs of the ladder. Each response continues to be evaluated against the Socratic contract on its own.

(Previously: Each request was independent, the model could not see prior history, and "lo que te pregunté antes" was treated as a standalone query requiring clarification. History was not tracked at all.)

#### Scenario: Standalone query

- GIVEN the student sends a fresh query
- WHEN the assistant generates its response
- THEN it bases the hint level only on the current query's signal, not on prior turns

#### Scenario: Query referencing a previous message

- GIVEN the student writes "lo que te pregunté antes"
- WHEN the assistant HAS prior history in the injected window
- THEN the assistant MAY use that context to ask a targeted guiding question (level-1 behaviour) instead of requesting generic clarification
- AND still SHALL NOT give the final numerical answer or escalate past level 3 based on that history

#### Scenario: History does not unlock answer leakage

- GIVEN the student previously asked for the answer in the injected history and the assistant refused then
- WHEN the student asks again for the answer in a new turn
- THEN the assistant STILL SHALL NOT exceed level 3
- AND the "Pista máxima is operationally bounded" requirement continues to hold

## Out of Scope (unchanged from the active spec, retained for reviewer context)

- **Multi-turn Socratic adaptation** (escalating hint level based on the student's progress across turns) — separate future change.
- **Student identification / login UX** — defined in the `student-identification` capability.
- **Persistence mechanism and history window configuration** — defined in the `conversation-persistence` capability.
- **Dashboard, model/embedding/infra changes** — unrelated.
- **Changes to RAG retrieval logic or the `rag-grounding` capability** — unrelated.