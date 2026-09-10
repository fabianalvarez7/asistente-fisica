# AGENTS.md — Asistente de Física

> Read this file first. It is the constitution of this repository.
> Any agent (human or AI) working on this project must read it before doing anything.

---

## 1. Project Context

**Asistente de Física** is a web application that helps students of *Física 1* (a first-year physics course at Universidad Nacional de Rosario) work through exercise solving via a Socratic chat assistant.

The assistant is grounded in the course's own PDF materials (notes, exercises, theory). It does not answer physics questions from general knowledge. It guides the student through the problem with questions, never giving the solution directly.

This is a **prototype**, not a production system. It must work well at low scale, be free for end users (it serves a public university), and be simple enough for a single developer to maintain.

## 2. Stakeholders

| Role | Who | Responsibility |
|---|---|---|
| Promoter | **Nair** (Physics professor, UNR Bioquímica y Farmacia) | Owns the academic vision and validates the assistant's behaviour. |
| Developer | **Fabián** (TUIA student, 4th semester) | Sole developer. Owns architecture, code, and delivery. |
| Content owners | **Physics professors** (Física 1, UNR) | Upload and curate the source PDFs. View usage statistics. |
| End users | **Física 1 students** | Use the chat assistant. No technical skills assumed. |
| Project manager | **Tatiana** (student, other UNR career) | Handles project management and coordination. Non-developer. |
| UX & design | **Justo** (student, other UNR career) | Owns interface and user-experience design. Non-developer. |

Fabián is the only person writing code in this project. Tatiana, Justo, the professors, and Nair do not touch code.

## 3. Non-negotiable Constraints

These are not preferences. They are the project's hard boundaries.

- **Prototype, not production.** Optimise for clarity and learning, not for scale.
- **Free for end users.** The student must never be asked to pay or install anything.
- **No local install for end users.** The student must access the app through a browser URL. No Python, no `pip install`, no local models on the student's machine.
- **Socratic style.** The assistant guides with questions; it never solves the exercise directly. This is a pedagogical requirement, not a UX preference.
- **RAG-only answers.** The assistant answers from the course's own PDFs, never from the model's general knowledge. This is enforced by prompt design, not by trusting the model.
- **History per student.** Each student has a persistent conversation history. Conversations are not anonymous.
- **Cross-platform development.** Development must work on macOS (Fabián) and Windows (peer collaborators). Code paths, device detection, and line endings must be considered.
- **Cross-platform deployment.** The deployed app must work in any modern browser, including on low-end Windows machines with slow connections.

## 4. Confirmed Stack

| Layer | Choice | Why |
|---|---|---|
| Language | **Python 3.11+** | Fabián's only language. |
| Backend | **FastAPI** | Python-native, async, auto docs, simple. |
| RAG framework | **LangChain** | Used as a toolbox (loaders, splitters, retrievers), not as an opinionated framework. We own the orchestration. |
| Vector store | **ChromaDB** | Local, persistent, simple, free. |
| LLM provider | **Groq** (API) | Free tier, fast, supports Spanish and LaTeX. |
| Embeddings | **sentence-transformers** with `intfloat/multilingual-e5-small` (270MB) | Local, free, no network, multilingual. Runs on MPS (macOS), CUDA (Windows with NVIDIA GPU), or CPU as fallback. |
| Persistence | **SQLite** | File-based, zero setup, easy to migrate to Postgres if the prototype grows. |
| PDF → Markdown | **pymupdf4llm** (start), with `marker-pdf` or **Mathpix** as plan B if formulas/images are lost | pymupdf4llm is the lightest starting point. Mathpix has a 1000-page/month free tier. |
| Frontend (chat) | **Plain HTML + CSS + JS** served by FastAPI | One page. No React, no SPA. Fetch to `/chat` endpoint. |
| Frontend (dashboard) | **Streamlit** | Ideal for static analytics, charts, filters. No conversational state. |
| Deploy | **Hugging Face Spaces Docker** (free cpu-basic) | 16 GB RAM, supports Docker, ~48 h sleep. Replaces Render after OOM at 967 MB. |

