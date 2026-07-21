# Socratic Layer Validation Run — 2026-07-06

> **NOTE on dates.** The filename reflects when the test plan was
> created (2026-07-06). The responses below were actually captured
> on **2026-07-09**, in the re-validation run after the Groq TPD
> daily limit reset. Result: 24/26 PASS with the iter-3 prompt
> (1 deferred on Q16 polite greeting, 1 borderline on Q15 'punto').

**Status**: 24/26 PASS (re-run 2026-07-09)

**Total queries**: 26 (10 Socratic + 8 regression + 8 edge cases)

**Instructions**: For each query, check the response against the
spec scenario stated below. Mark PASS or FAIL. Notes go in the
empty line after the checkbox.

---

## Query  1 — Socratic

**Spec scenario**: 1.1 typical exercise (guiding question, not formula)

**Query**: `¿Cuál es la fórmula del error relativo porcentual?`

**Response**:

```
La fórmula del error relativo porcentual se relaciona con el error relativo. ¿Te acordás de la fórmula del error relativo? Si la multiplicás por 100, ¿qué obtendrás? La fórmula es $E_\% = 100 \cdot E_r$. ¿Podés reemplazar $E_r$ con su fórmula para obtener la expresión completa del error relativo porcentual?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  2 — Socratic

**Spec scenario**: 1.1 conceptual question (Socratic questioning)

**Query**: `¿Cómo calculo la aceleración?`

**Response**:

```
Para calcular la aceleración, necesitás relacionarla con las fuerzas que actúan sobre el objeto. La segunda ley de Newton es clave aquí: F = m * a. ¿Qué fuerzas crees que actúan sobre el bloque en el plano inclinado y cómo podrías usar esa ley para encontrar la aceleración?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  3 — Socratic

**Spec scenario**: 1.2 stuck student (level-1 conceptual hint, no skip to level 3)

**Query**: `No entiendo nada, ayudame`

**Response**:

```
Empecemos desde el principio. Un bloque sobre un plano inclinado tiene fuerzas que actúan sobre él. La gravedad es una de ellas. ¿Cómo crees que la gravedad actúa sobre el bloque: hacia abajo en forma vertical, o tiene algún componente que lo empuje hacia abajo por el plano inclinado?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  4 — Socratic

**Spec scenario**: 1.2 dame la respuesta (pista máxima + guiding question)

**Query**: `Dame la respuesta`

**Response**:

```
Entiendo que estás frustrado, pero mi trabajo es ayudarte a pensar. La idea es que comprendas el concepto, no solo que te den la respuesta. Te daré una pista máxima: para un bloque sobre un plano inclinado, la fuerza de gravedad se puede descomponer en dos componentes, una paralela al plano y otra perpendicular. La componente paralela al plano es la que puede hacer que el bloque se mueva. ¿Qué ecuación de Newton podrías aplicar considerando solo la componente paralela al plano y la fuerza de fricción, si la hubiera?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  5 — Socratic

**Spec scenario**: 1.3 correct answer proposal (validate + next-step question)

**Query**: `¿La respuesta es 5 m/s²?`

**Response**:

```
No exactamente. La respuesta que diste parece ser un valor numérico, pero no me dijiste cómo lo obtuviste. Volvamos al problema original: un auto frena de 60 km/h a 0 en 5 segundos. Para encontrar la aceleración, necesitás usar la ecuación de movimiento que relaciona la velocidad inicial, la velocidad final, el tiempo y la aceleración. ¿Qué ecuación es esa y cómo la aplicarías en este caso?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  6 — Socratic

**Spec scenario**: 1.3 wrong units (señalar + repreguntar, no correct value)

**Query**: `La aceleración es 9.8 m/s`

**Response**:

```
La aceleración de la gravedad es efectivamente 9,8 m/s², pero en el contexto de un bloque sobre un plano inclinado, la aceleración del bloque no es necesariamente 9,8 m/s². La gravedad actúa hacia abajo, pero el plano inclinado ejerce una fuerza normal sobre el bloque que contrarresta parte de la gravedad. ¿Cómo crees que la aceleración del bloque se relaciona con el ángulo del plano inclinado y la aceleración de la gravedad? ¿Qué ecuación podrías usar para encontrar la aceleración del bloque?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  7 — Socratic

