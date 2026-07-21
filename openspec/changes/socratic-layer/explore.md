# Exploration: Socratic Layer

> **Status**: complete
> **Change**: `socratic-layer`
> **Scope**: System prompt + few-shot examples only. No history, no auth, no infra.

---

## Executive Summary

The current system is a RAG-only chat: a short system prompt (`rag/prompts/chat_prompt.py`, 20 lines) enforces grounding on retrieved context and a hard refusal fallback. There is zero pedagogical behavior — the assistant answers questions directly from the corpus. Adding the Socratic layer is a prompt-only change: extend `SYSTEM_PROMPT` with Socratic instructions and few-shot examples, keeping the RAG grounding rules intact. The main design tension is between "never give the answer" (hard pedagogical requirement) and "student is stuck and anxious" (real user profile). The recommendation is a **progressive hint ladder** encoded in the prompt, with a maximum of 3 escalation levels before a near-answer hint — never the full solution.

---

## 1. Current State (Code Audit)

### 1.1 System Prompt — `rag/prompts/chat_prompt.py:10-20`

```
Sos un asistente de Física 1. Respondé ÚNICAMENTE con la información provista
en el contexto de abajo. Antes de responder, verificá que el contexto realmente
trate la pregunta planteada.

- Si el contexto está presente pero no responde a ESTA pregunta específica,
  decí exactamente: "No encuentro info sobre esto en los apuntes".
- Si el contexto no contiene información suficiente para responder la pregunta,
  decí exactamente: "No encuentro info sobre esto en los apuntes".
- No respondas preguntas que no sean de Física 1. Si te preguntan algo fuera
  del alcance (otra materia, meta-preguntas, "quién sos"), respondé con:
  "No encuentro info sobre esto en los apuntes".
- No uses conocimiento general. No inventes fórmulas ni conceptos.
- Si el contexto tiene fórmulas en LaTeX, incluílas en tu respuesta.
- Respondé en español, con un tono claro y didáctico.

Contexto:
{context}
```

**Key observations:**
- 20 lines total, ~180 tokens.
- Uses Rioplatense Spanish voseo (`sos`, `respondé`, `verificá`, `decí`, `incluílas`).
- Has a single `{context}` placeholder filled at `rag/chain.py:71`.
- Explicitly NOT Socratic — the docstring at line 3 says: "This prompt is intentionally NOT Socratic — that layer belongs to week 5-6."
- The fallback phrase "No encuentro info sobre esto en los apuntes" is hardcoded in both the prompt AND `rag/chain.py:27` (`_NO_CONTEXT_FALLBACK`). The chain-level fallback fires BEFORE Groq is called (when cosine distance > 0.5). The prompt-level fallback handles the case where context is retrieved but doesn't answer the specific question.

### 1.2 Prompt Loading — `rag/chain.py:12, 71`

```python
from rag.prompts import SYSTEM_PROMPT  # line 12
prompt = SYSTEM_PROMPT.format(context=context)  # line 71
```

The prompt is imported as a module-level constant, formatted with the retrieved context string, and passed as the `system` message to Groq. There is no dynamic prompt composition — no conversation history, no user profile, no adaptive behavior.

### 1.3 RAG Context Injection — `rag/chain.py:29-35, 62-71`

```python
def _build_context(documents: list) -> str:
    parts = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "desconocido")
        parts.append(f"[Extracto {i} - {source}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)
```

- Retrieves top-4 chunks by cosine similarity (`k=4`, line 62).
- Distance threshold: 0.5 (cosine distance; line 25). If best chunk has distance > 0.5, the chain short-circuits with the hardcoded fallback and Groq is NEVER called.
- Context is formatted as numbered extracts with source attribution.
- The context string is injected into `{context}` in the system prompt.

### 1.4 Groq Call — `rag/chain.py:73-82`

```python
model = os.getenv("LLM_MODEL", _DEFAULT_MODEL)  # llama-3.3-70b-versatile
stream = _OPENAI_CLIENT.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": prompt},
        {"role": "user", "content": query},
    ],
    stream=True,
    temperature=0.0,
)
```

- Two messages only: system + user. No assistant history, no few-shot messages.
- `temperature=0.0` — deterministic output.
- Streaming via SSE. Tokens are yielded as `data: <token>\n\n` frames.
- Model: `llama-3.3-70b-versatile` — 128k token context window.

### 1.5 Response Return — `rag/chain.py:84-90`

