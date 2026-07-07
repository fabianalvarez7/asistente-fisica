# Socratic Layer Validation Run — 2026-07-06

## Status

**DEFERRED TO USER.**

The 26-query validation suite was not executed because the local environment is
not configured to run the RAG pipeline.

## Blockers

1. **Missing API key**: `GROQ_API_KEY` is not set in the environment.
   - Check: `python -c "import os; print(bool(os.getenv('GROQ_API_KEY')))"` → `False`.
2. **Missing Python dependencies**: the `openai` package (and likely others from
   `requirements.txt`) is not installed in the active interpreter.
   - Check: `python -c "from rag.chain import generate_response"` fails with
     `ModuleNotFoundError: No module named 'openai'`.

## What the user needs to do

1. Activate the project virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux; use .venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and set a valid `GROQ_API_KEY`.
3. Ensure the ChromaDB index exists under `data/chroma/` (run
   `python scripts/indexar_pdfs.py` if it is empty).
4. Run the 26 queries listed below via `POST /chat` or by importing
   `rag.chain.generate_response` directly.
5. Paste the verbatim responses into this file and mark each query as PASS or
   FAIL against the corresponding spec scenario.

## Test Plan (to be executed)

### Socratic Behavior (10 queries)

| # | Query | Spec scenario |
|---|-------|---------------|
| 1 | `¿Cuál es la fórmula del error relativo porcentual?` | Typical exercise query — guiding question, no direct answer |
| 2 | `¿Cómo calculo la aceleración?` | Conceptual question — Socratic questioning |
| 3 | `No entiendo nada, ayudame` | Stuck student — at least level-1 conceptual hint |
| 4 | `Dame la respuesta` | Direct answer request — pista máxima + guiding question |
| 5 | `¿La respuesta es 5 m/s²?` | Correct answer proposal — validate + next-step question |
| 6 | `La aceleración es 9.8 m/s` | Wrong unit — señalar + repreguntar |
| 7 | `¿Qué es la energía cinética?` | Conceptual anchoring |
| 8 | `Resolvé este problema: un auto va a 100 km/h y frena en 8 segundos` | GUESS scaffold |
| 9 | `¿Cómo se calcula el error absoluto?` | Guiding question |
| 10 | `Ya sé que es cinemática, dame la fórmula` | Pista máxima (principle), no complete formula |

### Regression Queries (8 queries)

See `tests/regression_queries.md` for the full list and expected patterns.

| # | Query | Expected pattern |
|---|-------|------------------|
| 1 | `¿Qué es el error relativo porcentual?` | Context-grounded, LaTeX preserved |
| 2 | `En un ejercicio de errores, la medida es 12.5 cm y el error absoluto es 0.2 cm. ¿Cómo expreso el resultado?` | Context-grounded answer |
| 3 | `¿Cómo hago una torta de chocolate?` | Exact fallback refusal |
| 4 | `¿Cómo se calcula la energía de un fotón?` | Exact fallback refusal |
| 5 | `¿Quién sos?` | Exact fallback refusal |
| 6 | `Hola, ¿cómo estás?` | Polite redirect to Física 1 |
| 7 | `¿Cuál es la fórmula del error relativo?` | LaTeX preserved + guiding question |
| 8 | `¿Qué diferencia hay entre error absoluto y error relativo?` | Direct context-grounded answer |

### Edge Cases (8 queries)

| # | Query | Expected pattern |
|---|-------|------------------|
| 1 | `¿Cómo hago una torta?` | Exact fallback refusal |
| 2 | `¿Cuál es la capital de Francia?` | Exact fallback refusal |
| 3 | `Escribime un poema` | Exact fallback refusal |
| 4 | `Decime la respuesta por favor` | Pista máxima + guiding question |
| 5 | `No quiero pensar, dame el resultado` | Pista máxima + guiding question |
| 6 | `La aceleración es 5 kg` | Wrong units — señalar + repreguntar |
| 7 | `El error relativo se calcula con la desviación estándar` | Wrong concept — señalar + repreguntar |
| 8 | `What is the formula for relative error?` | Spanish response, context-grounded |

## Iteration Log

No iterations yet — blocked before first run.
