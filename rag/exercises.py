"""Curated exercise catalog and Socratic guidance metadata.

Only exercises with ``status == "published"`` should be exposed to students.
The teacher key is kept separate from the student-facing guidance so the
assistant can validate progress without revealing the complete solution.
"""

from dataclasses import dataclass
from itertools import combinations
import re
from typing import Literal


ExerciseStatus = Literal["draft", "validated", "published", "archived"]


def plain_text(value: str) -> str:
    """Return the string with emphasis markers removed (for storage and LLM prompts)."""

    return re.sub(r"\*([^*\n]+)\*", r"\1", value)


@dataclass(frozen=True)
class GuidanceStep:
    """One checkpoint in the guided resolution of an exercise."""

    id: str
    question: str
    expected_idea: str
    hint: str


@dataclass(frozen=True)
class GraphDescriptor:
    """Safe server-controlled data used to render a qualitative graph card."""

    kind: Literal["polyline", "curve"]
    points: tuple[tuple[float, float], ...]
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    x_label: str
    y_label: str


@dataclass(frozen=True)
class CheckpointOption:
    """A student-visible option for a deterministic exercise checkpoint."""

    id: str
    label: str
    graph: GraphDescriptor | None = None


@dataclass(frozen=True)
class Checkpoint:
    """A checkpoint whose progression is validated by the exercise domain."""

    id: str
    prompt: str
    input_type: Literal["single_choice", "multi_select", "ordering"]
    options: tuple[CheckpointOption, ...]
    correct_option_ids: tuple[str, ...]
    hint: str
    help_hint: str
    explanation: str
    part: Literal["a", "b"] = "a"
    presentation: Literal["text", "graph"] = "text"


@dataclass(frozen=True)
class TeacherKey:
    """Private validation data; never serialize this for the student UI."""

    position_equation: str
    velocity_equation: str
    acceleration_equation: str
    initial_position: str
    initial_velocity: str
    acceleration: str
    checkpoints: tuple[str, ...]


@dataclass(frozen=True)
class Exercise:
    id: str
    status: ExerciseStatus
    title: str
    unit: str
    source_file: str
    source_page: int
    statement: str
    graph_asset: str
    starter_ideas: tuple[str, ...]
    concepts: tuple[str, ...]
    guidance: tuple[GuidanceStep, ...]
    checkpoints: tuple[Checkpoint, ...]
    teacher_key: TeacherKey


