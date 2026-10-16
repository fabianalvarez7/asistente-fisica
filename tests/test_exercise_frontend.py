"""DOM-level regression coverage for the dedicated exercise experience.

The repository does not ship a browser runner, so these tests execute the real
``exercise.js`` in Node with a small DOM double. This covers the page behavior
that an API-only test cannot observe: catalog data becoming visible in the
exercise page and an SSE error remaining visible after ``[DONE]``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXERCISE_SCRIPT = ROOT / "app" / "static" / "exercise.js"
EXERCISE_PAGE = ROOT / "app" / "static" / "exercises.html"
STYLE_SHEET = ROOT / "app" / "static" / "style.css"


def _run_node_contract(
    assertion: str,
    *,
    progress_failure: bool = False,
    checkpoint_post_503: bool = False,
    graph_checkpoint: bool = False,
    final_part_a: bool = False,
    wrong_submission: bool = False,
    completed: bool = False,
    completed_review: list[dict] | None = None,
    history_messages: list[dict] | None = None,
    viewport_width: int = 375,
) -> subprocess.CompletedProcess[str]:
    catalog = [
        {
            "id": "cinematica-1d-ejercicio-02",
            "title": "Ejercicio de prueba",
            "statement": "Observá el gráfico de posición *x*(*t*).",
            "graph_asset": "/img/test-graph.png",
            "starter_ideas": [
                "Primera pista: *t* y *x*.",
                "Segunda pista desde el catálogo.",
            ],
        },
        {
            "id": "cinematica-1d-ejercicio-03",
            "title": "Ejercicio publicado siguiente",
            "statement": "Otro enunciado publicado.",
            "graph_asset": "/img/second-test-graph.png",
            "starter_ideas": ["Otra pista."],
        },
    ]
    current_checkpoint = {
        "id": "axes",
        "part": "a",
        "prompt": "¿Qué representan *t* y *x*?",
        "input_type": "single_choice",
        "options": [{"id": "axes-correct", "label": "*t* y *x*"}],
        "hint": "Mirá las unidades de *t*.",
        "help_hint": "El eje horizontal es *t*.",
    }
    if graph_checkpoint:
        current_checkpoint = {
            "id": "velocity-graph-shape",
            "part": "b",
            "prompt": "Dibujá *v*(*t*) en el cuadernillo y elegí el gráfico.",
            "input_type": "single_choice",
            "presentation": "graph",
            "options": [
                {
                    "id": "graph-correct",
                    "label": "Gráfico A",
                    "graph": {
                        "kind": "polyline",
                        "points": [[0, 6], [20, 30]],
                        "x_min": 0,
                        "x_max": 20,
                        "y_min": 0,
                        "y_max": 32,
                        "x_label": "t (s)",
                        "y_label": "v (m/s)",
                    },
                },
                {
                    "id": "graph-wrong",
                    "label": "Gráfico B",
                    "graph": {
                        "kind": "polyline",
                        "points": [[0, 16], [20, 16]],
                        "x_min": 0,
                        "x_max": 20,
                        "y_min": 0,
                        "y_max": 32,
                        "x_label": "t (s)",
                        "y_label": "v (m/s)",
                    },
                },
            ],
            "hint": "Buscá una recta creciente.",
            "help_hint": "La velocidad empieza en 6 m/s.",
        }
    if final_part_a:
        current_checkpoint = {
            "id": "determine-initial-values",
            "part": "a",
            "prompt": "Usando *x*(10) y *x*(20), ¿qué relaciones sirven?",
            "input_type": "multi_select",
            "options": [
                {"id": "equation-at-10", "label": "120 = 10*v₀* + 50*a*"},
                {"id": "equation-at-20", "label": "360 = 20*v₀* + 200*a*"},
                {"id": "solution-v0-a", "label": "*v₀* = 6 m/s y *a* = 1,2 m/s²"},
            ],
            "hint": "Reemplazá cada tiempo en la ecuación general.",
            "help_hint": "Las dos ecuaciones correctas salen de sustituir *t*=10 y *t*=20.",
        }
    script = f"""
