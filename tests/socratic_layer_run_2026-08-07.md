# Socratic Layer Validation Run — 2026-08-07

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
La fórmula del error relativo porcentual se relaciona con el error relativo. ¿Te acordás de la fórmula del error relativo? Es algo así como el error absoluto dividido por el valor medido. Para pasar al error porcentual, ¿qué operación crees que se debería aplicar sobre el error relativo?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  2 — Socratic

**Spec scenario**: 1.1 conceptual question (Socratic questioning)

**Query**: `¿Cómo calculo la aceleración?`

**Response**:

```
La aceleración se puede calcular si conocés la fuerza neta que actúa sobre un objeto y su masa. ¿Te acordás de la segunda ley de Newton? ¿Cómo se relaciona la fuerza neta con la masa y la aceleración en esa ley?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  3 — Socratic

**Spec scenario**: 1.2 stuck student (level-1 conceptual hint, no skip to level 3)

**Query**: `No entiendo nada, ayudame`

**Response**:

```
Empecemos desde el principio. Un bloque sobre un plano inclinado está sometido a la gravedad, que es una fuerza que actúa hacia abajo. ¿Cómo crees que podrías descomponer esta fuerza en dos componentes: una paralela al plano inclinado y otra perpendicular a él? ¿Qué principios de física podrían ayudarte a entender cómo se mueve el bloque en este escenario?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  4 — Socratic

**Spec scenario**: 1.2 dame la respuesta (pista máxima + guiding question)

**Query**: `Dame la respuesta`

**Response**:

```
Entiendo que estás frustrado, pero mi trabajo es ayudarte a pensar. La clave para resolver problemas de un bloque sobre un plano inclinado está en descomponer las fuerzas que actúan sobre el bloque, especialmente el peso, en componentes paralelas y perpendiculares al plano. Dada la frustración, te doy una pista máxima: la fuerza neta que actúa sobre el bloque en la dirección paralela al plano es lo que determina su aceleración. ¿Qué fuerzas contribuirían a esta fuerza neta y cómo podrías calcular la aceleración del bloque usando la segunda ley de Newton?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  5 — Socratic

**Spec scenario**: 1.3 correct answer proposal (validate + next-step question)

**Query**: `¿La respuesta es 5 m/s²?`

**Response**:

```
No tan rápido. Antes de confirmar si la respuesta es correcta o no, revisemos el cálculo. La fórmula para la aceleración cuando conocemos la velocidad inicial, la velocidad final y el tiempo es $a = \frac{v_f - v_i}{t}$. ¿Podés aplicar esta fórmula con los valores del problema: $v_i = 60$ km/h, $v_f = 0$ km/h y $t = 5$ s, teniendo en cuenta que debes convertir las velocidades a m/s antes de calcular?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  6 — Socratic

**Spec scenario**: 1.3 wrong units (señalar + repreguntar, no correct value)

**Query**: `La aceleración es 9.8 m/s`

**Response**:

```
No encuentro info sobre esto en los apuntes.
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  7 — Socratic

**Spec scenario**: 1.1 conceptual anchoring before definition

**Query**: `¿Qué es la energía cinética?`

**Response**:

```
La energía cinética está relacionada con el movimiento de un objeto. ¿Te acordás de qué factores influyen en la cantidad de energía cinética que tiene un objeto en movimiento? ¿Hay alguna fórmula que relacione la energía cinética con la masa y la velocidad del objeto?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  8 — Socratic

**Spec scenario**: 1.1 GUESS scaffold

**Query**: `Resolvé este problema: un auto va a 100 km/h y frena en 8 segundos`

**Response**:

```
No encuentro info sobre esto en los apuntes.
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query  9 — Socratic

**Spec scenario**: 1.1 guiding question, not the formula

**Query**: `¿Cómo se calcula el error absoluto?`

**Response**:

```
El error absoluto se relaciona con la diferencia entre el valor medido y el valor verdadero. ¿Te acordás de la fórmula que expresa esta diferencia? Tiene algo que ver con el valor absoluto de la resta entre el valor verdadero y el medido. ¿Podés recordarla o necesitás una pista?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 10 — Socratic

**Spec scenario**: 1.2 pista máxima (principle only, no complete formula)

**Query**: `Ya sé que es cinemática, dame la fórmula`

