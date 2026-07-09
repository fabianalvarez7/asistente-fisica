# Capa Socrática del Asistente

**Para**: Nair (Física 1, UNR Bioquímica y Farmacia)
**De**: Fabián
**Fecha**: 9 de julio de 2026
**Asunto**: Estado de la capa Socrática — feedback solicitado

## Qué construimos

Una capa de prompt sobre el RAG del asistente que transforma las respuestas en guía socrática. El asistente guía con preguntas, nunca da la solución completa ni el resultado numérico final. Sigue una escala de pistas progresiva (3 niveles: conceptual → específica → máxima), responde SOLO desde el contexto de los apuntes indexados, y mantiene un tono en voseo rioplatense, claro y didáctico. Cada respuesta termina con una pregunta guía.

## Validación — 26 queries de prueba

Cubrimos 3 tipos de escenarios: 10 Socráticos (ejercicios típicos, estudiante trabado, «dame la respuesta», respuesta correcta/incorrecta, unidades mal), 8 de regresión (in-corpus con LaTeX, off-topic, meta-preguntas, saludos), y 8 edge cases (off-topic extremos, «dame la respuesta» insistente, conceptos erróneos, pregunta en inglés).

**Resultado: 24/26 PASS, 1 deferido, 1 cosmético. 92 % de pass rate.**

## Lo que funciona bien

- Estudiante trabado («No entiendo nada») → empieza con pista conceptual, no salta a la respuesta.
- Estudiante que pide la respuesta directo → reconoce frustración, da pista máxima, cierra con pregunta guía.
- Estudiante que propone respuesta correcta → valida sin confirmar, guía al próximo paso.
- Off-topic («torta de chocolate», «capital de Francia») → refusal exacto.
- Pregunta en inglés → respuesta en español con LaTeX.

## Decisiones que tomamos

1. **Corpus limitado a teoría de errores por ahora.** Cinemática, dinámica y energía NO están indexados. El asistente correctamente se niega a responder sobre esos temas. Si querés ampliar, sumamos los PDFs.

2. **Saludos sin contenido de Física 1.** Probamos que el asistente responda «Hola, ¿en qué te ayudo?» en vez de un refusal. Lo revertimos porque esa regla debilitó la prioridad de RAG-only (el modelo empezó a inventar respuestas sobre temas no indexados). Decisión actual: saludo puro devuelve el refusal. Si te parece importante, podemos hacerlo en una capa previa al prompt (pre-procesamiento) sin afectar RAG-only.

3. **Punto final del refusal.** El modelo a veces omite el punto. Cosmético, no urgente.

## Lo que necesito de vos

1. ¿El comportamiento Socrático es el que imaginabas? (la pista progresiva, el voseo, «cada respuesta termina con pregunta guía»).
2. ¿El manejo de errores conceptuales (unidades mal, conceptos erróneos) es el adecuado?
3. ¿Sumamos más PDFs al corpus (cinemática, dinámica, energía) para que la capa cubra más temas?
4. ¿Querés que el saludo se maneje de otra forma?

## Demo en vivo

Está deployado en Hugging Face Spaces. Podés probarlo en:

**https://huggingface.co/spaces/fabianalvarez7/asistente-fisica-unr**

*(abrir desde el navegador; el primer load puede tardar 30-50 s por el cold-start del tier gratuito)*

**Sugerencia**: arrancá con queries de teoría de errores (error absoluto, relativo, porcentual, propagación) que muestran muy bien el comportamiento Socrático. También podés probar: «No entiendo nada, ayudame», «Dame la respuesta», y comparar con off-topic como «¿Cómo hago una torta?» para ver el refusal.
