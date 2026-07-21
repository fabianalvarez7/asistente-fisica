"""Run the 26-query Socratic layer validation suite and save results to markdown.

Usage:
    source .venv/bin/activate
    python scripts/run_socratic_tests.py

Output:
    tests/socratic_layer_run_<YYYY-MM-DD>.md

The script imports rag.chain.generate_response directly (skipping HTTP/SSE),
captures the concatenated tokens for each query, and writes a markdown report
with one section per query. Each section has a [ ] PASS / [ ] FAIL checkbox
for the user to fill in after review.

This script is not part of the socratic-layer scope (the design says tests are
manual chat queries), but it speeds up validation when running 26 queries in a
row. Discard or commit as preferred after the test run.
"""

import datetime
import sys
from pathlib import Path

from dotenv import load_dotenv  # noqa: E402

# Repo root on sys.path so we can import rag.* as the app does.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Load .env BEFORE importing rag.chain — chain.py creates the OpenAI client at
# module load with os.getenv("GROQ_API_KEY", ""), so the env var must be
# populated first. This mirrors the fix in app/main.py.
load_dotenv()

from rag.chain import generate_response  # noqa: E402


QUERIES: list[dict] = [
    # Socratic Behavior (10) — design.md §Test Plan → Socratic Behavior
    {"category": "Socratic", "spec": "1.1 typical exercise (guiding question, not formula)",
     "query": "¿Cuál es la fórmula del error relativo porcentual?"},
    {"category": "Socratic", "spec": "1.1 conceptual question (Socratic questioning)",
     "query": "¿Cómo calculo la aceleración?"},
    {"category": "Socratic", "spec": "1.2 stuck student (level-1 conceptual hint, no skip to level 3)",
     "query": "No entiendo nada, ayudame"},
    {"category": "Socratic", "spec": "1.2 dame la respuesta (pista máxima + guiding question)",
     "query": "Dame la respuesta"},
    {"category": "Socratic", "spec": "1.3 correct answer proposal (validate + next-step question)",
     "query": "¿La respuesta es 5 m/s²?"},
    {"category": "Socratic", "spec": "1.3 wrong units (señalar + repreguntar, no correct value)",
     "query": "La aceleración es 9.8 m/s"},
    {"category": "Socratic", "spec": "1.1 conceptual anchoring before definition",
     "query": "¿Qué es la energía cinética?"},
    {"category": "Socratic", "spec": "1.1 GUESS scaffold",
     "query": "Resolvé este problema: un auto va a 100 km/h y frena en 8 segundos"},
    {"category": "Socratic", "spec": "1.1 guiding question, not the formula",
     "query": "¿Cómo se calcula el error absoluto?"},
    {"category": "Socratic", "spec": "1.2 pista máxima (principle only, no complete formula)",
     "query": "Ya sé que es cinemática, dame la fórmula"},

    # Regression (8) — tests/regression_queries.md
    {"category": "Regression", "spec": "reg-1 in-corpus error theory, LaTeX preserved",
     "query": "¿Qué es el error relativo porcentual?"},
    {"category": "Regression", "spec": "reg-2 in-corpus exercise, no invented rule",
     "query": "En un ejercicio de errores, la medida es 12.5 cm y el error absoluto es 0.2 cm. ¿Cómo expreso el resultado?"},
    {"category": "Regression", "spec": "reg-3 off-topic → exact fallback refusal",
     "query": "¿Cómo hago una torta de chocolate?"},
    {"category": "Regression", "spec": "reg-4 out-of-Física-1 → exact fallback refusal",
     "query": "¿Cómo se calcula la energía de un fotón?"},
    {"category": "Regression", "spec": "reg-5 meta-question → exact fallback refusal",
     "query": "¿Quién sos?"},
    {"category": "Regression", "spec": "reg-6 polite greeting, redirect to Física 1",
     "query": "Hola, ¿cómo estás?"},
    {"category": "Regression", "spec": "reg-7 LaTeX formula preserved + guiding question",
     "query": "¿Cuál es la fórmula del error relativo?"},
    {"category": "Regression", "spec": "reg-8 factual context-grounded, no general knowledge",
     "query": "¿Qué diferencia hay entre error absoluto y error relativo?"},

    # Edge cases (8) — design.md §Test Plan → Edge Cases
    {"category": "Edge", "spec": "edge-1 off-topic → exact fallback refusal",
     "query": "¿Cómo hago una torta?"},
    {"category": "Edge", "spec": "edge-2 off-topic → exact fallback refusal",
     "query": "¿Cuál es la capital de Francia?"},
    {"category": "Edge", "spec": "edge-3 off-topic → exact fallback refusal",
     "query": "Escribime un poema"},
    {"category": "Edge", "spec": "edge-4 dame la respuesta → pista máxima + guiding question",
     "query": "Decime la respuesta por favor"},
    {"category": "Edge", "spec": "edge-5 dame la respuesta → pista máxima + guiding question",
     "query": "No quiero pensar, dame el resultado"},
    {"category": "Edge", "spec": "edge-6 wrong units → señalar + repreguntar",
     "query": "La aceleración es 5 kg"},
    {"category": "Edge", "spec": "edge-7 wrong concept → señalar + repreguntar",
     "query": "El error relativo se calcula con la desviación estándar"},
    {"category": "Edge", "spec": "edge-8 English → Spanish response, context-grounded",
     "query": "What is the formula for relative error?"},
]