Tokens are streamed directly to the frontend. No post-processing, no filtering, no Socratic transformation. What Groq generates is what the student sees.

### 1.6 Frontend — `app/static/chat.js`

- Sends `POST /chat` with `{ query: string }`.
- Receives SSE stream, appends tokens to a chat bubble.
- KaTeX renders LaTeX in the bubble on `[DONE]`.
- No conversation history is maintained client-side. Each request is independent.
- Max 500 chars per query.

### 1.7 Critical Constraint: No Conversation History

The current architecture is **single-turn**. Each request is an independent RAG query. There is no list of previous messages passed to Groq. This means:
- The Socratic layer CANNOT do true multi-turn scaffolding in this cycle.
- "Student is stuck in a loop" cannot be detected by the model (no history to see the loop).
- Multi-turn Socratic flow requires the SQLite history work (separate cycle, week 5-6).

**Implication for this cycle**: the Socratic layer must work within a single turn. The prompt can instruct the model to ask guiding questions, but it cannot track whether the student already answered a previous guiding question. The "progressive hint ladder" can only be encoded as static instructions, not as adaptive state.

---

## 2. Socratic Method Design Space (First-Year Physics)

### 2.1 What Good Socratic Guidance Looks Like

For first-year physics (kinematics, dynamics, energy, error theory — the Física 1 syllabus at UNR), the established pedagogical patterns are:

| Pattern | Description | When to use |
|---------|-------------|-------------|
| **GUESS framework** | Given → Unknown → Equation → Substitute → Solve. Ask the student to identify each step. | Exercise solving (the primary use case). |
| **Conceptual anchoring** | "What principle applies here?" → Newton's 2nd law, conservation of energy, etc. | When the student jumps to formulas without understanding. |
| **Hint ladder** | Start with a meta-question → progressively more specific hints → near-answer hint. NEVER the full solution. | When the student is stuck. |
| **Error analysis prompt** | "Check your units", "Does the magnitude make physical sense?", "What happens at the limit?" | After the student proposes an answer. |
| **Decomposition** | Break a complex problem into sub-problems. "First, let's find the acceleration. Then we'll use it for the velocity." | Multi-step problems. |
| **Socratic反问 (counter-question)** | Student: "What's the formula?" → Assistant: "What variables do you have, and what are you trying to find?" | When the student asks for the answer directly. |

### 2.2 Intervention Levels

The key design question: how much should the assistant push vs. help?

| Level | Behavior | Risk |
|-------|----------|------|
| **Pure Socratic** | ALWAYS asks questions. Never gives any information. | Student frustration. Anxious students give up. |
| **Progressive hints** | Start with questions. If stuck, give increasingly specific hints. Never the full answer. | Requires detecting "stuck" — hard without history. |
| **Guided solution** | Walk through the problem step by step, asking the student to fill in each step. | Close to "solving it" — risks violating the non-negotiable. |

**Recommendation**: **Progressive hints** with a maximum of 3 escalation levels. The prompt should instruct the model to:
1. First response: always a guiding question (never information).
2. If the student's question implies confusion: give a conceptual hint + a guiding question.
3. If the student explicitly asks for the answer: acknowledge the frustration, give a near-answer hint (e.g., "the key equation involves conservation of energy"), then ask a final guiding question.
4. NEVER give the complete solution or the final numerical answer.

### 2.3 Single-Turn Constraint

Without conversation history, the model cannot know if this is the student's 1st or 5th message. Two strategies:

- **Strategy A**: Assume every message is the first. The prompt gives general Socratic instructions. The model asks a guiding question based on the query alone.
- **Strategy B**: The prompt instructs the model to interpret the query's tone. If the query says "ya te pregunté esto" or "no entiendo", the model escalates to a more specific hint. This is fragile (the model may misread tone) but works without history.

**Recommendation**: Strategy A for this cycle. Strategy B is a nice-to-have for when history arrives. The prompt should include a general instruction: "If the student expresses frustration or says they are stuck, provide a more specific hint, but never the complete answer."

---

## 3. Composition with RAG — Approaches

### Approach A: Replace the System Prompt

Replace `SYSTEM_PROMPT` entirely with a Socratic prompt that includes RAG grounding rules inline.

- **Pros**: Clean slate. No legacy phrasing to work around.
- **Cons**: Must re-implement all the grounding rules (refuse out-of-scope, use only context, LaTeX handling). Risk of losing a grounding rule.
- **Effort**: Low.

### Approach B: Wrap the Existing Prompt (RECOMMENDED)