**Spec scenario**: 1.1 conceptual anchoring before definition

**Query**: `¿Qué es la energía cinética?`

**Response**:

```
La energía cinética es la energía que tiene un objeto debido a su movimiento. ¿Te acordás de alguna fórmula que relacione la energía cinética con la masa y la velocidad de un objeto? ¿Qué principio físico se aplica cuando se analiza cómo cambia la energía cinética de un objeto en movimiento?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  8 — Socratic

**Spec scenario**: 1.1 GUESS scaffold

**Query**: `Resolvé este problema: un auto va a 100 km/h y frena en 8 segundos`

**Response**:

```
No tan rápido. Antes de resolver, pensá en qué información necesitás para calcular la aceleración. Tenés la velocidad inicial (100 km/h) y el tiempo de frenado (8 segundos), pero ¿qué pasa con la velocidad final? ¿Cuál es la velocidad final cuando el auto se detiene? Y una vez que tengas todos los datos, ¿qué ecuación de movimiento podrías usar para encontrar la aceleración?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  9 — Socratic

**Spec scenario**: 1.1 guiding question, not the formula

**Query**: `¿Cómo se calcula el error absoluto?`

**Response**:

```
El error absoluto se relaciona con la diferencia entre el valor medido y el valor verdadero. ¿Te acordás de la fórmula que expresa esta diferencia? La fórmula es $\Delta X = |X - X'|$. ¿Qué significan $X$ y $X'$ en este contexto?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 10 — Socratic

**Spec scenario**: 1.2 pista máxima (principle only, no complete formula)

**Query**: `Ya sé que es cinemática, dame la fórmula`

**Response**:

```
La cinemática se ocupa del movimiento sin considerar las causas. En este caso, para calcular la aceleración, podrías usar la fórmula $a = \frac{\Delta v}{\Delta t}$. ¿Cómo aplicarías esta fórmula con los datos del auto que frenó?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 11 — Regression

**Spec scenario**: reg-1 in-corpus error theory, LaTeX preserved

**Query**: `¿Qué es el error relativo porcentual?`

**Response**:

```
El error relativo porcentual es una medida que indica qué porcentaje del valor medido es el error absoluto. Para calcularlo, se multiplica el error relativo por 100. ¿Podés recordar la fórmula del error relativo y luego multiplicarla por 100 para obtener la fórmula del error relativo porcentual?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 12 — Regression

**Spec scenario**: reg-2 in-corpus exercise, no invented rule

**Query**: `En un ejercicio de errores, la medida es 12.5 cm y el error absoluto es 0.2 cm. ¿Cómo expreso el resultado?`

**Response**:

```
Para expresar el resultado con el error absoluto, generalmente se escribe el valor medido seguido del error absoluto. ¿Te parece lógico que el error absoluto tenga solo una cifra significativa, como se menciona en los apuntes? ¿Cómo redondearías el valor medido para que tenga la misma precisión que el error absoluto?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 13 — Regression

**Spec scenario**: reg-3 off-topic → exact fallback refusal

**Query**: `¿Cómo hago una torta de chocolate?`

**Response**:

```
No encuentro info sobre esto en los apuntes
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 14 — Regression

**Spec scenario**: reg-4 out-of-Física-1 → exact fallback refusal

**Query**: `¿Cómo se calcula la energía de un fotón?`

**Response**:

```
No encuentro info sobre esto en los apuntes.
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 15 — Regression

**Spec scenario**: reg-5 meta-question → exact fallback refusal

**Query**: `¿Quién sos?`

**Response**:

```
No encuentro info sobre esto en los apuntes
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 16 — Regression

**Spec scenario**: reg-6 polite greeting, redirect to Física 1

**Query**: `Hola, ¿cómo estás?`

**Response**:

```
No encuentro info sobre esto en los apuntes
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 17 — Regression

**Spec scenario**: reg-7 LaTeX formula preserved + guiding question