import assert from 'node:assert';
import fs from 'node:fs';
import vm from 'node:vm';

class ClassList {{
  constructor() {{ this.values = new Set(); }}
  add(value) {{ this.values.add(value); }}
  remove(value) {{ this.values.delete(value); }}
  contains(value) {{ return this.values.has(value); }}
  toggle(value, force) {{
    const next = force === undefined ? !this.values.has(value) : force;
    if (next) this.values.add(value); else this.values.delete(value);
    return next;
  }}
}}

class Element {{
  constructor(id) {{
    this.id = id;
    this.tagName = id;
    this.children = [];
    this.listeners = {{}};
    this.classList = new ClassList();
    this.textContent = '';
    this.innerHTML = '';
    this.hidden = false;
    this.disabled = false;
   this.value = '';
   this.dataset = {{}};
    this.rawText = '';
    this.hasError = false;
   this.scrollHeight = 0;
    this.style = {{}};
    this.attributes = {{}};
  }}
  addEventListener(type, listener) {{
    (this.listeners[type] ??= []).push(listener);
  }}
  dispatchEvent(event) {{
    for (const listener of this.listeners[event.type] ?? []) listener(event);
  }}
  appendChild(child) {{ this.children.push(child); return child; }}
   replaceChildren(...children) {{ this.children = children; }}
   querySelectorAll(selector) {{
     return selector === 'button' ? this.children.filter((child) => child.type === 'button') : [];
   }}
   click() {{ this.dispatchEvent({{ type: 'click' }}); }}
   setAttribute(name, value) {{ this.attributes[name] = String(value); this[name] = String(value); }}
  focus() {{}}
}}

const ids = [
  'chat-form', 'query', 'messages', 'hint', 'send-btn', 'name-area',
     'student-name', 'login-screen', 'login-hint', 'app-shell', 'exercise-title',
     'exercise-statement', 'exercise-graph', 'starter-ideas', 'exercise-status',
     'exercise-retry',
     'exercise-list',
    'history-banner', 'mobile-menu-toggle', 'mobile-menu-close', 'sidebar',
    'checkpoint-panel', 'checkpoint-progress', 'checkpoint-part', 'progress-bar', 'checkpoint-prompt',
    'checkpoint-options', 'checkpoint-feedback', 'checkpoint-submit',
    'checkpoint-hint', 'checkpoint-help',
    'exercise-review', 'exercise-review-list',
  ];
const elements = Object.fromEntries(ids.map((id) => [id, new Element(id)]));
  const document = {{
  getElementById: (id) => elements[id] ?? null,
  querySelector: (selector) => selector === '.sidebar' ? elements.sidebar : null,
  createElement: (tag) => new Element(tag),
  createElementNS: (_namespace, tag) => new Element(tag),
  addEventListener: () => {{}},
}};
const storage = {{
  value: null,
  getItem() {{ return this.value; }},
  setItem(_key, value) {{ this.value = value; }},
}};
const catalog = {json.dumps(catalog)};
const currentCheckpoint = {json.dumps(current_checkpoint)};
const secondCheckpoint = {{
  id: 'second-exercise-checkpoint',
  part: 'a',
  prompt: '¿Qué representa el segundo ejercicio?',
  input_type: 'single_choice',
  options: [{{ id: 'second-exercise-option', label: 'La opción del ejercicio B' }}],
  hint: 'Mirá el segundo enunciado.',
  help_hint: 'Elegí la opción del ejercicio B.',
}};
const progressFailure = {json.dumps(progress_failure)};
const checkpointPost503 = {json.dumps(checkpoint_post_503)};
const completed = {json.dumps(completed)};
const completedReview = {json.dumps(completed_review or [
        {
          "checkpoint_id": "axes",
          "part": "a",
          "question": "¿Qué representan *t* y *x*?",
          "correct_answers": [{"label": "*t* en segundos y *x* en metros", "value": "axes-correct"}],
        },
        {
          "checkpoint_id": "model",
          "part": "b",
          "question": "¿Qué modelo corresponde?",
          "correct_answers": [{"label": "Aceleración constante", "value": "model-correct"}],
        },
      ])};
