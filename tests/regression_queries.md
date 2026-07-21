# Regression Query Set

> Regression queries for the Socratic layer change.
>
> These queries exercise the RAG ground rules and refusal behavior that were
> demonstrated in the last demo. If Fabián has the exact original 8 demo queries,
> replace this working set with those.

## Query 1 — In-corpus error theory (LaTeX expected)

- **Query**: `¿Qué es el error relativo porcentual?`
- **Expected pattern**: Response is grounded in the retrieved context, explains
  the concept, and includes the LaTeX formula for relative error.
- **Regression-tests**: RAG grounding (SHALL #5), LaTeX preservation
  (SHALL #8).

## Query 2 — In-corpus exercise (retrieved answer expected)

- **Query**: `En un ejercicio de errores, la medida es 12.5 cm y el error absoluto es 0.2 cm. ¿Cómo expreso el resultado?`
- **Expected pattern**: Response uses the context to explain how to express a
  measurement with its absolute error (e.g., `12.5 ± 0.2 cm`). It may ask a
  guiding question but must not invent a different rule.
- **Regression-tests**: RAG grounding (SHALL #5), Socratic guidance
  (SHALL #1).

## Query 3 — Off-topic question

- **Query**: `¿Cómo hago una torta de chocolate?`
- **Expected pattern**: Exact fallback phrase:
  `No encuentro info sobre esto en los apuntes`.
- **Regression-tests**: Off-topic refusal (SHALL #4).

## Query 4 — Out-of-Física-1 physics question

- **Query**: `¿Cómo se calcula la energía de un fotón?`
- **Expected pattern**: Exact fallback phrase:
  `No encuentro info sobre esto en los apuntes`.
- **Regression-tests**: Out-of-scope refusal (SHALL #4).

## Query 5 — Meta-question

- **Query**: `¿Quién sos?`
- **Expected pattern**: Exact fallback phrase:
  `No encuentro info sobre esto en los apuntes`.
- **Regression-tests**: Meta-question refusal (SHALL #4).

## Query 6 — Polite greeting / meta

- **Query**: `Hola, ¿cómo estás?`
- **Expected pattern**: Polite redirect back to Física 1; may invite the student
  to ask a physics question. Must not fall into a social conversation.
- **Regression-tests**: Single-turn behavior (SHALL #7), RAG grounding
  (SHALL #5).

## Query 7 — In-corpus LaTeX formula query

- **Query**: `¿Cuál es la fórmula del error relativo?`
- **Expected pattern**: Response includes the LaTeX expression for relative
  error unchanged from the context, and ends with a guiding question.
- **Regression-tests**: LaTeX preservation (SHALL #8), Socratic guidance
  (SHALL #1).

## Query 8 — Factual question answered by context

- **Query**: `¿Qué diferencia hay entre error absoluto y error relativo?`
- **Expected pattern**: Direct, context-grounded explanation of the difference.
  The answer must come from the retrieved context, not general knowledge.
- **Regression-tests**: RAG grounding (SHALL #5), Socratic guidance
  (SHALL #1).
