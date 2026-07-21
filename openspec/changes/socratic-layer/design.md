# Design: Socratic Layer

## Technical Approach

Prompt-only change using the **wrap approach** (explore.md §3, Approach B). A Socratic instructions block is prepended to the existing `SYSTEM_PROMPT` in `rag/prompts/chat_prompt.py`, preserving all RAG ground rules untouched. Three few-shot user/assistant message pairs are injected into the Groq call in `rag/chain.py` to reinforce the pedagogical pattern. No new dependencies, no infra changes, no frontend changes. Total diff: ~45 lines across 3 files.

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Prompt composition | Wrap — prepend Socratic block, keep RAG rules | Replace (risk losing ground rules), post-process (doubles Groq calls) | Preserves tested refusal behavior; additive and trivially revertable |
| Few-shot location | Messages in Groq call (`chain.py:76-80`) | Inline in system prompt | Separates instruction from demonstration; ~300 tokens vs. inflating system prompt; easier to iterate examples independently |
| Intervention ceiling | Pista máxima: key principle or general formula, never final numerical answer | Pure Socratic (no hints) or guided solution | Product decision validated with Nair — prevents student frustration without violating non-negotiable |
| Single-turn constraint | Accept it; no history tracking | — | SQLite history is a separate cycle. The model asks guiding questions but cannot track previous answers |

## Prompt Structure

The new `SYSTEM_PROMPT` layout (structure only — exact text is a sdd-apply concern):

```
[Socratic instructions block — ~250-350 tokens]
  - Role: Socratic guide, never a solver
  - Hint ladder: 3 levels (conceptual → specific → near-answer)
  - Edge cases: "dame la respuesta" → acknowledge + pista máxima; wrong answer → señalar + repreguntar
  - Tone: Rioplatense voseo, warm, paciente
  - Language: always Spanish; English queries understood but answered in Spanish

[RAG ground rules block — preserved verbatim from current prompt, ~180 tokens]
  - Answer only from context
  - Refuse with exact fallback phrase when context is absent or irrelevant
  - No general knowledge, no invented formulas
  - LaTeX preservation
  - Out-of-scope refusal

Contexto:
{context}
```

Total prompt: ~450-600 tokens. Context window: 128k — well within limits.

## Few-Shot Injection

In `rag/chain.py`, the `messages` list in `generate_response` changes from:

```python
messages = [system, user]  # 2 messages
```

To:

```python
_FEW_SHOT = [
    {"role": "user", "content": "¿Cuál es la fórmula del error relativo porcentual?"},
    {"role": "assistant", "content": "Antes de darte la fórmula, pensemos... [guiding question]"},
    {"role": "user", "content": "Un auto frena de 60 km/h a 0 en 5 segundos..."},
    {"role": "assistant", "content": "Buen problema. Para resolverlo... [GUESS scaffold]"},
    {"role": "user", "content": "No entiendo, no sé cómo empezar"},
    {"role": "assistant", "content": "Tranquilo, vamos de a poco... [topic identification question]"},
]

messages = [system] + _FEW_SHOT + [{"role": "user", "content": query}]
```

`_FEW_SHOT` is defined as a module-level constant in `chain.py` (keeps the diff small — no separate file needed). If the list grows beyond ~6 pairs in a future cycle, extract to `rag/prompts/few_shot.py` and re-export from `__init__.py`.

## File Changes

| File | Action | Est. Δ lines | Rationale |
|------|--------|-------------|-----------|
| `rag/prompts/chat_prompt.py` | Modify | +25 to +30 | Wrap: prepend Socratic instructions block before existing RAG rules. Docstring updated. |
| `rag/chain.py` | Modify | +12 to +15 | Define `_FEW_SHOT` constant; inject into messages list. Docstring updated. |
| `rag/prompts/__init__.py` | Modify | 0 to +2 | If `_FEW_SHOT` is extracted to a separate constant file in this cycle, re-export. Likely not needed — `_FEW_SHOT` lives in `chain.py`. |

**Verified**: current `__init__.py` only exports `SYSTEM_PROMPT`. No change needed unless a new `few_shot.py` file is created — the design does not require it.

**Total diff**: ~40-45 lines. Well under the 200-line flag threshold, and under the 400-line review budget.

## Edge Case Handling at Code Level

| Edge Case | Detection | Code Path | Expected Response |
|-----------|-----------|-----------|-------------------|
| Off-topic / no context | Cosine distance > 0.5 (chain.py:64) | Short-circuit BEFORE Groq: line 65-67. No change. | "No encuentro info sobre esto en los apuntes" |
| Context present but irrelevant | Prompt instruction (RAG ground rules) | Groq evaluates; prompt says "si el contexto no responde a ESTA pregunta" | Same fallback phrase |
| "Dame la respuesta" | Prompt instruction (Socratic block) | Groq evaluates; prompt says "reconocé frustración → pista máxima → pregunta guía" | Acknowledgement + principle/formula hint + guiding question. NEVER final numerical answer. |
| Wrong answer from student | Prompt instruction (Socratic block) | Groq evaluates; prompt says "señalá el error → pedí reconsiderar → nueva pregunta guía" | Error flagged, redirect to guiding question |
| English query | Prompt instruction (Socratic block) | Groq evaluates; prompt says "respondé siempre en español" | Spanish response; multilingual embeddings handle retrieval |
| "No encuentro info" on valid query | Cosine threshold (0.5) — current behavior preserved | Short-circuit at chain.py:64 | No regression: the threshold is untouched |