const historyMessages = {json.dumps(history_messages or [])};
const finalPartA = {json.dumps(final_part_a)};
const wrongSubmission = {json.dumps(wrong_submission)};
const viewportWidth = {viewport_width};
const stylesheet = fs.readFileSync({json.dumps(str(STYLE_SHEET))}, 'utf8');
const sse = 'event: error\\ndata: El error debe quedar visible\\n\\ndata: [DONE]\\n\\n';
const fetchCalls = [];
let checkpointAttempts = 0;
const fetch = async (url, options = {{}}) => {{
  fetchCalls.push({{ url, options }});
  if (url === '/api/exercises') return {{ ok: true, json: async () => catalog }};
  if (url.startsWith('/history?')) return {{ ok: true, json: async () => ({{ messages: historyMessages, degraded: false }}) }};
  if (progressFailure && url.includes('/progress?')) return {{
    ok: false,
    status: 503,
    json: async () => ({{ detail: 'No se pudo leer tu progreso. No se generó una nueva guía. Reintentá.' }}),
  }};
  if (url.includes('/progress?')) {{
    const isSecondExercise = url.includes('/api/exercises/cinematica-1d-ejercicio-03/progress?');
    const activeCheckpoint = isSecondExercise ? secondCheckpoint : currentCheckpoint;
    return {{
      ok: true,
      json: async () => ({{
        current_index: finalPartA ? 1 : (completed ? 1 : 0),
        total: finalPartA ? 4 : 1,
        completed_count: finalPartA ? 1 : (completed ? 1 : 0),
        complete: completed,
        current_checkpoint: completed ? null : activeCheckpoint,
        ...(completed ? {{ completed_review: completedReview }} : {{}}),
      }}),
    }};
  }}
  if (url.endsWith('/checkpoint')) return {{
    ...(checkpointPost503 && checkpointAttempts++ === 0 ? {{
      ok: false,
      status: 503,
      json: async () => ({{ detail: {{
        code: 'exercise_progress_unavailable',
        message: 'No se pudo leer tu progreso. No se generó una nueva guía. Reintentá.',
        retryable: true,
      }} }}),
    }} : {{
      ok: true,
      json: async () => ({{
         result: wrongSubmission ? 'incorrect' : 'correct',
         feedback: wrongSubmission ? 'Todavía no: revisá *x*.' : 'Bien: *v*(*t*) queda creciente.',
         advanced: !wrongSubmission,
         progress: finalPartA
           ? {{
               current_index: 2,
               total: 4,
               completed_count: 2,
               complete: false,
               current_checkpoint: {{
                  id: 'velocity-graph-shape',
                  part: 'b',
                   prompt: 'Dibujá *v*(*t*) y elegí el gráfico que corresponde.',
                  input_type: 'single_choice',
                  presentation: 'graph',
                  options: [{{ id: 'velocity-graph-correct', label: 'Gráfico A' }}],
                  hint: 'Buscá una recta creciente.',
                  help_hint: 'La velocidad empieza en 6 m/s.',
                }},
             }}
           : {{ current_index: 1, total: 1, completed_count: 1, complete: true, current_checkpoint: null }},
      }}),
    }}),
  }};
  if (url === '/chat') {{
    let consumed = false;
    return {{
      ok: true,
      body: {{
        getReader() {{
          return {{
            async read() {{
              if (consumed) return {{ done: true }};
              consumed = true;
              return {{ done: false, value: new TextEncoder().encode(sse) }};
            }},
          }};
        }},
      }},
    }};
  }}
  throw new Error(`Unexpected fetch: ${{url}}`);
}};
const window = {{
  innerWidth: viewportWidth,
  matchMedia: () => ({{ matches: false }}),
  addEventListener: () => {{}},
}};
const context = {{
  assert, console, document, fetch, localStorage: storage, window,
  TextDecoder, TextEncoder, URLSearchParams, setTimeout, clearTimeout,
}};