## 5. Repository Structure

```
asistente-fisica/
├── app/                 # FastAPI backend (chat endpoints, API for dashboard)
├── dashboard/           # Streamlit app for professors
├── rag/                 # RAG logic: loaders, splitters, retrievers, prompts
│   ├── loaders/         # PDF → Markdown
│   ├── splitters/       # Chunking strategies
│   ├── retrievers/      # Vector retrieval, re-ranking
│   ├── prompts/         # System prompts (including the Socratic layer)
│   └── chain.py         # Orchestration (RAG pipeline composition)
├── scripts/             # CLI scripts (index PDFs, run dev tasks)
├── data/                # ChromaDB and SQLite (GITIGNORED, dev/local only)
│   ├── chroma/          # dev-time index when re-indexing locally
│   └── historial.db
├── rag/index/           # Pre-baked artifacts (COMMITTED, deploy-time only)
│   └── chroma/          # baked index — read-only at runtime
├── tests/               # Pytest tests (when they arrive)
├── docs/                # Architecture decisions, ADRs, what we discussed
├── .env.example         # Template for GROQ_API_KEY, etc.
├── .gitignore
├── requirements.txt
└── AGENTS.md            # This file
```

> `rag/index/hf-model/` is **not** in the repo. The Dockerfile downloads the embedding model (`intfloat/multilingual-e5-small`, 448 MB) at build time using `scripts/preparar_indice_hf.py` — GitHub LFS free tier caps per-file uploads at 100 MB, so tracking the model in git is not viable. Local devs run the same script (or just the app once) to populate the dir; it is gitignored.

**Rule:** business logic lives in `rag/`. FastAPI and Streamlit are thin transport layers. They do not contain retrieval or prompt logic. This separation is what allows us to swap pieces without rewriting endpoints.

## 6. Setup Local (macOS / Windows)

```bash
# 1. Clone
git clone <repo-url> asistente-fisica
cd asistente-fisica

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure secrets
cp .env.example .env
# Edit .env and set GROQ_API_KEY (get one at https://console.groq.com)

# 5. Index the PDFs (run once, or whenever the corpus changes)
python scripts/indexar_pdfs.py

# 6. Run the chat backend
uvicorn app.main:app --reload

# 7. Run the professor dashboard (separate terminal)
streamlit run dashboard/app.py
```

**Notes for the developer:**
- On macOS with Apple Silicon, embeddings will use MPS automatically.
- On Windows without a CUDA GPU, embeddings will use CPU. Indexing will be slower.
- On Windows with an NVIDIA GPU, set `EMBEDDINGS_DEVICE=cuda` in `.env`.

## 7. Architecture Decisions (and Why)

Each decision here was made consciously. Do not revert them without a written ADR in `docs/`.

1. **RAG first, Socratic layer later.** They are separate concerns. Mixing them makes the prompt and the retriever both harder to debug. Month 3 is dedicated to the Socratic layer.

2. **Two frontends, not one.** Streamlit re-renders the whole app on every interaction. That fights a chat interface. Streamlit shines for the dashboard, where there is no conversational state. Each tool where it fits best.

3. **Local embeddings, not an embedding API.** sentence-transformers is free, offline, and respects the "no network dependency" rule for embeddings. We could switch to an API later if quality demands it, but we are not starting there.

4. **ChromaDB on disk, not a managed service.** Free, simple, persistent. At low scale, this is the right tool. If we need a remote vector store later, ChromaDB has a client/server mode.

5. **No Docker for the dev distribution.** Three people on their own machines, two of them not developers. Docker adds a mental tax that pays for itself only at scale.

6. **Plain HTML for the chat, not React.** The chat is one page with a list of messages and a text input. React would be over-engineering. Fetch + DOM is enough. We can revisit this if the chat grows complex.

7. **SQLite for history, not Postgres yet.** A file. Zero setup. We know how to migrate to Postgres when the prototype graduates. Not before.

