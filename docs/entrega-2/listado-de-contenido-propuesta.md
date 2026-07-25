# Listado de Contenido — Entrega 2 (Sección 1)

> Documento de trabajo para la Entrega 2 (Primer Avance: Maquetación del Prototipo).
> Sección 1: Listado de Contenido.
> Estado: borrador inicial. Última actualización: 2026-07-25.

## Áreas del prototipo

El prototipo a entregar en esta etapa cubre únicamente el chat del estudiante
(el dashboard de Streamlit queda fuera de alcance de esta entrega). A los fines
del listado, "área" refiere a una sección visual con interacción propia dentro
de la página del chat.

### 1. Identificación del estudiante

- **Qué muestra**: input de texto y botón "Entrar", con el placeholder "Escribí tu nombre para empezar…".
- **Interacción**: el estudiante tipea su nombre y presiona "Entrar" o Enter. El nombre persiste en `localStorage` y en SQLite (vía `get_or_create_student`). Al recargar la página, si hay nombre guardado, se saltea este paso.
- **Información que usa**: solo el nombre tipeado (mín. 1, máx. 100 caracteres). Sin email, sin contraseña.
- **Qué falta**: logout, cambiar de nombre sin recargar la página, disambiguación entre estudiantes que escriben el mismo nombre.
- **Limitaciones / simplificaciones**: identificación por nombre, no por usuario y contraseña. Decisión consciente del proyecto (ver AGENTS §7, decisión 11). El trade-off es explícito: dos estudiantes que escriben el mismo nombre comparten el mismo hilo.

### 2. Cabecera

- **Qué muestra**: título "Asistente de Física 1" y subtítulo "Respondemos desde los apuntes del curso".
- **Interacción**: ninguna, es estática.
- **Información que usa**: literales hardcodeados en el HTML.
- **Qué falta**: logo, isotipo/isologo/imagotipo (lo entrega el diseñador en la sección 2 de la entrega). Tagline alternativo si lo hubiera.
- **Limitaciones / simplificaciones**: la paleta actual es un azul único (`#0f4c81`) que se va a reemplazar cuando llegue la identidad visual. La tipografía es la `system-ui` del sistema operativo.

### 3. Área de conversación

- **Qué muestra**: lista vertical de mensajes. Cada mensaje es una burbuja con un botón × para eliminar. Los mensajes del asistente renderizan LaTeX inline/display con KaTeX. Estado "Cargando…" mientras streamea la respuesta.
- **Interacción**: leer, scrollear, borrar cualquier mensaje propio (usuario o asistente) con la ×. Al borrar, se hace `DELETE /messages/{id}` con check de ownership por nombre.
- **Información que usa**: historial persistido en SQLite y stream de tokens vía `POST /chat` (SSE).
- **Qué falta**: indicador de streaming más rico (hoy es un texto "Cargando…"), animación de "el asistente está pensando", avatares, reacciones (thumbs up/down), agrupar mensajes del asistente largos.
- **Limitaciones / simplificaciones**: el render de LaTeX depende del CDN de KaTeX. Si el CDN falla, el texto crudo se ve igual (`throwOnError: false`). El borrado es silencioso: si el backend rechaza con 403/404, la UI no muestra error para mantenerse consistente.

### 4. Entrada de pregunta

- **Qué muestra**: input de texto y botón "Enviar". Hints en una línea debajo para validaciones y errores.
- **Interacción**: tipear pregunta, Enter o clic en "Enviar", se deshabilita el input hasta que termina el stream. Validaciones: vacío, máx. 500 caracteres. La pregunta llega al backend como `{query, student_name}`.
- **Información que usa**: el texto tipeado y el `studentName` guardado en `localStorage`.
- **Qué falta**: contador de caracteres visible mientras tipea, sugerencias de preguntas, autocompletar, historial de preguntas recientes, atajos de teclado.
- **Limitaciones / simplificaciones**: el límite de 500 caracteres está replicado en frontend y backend (`ChatRequest.max_length`). Sin sugerencias, la primera interacción con un input vacío puede ser intimidante para un estudiante que no sabe qué preguntar.

### 5. Feedback al usuario

- **Qué muestra**: una línea de hint bajo el input. Color rojo para errores (`#b00020`). El mensaje de fallback del backend ("Ocurrió un error, intentá de nuevo") reemplaza el contenido del mensaje asistente cuando el stream falla.
- **Interacción**: pasiva, el usuario lee el hint cuando aparece.
- **Información que usa**: textos hardcodeados en `chat.js` y `main.py` (cinco strings en total: "Escribí tu nombre para empezar", "Escribí una pregunta", "Máximo 500 caracteres", "No se pudo cargar el historial", "Ocurrió un error, intentá de nuevo").
- **Qué falta**: feedback de éxito (no hay "Pregunta enviada" ni "Guardado"), feedback de carga del historial al abrir la app, mensaje para el caso "no tenés preguntas previas".
- **Limitaciones / simplificaciones**: todos los textos están en español rioplatense (voseo). Asumimos que el público objetivo habla español de Argentina. No hay i18n.

## Mapa de navegación

> Pendiente. Próxima sección a desarrollar. Referencia metodológica: pp. 110-114
> de *Experiencia de Usuario: Principios y Métodos* (Hassan Montero) y Fase 2
> de la *Guía práctica de Arquitectura de Información para aplicaciones
> multimedia educativas* (Arencibia Cobas et al.).

## Contenidos visuales / gráficos (a coordinar con el diseñador)

> Pendiente. Esta lista se completará en función de lo que defina el diseñador
> en la sección 2 de la entrega (Modelos de Diseño). Los candidatos a assets
> que el chat necesitaría, a confirmar:
>
> - Logo / isotipo / isologo del proyecto (cabecera).
> - Avatar del asistente (opcional, área de conversación).
> - Ilustración o ícono para el estado de "pensando / cargando".
> - Paleta de colores (reemplaza el azul actual `#0f4c81`).
> - Tipografía (reemplaza la `system-ui` actual).