**Regression guard**: the existing refusal rule (cosine > 0.5 → hardcoded fallback, Groq never called) is **untouched**. The Socratic block is only active when Groq is invoked. If retrieval fails, the student never reaches the Socratic layer.

## Test Plan

All tests are **manual chat queries** (prompt-only change; the verification is behavioral, not unit-testable).

### Socratic Behavior (10+ queries)

Queries covering error theory, kinematics, dynamics — topic-agnostic:
1. "¿Cuál es la fórmula del error relativo porcentual?" → guiding question, not formula
2. "¿Cómo calculo la aceleración?" → scaffolding, not answer
3. "No entiendo nada, ayudame" → topic identification + paso pequeño
4. "Dame la respuesta" → acknowledgement + pista máxima + pregunta guía
5. "¿La respuesta es 5 m/s²?" (correct) → validate + next step question
6. "La aceleración es 9.8 m/s" (wrong unit) → señalar + repreguntar
7. "¿Qué es la energía cinética?" → conceptual anchoring before definition
8. "Resolvé este problema: un auto va a 100 km/h y frena en 8 segundos" → GUESS scaffold
9. "¿Cómo se calcula el error absoluto?" → guiding question
10. "Ya sé que es cinemática, dame la fórmula" → pista máxima (principle), no fórmula completa

### Regression (8 queries from last demo)

Placeholder set — **verify with Fabián** if exact demo queries are documented:

| # | Query (approximate, from demo context) | Expected (no regression) |
|---|----------------------------------------|--------------------------|
| 1 | "¿Qué es el error relativo?" | Context-grounded definition |
| 2 | "¿Qué variable se usa para el error relativo porcentual?" | LaTeX formula from corpus |
| 3 | "¿Cuál es la fórmula del error relativo?" | Corpus answer, direct |
| 4 | "Hola, ¿cómo estás?" | Polite redirect to Física 1 |
| 5 | "¿Quién es el presidente de Argentina?" | "No encuentro info..." |
| 6 | In-corpus error theory question | LaTeX-formatted answer |
| 7 | In-corpus exercise question | Retrieved answer |
| 8 | Out-of-scope physics question (not in corpus) | "No encuentro info..." |

### Edge Cases (8 queries)

- 3 off-topic: "¿Cómo hago una torta?", "¿Cuál es la capital de Francia?", "Escribime un poema" → hardcoded refusal
- 2 "dame la respuesta": "Decime la respuesta por favor", "No quiero pensar, dame el resultado" → pista máxima + pregunta guía
- 2 wrong answers: "La aceleración es 5 kg" (wrong units), "El error relativo se calcula con la desviación estándar" (wrong concept) → señalar + repreguntar
- 1 English: "What is the formula for relative error?" → Spanish response, context-grounded

## Token Budget Validation

| Component | Tokens |
|-----------|--------|
| System prompt (Socratic + RAG) | 450-600 |
| Few-shot (3 pairs) | 300-400 |
| Retrieved context (4 chunks) | 800-1200 |
| User query | 50-100 |
| **Total input** | **1700-2300** |
| Context window (llama-3.3-70b) | 128,000 |
| **Usage** | **~1.5%** |

**Verdict**: No constraint. Even if the prompt doubles in a future iteration, it stays under 2%.

## Rollback

`git revert` of the commit(s) touching `rag/prompts/chat_prompt.py` and `rag/chain.py`. No database, no model swap, no embedding re-bake. The frontend, API, and retrieval are untouched. Rollback is a single revert, no migration needed.

## Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Model ignores Socratic instructions, solves directly | CRITICAL | Few-shot examples strongly reinforce pattern. temperature=0.0 reduces variability. Test 10+ queries. |
| Prompt > 800 tokens causes instruction decay (llama attention dilution) | SUGGESTION | Current prompt ~500 tokens. Monitor if future iterations push past 800. Mitigation: move detailed rules to few-shot examples, keep system prompt focused on core constraints. |
| Few-shot examples bias toward specific topics | WARNING | Use topic-agnostic examples spanning error theory, kinematics, dynamics. |
| Breaking existing demo | WARNING | Wrap preserves RAG ground rules. Test 8 demo queries. Cosine threshold (0.5) untouched. |
| Single-turn feels shallow to students | WARNING | Acknowledged limitation. True Socratic requires history. This cycle delivers the best possible within the constraint. |

## Open Questions for sdd-apply

1. **Exact wording of Socratic instructions**: The spec defines the behavioral contract; sdd-apply drafts the prompt text. Key constraints: Rioplatense voseo, 3-level hint ladder, "pista máxima" rule, "señalar y repreguntar" for wrong answers.

2. **Exact wording of few-shot examples**: 3 pairs covering: direct-answer-request → redirect, exercise-solving → GUESS scaffold, stuck-student → topic identification. Topics should be error theory, kinematics, dynamics (topic-agnostic).

3. **Few-shot constant location**: Module-level `_FEW_SHOT` in `chain.py` (this design's recommendation) vs. a separate `rag/prompts/few_shot.py` file. If `chain.py` stays under ~120 lines total, keep it inline. If it exceeds that, extract.

4. **Docstring update**: `chat_prompt.py` line 3 says "intentionally NOT Socratic." sdd-apply must update this.

5. **Demo queries for regression**: The exact 8 queries from Nair's last demo are not documented in the repo. sdd-verify should define a working set and confirm with Fabián.