8. **Hugging Face Spaces for deploy, accepting the cold-start.** The free `cpu-basic` tier gives us 16 GB RAM and sleeps after ~48 hours of inactivity. This replaces Render, where the prototype OOM'd at ~967 MB against a 512 MB cap. The first visitor after sleep waits ~20-40 seconds for the container to spin up.

9. **LangChain as a toolbox, not a framework.** We use only the parts we need (loaders, splitters, retrievers). We do not use LangChain's agent abstractions, chains of chains, or memory helpers. We own the orchestration in `rag/chain.py`. This keeps the learning path honest and avoids the "LangChain magic" trap.

10. **All content and code is in the repo. No cloned third-party RAG repos.** This is a hard rule. We may read other repositories for reference, but we do not copy them. Every line of RAG code in this repo is written and understood by Fabián.

11. **Typed-name identification for the chat, not user/password auth.** The prototype asks the student for a display name and uses it as the identity key for the SQLite history thread. This keeps the barrier to entry low: no passwords, no email, no session cookies. The trade-offs are intentional and accepted: two students who type the exact same name share a thread (we do not disambiguate "Ana" vs "Ana"), and there is no logout because there is no session. A future auth hardening pass can replace this without changing the history schema.

12. **History persistence via Turso (libSQL).** Conversation history is stored in a remote Turso database (libSQL, SQLite-compatible) outside the HF Spaces container. The backend connects via `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`; when both are unset it falls back to local SQLite at `SQLITE_PATH` for dev convenience only. In production (HF Spaces), both Turso variables MUST be configured as Space Secrets. This eliminates the history loss on Space sleep that was previously accepted in this decision.

13. **HF Spaces via Docker SDK.** The deploy is described by a `Dockerfile` plus a Space `README.md` with `sdk: docker` and `app_port: 7860`. The container runs as UID 1000, the embedding model is tracked via Git LFS, and pre-baked artifacts survive sleep/wake. This keeps the deploy target explicit and avoids Render-specific magic.

## 8. Roadmap (indicative, not a contract)

**Timeline context:** the project has 4 months total, but Fabián has ~3 months of dedicated dev time (~12 weeks) before returning to other project tasks. The roadmap below fits in that window. Items that do not fit ship later or are cut. The exact week-by-week schedule will be re-anchored once Fabián has Nair's full delivery calendar.

**Fabián is the only developer.** Tatiana, Justo, Nair, and the professors do not write code and cannot help with technical issues. This means Fabián is the single point of failure for delivery — the roadmap below must respect that (no parallel work, no "we'll fix it later in QA", no scope creep mid-week).

**Priority rule (decided up front):** the **Socratic chat is the heart of the prototype**. If the dashboard or any other nice-to-have threatens the chat's quality, it gets cut — not the chat. This is a hard rule, not a suggestion, and it was decided jointly with Fabián on day 1.

| Weeks | Milestone | Demo-able to Nair? |
|---|---|---|
| **1-2** | Repo setup, PDF → Markdown pipeline, ChromaDB indexing, query script in terminal. Validate retrieval quality on the sample PDFs. | **No.** Internal work only. |
| **3-4** | FastAPI chat endpoint + plain HTML frontend, basic RAG-only chat (no Socratic layer yet). **First deploy to HF Spaces (dev environment).** | **Yes.** Informal demo: she can open a URL and chat. |
| **5-6** | Socratic layer (system prompt + few-shot examples). Iterate with Nair's feedback. Student history in SQLite. Basic identification (name or simple login). | **Yes.** Behaviour is the pedagogical differentiator. |
| **7-8** | Polish, prompt iteration, auth hardening if time allows. Second Nair demo. | **Yes.** |
| **9-10** | Optional: Streamlit dashboard for professors. **Cut if it threatens the Socratic layer.** | Maybe. |
| **11-12** | Final deploy, polish, final demo with Nair and the project team. | **Yes.** Full prototype. |

