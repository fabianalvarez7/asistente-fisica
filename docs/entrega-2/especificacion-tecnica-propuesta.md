# Especificación Técnica — Entrega 2 (Sección 3)

**Documento de trabajo** para la Entrega 2 (Primer Avance: Maquetación del Prototipo). **Sección 3:** Especificación Técnica. **Estado:** borrador inicial. **Última actualización:** 2026-08-07.

> **Aviso (2026-09-08)**: las menciones a `marker-pdf`/`surya` en este documento reflejan una decisión que fue revertida en septiembre 2026 (ver `docs/adr/0001-pdf-loader-marker.md` para la historia completa). El loader vigente es `pymupdf4llm`. El resto de la propuesta sigue vigente.

## Avance de desarrollo

**El prototipo se encuentra funcional y desplegado en https://huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr**. La mecánica principal del chat está operativa tanto en entorno local (`uvicorn app.main:app --reload`) como en producción (Hugging Face Spaces, contenedor Docker `cpu-basic`). Lo que sigue describe los componentes preliminares que ya están resueltos y los placeholders explícitos que se mantienen para iteraciones posteriores.

### Componentes resueltos

**Frontend (chat del estudiante).** Página única servida por FastAPI como estáticos. HTML plano + CSS + JavaScript sin framework. Componentes interactivos resueltos: pantalla de identificación (input + botón "Entrar"), cabecera con título, área de conversación con burbujas, render de LaTeX inline/display mediante KaTeX, input de pregunta con validación de longitud (máx. 500 caracteres), botón de borrado por mensaje.

**Backend (API REST).** FastAPI con tres endpoints principales: `POST /chat` (Server-Sent Events para streaming de tokens), `GET /messages` (historial por nombre de estudiante), `DELETE /messages/{id}` (borrado con check de ownership por nombre). Modelos `ChatRequest` y `ChatMessage` en `app/models.py`. Manejo de errores uniforme con `event: error` en SSE y mensaje de fallback en frontend.

**RAG (recuperación + prompt).** Indexación de PDFs del curso en base de datos vectorial de ChromaDB con embeddings locales `intfloat/multilingual-e5-small` (sentence-transformers). Pipeline de retrieval configurable (parámetro `k`, dispositivo MPS/CUDA/CPU según plataforma). El orquestador vive en `rag/chain.py` y aplica el system prompt Socrático antes de invocar al LLM.

**Capa Socrática.** System prompt dedicado (en `rag/prompts/`) que instruye al LLM a guiar con preguntas, validar el intento del estudiante, escalar el nivel de ayuda en tres pasos (pregunta orientadora → pista → fórmula) y nunca resolver el ejercicio de forma directa.

**Persistencia de historial.** Base de datos SQLite local con tabla `messages(id, student_name, role, content, created_at)`. Función `get_or_create_student(name)` que crea el registro si no existe. El historial se inyecta en la ventana de contexto del LLM (`HISTORY_WINDOW=10` por defecto) para mantener coherencia multi-turno.

**Despliegue.** Imagen Docker construida a partir de un `Dockerfile` mínimo, hospedada en Hugging Face Spaces (tier `cpu-basic`, 16 GB RAM, puerto 7860). El modelo de embeddings se bakea en build time mediante `scripts/preparar_indice_hf.py`. Los modelos de `marker-pdf`/`surya` (~3.45 GB) también se hornean en la imagen mediante `create_model_dict()` y la variable `MODEL_CACHE_DIR` — así el Space no re-descarga modelos en cada cold-start.

### Placeholders explícitos (a iterar en próximas etapas)

- **Avatar del asistente** en el área de conversación: por ahora no hay, a definir con el diseñador.
- **Indicador de "pensando"** durante el stream: hoy un texto literal "Cargando…"; pendiente reemplazar por animación o spinner.
- **Feedback de éxito** (por ejemplo "Pregunta enviada", "Guardado"): no se muestra; los estados de UI solo cubren error y carga.
- **Re-identificación sin recarga de página**: si el estudiante tipea un nombre distinto al guardado, hoy se ignora; pendiente flujo de confirmación.
- **Paginación o scroll virtual** del historial para hilos muy largos: no implementado (no es problema en el volumen actual del prototipo).

## Herramientas, motores y entornos de desarrollo

**Lenguaje:** Python 3.11+.

**Backend:** FastAPI. Asíncrono, documentación automática (OpenAPI), tipado con Pydantic. Liviano y sin opiniones sobre ORM o autenticación.