**Response**:

```
La cinemática se ocupa del movimiento sin considerar las causas. En este caso, la fórmula que podrías necesitar es $v_f = v_i + at$, que relaciona la velocidad final $v_f$, la velocidad inicial $v_i$, la aceleración $a$ y el tiempo $t$. ¿Cómo crees que podrías aplicar esta fórmula al problema del auto que frena?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 11 — Regression

**Spec scenario**: reg-1 in-corpus error theory, LaTeX preserved

**Query**: `¿Qué es el error relativo porcentual?`

**Response**:

```
El error relativo porcentual es una medida que compara el error absoluto con el valor medido, pero expresado como un porcentaje. ¿Te acordás de la fórmula del error relativo? Si la multiplicás por 100, ¿qué obtendrías?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 12 — Regression

**Spec scenario**: reg-2 in-corpus exercise, no invented rule

**Query**: `En un ejercicio de errores, la medida es 12.5 cm y el error absoluto es 0.2 cm. ¿Cómo expreso el resultado?`

**Response**:

```
Para expresar el resultado con el error, recordá que el error absoluto se suma y resta del valor medido. ¿Cómo escribirías el valor medido con su error absoluto, siguiendo el formato que vimos antes, como $A = A' \pm \Delta A$?
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
La fórmula del error relativo es una relación entre el error absoluto y el valor medido. ¿Te acordás de que el error relativo es adimensional y se utiliza para comparar la precisión de mediciones? La fórmula es $E_r = \frac{\Delta X}{X'}$. ¿Qué significa cada parte de esta ecuación en el contexto de una medición?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 18 — Regression

**Spec scenario**: reg-8 factual context-grounded, no general knowledge

**Query**: `¿Qué diferencia hay entre error absoluto y error relativo?`

**Response**:

```
Excelente pregunta. El error absoluto se refiere a la diferencia entre el valor medido y el valor real, pero no nos da una idea de cuán significativo es ese error. El error relativo, por otro lado, nos permite comparar el error absoluto con el valor medido. ¿Qué tipo de operación matemática podrías hacer entre el error absoluto y el valor medido para obtener una medida adimensional que nos dé una idea de la precisión de la medición?
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
Entiendo que estás un poco frustrado, pero mi trabajo es ayudarte a pensar. Te daré una pista máxima: para un bloque en un plano inclinado, la fuerza de gravedad se puede descomponer en dos componentes, una paralela al plano y otra perpendicular. La componente paralela al plano es la que hace que el bloque se mueva. ¿Qué ecuación de Newton podrías aplicar considerando solo las fuerzas que actúan a lo largo del plano inclinado?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 23 — Edge

**Spec scenario**: edge-5 dame la respuesta → pista máxima + guiding question

**Query**: `No quiero pensar, dame el resultado`

**Response**:

```
Entiendo que estás frustrado, pero mi trabajo es ayudarte a pensar y entender los conceptos. La idea es que llegues a la solución por ti mismo. Te daré una pista máxima: para un bloque en un plano inclinado, la fuerza de gravedad se puede descomponer en dos componentes, una paralela y otra perpendicular al plano. La componente paralela al plano es la que hace que el bloque se mueva. ¿Qué ecuación de Newton podrías aplicar considerando solo las fuerzas que actúan paralelamente al plano?
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
No exactamente. El error relativo se relaciona con el error absoluto y el valor medido, no directamente con la desviación estándar. La fórmula del error relativo es $E_r = \frac{\Delta X}{X'}$. ¿Qué es $\Delta X$ y $X'$ en este contexto? ¿Y cómo se relaciona esto con la idea de comparar la precisión de una medición?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

## Query 26 — Edge

**Spec scenario**: edge-8 English → Spanish response, context-grounded

**Query**: `What is the formula for relative error?`

**Response**:

```
Vamos a ver... El error relativo es una forma de medir la precisión de una medición comparando el error absoluto con el valor medido. ¿Te acordás de la fórmula que relaciona el error absoluto con el valor medido para obtener el error relativo? Tiene algo que ver con una división... ¿Podrías intentar recordarla o pensar en cómo se relacionan esas dos cantidades?
```

**Pass/Fail**: [ ] PASS  [ ] FAIL

**Notes**:


---