vm.runInNewContext(
  fs.readFileSync({json.dumps(str(EXERCISE_SCRIPT))}, 'utf8'),
  context,
  {{ filename: 'exercise.js' }},
);
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

{assertion}
"""
    return subprocess.run(
        [shutil.which("node") or "node", "--input-type=module", "-"],
        input=script,
        text=True,
        capture_output=True,
        cwd=ROOT,
        check=False,
    )


class ExerciseFrontendContractTests(unittest.TestCase):
    def test_exercise_copy_avoids_guided_labels_and_keeps_part_labels(self):
        page = EXERCISE_PAGE.read_text(encoding="utf-8")
        script = EXERCISE_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("Ejercicios guiados", page)
        self.assertNotIn("recorrido guiado", script)
        self.assertIn("Parte a", page)
        self.assertIn("Parte ${current.part}", script)

    def test_catalog_starter_guidance_renders_into_exercise_page(self):
        page = EXERCISE_PAGE.read_text(encoding="utf-8")
        for element_id in (
            "exercise-title",
            "exercise-statement",
            "exercise-graph",
            "starter-ideas",
        ):
            self.assertIn(f'id="{element_id}"', page)

        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        result = _run_node_contract(
            """
assert.strictEqual(elements['exercise-title'].textContent, catalog[0].title);
assert.strictEqual(elements['exercise-statement'].innerHTML, 'Observá el gráfico de posición <span class="physics-var">x</span>(<span class="physics-var">t</span>).');
assert.strictEqual(elements['exercise-graph'].src, catalog[0].graph_asset);
assert.strictEqual(elements['exercise-graph'].hidden, false);
assert.deepStrictEqual(
  elements['starter-ideas'].children.map((item) => item.innerHTML),
  ['Primera pista: <span class="physics-var">t</span> y <span class="physics-var">x</span>.', 'Segunda pista desde el catálogo.'],
);
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_published_exercise_list_switches_statement_and_scoped_requests(self):
        result = _run_node_contract(
            """
assert.strictEqual(elements['exercise-list'].children.length, catalog.length);
assert.strictEqual(elements['exercise-title'].textContent, catalog[0].title);
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
elements['exercise-list'].children[1].click();
assert.strictEqual(elements['checkpoint-panel'].hidden, true);
assert.strictEqual(elements['exercise-review'].hidden, true);
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['exercise-title'].textContent, catalog[1].title);
assert.strictEqual(elements['exercise-statement'].innerHTML, catalog[1].statement);
assert.strictEqual(elements['exercise-graph'].src, catalog[1].graph_asset);
assert.ok(fetchCalls.some((call) => call.url.includes('/api/exercises/cinematica-1d-ejercicio-03/progress?')));
assert.ok(fetchCalls.some((call) => call.url.includes('exercise_id=cinematica-1d-ejercicio-03')));
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_switching_exercises_resets_selected_options_before_submission(self):
        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

const exerciseAOption = elements['checkpoint-options'].children[0];
exerciseAOption.click();
assert.strictEqual(exerciseAOption.dataset.optionId, 'axes-correct');
assert.strictEqual(exerciseAOption.classList.contains('is-selected'), true);
assert.strictEqual(exerciseAOption.attributes['aria-pressed'], 'true');

elements['exercise-list'].children[1].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

const exerciseBOption = elements['checkpoint-options'].children[0];
assert.strictEqual(exerciseBOption.dataset.optionId, 'second-exercise-option');
assert.strictEqual(exerciseBOption.classList.contains('is-selected'), false);
assert.strictEqual(exerciseBOption.attributes['aria-pressed'], 'false');
exerciseBOption.click();
assert.strictEqual(exerciseBOption.attributes['aria-pressed'], 'true');
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

const checkpointCall = fetchCalls.find((call) => call.url.endsWith('/checkpoint'));
assert.ok(checkpointCall);
const submittedIds = JSON.parse(checkpointCall.options.body).answer_ids;
assert.deepStrictEqual(submittedIds, ['second-exercise-option']);
assert.strictEqual(submittedIds.includes('axes-correct'), false);
""",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_incomplete_exercise_hides_completed_review_payload(self):
        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['exercise-review'].hidden, true);
