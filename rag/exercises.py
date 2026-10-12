"""Curated exercise catalog and Socratic guidance metadata.

Only exercises with ``status == "published"`` should be exposed to students.
The teacher key is kept separate from the student-facing guidance so the
assistant can validate progress without revealing the complete solution.
"""

from dataclasses import dataclass
from itertools import combinations
from typing import Literal


ExerciseStatus = Literal["draft", "validated", "published", "archived"]


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
    points=((0, 6), (20, 30)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
_V_GRAPH_HORIZONTAL = GraphDescriptor(
    kind="polyline",
    points=((0, 16), (20, 16)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
_V_GRAPH_DECREASING = GraphDescriptor(
    kind="polyline",
    points=((0, 30), (20, 6)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
_V_GRAPH_CURVE = GraphDescriptor(
    kind="curve",
    points=((0, 6), (5, 14), (10, 8), (15, 24), (20, 12)),
    x_min=0,
    x_max=20,
    y_min=0,
    y_max=32,
    x_label="t (s)",
    y_label="v (m/s)",
)
_A_GRAPH_CORRECT = GraphDescriptor(
    kind="polyline",
    points=((0, 1.2), (20, 1.2)),
    x_min=0,
    x_max=20,
    y_min=-2,
    y_max=2,
    x_label="t (s)",
    y_label="a (m/s²)",
)
_A_GRAPH_ZERO = GraphDescriptor(
    kind="polyline",
    points=((0, 0), (20, 0)),
    x_min=0,
    x_max=20,
    y_min=-2,
    y_max=2,
    x_label="t (s)",
    y_label="a (m/s²)",
)
_A_GRAPH_INCREASING = GraphDescriptor(
    kind="polyline",
    points=((0, -1), (20, 1.8)),
    x_min=0,
    x_max=20,
    y_min=-2,
    y_max=2,
    x_label="t (s)",
    y_label="a (m/s²)",
)
_A_GRAPH_NEGATIVE = GraphDescriptor(
    kind="polyline",
    points=((0, -1.2), (20, -1.2)),
    x_min=0,
    x_max=20,
    y_min=-2,
    y_max=2,
    x_label="t (s)",
    y_label="a (m/s²)",
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
            "2. A partir del gráfico de la curva mostrado x(t):\n"
            "a. Escribir las ecuaciones correspondientes al movimiento, indicando "
            "los valores de posición y velocidad iniciales, así como de la "
            "aceleración si hubiera (en el origen de la gráfica, la curva "
            "parabólica forma un ángulo de salida α no nulo respecto de la horizontal).\n"
            "b. Confeccionar las gráficas cinemáticas restantes: v(t) y a(t), "
            "indicando en ellas los valores que asumen las magnitudes para los "
            "tiempos de 10 s y 20 s."
        ),
        graph_asset="/img/exercise-cinematica-1d-ejercicio-02.png",
        starter_ideas=(
            "Leé primero los ejes y sus unidades: t está en segundos y x en metros.",
            "Observá la forma de la curva x(t) antes de sacar conclusiones.",
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
                id="graph-reading",
                question=(
                    "¿Qué representan los ejes y qué unidades tienen?"
                ),
                expected_idea="El gráfico muestra posición x en metros en función del tiempo t en segundos.",
                hint="Mirá primero las magnitudes y unidades antes de hacer cuentas.",
            ),
            GuidanceStep(
                id="motion-model",
                question=(
                    "La curva x(t) es una parábola. ¿Qué modelo de movimiento representa?"
                ),
                expected_idea="Movimiento con aceleración constante.",
                hint="Pensá qué ocurre con la posición cuando la velocidad cambia uniformemente.",
            ),
            GuidanceStep(
                id="initial-position",
                question="¿Qué podés identificar al comienzo del gráfico?",
                expected_idea="x₀ = 0 m.",
                hint="Buscá dónde corta la curva al eje de posición cuando comienza el tiempo.",
            ),
            GuidanceStep(
                id="general-equation",
                question="¿Qué forma tiene la ecuación de posición para aceleración constante?",
                expected_idea="x(t) = x₀ + v₀t + ½at².",
                hint="Es la ecuación que contiene posición inicial, velocidad inicial y aceleración.",
            ),
            GuidanceStep(
                id="equations-from-graph",
                question=(
                    "Usando x(10)=120 m y x(20)=360 m, ¿qué relaciones y valores "
                    "sirven para determinar v₀ y a?"
                ),
                expected_idea="120 = 10v₀ + 50a y 360 = 20v₀ + 200a.",
                hint="Reemplazá cada tiempo y posición en la ecuación general.",
            ),
            GuidanceStep(
                id="solve-system",
                question="Con v₀ y a conocidos, ¿qué expresiones corresponden a v(t) y a(t)?",
                expected_idea="v₀ = 6 m/s y a = 1,2 m/s².",
                hint="Podés usar eliminación: primero hacé que ambas ecuaciones tengan el mismo término 20v₀.",
            ),
            GuidanceStep(
                id="velocity-and-acceleration",
                question=(
                    "Primero dibujá v(t) en el cuadernillo. Después, elegí el gráfico "
                    "que mejor representa tu dibujo."
                ),
                expected_idea="v(t) = 6 + 1,2t y a(t) = 1,2 m/s².",
                hint="La velocidad es v(t)=v₀+at; la aceleración permanece constante.",
            ),
            GuidanceStep(
                id="velocity-graph-shape",
                question="¿Qué valor inicial y qué tipo de trazo debería tener v(t)?",
                expected_idea="v(t) empieza en 6 m/s y es una recta creciente.",
                hint="El intercepto es v₀ y la pendiente de v(t) es la aceleración.",
            ),
            GuidanceStep(
                id="velocity-slope",
                question="¿Qué signo tiene la pendiente de v(t)?",
                expected_idea="La pendiente es positiva porque a = 1,2 m/s².",
                hint="Una aceleración positiva hace que la velocidad aumente.",
            ),
            GuidanceStep(
                id="requested-velocity-values",
                question="¿Qué valores de velocidad corresponden a t=10 s y t=20 s?",
                expected_idea="v(10)=18 m/s y v(20)=30 m/s.",
                hint="Usá la expresión de v(t) y reemplazá cada tiempo pedido.",
            ),
            GuidanceStep(
                id="acceleration-graph-shape",
                question=(
                    "Ahora dibujá a(t) en el cuadernillo. Después, elegí el gráfico "
                    "que mejor representa tu dibujo."
                ),
                expected_idea="a(t) es una recta horizontal positiva en 1,2 m/s².",
                hint="La aceleración no cambia con el tiempo en este movimiento.",
            ),
            GuidanceStep(
                id="acceleration-value",
                question="¿Qué valor debe marcar la gráfica a(t)?",
                expected_idea="a(t)=1,2 m/s².",
                hint="Es la pendiente constante de v(t).",
            ),
            GuidanceStep(
                id="requested-acceleration-values",
                question="¿Qué valores de aceleración corresponden a t=10 s y t=20 s?",
                expected_idea="a(10)=1,2 m/s² y a(20)=1,2 m/s².",
                hint="Como a(t) es constante, el valor se mantiene en ambos tiempos.",
            ),
            GuidanceStep(
                id="verification",
                question="¿Cómo verificarías que las ecuaciones representan el gráfico?",
                expected_idea=(
                    "Evaluando x(10), x(20), v(10), v(20), a(10) y a(20), y "
                    "comparando las formas de las gráficas."
                ),
                hint="Revisá los valores pedidos y compará las formas de v(t) y a(t).",
            ),
        ),
        checkpoints=(
            Checkpoint(
                id="read-axes-units",
                prompt="¿Qué representan los ejes y qué unidades tienen?",
                input_type="single_choice",
                options=(
                    CheckpointOption("time-position-meters-seconds", "t en segundos y x en metros"),
                    CheckpointOption("time-velocity-meters-seconds", "t en metros y v en segundos"),
                    CheckpointOption("position-time-seconds-meters", "x en segundos y t en metros"),
                ),
                correct_option_ids=("time-position-meters-seconds",),
                hint="Mirá primero qué magnitud aparece en cada eje y sus unidades.",
                help_hint="El eje horizontal es t y el vertical es x.",
                explanation="Leemos una posición x medida en metros en función del tiempo t medido en segundos.",
            ),
            Checkpoint(
                id="motion-model",
                prompt="La curva x(t) es una parábola. ¿Qué modelo de movimiento representa?",
                input_type="single_choice",
                options=(
                    CheckpointOption("constant-velocity", "Movimiento con velocidad constante"),
                    CheckpointOption("constant-acceleration", "Movimiento con aceleración constante"),
                    CheckpointOption("rest", "Partícula en reposo"),
                ),
                correct_option_ids=("constant-acceleration",),
                hint="Pensá qué forma tiene x(t) cuando la velocidad cambia uniformemente.",
                help_hint="Una parábola en x(t) aparece cuando la aceleración es constante.",
                explanation="La forma parabólica de x(t) es compatible con una aceleración constante.",
            ),
            Checkpoint(
                id="initial-conditions",
                prompt="¿Qué podés identificar al comienzo del gráfico?",
                input_type="multi_select",
                options=(
                    CheckpointOption("initial-position-zero", "x₀ = 0 m"),
                    CheckpointOption("initial-velocity-positive", "La velocidad inicial es positiva"),
                    CheckpointOption("initial-velocity-negative", "La velocidad inicial es negativa"),
                    CheckpointOption("initial-position-120", "x₀ = 120 m"),
                ),
                correct_option_ids=("initial-position-zero", "initial-velocity-positive"),
                hint="Observá dónde empieza la curva y hacia dónde crece al inicio.",
                help_hint="La curva parte de x=0 y tiene pendiente inicial hacia arriba.",
                explanation="El gráfico permite identificar x₀ = 0 m y una velocidad inicial positiva.",
            ),
            Checkpoint(
                id="position-equation",
                prompt="¿Qué forma tiene la ecuación de posición para aceleración constante?",
                input_type="single_choice",
                options=(
                    CheckpointOption("position-equation-correct", "x(t) = x₀ + v₀t + ½at²"),
                    CheckpointOption("position-equation-linear", "x(t) = x₀ + vt"),
                    CheckpointOption("position-equation-velocity", "x(t) = v₀ + at"),
                ),
                correct_option_ids=("position-equation-correct",),
                hint="Elegí la expresión que contiene posición inicial, velocidad inicial y aceleración.",
                help_hint="La aceleración constante aporta un término proporcional a t².",
                explanation="La ecuación general incorpora x₀, v₀ y el término ½at².",
            ),
            Checkpoint(
                id="determine-initial-values",
                prompt="Usando x(10)=120 m y x(20)=360 m, ¿qué relaciones y valores sirven para determinar v₀ y a?",
                input_type="multi_select",
                options=(
                    CheckpointOption("equation-at-10", "120 = 10v₀ + 50a"),
                    CheckpointOption("equation-at-20", "360 = 20v₀ + 200a"),
                    CheckpointOption("solution-v0-a", "Al resolver: v₀ = 6 m/s y a = 1,2 m/s²"),
                    CheckpointOption("equation-at-10-wrong", "120 = 10v₀ + 10a"),
                    CheckpointOption("solution-negative", "v₀ = -6 m/s y a = -1,2 m/s²"),
                ),
                correct_option_ids=("equation-at-10", "equation-at-20", "solution-v0-a"),
                hint="Reemplazá cada tiempo en la ecuación general y luego resolvé el sistema.",
                help_hint="Las dos ecuaciones correctas salen de sustituir t=10 y t=20; ambas llevan al mismo par v₀,a.",
                explanation="Los puntos del gráfico forman un sistema que determina v₀ = 6 m/s y a = 1,2 m/s².",
            ),
            Checkpoint(
                id="velocity-and-acceleration",
                prompt="Con v₀ y a conocidos, ¿qué expresiones corresponden a v(t) y a(t)?",
                input_type="single_choice",
                options=(
                    CheckpointOption("velocity-acceleration-correct", "v(t)=6+1,2t y a(t)=1,2 m/s²"),
                    CheckpointOption("velocity-acceleration-constant-v", "v(t)=6 y a(t)=0"),
                    CheckpointOption("velocity-acceleration-swapped", "v(t)=1,2+6t y a(t)=6 m/s²"),
                ),
                correct_option_ids=("velocity-acceleration-correct",),
                hint="Usá v(t)=v₀+at y recordá que la aceleración permanece constante.",
                help_hint="La pendiente de v(t) es a y el valor inicial de v(t) es v₀.",
                explanation="La velocidad crece linealmente y la aceleración queda constante.",
                part="b",
            ),
            Checkpoint(
                id="velocity-graph-shape",
                prompt=(
                    "Primero dibujá v(t) en el cuadernillo. Después, elegí el gráfico "
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
                hint="Buscá una recta que empiece en 6 m/s y aumente con el tiempo.",
                help_hint="La velocidad inicial es 6 m/s y la aceleración positiva hace que la recta suba.",
                explanation="El gráfico correcto es una recta creciente que comienza en 6 m/s.",
                part="b",
                presentation="graph",
            ),
            Checkpoint(
                id="velocity-initial-value",
                prompt="En tu dibujo de v(t), ¿qué valor debe marcar el intercepto en t=0?",
                input_type="single_choice",
                options=(
                    CheckpointOption("velocity-intercept-6", "6 m/s"),
                    CheckpointOption("velocity-intercept-0", "0 m/s"),
                    CheckpointOption("velocity-intercept-12", "12 m/s"),
                ),
                correct_option_ids=("velocity-intercept-6",),
                hint="El intercepto de v(t) representa la velocidad inicial v₀.",
                help_hint="Volvé al valor de v₀ que obtuviste antes de dibujar.",
                explanation="La recta de velocidad corta el eje vertical en v₀ = 6 m/s.",
                part="b",
            ),
            Checkpoint(
                id="velocity-slope-sign",
                prompt="¿Qué signo tiene la pendiente de v(t) en tu dibujo?",
                input_type="single_choice",
                options=(
                    CheckpointOption("velocity-slope-positive", "Positiva: la recta sube"),
                    CheckpointOption("velocity-slope-zero", "Cero: la recta es horizontal"),
                    CheckpointOption("velocity-slope-negative", "Negativa: la recta baja"),
                ),
                correct_option_ids=("velocity-slope-positive",),
                hint="La pendiente de v(t) es la aceleración.",
                help_hint="Una aceleración positiva hace que la velocidad aumente.",
                explanation="La pendiente es positiva porque la aceleración vale 1,2 m/s².",
                part="b",
            ),
            Checkpoint(
                id="evaluate-requested-times",
                prompt="¿Qué valores se obtienen al evaluar las magnitudes en los tiempos pedidos?",
                input_type="multi_select",
                options=(
                    CheckpointOption("position-at-10", "x(10)=120 m"),
                    CheckpointOption("position-at-20", "x(20)=360 m"),
                    CheckpointOption("velocity-at-10", "v(10)=18 m/s"),
                    CheckpointOption("velocity-at-20", "v(20)=30 m/s"),
                    CheckpointOption("velocity-at-10-wrong", "v(10)=12 m/s"),
                ),
                correct_option_ids=("position-at-10", "position-at-20", "velocity-at-10", "velocity-at-20"),
                hint="Sustituí t=10 y t=20 en x(t) y v(t).",
                help_hint="Los puntos x(10) y x(20) son los del gráfico; calculá v con v(t)=6+1,2t.",
                explanation="Las evaluaciones recuperan los puntos conocidos y dan v(10)=18 m/s y v(20)=30 m/s.",
                part="b",
            ),
            Checkpoint(
                id="acceleration-graph-shape",
                prompt=(
                    "Ahora dibujá a(t) en el cuadernillo. Después, elegí el gráfico "
                    "que mejor representa tu dibujo."
                ),
                input_type="single_choice",
                options=(
                    CheckpointOption("acceleration-graph-correct", "Gráfico A", _A_GRAPH_CORRECT),
                    CheckpointOption("acceleration-graph-zero", "Gráfico B", _A_GRAPH_ZERO),
                    CheckpointOption("acceleration-graph-increasing", "Gráfico C", _A_GRAPH_INCREASING),
                    CheckpointOption("acceleration-graph-negative", "Gráfico D", _A_GRAPH_NEGATIVE),
                ),
                correct_option_ids=("acceleration-graph-correct",),
                hint="Buscá una línea horizontal por encima de cero.",
                help_hint="La aceleración es constante y positiva: a(t)=1,2 m/s².",
                explanation="El gráfico correcto es horizontal y positivo, en 1,2 m/s².",
                part="b",
                presentation="graph",
            ),
            Checkpoint(
                id="acceleration-value",
                prompt="¿Qué valor debe marcar la gráfica a(t)?",
                input_type="single_choice",
                options=(
                    CheckpointOption("acceleration-value-correct", "1,2 m/s²"),
                    CheckpointOption("acceleration-value-zero", "0 m/s²"),
                    CheckpointOption("acceleration-value-six", "6 m/s²"),
                ),
                correct_option_ids=("acceleration-value-correct",),
                hint="La aceleración es la pendiente constante de v(t).",
                help_hint="Usá el valor de a que obtuviste al resolver el sistema.",
                explanation="La gráfica de aceleración se mantiene en 1,2 m/s².",
                part="b",
            ),
            Checkpoint(
                id="acceleration-at-requested-times",
                prompt="¿Qué valores de aceleración corresponden a t=10 s y t=20 s?",
                input_type="multi_select",
                options=(
                    CheckpointOption("acceleration-at-10", "a(10)=1,2 m/s²"),
                    CheckpointOption("acceleration-at-20", "a(20)=1,2 m/s²"),
                    CheckpointOption("acceleration-at-10-wrong", "a(10)=0 m/s²"),
                    CheckpointOption("acceleration-at-20-wrong", "a(20)=6 m/s²"),
                ),
                correct_option_ids=("acceleration-at-10", "acceleration-at-20"),
                hint="Como a(t) es constante, buscá el mismo valor en ambos tiempos.",
                help_hint="La línea horizontal conserva su valor en t=10 s y t=20 s.",
                explanation="a(10) y a(20) valen 1,2 m/s² porque la aceleración es constante.",
                part="b",
            ),
            Checkpoint(
                id="final-verification",
                prompt="¿Cuál es una buena verificación final del modelo?",
                input_type="single_choice",
                options=(
                    CheckpointOption("verify-correct", "Reemplazar t=10 y t=20, y revisar que v(t) sea lineal y a(t) constante"),
                    CheckpointOption("verify-one-point", "Comprobar solamente que x(0)=0"),
                    CheckpointOption("verify-ignore-graph", "No comparar las ecuaciones con el gráfico"),
                ),
                correct_option_ids=("verify-correct",),
                hint="Una verificación usa más de un dato conocido y también compara la forma de las gráficas.",
                help_hint="Revisá x(10), x(20), la recta v(t) y la constante a(t).",
                explanation="El modelo queda verificado al recuperar los puntos conocidos y las formas esperadas de v(t) y a(t).",
                part="b",
            ),
        ),
        teacher_key=TeacherKey(
            position_equation="x(t) = 6t + 0.6t²",
            velocity_equation="v(t) = 6 + 1.2t",
            acceleration_equation="a(t) = 1.2 m/s²",
            initial_position="0 m",
            initial_velocity="6 m/s",
            acceleration="1.2 m/s²",
            checkpoints=(
                "x(10) = 120 m",
                "x(20) = 360 m",
                "v(10) = 18 m/s",
                "v(20) = 30 m/s",
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
            (checkpoint.hint, checkpoint.help_hint, checkpoint.explanation)
        )
        labels = [option.label for option in checkpoint.options]
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
