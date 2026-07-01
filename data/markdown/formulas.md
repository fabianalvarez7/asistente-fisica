# Fórmulas de Teoría de Errores

> Suplemento manual al cuadernillo de Física 1. Cada fórmula está escrita en
> LaTeX y se incluye una breve explicación en español para que el asistente
> pueda recuperar la fórmula cuando el estudiante la pida. Editar este archivo
> es la forma soportada de cubrir fórmulas que el PDF loader no extrae como
> texto (típicamente fórmulas embebidas como imágenes).
>
> **Mantenimiento**: cuando Nair confirme que la lista está completa, mover
> este set a un ADR (`docs/adr/0003-formulas-suplemento.md`) para dejar
> registro de qué se decidió cubrir a mano y por qué.

## Error absoluto

El **error absoluto** $\Delta X$ es la diferencia entre el valor medido $X'$ y
el valor de referencia (o valor verdadero) $X$:

$$\Delta X = |X - X'|.$$

Tiene la misma unidad que la magnitud medida. Caracteriza la **exactitud**
de una medición individual pero no su precisión relativa: equivocarse en
$\Delta X = 1\text{ cm}$ es muy distinto si mediste $1\text{ m}$ que si
mediste $1\text{ km}$.

## Error relativo

El **error relativo** $E_r$ es el cociente entre el error absoluto y el valor
medido. Es **adimensional** y permite comparar la precisión de mediciones de
distintas magnitudes o escalas:

$$E_r = \frac{\Delta X}{X'}.$$

Por ejemplo, $E_r = 0{,}01$ significa que el error absoluto es el $1\%$ del
valor medido, sin importar las unidades.

## Error porcentual

El **error porcentual** $E_\%$ es el error relativo multiplicado por cien. Es
la forma más habitual de reportar precisión en contextos aplicados (laboratorio,
especificaciones técnicas):

$$E_\% = 100 \cdot E_r = 100 \cdot \frac{\Delta X}{X'}.$$

## Propagación de errores: suma y resta

Si $Z = X \pm Y$ y los errores de $X$ e $Y$ son **independientes**, el error
absoluto de $Z$ se propaga en cuadratura:

$$\Delta Z = \sqrt{(\Delta X)^2 + (\Delta Y)^2}.$$

Notar que el error de la suma/resta se acumula siempre en cuadratura, no en
forma lineal: $\Delta Z$ nunca es menor que el mayor de $\Delta X$ o $\Delta Y$.

## Propagación de errores: producto y cociente

Si $Z = X \cdot Y$ o $Z = X / Y$ con errores independientes, lo que se propaga
en cuadratura es el **error relativo**, no el absoluto:

$$\frac{\Delta Z}{|Z|} = \sqrt{\left(\frac{\Delta X}{X}\right)^2 + \left(\frac{\Delta Y}{Y}\right)^2}.$$

Por eso en productos y cocientes la precisión se expresa siempre en términos
relativos o porcentuales, no absolutos.

## Valor medio

Dada una serie de $n$ mediciones $X_1, X_2, \ldots, X_n$ de la misma magnitud
y en las mismas condiciones, el **valor medio** (o promedio) es el mejor
estimador del valor verdadero:

$$\bar{X} = \frac{1}{n} \sum_{i=1}^{n} X_i.$$

## Desviación estándar de la media

La **desviación estándar de la media** $\sigma_{\bar{X}}$ cuantifica cuánto
se apartan, en promedio, las mediciones individuales del valor medio. Se
reduce con la raíz de $n$, por eso medir más veces mejora la precisión
(pero cada vez menos):

$$\sigma_{\bar{X}} = \frac{\sigma}{\sqrt{n}}, \quad \text{donde} \quad \sigma = \sqrt{\frac{1}{n-1} \sum_{i=1}^{n} (X_i - \bar{X})^2}.$$

El factor $n-1$ (en lugar de $n$) se llama corrección de Bessel y refleja
que usamos $\bar{X}$ (calculado a partir de los datos) en lugar del valor
verdadero desconocido.

## Cifras significativas

El número de **cifras significativas** de una medición son todos los dígitos
que se conocen con certeza **más uno estimado** (el último, que es incierto
por el error absoluto). Reglas prácticas:

- **Ceros a la izquierda** no son significativos: $0{,}0042$ tiene 2 cifras
  significativas.
- **Ceros entre dígitos no nulos** sí son significativos: $4002$ tiene 4
  cifras significativas.
- **Ceros a la derecha** son significativos solo si hay punto decimal:
  $4200$ es ambiguo (¿2 o 4 cifras?), mejor escribir $4{,}2 \times 10^3$ o
  $4{,}200 \times 10^3$.

## Notación científica

Toda magnitud física se expresa con la **notación científica**

$$X = M \times 10^n, \quad 1 \le |M| < 10, \quad n \in \mathbb{Z}.$$

Esta forma elimina la ambigüedad de las cifras significativas y facilita
comparar órdenes de magnitud.