_V_GRAPH_CORRECT = GraphDescriptor(
    kind="polyline",
    points=((0, 8), (20, 28)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
# Distractor: assumes the average velocity 18 m/s (v(10)) stays constant.
_V_GRAPH_HORIZONTAL = GraphDescriptor(
    kind="polyline",
    points=((0, 18), (20, 18)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
# Distractor: mixes up the axes, plotting the position values in v(t).
_V_GRAPH_DECREASING = GraphDescriptor(
    kind="polyline",
    points=((0, 28), (20, 8)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
# Distractor: guesses a non-uniform velocity instead of a constant acceleration.
_V_GRAPH_CURVE = GraphDescriptor(
    kind="curve",
    points=((0, 8), (5, 16), (10, 20), (15, 24), (20, 28)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)


EXERCISES: tuple[Exercise, ...] = (
    Exercise(
        id="cinematica-1d-ejercicio-02",
        status="published",
        title="Guía nº 2 Cinemática de la partícula en 1D - Ejercicio 2",
        unit="Cinemática de la partícula en 1D",
        source_file="Fisica1-Cuadernillo-2026.pdf",
        source_page=29,
        statement=(
            "2. A partir del gráfico de la curva mostrado *x*(*t*):\n"
            "a. Escribir las ecuaciones correspondientes al movimiento, indicando "
            "los valores de posición y velocidad iniciales, así como de la "
            "aceleración si hubiera (en el origen de la gráfica, la curva "
            "parabólica forma un ángulo de salida α no nulo respecto de la horizontal).\n"
            "b. Confeccionar las gráficas cinemáticas restantes: *v*(*t*) y *a*(*t*), "
            "indicando en ellas los valores que asumen las magnitudes para los "
            "tiempos de 10 s y 20 s."
        ),
        graph_asset="/img/exercise-cinematica-1d-ejercicio-02.png",
        starter_ideas=(
            "Leé primero los ejes y sus unidades: *t* está en segundos y *x* en metros.",
            "Observá la forma de la curva *x*(*t*) antes de sacar conclusiones.",
        ),
        concepts=(
            "position-time graph",
            "uniformly accelerated motion",
            "initial conditions",
            "velocity",
            "acceleration",
        ),
        guidance=(
            GuidanceStep(
                id="initial-conditions",
                question="¿Qué podés identificar al comienzo del gráfico?",
                expected_idea="x₀ = 0 m y la velocidad inicial es positiva.",
                hint="Observá dónde empieza la curva y hacia dónde crece al inicio.",
            ),
            GuidanceStep(
                id="determine-initial-values",
                question=(
                    "Usando x(10)=130 m y x(20)=360 m, ¿qué relaciones y valores "
                    "sirven para determinar v₀ y a?"
                ),
                expected_idea=(
                    "130 = 10v₀ + 50a y 360 = 20v₀ + 200a; al resolver, "
                    "v₀ = 8 m/s y a = 1 m/s²."
                ),
                hint="Reemplazá cada tiempo en la ecuación general y luego resolvé el sistema.",
            ),
            GuidanceStep(
                id="velocity-graph-shape",
                question=(
                    "Primero dibujá v(t) en el cuadernillo. Después, elegí el gráfico "
                    "que mejor representa tu dibujo."
                ),
                expected_idea="v(t) es una recta creciente que empieza en 8 m/s.",
                hint="La velocidad inicial es v₀ y la pendiente de la recta es a.",
            ),
            GuidanceStep(
                id="evaluate-requested-times",
                question="¿Qué valores se obtienen al evaluar las magnitudes en los tiempos pedidos?",
                expected_idea="x(10)=130 m, x(20)=360 m, v(10)=18 m/s y v(20)=28 m/s.",
                hint="Sustituí t=10 y t=20 en x(t) y v(t).",
            ),
        ),
        checkpoints=(
            Checkpoint(
                id="initial-conditions",
                prompt="¿Qué podés identificar al comienzo del gráfico?",
                input_type="multi_select",
                options=(
                    CheckpointOption("initial-position-zero", "*x₀* = 0 m"),
                    CheckpointOption("initial-velocity-positive", "La velocidad inicial es positiva"),
                    CheckpointOption("initial-velocity-negative", "La velocidad inicial es negativa"),
                    CheckpointOption("initial-position-130", "*x₀* = 130 m"),
                ),
                correct_option_ids=("initial-position-zero", "initial-velocity-positive"),
                hint="Observá dónde empieza la curva y hacia dónde crece al inicio.",
                help_hint="La curva parte de *x*=0 y tiene pendiente inicial hacia arriba.",
                explanation="El gráfico permite identificar *x₀* = 0 m y una velocidad inicial positiva.",
            ),
            Checkpoint(
                id="determine-initial-values",
                prompt="Usando *x*(10)=130 m y *x*(20)=360 m, ¿qué relaciones y valores sirven para determinar *v₀* y *a*?",
                input_type="multi_select",
                options=(
                    CheckpointOption("equation-at-10", "130 = 10*v₀* + 50*a*"),
                    CheckpointOption("equation-at-20", "360 = 20*v₀* + 200*a*"),
                    CheckpointOption("solution-v0-a", "Al resolver: *v₀* = 8 m/s y *a* = 1 m/s²"),
                    CheckpointOption("equation-at-10-wrong", "130 = 10*v₀* + 10*a*"),
                    CheckpointOption("solution-swap-roles", "Al resolver: *v₀* = 1 m/s y *a* = 8 m/s²"),
                ),
                correct_option_ids=("equation-at-10", "equation-at-20", "solution-v0-a"),
                hint="Reemplazá cada tiempo en la ecuación general y luego resolvé el sistema.",
                help_hint="Las dos ecuaciones correctas salen de sustituir *t*=10 y *t*=20; ambas llevan al mismo par *v₀*,*a*.",
                explanation="Los puntos del gráfico forman un sistema que determina *v₀* = 8 m/s y *a* = 1 m/s².",
            ),
            Checkpoint(
                id="velocity-graph-shape",
                prompt=(
                    "Primero dibujá *v*(*t*) en el cuadernillo. Después, elegí el gráfico "
                    "que mejor representa tu dibujo."
                ),
                input_type="single_choice",
                options=(
                    CheckpointOption("velocity-graph-correct", "Gráfico A", _V_GRAPH_CORRECT),
                    CheckpointOption("velocity-graph-horizontal", "Gráfico B", _V_GRAPH_HORIZONTAL),
                    CheckpointOption("velocity-graph-decreasing", "Gráfico C", _V_GRAPH_DECREASING),
                    CheckpointOption("velocity-graph-curve", "Gráfico D", _V_GRAPH_CURVE),
                ),
                correct_option_ids=("velocity-graph-correct",),
                hint="Buscá una recta que empiece en 8 m/s y aumente con el tiempo.",
                help_hint="La velocidad inicial es 8 m/s y la aceleración positiva hace que la recta suba.",
                explanation="El gráfico correcto es una recta creciente que comienza en 8 m/s.",
                part="b",
                presentation="graph",
            ),
            Checkpoint(
                id="evaluate-requested-times",
                prompt="¿Qué valores se obtienen al evaluar las magnitudes en los tiempos pedidos?",
                input_type="multi_select",
                options=(
                    CheckpointOption("position-at-10", "*x*(10)=130 m"),
                    CheckpointOption("position-at-20", "*x*(20)=360 m"),
                    CheckpointOption("velocity-at-10", "*v*(10)=18 m/s"),
                    CheckpointOption("velocity-at-20", "*v*(20)=28 m/s"),
                    CheckpointOption("velocity-at-10-wrong", "*v*(10)=8 m/s"),
                ),
                correct_option_ids=("position-at-10", "position-at-20", "velocity-at-10", "velocity-at-20"),
                hint="Sustituí *t*=10 y *t*=20 en *x*(*t*) y *v*(*t*).",
                help_hint="Los puntos *x*(10) y *x*(20) son los del gráfico; calculá *v* con *v*(*t*)=8+*t*.",
                explanation="Las evaluaciones recuperan los puntos conocidos y dan *v*(10)=18 m/s y *v*(20)=28 m/s.",
                part="b",
            ),
        ),
        teacher_key=TeacherKey(
            position_equation="x(t) = 8t + 0.5t²",
            velocity_equation="v(t) = 8 + t",
            acceleration_equation="a(t) = 1 m/s²",
            initial_position="0 m",
            initial_velocity="8 m/s",
            acceleration="1 m/s²",
            checkpoints=(
                "x(10) = 130 m",
                "x(20) = 360 m",
                "v(10) = 18 m/s",
                "v(20) = 28 m/s",
            ),
        ),
    ),
)


def get_published_exercises() -> tuple[Exercise, ...]:
    """Return only exercises approved for the student-facing catalog."""

    return tuple(exercise for exercise in EXERCISES if exercise.status == "published")


def get_exercise(exercise_id: str, *, published_only: bool = True) -> Exercise | None:
    """Look up an exercise, optionally enforcing the publication boundary."""

    exercises = get_published_exercises() if published_only else EXERCISES
    return next((exercise for exercise in exercises if exercise.id == exercise_id), None)


def serialize_for_student(exercise: Exercise) -> dict:
    """Return public catalog metadata only.

    Checkpoint prompts and choices are loaded separately from the canonical
    progress endpoint. Keeping them out of the catalog prevents future
    choices (and their labels) from being sent to the student in advance.
    """

    return {
        "id": exercise.id,
        "status": exercise.status,
        "title": exercise.title,
        "unit": exercise.unit,
        "source_file": exercise.source_file,
        "source_page": exercise.source_page,
        "statement": exercise.statement,
        "graph_asset": exercise.graph_asset,
        "starter_ideas": exercise.starter_ideas,
        "concepts": exercise.concepts,
    }


def serialize_checkpoint(checkpoint: Checkpoint) -> dict:
    """Return checkpoint data without the server-only correct option IDs."""

    def serialize_graph(graph: GraphDescriptor | None) -> dict | None:
        if graph is None:
            return None
        return {
            "kind": graph.kind,
            "points": graph.points,
            "x_min": graph.x_min,
            "x_max": graph.x_max,
            "y_min": graph.y_min,
            "y_max": graph.y_max,
            "x_label": graph.x_label,
            "y_label": graph.y_label,
        }

    return {
        "id": checkpoint.id,
        "part": checkpoint.part,
        "prompt": checkpoint.prompt,
        "input_type": checkpoint.input_type,
        "presentation": checkpoint.presentation,
        "options": tuple(
            {
                "id": option.id,
                "label": option.label,
                "graph": serialize_graph(option.graph),
            }
            for option in checkpoint.options
        ),
        "hint": checkpoint.hint,
        "help_hint": checkpoint.help_hint,
    }


def evaluate_checkpoint(
    exercise: Exercise,
    checkpoint_id: str,
    selected_option_ids: list[str] | tuple[str, ...],
    *,
    action: Literal["answer", "hint", "help"] = "answer",
) -> dict:
    """Evaluate one checkpoint without involving the language model."""

    checkpoint = next(
        (item for item in exercise.checkpoints if item.id == checkpoint_id), None
    )
    if checkpoint is None:
        raise ValueError("unknown checkpoint")

    selected = set(selected_option_ids)
    known_ids = {option.id for option in checkpoint.options}
    if action != "answer" or not selected:
        return {
            "result": "unknown",
            "feedback": checkpoint.help_hint if action == "help" else checkpoint.hint,
            "hint": checkpoint.help_hint if action == "help" else checkpoint.hint,
            "advanced": False,
        }
    if not selected <= known_ids:
        return {
            "result": "unknown",
            "feedback": "No reconozco alguna de las opciones elegidas. Probá con las opciones visibles.",
            "hint": checkpoint.hint,
            "advanced": False,
        }

    expected = set(checkpoint.correct_option_ids)
    if selected == expected:
        return {
            "result": "correct",
            "feedback": checkpoint.explanation,
            "hint": "",
            "advanced": True,
        }
    if checkpoint.input_type == "multi_select" and selected < expected:
        return {
            "result": "partially_correct",
            "feedback": "Vas bien, pero todavía falta una parte de este checkpoint.",
            "hint": checkpoint.hint,
            "advanced": False,
        }
    return {
        "result": "incorrect",
        "feedback": "Todavía no. Revisá la idea y volvé a intentarlo.",
        "hint": checkpoint.hint,
        "advanced": False,
    }


def serialize_progress(exercise: Exercise, checkpoint_index: int) -> dict:
    """Serialize canonical progression and only the current public checkpoint."""

    complete = checkpoint_index >= len(exercise.checkpoints)
    current = None if complete else serialize_checkpoint(exercise.checkpoints[checkpoint_index])
    progress = {
        "current_index": min(checkpoint_index, len(exercise.checkpoints)),
        "total": len(exercise.checkpoints),
        "completed_count": min(checkpoint_index, len(exercise.checkpoints)),
        "complete": complete,
        "current_checkpoint": current,
    }
    if complete:
        progress["completed_review"] = serialize_completed_review(exercise)
    return progress


def serialize_completed_review(exercise: Exercise) -> list[dict]:
    """Return the student-safe answer key for a completed exercise only."""

    return [
        {
            "checkpoint_id": checkpoint.id,
            "part": checkpoint.part,
            "question": checkpoint.prompt,
            "correct_answers": [
                {"label": option.label, "value": option.id}
                for option in checkpoint.options
                if option.id in checkpoint.correct_option_ids
            ],
        }
        for checkpoint in exercise.checkpoints
    ]


def filter_review_messages(exercise: Exercise, messages: list[dict]) -> list[dict]:
    """Keep only checkpoint answers and curated feedback for exercise review.

    Exercise-scoped history also stores the free-form tutor chat. That chat is
    not part of the review contract because a model response could
    accidentally reveal a future answer or private teacher data. Checkpoint
    turns have no persisted metadata yet, so this domain-owned allowlist
    recognizes the exact strings produced by the checkpoint endpoint.
    """

    answer_texts = {"Pedí una pista", "Necesité ayuda", "Respuesta: sin selección"}
    feedback_texts = {
        "No reconozco alguna de las opciones elegidas. Probá con las opciones visibles.",
        "Vas bien, pero todavía falta una parte de este checkpoint.",
        "Todavía no. Revisá la idea y volvé a intentarlo.",
    }
    for checkpoint in exercise.checkpoints:
        feedback_texts.update(
            tuple(
                plain_text(value)
                for value in (checkpoint.hint, checkpoint.help_hint, checkpoint.explanation)
            )
        )
        labels = [plain_text(option.label) for option in checkpoint.options]
        for size in range(1, len(labels) + 1):
            answer_texts.update(
                "Respuesta: " + ", ".join(selection)
                for selection in combinations(labels, size)
            )

    return [
        message
        for message in messages
        if (
            message.get("role") == "user"
            and message.get("content") in answer_texts
        )
        or (
            message.get("role") == "assistant"
            and message.get("content") in feedback_texts
        )
    ]
