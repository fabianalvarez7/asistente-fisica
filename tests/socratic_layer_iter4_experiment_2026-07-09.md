# Socratic Layer Validation Run — 2026-07-09

**Status**: pending review

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
El error relativo porcentual se relaciona con el error relativo. ¿Te acordás de la fórmula del error relativo $E_r$? Es $E_r = \frac{\Delta X}{X'}$. Para obtener el error porcentual, ¿qué operación crees que se debería aplicar sobre $E_r$ para expresarlo como porcentaje?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  2 — Socratic

**Spec scenario**: 1.1 conceptual question (Socratic questioning)

**Query**: `¿Cómo calculo la aceleración?`

**Response**:

```
Para calcular la aceleración, necesitás relacionarla con las fuerzas que actúan sobre el objeto y su masa. ¿Te acordás de la segunda ley de Newton? ¿Cómo se relaciona la fuerza neta con la aceleración y la masa de un objeto? La fórmula es bastante directa... ¿la recordás?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  3 — Socratic

**Spec scenario**: 1.2 stuck student (level-1 conceptual hint, no skip to level 3)

**Query**: `No entiendo nada, ayudame`

**Response**:

```
Empecemos desde el principio. Un bloque sobre un plano inclinado tiene fuerzas que actúan sobre él. La gravedad es una de ellas. ¿En qué dirección actúa la fuerza de gravedad sobre el bloque? ¿Y qué pasa con la normal, la fuerza que ejerce el plano sobre el bloque? ¿En qué dirección actúa?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  4 — Socratic

**Spec scenario**: 1.2 dame la respuesta (pista máxima + guiding question)

**Query**: `Dame la respuesta`

**Response**:

```
Entiendo que estás frustrado, pero mi trabajo es ayudarte a pensar. La respuesta directa no te ayudaría a entender el concepto. Te daré una pista máxima: para un bloque en un plano inclinado, la fuerza de gravedad se puede descomponer en dos componentes, una paralela al plano y otra perpendicular. La componente paralela al plano es la que hace que el bloque se mueva. ¿Podés pensar en cómo aplicar la segunda ley de Newton considerando solo la componente paralela al plano? ¿Qué fuerzas actúan en esa dirección?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  5 — Socratic

**Spec scenario**: 1.3 correct answer proposal (validate + next-step question)

**Query**: `¿La respuesta es 5 m/s²?`

**Response**:

```
Antes de confirmar, revisemos el cálculo. La fórmula para la aceleración cuando se conoce la velocidad inicial, la velocidad final y el tiempo es \(a = \frac{v_f - v_i}{t}\). En este caso, \(v_i = 60\) km/h, \(v_f = 0\) km/h y \(t = 5\) segundos. Pero, ¿estás seguro de que las unidades son consistentes? ¿Qué pasa si convertís la velocidad de km/h a m/s antes de calcular? ¿Cuál sería el resultado entonces?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  6 — Socratic

**Spec scenario**: 1.3 wrong units (señalar + repreguntar, no correct value)

**Query**: `La aceleración es 9.8 m/s`

**Response**:

```
No exactamente. La aceleración de la gravedad es 9.8 m/s², pero en el caso de un bloque sobre un plano inclinado, la aceleración del bloque no es necesariamente 9.8 m/s². Dependiendo del ángulo del plano, la componente de la gravedad que actúa paralela al plano es distinta. ¿Qué ecuación usarías para encontrar la aceleración del bloque en función del ángulo del plano inclinado?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  7 — Socratic

**Spec scenario**: 1.1 conceptual anchoring before definition

**Query**: `¿Qué es la energía cinética?`

**Response**:

```
La energía cinética es la energía que tiene un objeto debido a su movimiento. ¿Te acordás de alguna fórmula que relacione la energía cinética con la masa y la velocidad de un objeto? ¿Qué principio físico se aplica cuando se considera cómo cambia la energía cinética de un objeto?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  8 — Socratic

**Spec scenario**: 1.1 GUESS scaffold

**Query**: `Resolvé este problema: un auto va a 100 km/h y frena en 8 segundos`

**Response**:

```
No tan rápido. Antes de resolver, pensá: ¿qué información nos dan y qué queremos encontrar? Nos dan la velocidad inicial (100 km/h) y el tiempo de frenado (8 segundos), y queremos encontrar la aceleración. ¿Qué ecuación de cinemática podrías usar para relacionar esas variables? ¿Y no olvides convertir las unidades adecuadamente antes de calcular. ¿Cuál crees que sería el primer paso para resolver este problema?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  9 — Socratic

**Spec scenario**: 1.1 guiding question, not the formula

**Query**: `¿Cómo se calcula el error absoluto?`

**Response**:

```
El error absoluto se relaciona con la diferencia entre el valor medido y el valor verdadero. ¿Te acordás de la fórmula que expresa esta diferencia? La fórmula del error absoluto es $\Delta X = |X - X'|$. ¿Qué significan $X$ y $X'$ en esta ecuación?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 10 — Socratic

**Spec scenario**: 1.2 pista máxima (principle only, no complete formula)

**Query**: `Ya sé que es cinemática, dame la fórmula`

**Response**:

```
La cinemática se ocupa del movimiento de los objetos sin considerar las causas del mismo. En este caso, para encontrar la aceleración, podés usar la fórmula que relaciona la velocidad inicial, la velocidad final y el tiempo. ¿Te acordás de la fórmula que tiene la forma $a = \frac{\Delta v}{\Delta t}$? ¿O quizás otra que involucre esas variables? ¿Cómo la aplicarías a este problema?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 11 — Regression

**Spec scenario**: reg-1 in-corpus error theory, LaTeX preserved

**Query**: `¿Qué es el error relativo porcentual?`

**Response**:

```
El error relativo porcentual es una medida que indica qué porcentaje del valor medido es el error absoluto. Para calcularlo, se utiliza el error relativo y se multiplica por 100. ¿Te acordás de la fórmula del error relativo? ¿Cómo crees que se relaciona con el error relativo porcentual?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 12 — Regression

**Spec scenario**: reg-2 in-corpus exercise, no invented rule

**Query**: `En un ejercicio de errores, la medida es 12.5 cm y el error absoluto es 0.2 cm. ¿Cómo expreso el resultado?`

**Response**:

```
Para expresar el resultado con el error, pensá que el error absoluto debe tener una única cifra significativa. ¿Cuántas cifras significativas tiene la medida de 12.5 cm? ¿Y cómo deberías redondear el error absoluto para que tenga solo una cifra significativa?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 13 — Regression

**Spec scenario**: reg-3 off-topic → exact fallback refusal

**Query**: `¿Cómo hago una torta de chocolate?`

**Response**:

```
No encuentro info sobre esto en los apuntes.
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
Hola, estoy bien, gracias. ¿En qué tema de Física 1 necesitás ayuda? ¿Querés hablar de cinemática, dinámica, energía o algo más? Estoy acá para ayudarte. ¿Qué te trae por aquí hoy?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 17 — Regression

**Spec scenario**: reg-7 LaTeX formula preserved + guiding question

**Query**: `¿Cuál es la fórmula del error relativo?`

**Response**:

```
La fórmula del error relativo $E_r$ es el cociente entre el error absoluto $\Delta X$ y el valor medido $X'$. ¿Podés escribirla en forma de ecuación? ¿Y qué significa que sea adimensional?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 18 — Regression

**Spec scenario**: reg-8 factual context-grounded, no general knowledge

**Query**: `¿Qué diferencia hay entre error absoluto y error relativo?`

**Response**:

```
Excelente pregunta. El error absoluto se refiere a la diferencia entre el valor medido y el valor real, pero no nos da una idea de cuán significativo es ese error. El error relativo, por otro lado, nos permite comparar el error absoluto con el valor medido. ¿Qué tipo de operación crees que se necesita para calcular el error relativo, considerando que es adimensional? ¿Te viene a la mente alguna fórmula que involucre una división?
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
No encuentro info sobre esto en los apuntes
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
Reconozco que estás frustrado, pero mi trabajo es ayudarte a pensar. La clave para resolver problemas de física está en entender los conceptos y aplicarlos paso a paso. Te daré una pista máxima: para un bloque sobre un plano inclinado, la fuerza de gravedad se puede descomponer en dos componentes, una paralela y otra perpendicular al plano. La componente paralela al plano es la que puede hacer que el bloque se mueva. ¿Qué ecuación de Newton podrías aplicar considerando solo las fuerzas que actúan paralelamente al plano?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 23 — Edge

**Spec scenario**: edge-5 dame la respuesta → pista máxima + guiding question

**Query**: `No quiero pensar, dame el resultado`

**Response**:

```
Entiendo que estás frustrado, pero mi trabajo es ayudarte a pensar y entender los conceptos. La fórmula para la aceleración de un objeto bajo una fuerza constante es $a = \frac{F_{net}}{m}$. Si aplicamos esto a un bloque en un plano inclinado, debemos considerar las fuerzas que actúan sobre él. ¿Podés intentar identificar la fuerza neta que actúa sobre el bloque en el plano inclinado?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 24 — Edge

**Spec scenario**: edge-6 wrong units → señalar + repreguntar

**Query**: `La aceleración es 5 kg`

**Response**:

```
No encuentro info sobre esto en los apuntes.
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 25 — Edge

**Spec scenario**: edge-7 wrong concept → señalar + repreguntar

**Query**: `El error relativo se calcula con la desviación estándar`

**Response**:

```
ERROR: Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_***` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99334, Requested 2087. Please try again in 20m27.744s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 26 — Edge

**Spec scenario**: edge-8 English → Spanish response, context-grounded

**Query**: `What is the formula for relative error?`

**Response**:

```
ERROR: Error code: 429 - {'error': {'message': 'Rate limit reached for model `llama-3.3-70b-versatile` in organization `org_***` service tier `on_demand` on tokens per day (TPD): Limit 100000, Used 99334, Requested 2106. Please try again in 20m44.159999999s. Need more tokens? Upgrade to Dev Tier today at https://console.groq.com/settings/billing', 'type': 'tokens', 'code': 'rate_limit_exceeded'}}
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