**Optional / cut candidates (revisit at week 6 and week 9):**
- Streamlit dashboard for professors — nice-to-have, not critical. **First candidate to cut** if the Socratic chat needs more time.
- Robust authentication (user/pass with hash, sessions). Minimum viable identification may be enough.
- Multiple user roles with distinct UIs.
- Re-ranking, hybrid search, advanced retrieval strategies. Basic vector search first.

The roadmap is a guide, not a commitment. Each week we reassess against the priority rule. We can reorder, add, or cut. But we do not move a milestone forward to look productive — we move it when it is genuinely done. And if the Socratic chat is not yet solid, the dashboard does not get built.

## 9. Roles and Permissions

| Role | Can chat | Can upload content | Can view dashboard | Can edit own history |
|---|---|---|---|---|
| Student | Yes | No | No | Yes (own history) |
| Professor | Yes (sanity check) | Yes | Yes | N/A |
| Nair (promoter) | Yes | Yes | Yes | Yes |
| Fabián (dev) | Yes | Yes | Yes | Yes |

**Note:** professors can use the chat as a sanity check on the assistant's behaviour, not as a primary tool. Nair has full permissions because she owns the academic vision and may need to inspect the system at any level.

## 10. What NOT to Do

These are anti-patterns specific to this project. Violating them is a sign that the work is drifting.

- **Do not clone a third-party RAG repo and pray.** Every line in `rag/` is written and understood.
- **Do not make the assistant solve the exercise directly.** The Socratic layer is the point. The system prompt enforces this; do not weaken it.
- **Do not hardcode API keys, paths, or model names.** Everything that varies between environments goes in `.env` (template in `.env.example`).
- **Do not put RAG logic inside FastAPI or Streamlit handlers.** It belongs in `rag/`. The transport layers are thin.
- **Do not assume the production environment matches the dev environment.** HF Spaces runs a Linux Docker container, the dev may be macOS or Windows. Test in the closest-to-prod setup you can.
- **Do not use LangChain's high-level abstractions** (Agents, Memory, RetrievalQA with built-in prompts) without reading what they do. We use LangChain as a toolbox, not as a black box.
- **Do not introduce Docker, Kubernetes, or any container orchestration** for the prototype. The single `Dockerfile` we have is a deploy artifact for HF Spaces (§7.11), not a dev tool. Do not add docker-compose, multi-stage builds, orchestration, or "containerize the dev workflow" proposals.
- **Do not write code in a hurry to "look productive".** This is a 4-month project, not a sprint. Slow is smooth, smooth is fast.
- **Do not add features Nair did not ask for.** If in doubt, ask Nair through Fabián.

## 11. Key Commands

| Command | What it does |
|---|---|
| `python scripts/indexar_pdfs.py` | Reads PDFs from `data/pdfs/`, chunks, embeds, and writes to ChromaDB (dev/local). |
| `python scripts/preparar_indice_hf.py` | Re-bakes `rag/index/chroma/` and re-validates the embedding model snapshot at `rag/index/hf-model/`. Run after a corpus change, before pushing a new deploy. |
| `uvicorn app.main:app --reload` | Runs the chat backend in dev mode. |
| `streamlit run dashboard/app.py` | Runs the professor dashboard. |
| `pytest` | Runs tests (when they exist). |
| `pip freeze > requirements.txt` | Refresh dependencies after a `pip install`. |