Keep the existing RAG grounding rules. Add a Socratic section BEFORE the context block. The prompt becomes:

```
[Socratic instructions: guide with questions, never solve directly, hint ladder, language/tone]
[RAG grounding rules: answer only from context, refuse if not found, no general knowledge, LaTeX]
Contexto:
{context}
```

- **Pros**: Minimal risk. Grounding rules stay intact and tested. Socratic layer is additive. Easy to revert (remove the Socratic section). Clear separation of concerns in the prompt.
- **Cons**: Prompt gets longer (~400-600 tokens total). Still well within 128k context.
- **Effort**: Low.

### Approach C: Post-Process the LLM Response

Let the LLM answer directly (current behavior), then pass the response through a second LLM call that rewrites it in Socratic style.

- **Pros**: Decouples Socratic from RAG.
- **Cons**: Doubles Groq API calls (cost, latency). Fragile — the second call may lose information from the context. Hard to debug.
- **Effort**: Medium-High.

### Approach D: Two-Stage (Rewrite Query → RAG → Socratic)

Rewrite the student's query into a "Socratic query" before RAG retrieval. Then retrieve and answer.

- **Pros**: Could improve retrieval quality for vague student questions.
- **Cons**: Over-engineering for a prototype. Adds latency. Unclear benefit.
- **Effort**: Medium.

### Decision Matrix

| Criterion | A (Replace) | B (Wrap) | C (Post-process) | D (Two-stage) |
|-----------|-------------|----------|-------------------|---------------|
| Preserves RAG grounding | Risk | ✅ Yes | ✅ Yes | ✅ Yes |
| Diff size | ~40 lines | ~30 lines | ~80 lines | ~100 lines |
| Revertability | Medium | ✅ Easy | Hard | Hard |
| Latency impact | None | None | +1 Groq call | +1 Groq call |
| Debuggability | Medium | ✅ High | Low | Low |
| Fits 400-line budget | ✅ Yes | ✅ Yes | Risky | Risky |

**Recommendation: Approach B (Wrap)**. It preserves all existing grounding rules, adds the Socratic layer as a clearly delimited section, and is trivially revertable. The diff is ~30 lines in `chat_prompt.py`.

---

## 4. Edge Case Strategy

### 4.1 "Dame la respuesta" / "I just want the answer" / "decímela directo"

**Strategy**: Acknowledge the frustration, explain why the assistant can't give the answer, provide the most specific hint possible WITHOUT giving the solution, and end with a guiding question.

**Prompt instruction**: "Si el estudiante pide la respuesta directamente, reconocé su frustración, explicá brevemente que tu rol es ayudarle a pensar, dale la pista más específica que puedas sin resolver el ejercicio, y cerrá con una pregunta guía."

**Example**:
> Student: "Decime la respuesta, por favor"
> Assistant: "Entiendo que quieras terminar rápido, pero mi trabajo es ayudarte a pensar. Te doy una pista: el problema se resuelve con conservación de energía mecánica. ¿Podés identificar cuáles son la energía cinética y la potencial en el estado inicial y final?"

### 4.2 Student Stuck in a Loop

**Strategy**: Without conversation history, the model cannot detect a loop. The prompt should include a general instruction for when the student expresses being stuck: "Si el estudiante dice que no entiende o que está trabado, dividí el problema en un paso más pequeño y preguntá por ese paso específico."

**Future (with history)**: Detect repeated queries and escalate to a fundamentally different approach (e.g., a worked analogy from the corpus).

### 4.3 Off-Topic Question (Not in Corpus)

**Strategy**: Already handled by the existing RAG grounding. The cosine distance threshold (0.5) catches most off-topic queries before Groq is called. If context IS retrieved but doesn't match, the prompt instructs the model to say "No encuentro info sobre esto en los apuntes". The Socratic layer should NOT change this behavior.

**Prompt addition**: Keep the existing refusal rule. Add: "Si la pregunta no está en los apuntes, no intentes guiar al estudiante. Decí simplemente que no encontrás la información."

### 4.4 Outside Física 1 Syllabus

**Strategy**: Same as off-topic. The existing prompt already says: "No respondas preguntas que no sean de Física 1." The Socratic layer should not weaken this rule.

### 4.5 Multi-Turn Socratic Flow

**Strategy**: NOT POSSIBLE in this cycle (no conversation history). The prompt can instruct the model to ask guiding questions, but it cannot track whether the student answered a previous question.