assert.strictEqual(elements['exercise-review-list'].children.length, 0);
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_active_checkpoint_renders_its_current_part(self):
        for graph_checkpoint, expected_part in ((False, 'Parte a'), (True, 'Parte b')):
            with self.subTest(graph_checkpoint=graph_checkpoint):
                result = _run_node_contract(
                    """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['checkpoint-part'].textContent, expectedPart);
""".replace('expectedPart', json.dumps(expected_part)),
                    graph_checkpoint=graph_checkpoint,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_submitting_final_part_a_checkpoint_renders_part_b(self):
        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['checkpoint-part'].textContent, 'Parte a');
for (const option of elements['checkpoint-options'].children) option.click();
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
const checkpointCall = fetchCalls.find((call) => call.url.endsWith('/checkpoint'));
assert.ok(checkpointCall);
assert.deepStrictEqual(
  JSON.parse(checkpointCall.options.body).answer_ids,
  ['equation-at-10', 'equation-at-20', 'solution-v0-a'],
);
assert.strictEqual(elements['checkpoint-part'].textContent, 'Parte b');
assert.strictEqual(elements['checkpoint-feedback'].hidden, true);
assert.strictEqual(elements['checkpoint-feedback'].textContent, '');
""",
            final_part_a=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_active_exercise_does_not_render_historical_checkpoint_messages(self):
        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['messages'].children.length, 0);
assert.strictEqual(elements['exercise-review'].hidden, true);
""",
            history_messages=[
                {"role": "user", "content": "Respuesta: x₀ = 0 m"},
                {"role": "assistant", "content": "El gráfico parte de x=0."},
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_completed_exercise_renders_persisted_review_after_reload(self):
        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['exercise-review'].hidden, false);
assert.strictEqual(elements['exercise-review-list'].children.length, 2);
assert.strictEqual(elements['exercise-review-list'].children[0].children[0].innerHTML, '¿Qué representan <span class="physics-var">t</span> y <span class="physics-var">x</span>?');
assert.strictEqual(elements['exercise-review-list'].children[0].children[2].children[0].innerHTML, '<span class="physics-var">t</span> en segundos y <span class="physics-var">x</span> en metros');
assert.strictEqual(elements['messages'].children.length, 0);
assert.ok(!elements['exercise-review-list'].children.some((item) => item.textContent.includes('teacher_key')));
assert.ok(!elements['exercise-review-list'].children.some((item) => item.textContent.includes('Respuesta: x₀ = 0 m')));
""",
        completed=True,
            history_messages=[
                {"role": "user", "content": "Respuesta: x₀ = 0 m"},
                {"role": "assistant", "content": "El gráfico parte de x=0."},
                {"role": "user", "content": "Respuesta: v(t) creciente"},
                {"role": "assistant", "content": "La recta es creciente."},
                {"role": "system", "content": "teacher_key: hidden future answer"},
            ],
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_exercise_page_removes_optional_copy_and_extra_decorative_control(self):
        page = EXERCISE_PAGE.read_text(encoding='utf-8')
        self.assertNotIn('¿Querés agregar una explicación? (opcional)', page)
        self.assertNotIn('optional-input-label', page)
        self.assertEqual(page.count('id="send-btn"'), 1)
        self.assertIn('enterkeyhint="send"', page)
        input_form = page.split('<form id="chat-form"', 1)[1].split('</form>', 1)[0]
        self.assertEqual(input_form.count('<button'), 1)
        self.assertNotIn('decorative', input_form)

    def test_sse_error_remains_visible_after_done_frame(self):
        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
elements['query'].value = '¿Qué observo?';
elements['chat-form'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

assert.strictEqual(elements['messages'].children.length, 2);
const assistant = elements['messages'].children[1];
const assistantContent = assistant.children[0].children[0];
assert.strictEqual(assistantContent.textContent, 'El error debe quedar visible');
assert.notStrictEqual(assistantContent.textContent, '');
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_progress_read_failure_disables_chat_and_offers_retry(self):
        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

assert.ok(elements['exercise-status'].textContent.includes('No se pudo leer tu progreso'));
assert.strictEqual(elements['exercise-retry'].hidden, false);
assert.strictEqual(elements['query'].disabled, true);
""",
            progress_failure=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_checkpoint_options_are_tappable_and_post_answer_ids(self):
        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['checkpoint-prompt'].innerHTML, '¿Qué representan <span class="physics-var">t</span> y <span class="physics-var">x</span>?');
