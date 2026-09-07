"""Smoke test script for the Socratic layer against the deployed HF Space.

Extracts the 26 queries from tests/socratic_layer_run_2026-08-07.md, sends
each one to the deployed /chat endpoint as SSE, and saves the response
text. The human then eyeballs each response against the expected pattern
in the spec file.

Usage:
  python scripts/smoke_test_space.py [space_url]

Default URL: https://fabianalvarez7-asistente-fisica-unr.hf.space
"""

import json
import re
import sys
import time
from pathlib import Path

import urllib.request
import urllib.error

REPO_ROOT = Path(__file__).resolve().parent.parent
QUERIES_FILE = REPO_ROOT / "tests" / "socratic_layer_run_2026-08-07.md"
OUTPUT_DIR = Path("/tmp/smoke-results")

DEFAULT_URL = "https://fabianalvarez7-asistente-fisica-unr.hf.space"
STUDENT_NAME = f"smoke-{int(time.time())}"


def extract_queries() -> list[str]:
    """Pull each query string out of the spec file (lines like `- **Query**: \`...\``)."""
    text = QUERIES_FILE.read_text()
    return re.findall(r"\*\*Query\*\*: `(.*?)`", text)


def stream_chat(url: str, query: str, student_name: str) -> str:
    """POST to /chat, read the SSE stream, return concatenated data payloads."""
    body = json.dumps({"query": query, "student_name": student_name}).encode()
    req = urllib.request.Request(
        f"{url}/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    out: list[str] = []
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            for raw in resp:
                line = raw.decode("utf-8", errors="replace").rstrip("\r\n")
                if line.startswith("data: "):
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    out.append(payload)
    except urllib.error.HTTPError as exc:
        return f"[HTTP {exc.code}] {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        return f"[ERROR] {exc}"
    return "".join(out)


def main() -> int:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    queries = extract_queries()
    if not queries:
        print(f"No queries found in {QUERIES_FILE}")
        return 1

    print(f"Smoke test against {url}")
    print(f"Student name: {STUDENT_NAME}")
    print(f"Queries: {len(queries)}")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary: list[tuple[int, str, str]] = []

    for i, q in enumerate(queries, start=1):
        print(f"[{i:02d}/{len(queries)}] {q[:60]}{'...' if len(q) > 60 else ''}")
        answer = stream_chat(url, q, STUDENT_NAME)
        snippet = (answer[:100] + "...") if len(answer) > 100 else answer
        print(f"      -> {snippet[:120]}")
        summary.append((i, q, answer))
        (OUTPUT_DIR / f"q{i:02d}.md").write_text(
            f"# Query {i}\n\n**Q**: {q}\n\n**A**: {answer}\n"
        )
        # tiny pause so we don't hammer the free-tier Space
        time.sleep(0.4)

    print()
    print(f"Done. Per-query transcripts in {OUTPUT_DIR}/")
    print()
    print("Now open tests/socratic_layer_run_2026-08-07.md next to /tmp/smoke-results/")
    print("and eyeball each response against the spec scenario.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())