**What this cycle CAN do**: The model asks a guiding question. The student's NEXT message (a new request) may answer that question. The model treats the new message as a fresh query, retrieves context, and asks a new guiding question that — by luck — builds on the student's answer. This is not true scaffolding, but it's the best possible without history.

**Future (with history)**: Pass the conversation history as additional messages in the Groq call. The model can then see the full dialogue and scaffold properly.

### 4.6 Student Writing in English

**Strategy**: The prompt instructs the model to respond in Spanish ("Respondé en español"). If the student writes in English, the model should still respond in Spanish (the course is at an Argentine public university). However, the model should understand the English query and retrieve context based on it (the embedding model is multilingual).

**Prompt instruction**: "Respondé siempre en español, incluso si el estudiante escribe en otro idioma. El curso es en español."

---

## 5. Few-Shot Examples

### 5.1 Recommendation

- **Number**: 3 examples. Enough to show the pattern without bloating the prompt.
- **Language**: Spanish (Rioplatense voseo, matching the existing prompt).
- **Style**: Progressive questioning. No full solutions. Each example shows a different intervention level.
- **Format**: Injected as additional messages in the Groq call (user/assistant pairs), NOT in the system prompt. This follows the established pattern for few-shot in LLM prompting and keeps the system prompt focused on instructions.

### 5.2 Sketch Examples

**Example 1: Direct answer request → redirect to guiding question**

```
User: ¿Cuál es la fórmula del error relativo porcentual?
Assistant: Antes de darte la fórmula, pensemos juntos. ¿Podés decirme qué es el error relativo? ¿Y qué diferencia hay entre error absoluto y relativo?
```

**Example 2: Exercise solving → GUESS framework scaffolding**

```
User: Un auto frena de 60 km/h a 0 en 5 segundos. ¿Cuánto vale la aceleración?
Assistant: Buen problema. Para resolverlo, primero necesitamos identificar qué datos tenemos. ¿Podés listar las variables que conocés y la que buscás?
```

**Example 3: Stuck student → progressive hint**

```
User: No entiendo, no sé cómo empezar
Assistant: Tranquilo, vamos de a poco. Empecemos por lo básico: ¿de qué tema del curso trata este problema? ¿Es cinemática, dinámica, energía, o error de medición?
```

### 5.3 Implementation

The few-shot examples should be passed as messages in the Groq call:

```python
messages = [
    {"role": "system", "content": prompt},
    {"role": "user", "content": "¿Cuál es la fórmula del error relativo porcentual?"},
    {"role": "assistant", "content": "Antes de darte la fórmula..."},
    {"role": "user", "content": "Un auto frena de 60 km/h a 0 en 5 segundos..."},
    {"role": "assistant", "content": "Buen problema. Para resolverlo..."},
    {"role": "user", "content": "No entiendo, no sé cómo empezar"},
    {"role": "assistant", "content": "Tranquilo, vamos de a poco..."},
    {"role": "user", "content": query},  # actual student query
]
```

This approach:
- Keeps the system prompt clean (instructions only).
- Shows the model concrete examples of the desired behavior.
- Uses ~300-400 tokens for the examples — well within the 128k context.
- Is easy to iterate: change the examples without touching the system prompt logic.

---

## 6. Affected Areas

| File | Why it's affected |
|------|-------------------|
| `rag/prompts/chat_prompt.py` | System prompt gets Socratic instructions added (wrap approach). ~30 lines added. |
| `rag/chain.py` | Few-shot examples injected as messages before the actual user query. ~15 lines added. |
| `rag/prompts/__init__.py` | May need to export few-shot message list if it's a separate constant. ~2 lines. |

**NOT affected**: `app/main.py`, `app/static/*`, `rag/retrievers/*`, `rag/loaders/*`, `rag/splitters/*`, `Dockerfile`, `requirements.txt`.

---

## 7. Token Budget Analysis

| Component | Estimated tokens | Notes |
|-----------|-----------------|-------|
| System prompt (current) | ~180 | 20 lines, Spanish |
| System prompt (with Socratic) | ~450-600 | +Socratic instructions, hint ladder rules, edge cases |
| Few-shot examples (3 pairs) | ~300-400 | 3 user/assistant pairs, Spanish |
| Retrieved context (4 chunks) | ~800-1200 | ~200-300 tokens per chunk |
| User query | ~50-100 | Max 500 chars |
| **Total input** | **~1700-2300** | Well within 128k limit |
| Output (assistant response) | ~100-300 | Guiding question + hint |