assert.strictEqual(elements['checkpoint-options'].children.length, 1);
assert.strictEqual(elements['checkpoint-options'].children[0].innerHTML, '<span class="physics-var">t</span> y <span class="physics-var">x</span>');
assert.strictEqual(elements['checkpoint-options'].children[0].attributes['aria-label'], 't y x');
elements['checkpoint-options'].children[0].click();
assert.strictEqual(elements['checkpoint-options'].children[0].classList.contains('is-selected'), true);
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
const checkpointCall = fetchCalls.find((call) => call.url.endsWith('/checkpoint'));
assert.ok(checkpointCall);
assert.deepStrictEqual(JSON.parse(checkpointCall.options.body).answer_ids, ['axes-correct']);
"""
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_wrong_checkpoint_submission_keeps_formatted_feedback_visible(self):
        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
elements['checkpoint-options'].children[0].click();
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));
assert.strictEqual(elements['checkpoint-feedback'].hidden, false);
assert.strictEqual(elements['checkpoint-feedback'].innerHTML, 'Todavía no: revisá <span class="physics-var">x</span>.');
assert.strictEqual(elements['checkpoint-feedback'].textContent.includes('*'), false);
""",
            wrong_submission=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_graph_checkpoint_renders_visual_cards_and_posts_selection(self):
        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

assert.strictEqual(elements['checkpoint-options'].children.length, 2);
const firstCard = elements['checkpoint-options'].children[0];
assert.strictEqual(firstCard.classList.contains('checkpoint-option--graph'), true);
assert.strictEqual(firstCard.children[0].children[0].tagName, 'svg');
assert.strictEqual(firstCard.children[1].innerHTML, 'Gráfico A');
firstCard.click();
assert.strictEqual(firstCard.classList.contains('is-selected'), true);
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
const checkpointCall = fetchCalls.find((call) => call.url.endsWith('/checkpoint'));
assert.deepStrictEqual(JSON.parse(checkpointCall.options.body).answer_ids, ['graph-correct']);
""",
            graph_checkpoint=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_graph_cards_preserve_svg_and_fit_narrow_layout_contract(self):
        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        for viewport_width in (320, 375):
            with self.subTest(viewport_width=viewport_width):
                result = _run_node_contract(
                    """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

function declarations(selector, source = stylesheet) {
  const start = source.indexOf(`${selector} {`);
  assert.ok(start >= 0, `missing CSS rule: ${selector}`);
  const open = source.indexOf('{', start);
  const close = source.indexOf('}', open);
  return Object.fromEntries(source.slice(open + 1, close).split(';').map((declaration) => declaration.trim().split(/\\s*:\\s*/)).filter(([name, value]) => name && value));
}

