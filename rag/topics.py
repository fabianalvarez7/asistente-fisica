"""Índice temático del programa de Física 1.

Lista hardcodeada de las 12 unidades temáticas del curso, tomadas del PDF
``data/pdfs/Contenidos Temáticos.pdf`` (UNR — Facultad de Ciencias
Bioquímicas y Farmacéuticas). El PDF vive solo en local; en el deploy
se sirve desde este módulo porque ``data/`` está gitignoreado y
excluido del rsync al Space.

Cada unidad expone una lista ``preguntas`` con 2 o 3 preguntas socráticas
en español rioplatense (voseo). Las preguntas no validadas por la
docente llevan el prefijo ``[BORRADOR — falta validar con Nair]``. Para
publicar una pregunta, quitar el prefijo y dejar el texto plano; el
frontend lo usa como semilla de descubrimiento.

Si el syllabus cambia, editar esta lista y redesplegar. Mantener
sincronizado con el PDF al actualizar.
"""

from __future__ import annotations

from typing import List


_TOPICS: List[dict] = [
    {
        "numero": "I",
        "titulo": "Introducción a la Física",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué diferencia hay entre una magnitud escalar y una vectorial?",
            "[BORRADOR — falta validar con Nair] ¿Por qué creés que es importante usar unidades estandarizadas al medir?",
            "[BORRADOR — falta validar con Nair] ¿Cómo describirías con tus palabras qué es un modelo en física?",
        ],
    },
    {
        "numero": "II",
        "titulo": "Cinemática de la partícula en una dimensión",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] Si un auto se mueve con velocidad constante, ¿qué podés decir de su aceleración?",
            "[BORRADOR — falta validar con Nair] ¿Cómo diferenciás en una gráfica x(t) el reposo de un movimiento uniforme?",
            "[BORRADOR — falta validar con Nair] ¿Qué interpretación física tiene el signo de la aceleración en el eje x?",
        ],
    },
    {
        "numero": "III",
        "titulo": "Cinemática en dos y tres dimensiones",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Por qué en un tiro oblicuo la velocidad horizontal se mantiene constante (sin rozamiento)?",
            "[BORRADOR — falta validar con Nair] ¿Qué información te da el vector velocidad instantánea sobre el movimiento?",
            "[BORRADOR — falta validar con Nair] ¿Cómo decidís si conviene descomponer un vector en componentes cartesianas?",
        ],
    },
    {
        "numero": "IV",
        "titulo": "Leyes de Newton",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] Si sobre un cuerpo no actúa ninguna fuerza neta, ¿qué le pasará a su velocidad?",
            "[BORRADOR — falta validar con Nair] ¿Qué significa que la fuerza de reacción actúe sobre otro cuerpo distinto?",
            "[BORRADOR — falta validar con Nair] ¿Cómo elegís qué cuerpo conviene aislar para plantear las ecuaciones?",
        ],
    },
    {
        "numero": "V",
        "titulo": "Trabajo y energía",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Cuándo podés afirmar que una fuerza realiza trabajo sobre un cuerpo?",
            "[BORRADOR — falta validar con Nair] ¿Qué nos dice el teorema trabajo-energía cinética sobre un cambio de velocidad?",
            "[BORRADOR — falta validar con Nair] ¿En qué situaciones mecánicas se conserva la energía mecánica total?",
        ],
    },
    {
        "numero": "VI",
        "titulo": "Cinemática y dinámica circular",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué dirección tiene la aceleración centrípeta respecto a la velocidad?",
            "[BORRADOR — falta validar con Nair] ¿Por qué un cuerpo en movimiento circular uniforme sigue acelerando?",
            "[BORRADOR — falta validar con Nair] ¿Cómo relacionás el torque con el cambio del movimiento de rotación?",
        ],
    },
    {
        "numero": "VII",
        "titulo": "Estática de los fluidos",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué relación existe entre la presión y la profundidad en un fluido en reposo?",
            "[BORRADOR — falta validar con Nair] ¿Cómo explicás el principio de Arquímedes usando diferencias de presión?",
            "[BORRADOR — falta validar con Nair] ¿Por qué un barco de acero puede flotar mientras una moneda no?",
        ],
    },
    {
        "numero": "VIII",
        "titulo": "Dinámica de los fluidos",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué nos dice la ecuación de continuidad para un fluido incompresible?",
            "[BORRADOR — falta validar con Nair] ¿Cómo se relacionan la velocidad y la presión en el principio de Bernoulli?",
            "[BORRADOR — falta validar con Nair] ¿Qué papel juega la viscosidad en el movimiento de un fluido real?",
        ],
    },
    {
        "numero": "IX",
        "titulo": "Sistema de partículas y conservación del momento lineal",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿En qué condiciones se conserva el momento lineal total de un sistema?",
            "[BORRADOR — falta validar con Nair] ¿Cómo definirías el centro de masa de un sistema de partículas?",
            "[BORRADOR — falta validar con Nair] ¿Qué información te da la clasificación de un choque como elástico o inelástico?",
        ],
    },
    {
        "numero": "X",
        "titulo": "Rotación del cuerpo rígido",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué analogía podés establecer entre la segunda ley de Newton para traslación y rotación?",
            "[BORRADOR — falta validar con Nair] ¿Cómo se define el momento de inercia y qué representa físicamente?",
            "[BORRADOR — falta validar con Nair] ¿Por qué el momento angular se conserva cuando el torque externo neto es cero?",
        ],
    },
    {
        "numero": "XI",
        "titulo": "Movimiento oscilatorio",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué características debe tener un movimiento para considerarse armónico simple?",
            "[BORRADOR — falta validar con Nair] ¿Cómo afecta la constante elástica del resorte al período de oscilación?",
            "[BORRADOR — falta validar con Nair] ¿Qué aproximación permite modelar un péndulo simple como armónico?",
        ],
    },
    {
        "numero": "XII",
        "titulo": "Movimiento ondulatorio",
        "preguntas": [
            "[BORRADOR — falta validar con Nair] ¿Qué diferencia hay entre el movimiento de una partícula del medio y el movimiento de la onda?",
            "[BORRADOR — falta validar con Nair] ¿Cómo relacionás la velocidad de propagación con la longitud de onda y la frecuencia?",
            "[BORRADOR — falta validar con Nair] ¿Qué condiciones son necesarias para observar interferencia entre dos ondas?",
        ],
    },
]


def load_topics() -> List[dict]:
    """Devuelve las unidades del syllabus para el sidebar.

    Mantenido como función para no romper el contrato con el endpoint
    ``GET /topics`` que importa este símbolo. Devuelve la lista estática
    directamente — no hay parsing ni I/O en runtime.
    """
    return _TOPICS