**Frontend del chat:** HTML + CSS + JavaScript sin framework. La página es una lista de mensajes más un input; React sería sobre-ingeniería.

**Pipeline RAG (toolbox):** LangChain usado selectivamente como toolbox (loaders, splitters, retrievers). El orquestador del pipeline es propio, en `rag/chain.py`, y no usa las abstracciones de alto nivel de LangChain (Agentes, Memory, RetrievalQA).

**Vector store:** ChromaDB local persistente. Cero setup, archivo en disco, cliente/servidor disponible si el prototipo crece.

**LLM:** Groq API (modelo `llama-3.3-70b-versatile` por defecto). Tier gratuito, inferencia rápida, soporte de español rioplatense y LaTeX en el output.

**Embeddings:** sentence-transformers con el modelo `intfloat/multilingual-e5-small` (270 MB). Inferencia local — sin red, sin costo por consulta. Dispositivo auto-detectado: MPS (macOS Apple Silicon), CUDA (Windows con GPU NVIDIA), CPU (resto).

**Persistencia:** SQLite. Archivo único, sin servidor, fácil de migrar a Postgres si el prototipo crece.

**Conversión PDF → Markdown:** `marker-pdf` (1.10.2, instalado en `.venv`). Recuperó 2665 delimitadores LaTeX en la primera indexación del corpus canónico de 5 PDFs (Cinemática 1, Cinemática 2, Dinámica 1, Dinámica 2, cuadernillo), contra cero fórmulas que recuperaba `pymupdf4llm` en el mismo material. El singleton del converter amortiza la carga del modelo (~10 GB RAM peak) entre todos los PDFs del corpus. El bake de ChromaDB se valida con `scripts/verify_latex.py` (≥2000 LaTeX NFR) antes de commitear. `pymupdf4llm` fue removido del `requirements.txt` — la decisión se documenta en el design del change `marker-pdf-loader`.

**Despliegue:** Hugging Face Spaces con `sdk: docker`. Tier `cpu-basic` (16 GB RAM, sleep tras ~48 h de inactividad).

**Gestión de secretos:** variables de entorno vía `.env` en dev, Space Secrets en producción. `GROQ_API_KEY` es la única clave obligatoria.

## Entorno previsto para la interacción

**Dispositivo:** navegador web moderno (Chrome, Firefox, Safari, Edge, etc.). El prototipo es 100% browser-based; el estudiante no instala nada.

**Sistemas operativos:** Windows (incluyendo máquinas de gama baja con conexión lenta), macOS, Linux, y navegadores móviles (iOS Safari, Android Chrome). La elección de HTML/CSS plano y la dependencia mínima de JS pesado apuntan a este rango.

**Resoluciones:** layout responsive con breakpoints simples (mobile-first a ~480 px, tablet a ~768 px, desktop a partir de ~1024 px). El stream de mensajes y el input ocupan el alto completo de la viewport en mobile.

**Conectividad:** el prototipo asume conexión a internet (necesaria para Groq, KaTeX CDN y el Space HF). En conexiones muy lentas, el cold start del Space puede añadir entre 20 y 40 segundos antes de la primera respuesta.

**Identidad del estudiante:** por nombre tipeado, sin usuario ni contraseña. La identidad persiste en `localStorage` del navegador y en SQLite del backend.

**Persistencia de la conversación:** depende del estado del deploy. En local, la historia persiste mientras el archivo SQLite no se borre. En el Space HF, el disco es efímero y se reinicia cada vez que el contenedor despierta del sleep — la historia previa al sleep se pierde. Aceptado como trade-off del tier gratuito.

## Registro de pruebas de la mecánica principal

### Aciertos

**Calidad de retrieval validada en muestra de PDFs.** En las semanas 1-2 se construyó el pipeline con `pymupdf4llm` y se ejecutaron consultas de prueba. En las semanas 7-8 se reemplazó por `marker-pdf` después de validar que el primero perdía todas las fórmulas LaTeX del material limpio de Sears. La búsqueda semántica con `intfloat/multilingual-e5-small` recupera chunks relevantes para preguntas tipo ejercicio, y ahora esos chunks contienen LaTeX legible (`$v_{\text{med-}x} = \frac{\Delta x}{\Delta t}$` y similares) que llega al LLM y se renderiza en la respuesta al estudiante.

**Primer deploy a producción.** Semanas 3-4, el chat quedó desplegado en Hugging Face Spaces y accesible vía URL pública.

**Capa Socrática operativa en producción.** El system prompt con la rampa de tres niveles (pregunta → pista → fórmula) guía al estudiante sin resolverle el ejercicio. Validado manualmente con un set de preguntas de la guía práctica del curso. Comportamiento consistente en español rioplatense.