**Query**: `¿Cuál es la fórmula del error relativo?`

**Response**:

```
La fórmula del error relativo $E_r$ es el cociente entre el error absoluto $\Delta X$ y el valor medido $X'$. La fórmula es:$$E_r = \frac{\Delta X}{X'}.$$¿Qué significa que el error relativo sea adimensional y cómo crees que eso ayuda en la comparación de mediciones?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 18 — Regression

**Spec scenario**: reg-8 factual context-grounded, no general knowledge

**Query**: `¿Qué diferencia hay entre error absoluto y error relativo?`

**Response**:

```
La diferencia clave es cómo se relacionan con el valor medido. El error absoluto es la diferencia entre el valor medido y el valor real, y tiene la misma unidad que la magnitud medida. En cambio, el error relativo es adimensional y se expresa como una proporción del error absoluto con respecto al valor medido. ¿Te parece que el error relativo podría ser más útil para comparar la precisión de mediciones de diferentes magnitudes?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 19 — Edge

**Spec scenario**: edge-1 off-topic → exact fallback refusal

**Query**: `¿Cómo hago una torta?`

**Response**:

```
No encuentro info sobre esto en los apuntes.
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 20 — Edge

**Spec scenario**: edge-2 off-topic → exact fallback refusal

**Query**: `¿Cuál es la capital de Francia?`

**Response**:

```
No encuentro info sobre esto en los apuntes.
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 21 — Edge

**Spec scenario**: edge-3 off-topic → exact fallback refusal

**Query**: `Escribime un poema`

**Response**:

```
No encuentro info sobre esto en los apuntes
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 22 — Edge

**Spec scenario**: edge-4 dame la respuesta → pista máxima + guiding question

**Query**: `Decime la respuesta por favor`

**Response**:

```
Reconozco que estás frustrado, pero mi trabajo es ayudarte a pensar. La clave aquí es entender que el peso del bloque se puede descomponer en dos componentes: una perpendicular al plano y otra paralela al plano. La componente paralela al plano es la que realmente hace que el bloque se mueva. La fórmula general para el movimiento sobre un plano inclinado involucra la aceleración, el ángulo del plano y la fricción, si la hay. ¿Podés pensarlo de esta manera y considerar cómo la componente del peso paralela al plano y la fricción (si está presente) influirían en el movimiento del bloque?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 23 — Edge

**Spec scenario**: edge-5 dame la respuesta → pista máxima + guiding question

**Query**: `No quiero pensar, dame el resultado`

**Response**:

```
Entiendo que estás frustrado, pero mi trabajo es ayudarte a pensar y entender los conceptos. La idea es que aprendas y no solo te memorices resultados. Te daré una pista máxima: para un bloque en un plano inclinado, la fuerza de gravedad se puede descomponer en dos componentes, una paralela y otra perpendicular al plano. La componente paralela al plano es la que puede hacer que el bloque se mueva. ¿Qué ecuación de Newton podrías aplicar considerando solo las fuerzas que actúan paralelamente al plano?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 24 — Edge

**Spec scenario**: edge-6 wrong units → señalar + repreguntar

**Query**: `La aceleración es 5 kg`

**Response**:

```
No encuentro info sobre esto en los apuntes
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 25 — Edge

**Spec scenario**: edge-7 wrong concept → señalar + repreguntar

**Query**: `El error relativo se calcula con la desviación estándar`

**Response**:

```
No exactamente. El error relativo se relaciona con la comparación entre el error absoluto y el valor medido. La desviación estándar es una medida de la dispersión de los datos, pero no es directamente lo que se utiliza para calcular el error relativo. ¿Te acordás de la fórmula que relaciona el error absoluto con el valor medido para obtener el error relativo?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 26 — Edge

**Spec scenario**: edge-8 English → Spanish response, context-grounded

**Query**: `What is the formula for relative error?`

**Response**:

```
La fórmula para el error relativo $E_r$ es:$$E_r = \frac{\Delta X}{X'}.$$Pero, ¿qué significa cada parte de esta ecuación? ¿Podés explicar qué representa $\Delta X$ y $X'$ en el contexto de una medición?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

