---
title: Asistente de Física — Dashboard
emoji: 📊
sdk: docker
app_port: 8501
---

# Asistente de Física — Dashboard para profesores (v1)

Panel de métricas anonimizadas para que el equipo docente vea qué contenidos necesitan más refuerzo.

## Qué muestra

- KPIs: total de consultas, estudiantes únicos y última actividad.
- Top 20 de consultas más frecuentes agrupadas por texto exacto.
- Distribución aproximada de consultas por unidad temática.
- Últimas 10 consultas recibidas.

> **Anonimato**: el dashboard nunca muestra `student_id`, `display_name` ni ningún dato que permita identificar a un estudiante. Los agregados se cuentan por contenido exacto de la consulta.

## Deploy

Este Space usa Docker. El contenedor corre Streamlit en el puerto `8501`.

Requiere las variables de entorno:

- `TURSO_DATABASE_URL`
- `TURSO_AUTH_TOKEN`

Configuralas como **Space Secrets** en Hugging Face antes de arrancar.

## Estructura

```
dashboard/
├── app.py       # UI de Streamlit
├── queries.py   # Agregados puros, sin UI
└── Dockerfile   # Imagen del dashboard
```

El dashboard no necesita el modelo de embeddings ni ChromaDB; solo lee de Turso.