const graphCardRule = declarations('.checkpoint-option--graph');
const graphRule = declarations('.checkpoint-graph');
const svgRule = declarations('.checkpoint-graph-svg');
assert.strictEqual(graphCardRule.display, 'flex', 'graph cards must use a flexible row');
assert.strictEqual(graphRule.width, '100%', 'graph wrapper must shrink with its card');
assert.strictEqual(graphRule['max-width'], '17rem', 'graph wrapper must have a bounded width');
assert.strictEqual(svgRule.width, '100%', 'SVG must fill the graph wrapper');
assert.strictEqual(svgRule['height'], 'auto', 'SVG height must preserve its aspect ratio');

const cards = elements['checkpoint-options'].children;
assert.strictEqual(cards.length, 2, 'narrow viewport must retain both graph cards');
const pageHorizontalPadding = 16;
const checkpointPanelPadding = 20;
const checkpointPanelBorder = 2;
const optionPadding = 8;
const optionBorder = 1;
const optionsWidth = viewportWidth - (pageHorizontalPadding * 2)
  - (checkpointPanelPadding * 2) - (checkpointPanelBorder * 2);
const optionContentWidth = optionsWidth - (optionPadding * 2) - (optionBorder * 2);
assert.ok(optionContentWidth > 0);
assert.ok(Math.min(optionContentWidth, 17 * 16) <= optionContentWidth);

for (const card of cards) {
  assert.strictEqual(card.classList.contains('checkpoint-option--graph'), true, 'each rendered option must be a graph card');
  const graphWrapper = card.children[0];
  const svg = graphWrapper.children[0];
  const label = card.children[1];
  assert.strictEqual(graphWrapper.className, 'checkpoint-graph', 'graph wrapper must remain in the card');
  assert.strictEqual(svg.tagName, 'svg', 'graph card must render an SVG');
  assert.strictEqual(svg.attributes.viewBox, '0 0 240 160', 'SVG must retain its responsive viewBox');
  assert.strictEqual(svg.classList.contains('checkpoint-graph-svg'), true, 'SVG must retain its graph class');
  assert.ok(label.innerHTML.length > 0);
}
""",
                    graph_checkpoint=True,
                    viewport_width=viewport_width,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_checkpoint_post_503_renders_retry_and_recovers(self):
        node = shutil.which("node")
        if node is None:
            self.fail("Node.js is required for the exercise DOM contract tests")

        result = _run_node_contract(
            """
elements['student-name'].value = 'Ana';
elements['name-area'].dispatchEvent({ type: 'submit', preventDefault() {} });
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

elements['checkpoint-options'].children[0].click();
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

const checkpointCalls = () => fetchCalls.filter((call) => call.url.endsWith('/checkpoint'));
assert.strictEqual(checkpointCalls().length, 1);
assert.strictEqual(
  elements['exercise-status'].textContent,
  'No se pudo leer tu progreso. No se generó una nueva guía. Reintentá.',
);
assert.strictEqual(elements['exercise-retry'].hidden, false);
assert.strictEqual(elements['checkpoint-panel'].hidden, true);
assert.strictEqual(elements['query'].disabled, true);

const progressCallsBeforeRetry = fetchCalls.filter((call) => call.url.includes('/progress?')).length;
elements['exercise-retry'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

assert.strictEqual(
  fetchCalls.filter((call) => call.url.includes('/progress?')).length,
  progressCallsBeforeRetry + 1,
);
assert.strictEqual(elements['exercise-status'].textContent, '');
assert.strictEqual(elements['exercise-retry'].hidden, true);
assert.strictEqual(elements['checkpoint-panel'].hidden, false);
assert.strictEqual(elements['query'].disabled, false);

elements['checkpoint-options'].children[0].click();
elements['checkpoint-submit'].click();
await new Promise((resolve) => setTimeout(resolve, 0));
await new Promise((resolve) => setTimeout(resolve, 0));

assert.strictEqual(checkpointCalls().length, 2);
assert.strictEqual(elements['checkpoint-progress'].textContent, 'Ejercicio completo');
""",
            checkpoint_post_503=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