**Migración a `marker-pdf` completada y en producción.** El reemplazo de `pymupdf4llm` por `marker-pdf` se cerró en la semana 7-8: la nueva pipeline recuperó 2665 delimitadores LaTeX en el corpus canónico de 5 PDFs, los chunks ahora contienen fórmulas legibles que llegan al LLM, y el sistema renderiza LaTeX en la respuesta al estudiante (validado con `curl` al endpoint `/chat` del Space HF). El re-bake del corpus tarda 5-7 h en Mac MPS — aceptable para iteraciones futuras.

**Historial persistente por estudiante.** Al recargar la página, el estudiante identificado por nombre ve su historial completo y la conversación continúa con contexto coherente. Funcional en local y en el Space.

**Render de LaTeX.** KaTeX renderiza fórmulas inline y en bloque en el output del asistente, incluyendo derivadas, integrales y notación vectorial frecuente en Física 1. Si el CDN falla, el texto crudo se muestra igual (`throwOnError: false`).

### Dificultades

**Elección de la herramienta de PDF → Markdown — cerrada.** Se eligió `marker-pdf` después de comparar con `pymupdf4llm` sobre los 4 capítulos de Sears (Cinemática y Dinámica, ~440 páginas): `marker-pdf` recuperó 559 fórmulas LaTeX en Cinemática 1 (25 páginas) contra 0 de `pymupdf4llm`. La razón del descarte de Mathpix es su tier gratuito de 1000 páginas/mes, que se queda corto para el corpus combinado (5 PDFs + re-bakes). La razón del descarte de `docling` fue su peso en disco y el setup extra. La decisión se documenta en el SDD change `marker-pdf-loader` (`openspec/changes/archive/2026-08-06-marker-pdf-loader/`).

**Cold start del Space HF.** El primer request tras un período de inactividad (alrededor de 48 h) tarda entre 20 y 40 segundos en despertar el contenedor. Aceptado como trade-off del tier gratuito. Si el proyecto pasa a producción real, considerar Render con disco persistente o un servidor de la facultad.

**Pérdida de historial al despertar el Space.** El disco del tier `cpu-basic` es efímero. Cuando el contenedor se duerme y se vuelve a despertar, el archivo SQLite se reinicia vacío. Aceptado como limitación por servicio gratuito, pero es la queja más probable cuando el prototipo se pruebe con varios estudiantes.

### Iteraciones por área

Además de los aciertos y dificultades ya listados, dedicamos dos tandas de prueba focalizadas a las áreas más sensibles de la experiencia: el estilo de respuesta del asistente y el reconocimiento del estudiante entre sesiones.

**Capa Socrática.** El requisito central del proyecto es que el asistente guíe con preguntas y nunca resuelva el ejercicio. Para validarlo, armamos un set corto de consultas tipo ejercicio (cinemática, dinámica, trabajo y energía) y observamos el comportamiento conversando en la interfaz real. En la mayoría de los casos sostuvo bien la pregunta orientadora, validó los intentos del estudiante y devolvió una pregunta más específica. Detectamos, sin embargo, que ante un estudiante que no sabe por dónde empezar el asistente tendía a dar la fórmula directa — exactamente lo contrario del estilo buscado. Iteramos el prompt del sistema para reforzar una rampa de tres niveles: primero pregunta orientadora, después pista más concreta, fórmula solo cuando el estudiante está trabado. Esta iteración sigue abierta: falta validar el comportamiento con casos más diversos (estudiante apurado, estudiante frustrado, ejercicios con trampa) antes de cerrar el prompt.

**Identificación de usuarios.** El prototipo identifica a cada estudiante por el nombre que tipea al entrar, sin usuario ni contraseña — una decisión consciente para eliminar barreras de entrada en esta primera versión. Probamos tres flujos: estudiante nuevo, estudiante que vuelve y recarga la página, y estudiante que limpia la caché del navegador. El nombre se guarda en el navegador y en la base de datos; al recargar, el chat se abre directo en la conversación anterior con todo el historial. La fricción de entrada es nula y el estudiante no necesita recordar nada. Lo que queda como decisión pendiente: dos estudiantes que tipeen exactamente el mismo nombre comparten el mismo hilo, y cuando alguien tipea un nombre distinto al que ya tenía guardado el sistema lo ignora silenciosamente. Ambas son consecuencias explícitas de la decisión de no usar autenticación, y se revisitarán si el sistema crece más allá del prototipo.