def run_query(query: str) -> str:
    """Run a single query through the RAG chain and return the concatenated text.

    Parses SSE frames emitted by rag.chain.generate_response:
      data: <token>\\n\\n    -> append token
      data: [DONE]\\n\\n     -> terminator, ignored
      event: error\\ndata: .. -> captured as an ERROR prefix
    """
    tokens: list[str] = []
    error: str | None = None
    for frame in generate_response(query):
        if frame.startswith("data: "):
            content = frame[len("data: "):].rstrip("\n")
            if content != "[DONE]":
                tokens.append(content)
        elif frame.startswith("event: error"):
            for line in frame.splitlines():
                if line.startswith("data: "):
                    error = line[len("data: "):].rstrip("\n")
    if error:
        return f"ERROR: {error}"
    return "".join(tokens).strip()


def main() -> None:
    today = datetime.date.today().isoformat()
    output_path = Path(f"tests/socratic_layer_run_{today}.md")

    results: list[dict] = []
    total = len(QUERIES)
    for i, q in enumerate(QUERIES, start=1):
        print(f"[{i:>2}/{total}] {q['category']:<11} | {q['query'][:60]}")
        try:
            response = run_query(q["query"])
        except Exception as exc:  # noqa: BLE001
            response = f"ERROR (uncaught): {exc}"
        results.append({**q, "response": response})
        preview = response.replace("\n", " ")[:80]
        print(f"           → {preview}{'...' if len(response) > 80 else ''}")

    with output_path.open("w", encoding="utf-8") as f:
        f.write(f"# Socratic Layer Validation Run — {today}\n\n")
        f.write("**Status**: pending review\n\n")
        f.write(f"**Total queries**: {total} (10 Socratic + 8 regression + 8 edge cases)\n\n")
        f.write("**Instructions**: For each query, check the response against the\n")
        f.write("spec scenario stated below. Mark PASS or FAIL. Notes go in the\n")
        f.write("empty line after the checkbox.\n\n")
        f.write("---\n\n")
        for i, r in enumerate(results, start=1):
            f.write(f"## Query {i:>2} — {r['category']}\n\n")
            f.write(f"**Spec scenario**: {r['spec']}\n\n")
            f.write(f"**Query**: `{r['query']}`\n\n")
            f.write("**Response**:\n\n```\n")
            f.write(r["response"])
            f.write("\n```\n\n")
            f.write("**Pass/Fail**: [ ] PASS  [ ] FAIL\n\n")
            f.write("**Notes**:\n\n")
            f.write("\n---\n\n")

    print(f"\nResults written to {output_path}")


if __name__ == "__main__":
    main()