**Conclusion**: Token budget is NOT a constraint. We use <2% of the available context window.

---

## 8. Open Questions for Nair / Fabián

These should be resolved before or during the proposal phase:

1. **Intervention strictness**: Should the assistant NEVER give any numerical answer, even if the student is clearly about to give up? Or is there a "maximum hint" level where the assistant gives the final formula but asks the student to substitute the values? **This is a pedagogical decision that Nair must validate.**

2. **Tone calibration**: The current prompt uses Rioplatense voseo. Should the Socratic layer maintain this tone, or switch to a more neutral Spanish? The audience is Argentine students, so voseo feels natural — but Nair should confirm.

3. **Error handling philosophy**: When the student gives a wrong answer, should the assistant (a) point out the error and ask them to reconsider, or (b) ignore the wrong answer and redirect to the guiding question? Option (a) is better pedagogy but requires the model to evaluate the student's answer — which is hard without domain expertise in the prompt.

4. **Scope of "Física 1"**: The current corpus only covers error theory (cuadernillo). When the corpus expands to kinematics, dynamics, energy, etc., the Socratic examples may need to be updated. Should we write examples that are topic-agnostic, or specific to the current corpus?

5. **Few-shot example source**: Should the examples be invented (based on pedagogical best practices), or should they come from actual exercises in the cuadernillo? Using real exercises makes the examples more authentic but ties them to the current corpus.

6. **Multi-turn Socratic timeline**: True multi-turn Socratic requires conversation history (SQLite). Is the history work still planned for the same cycle (week 5-6), or is it deferred? If deferred, the Socratic layer will be single-turn for longer.

---

## 9. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Model ignores Socratic instructions and solves the exercise anyway** | CRITICAL | Few-shot examples strongly reinforce the pattern. Temperature=0.0 helps. Test with 10+ queries before deploying. |
| **Model gives up too quickly (just says "No encuentro info")** | WARNING | The cosine distance threshold (0.5) already filters bad retrievals. The prompt should reinforce: if context is present, TRY to guide, even if the match is imperfect. |
| **Prompt gets too long and confuses the model** | SUGGESTION | Unlikely at ~600 tokens. Llama 3.3 70B handles long system prompts well. Monitor output quality after deployment. |
| **Few-shot examples bias the model toward specific topics** | WARNING | Use topic-agnostic examples (error theory, kinematics, dynamics) to avoid bias. |
| **Student frustration leads to abandonment** | WARNING | The progressive hint ladder mitigates this. The "maximum hint" level should be validated with Nair. |
| **Breaking the existing demo** | CRITICAL | The wrap approach preserves all existing grounding rules. Test the exact same queries from the last demo to ensure they still work. |
| **Single-turn limitation makes Socratic feel shallow** | WARNING | Acknowledged. True Socratic requires history (next cycle). For now, the prompt asks guiding questions — it's not true scaffolding, but it's the pedagogical differentiator we can ship this cycle. |

---

## 10. Recommendation Summary

1. **Approach**: Wrap the existing system prompt with Socratic instructions (Approach B).
2. **Few-shot**: 3 examples in Spanish (Rioplatense voseo), injected as messages in the Groq call.
3. **Intervention level**: Progressive hint ladder with 3 levels. Never the full solution.
4. **Edge cases**: Off-topic and out-of-scope keep the existing hard refusal. "Dame la respuesta" gets a progressive hint. Multi-turn Socratic is deferred to the history cycle.
5. **Files changed**: `rag/prompts/chat_prompt.py` (~30 lines), `rag/chain.py` (~15 lines), `rag/prompts/__init__.py` (~2 lines). Total: ~47 lines. Well within the 400-line budget.
6. **Validation**: Test with 10+ queries covering: direct answer request, exercise solving, stuck student, off-topic, out-of-scope, LaTeX formulas. Compare with the 8 queries from the last demo to ensure no regression.

---

## Ready for Proposal

**Yes.** The exploration has enough detail to feed the proposal phase. The orchestrator should tell the user:

> "The Socratic layer is a prompt-only change: we wrap the existing system prompt with Socratic instructions and add 3 few-shot examples. The RAG grounding rules stay intact. The main design decision is the intervention level (progressive hint ladder, never the full answer), which Nair should validate. The biggest constraint is that true multi-turn Socratic requires conversation history — that's a separate cycle. This cycle ships single-turn Socratic guidance, which is the pedagogical differentiator we can demo."
