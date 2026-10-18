# 001 — Resultados reutilizables y condiciones / Reusable results and conditions

Fecha / Date: 2026-10-18.
Estado / Status: decisión propuesta para esta implementación / proposed decision
for this implementation.

## Español

### Problema

El texto de presentación de SymPy no es siempre entrada de Mathechan. Además,
`I` puede ser la constante imaginaria de una salida o un símbolo genérico de una
entrada. La simplificación puede eliminar un denominador sin conservar su
restricción: `x/x` se representa como `1`, aunque el problema original excluye 0.

### Decisión

Conservar `EvaluationResult.text` y añadir `input`, `conditions` y `warnings`.
El formato de cuaderno no se modifica: sus resultados persistidos siguen siendo
texto histórico y no constituyen una sesión de evaluación ni nuevos metadatos.

Un impresor propio crea candidatos en la sintaxis acotada. `Sqrt[-1]` representa
la constante imaginaria; `I` conserva su significado de símbolo. El núcleo solo
ofrece el candidato si respeta los límites de entrada, puede parsearse y reconstruye la
misma expresión estructural. No se añade una simplificación global a esa
verificación. Si no hay candidato, `input` es `None`/`null`, con aviso; el cálculo
válido y su salida de presentación permanecen disponibles.

El formato no busca una compresión óptima: por ejemplo, el entero resultante de
`2^1000` excede los cien dígitos de un literal y puede no tener `input`, aunque
su fuente original sea válida. Funciones nuevas producidas por simplificación,
como `tan`, tampoco se anuncian como entrada si no están en el lenguaje.

Antes de construir operaciones que pueden cancelar factores se acumulan
denominadores explícitos y bases con exponentes conocidos negativos. Se descartan
condiciones demostrablemente no nulas y se conservan las demás sin duplicados.
La lista expresa condiciones necesarias rastreadas, no suficientes para un
dominio completo. `Plot` las comprueba en sus muestras, incluso si el factor
original desapareció del resultado, y rechaza condiciones con parámetros que
no puede resolver. Los extremos se comprueban con sus valores simbólicos exactos
antes de convertir las coordenadas exportadas a float: por ejemplo, el cero de
Sin[Pi] no se reemplaza por el pequeño residuo de sin(float(Pi)). En puntos
interiores, el caso denominador igual a la variable usa la coordenada finita ya
validada y su comparación exacta con cero; no usa tolerancias. Para gráficos se
reutiliza la fuente original validada, sin
reejecutar todas las muestras solo para producir el campo `input`.

`--input` reserva stdout para código reutilizable y envía condiciones/avisos a
stderr. JSON transporta campos separados; la consola normal y el intérprete
interactivo muestran las condiciones. Reutilizar una expresión simplificada
requiere conservar por separado la información de dominio original.

### Consecuencias y límites

No cambian el símbolo `I`, la precedencia, los dominios complejos de SymPy ni
la arquitectura fundamental. Cambia deliberadamente un gráfico que antes
ocultaba un agujero muestreado tras cancelar un denominador: ahora se rechaza.
No se resuelven dominios generales, cortes de rama, ceros entre muestras,
condiciones de cada derivada, ni límites de tiempo/memoria. El texto histórico
de cuadernos sigue sin acreditar que el código actual fue ejecutado.

## English

### Problem

SymPy display text is not always Mathechan input. The displayed `I` may denote
an imaginary constant, while input `I` is a generic symbol. Simplification can
remove a denominator restriction: `x/x` becomes `1`, although the original
problem excludes zero.

### Decision

Keep `EvaluationResult.text` and add `input`, `conditions`, and `warnings`.
Do not change the notebook format: persisted results remain historical text,
not evaluation sessions or newly persisted domain metadata.

A dedicated printer produces bounded-syntax candidates. `Sqrt[-1]` encodes the
imaginary constant, while `I` remains a symbol. A candidate is offered only if
it passes current limits, parses, and rebuilds the structurally identical
expression. Verification adds no global simplification. Missing candidates yield
`None`/`null` with a warning; valid calculations and their display remain available.

The printer does not seek optimal compression: the integer from `2^1000` exceeds
the hundred-digit literal limit and may have no `input` despite valid original
source. Result functions such as `tan` are not advertised as input if the
language does not support them.

Before operations can cancel factors, collect explicit denominators and bases
with known negative exponents. Drop provably nonzero conditions and deduplicate
the rest. These are tracked necessary conditions, not a complete domain.
`Plot` checks them at sampled points even after cancellation and rejects conditions
with unresolved parameters. Endpoint conditions use exact symbolic values before
exported coordinates are converted to float: the zero of Sin[Pi] is not replaced
by the small residual of sin(float(Pi)). At interior points, a denominator equal
to the variable uses the already validated finite coordinate and exact zero
comparison, without a tolerance. Plot input preserves the validated original source,
without rerunning all samples simply to construct `input`.

`--input` reserves stdout for executable input and sends conditions/warnings to
stderr. JSON carries separate fields; ordinary and interactive consoles display
conditions. Reusing simplified input requires preserving original domain metadata
separately.

### Consequences and limits

The symbol `I`, precedence, SymPy complex conventions, and underlying architecture
are preserved. A plot that previously hid a sampled hole after cancellation now
fails deliberately. Universal domains, branch cuts, between-sample zeros, all
derivative conditions, and execution time/memory bounds remain unresolved.
Notebook display text still does not establish that current source was executed.