## 12. Environment Variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | — | API key for Groq. Get one at https://console.groq.com. Each dev has their own. |
| `CHROMA_PERSIST_DIR` | No | dev: `./data/chroma`; deploy (Dockerfile ENV): `./rag/index/chroma` | Where ChromaDB persists its vectors. Dev writes to `data/` (gitignored); the deployed Space reads from the committed `rag/index/chroma/` bake. Do not point dev at the deploy path — `scripts/preparar_indice_hf.py` is the only writer for that path. |
| `TURSO_DATABASE_URL` | No (dev) / Yes (deploy) | — | Turso database URL. Required in production as an HF Space Secret; dev falls back to `SQLITE_PATH` when unset. |
| `TURSO_AUTH_TOKEN` | No (dev) / Yes (deploy) | — | Turso auth token. Required in production as an HF Space Secret; dev falls back to `SQLITE_PATH` when unset. |
| `SQLITE_PATH` | No | `./data/historial.db` | Local SQLite fallback for conversation history. Dev-only; not used in production.
| `EMBEDDINGS_DEVICE` | No | `auto` | `auto` picks MPS (macOS) / CUDA (Windows with GPU) / CPU. Set explicitly if needed. |
| `LLM_MODEL` | No | `openai/gpt-oss-120b` | The Groq model used for the chat. |
| `HISTORY_WINDOW` | No | `10` | Number of recent messages injected into the Groq prompt. Set to `0` to disable history injection and restore single-turn behavior. |
| `PRODUCTION` | No | unset | If set to any value, suppresses the dev-mode console dump of the assembled messages list used for manual review. |
| `HF_HOME` | No | `./rag/index/hf-model` | Cache for huggingface_hub; points to the pre-baked model snapshot. |
| `SENTENCE_TRANSFORMERS_HOME` | No | `./rag/index/hf-model` | Cache for sentence-transformers; same path as `HF_HOME` to avoid duplicates. |
| `OMP_NUM_THREADS` | No | `1` | Caps torch OpenMP threads on the Space's CPU. |
| `TOKENIZERS_PARALLELISM` | No | `false` | Disables HuggingFace tokenizer parallelism to keep memory stable.

`.env` is **gitignored**. `.env.example` is committed and shows the structure with empty values.

## 13. Open Questions (to resolve before they block)

These are the questions we have not yet answered. Some of them are blocking for future work; others are nice to know. They are listed in the order we should tackle them.

- [x] **Faculty server for deploy?** Resolved 2026-06-30: we ship to HF Spaces Docker (`cpu-basic`, 16 GB). See decision #8 / #11 in §7 and `docs/hf-space.md` for the deploy runbook. Revisit if the faculty offers a maintained institutional URL.
- [ ] **Language of the code** (English vs Spanish for variable names, comments, commit messages). Default if no decision: English (industry standard, easier to search).
- [ ] **Nair's checkpoint cadence** — formal reviews or informal demos? Affects the Definition of Done for each milestone.
- [x] **PDF processing tool** — Resolved 2026-09-08: `pymupdf4llm` after the 2nd revert from `marker-pdf` (perf inviable on consumer hardware, ~12 min/element in text-recognition). Tradeoff: fórmulas-imagen se pierden, compensado parcialmente por `data/markdown/formulas.md`. Si en el futuro se necesita OCR de fórmulas-imagen, evaluar **Mathpix API** (1000 páginas/mes gratis). Full history in `docs/adr/0001-pdf-loader-marker.md`.
- [ ] **Socratic layer design** — system prompt structure, few-shot examples, how to handle the "I really want the answer" student. Month 3 work, but worth thinking from month 1.
- [ ] **Professor dashboard metrics** — which questions matter? Most-asked topics, students who are stuck, low-rated answers? Need Nair's input. Month 4 work.
- [ ] **Authentication strategy** — simple user/pass in SQLite? Magic link? Depends on faculty IT. Month 3 work.
- [ ] **Professors and Nair — do they chat with the assistant?** See section 9.

## 14. What "Done" Means for This Project

A feature is done when:
1. The code is in `rag/`, `app/`, `dashboard/`, or `scripts/` — not in a notebook.
2. The README / docstring explains what it does and how to use it.
3. If it touches the prompt, the prompt is documented in `docs/` with a before/after example.
4. If it touches the architecture, an ADR is written in `docs/`.
5. A dev (Fabián in 2 months, or a peer reviewer) can run it from a clean clone with the steps in section 6.

A feature is **not** done when:
- It "works on my machine" but not in the closest-to-prod setup.
- It has no test and cannot be tested manually in under 5 minutes.
- It introduces a decision that is not recorded in section 7 or in an ADR.

---

*This file is the source of truth. If reality drifts from what is written here, update the file in the same change that updates reality.*
