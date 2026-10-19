# 002 — Operaciones científicas / Scientific operations

Fecha / Date: 2026-10-19.
Estado / Status: adoptado en 0.1.1 / adopted in 0.1.1.
La implementación inicial se preparó en una rama de desarrollo antes de la
publicación. / The initial implementation was prepared on a development branch
before release.

## Español

### Objetivo y distribución

Ampliar la consola con operaciones útiles para formular problemas científicos,
sin presentar una biblioteca completa de física estadística ni compatibilidad
general con otro sistema. Estas capacidades se incorporan en 0.1.1. El ZIP
v0.1.0 anterior conserva su alcance original. Véanse las
[notas de versión](../es/versiones/0.1.1.md).

### Contrato de las operaciones

- `N[expresión,p]`: escalar numérico sin símbolos libres, 1–1000 dígitos
  significativos solicitados; 15 por defecto. Se usa evaluación estricta y se
  preservan Float, incluido cero. Una precisión solicitada no recupera datos
  perdidos de una entrada aproximada anterior; no se racionaliza la salida.
- `Factor`: polinomios sobre Q. `Together` y `Cancel`: funciones racionales
  sobre Q. No se aceptan Float, funciones ni coeficientes irracionales en ese
  primer alcance. Control previo: ocho símbolos, grado estimado 256 y hasta
  4096 términos estimados en numerador/denominador. No es un timeout.
- `Substitute[expresión,x,valor]`: sustitución exacta de un símbolo, anidable,
  con transformación de las restricciones originales. No reconstruye información
  que se haya perdido antes ni convierte cadenas en código. Solo admite valores
  escalares finitos; sustituir Infinity no es tomar un límite.
- `Sum[término,{n,a,b}]`: extremos enteros inclusivos; intervalo vacío igual a
  cero. Se evalúa cada término con sus bindings y restricciones. Hasta 1000
  términos por suma y 2000 compartidos en una evaluación, incluidas anidadas.
- `Integrate[f,x]` y `Integrate[f,{x,a,b}]`: la antiderivada omite la constante;
  los límites reales pueden ser infinitos. Se conservan ramas Piecewise y
  resultados no evaluados; no se solicita automáticamente valor principal.
- `Solve[ecuación,x]`, opcionalmente `Reals` o `Complexes`: dominio complejo por
  defecto. Para listas, sistemas lineales de hasta ocho ecuaciones y variables.
  Se devuelven conjuntos, no reglas de sustitución de otro lenguaje. Familias
  libres y casos paramétricos degenerados se conservan o declaran no resueltos.
- `DSolve[ecuación,y[x],x]`: una EDO ordinaria para una función, orden 1 o 2;
  puede recibir lista de EDO y hasta cuatro datos iniciales. Las derivadas son
  `D` anidadas y un dato derivado usa `Substitute[D[y[x],x],x,0]==valor`.

Las listas generales se limitan a 64 elementos, sujetos además al parser; no
habilitan por sí solas álgebra matricial. `==` crea una igualdad inerte con
precedencia menor que la aritmética, no una asignación ni una prueba booleana.
Se rechazan cadenas de igualdades; las ecuaciones múltiples van en listas.

### Estado, precisión y condiciones

Se mantienen los campos previos y se añaden `status`, `exact`, `details`.
`exact` solo indica ausencia de Float; no significa completitud, identidad
demostrada ni convergencia. `status` permite distinguir aproximación, respuesta
evaluada, condiciones, falta de solución y resultados no resueltos o no verificados.
`details` registra método, precisión solicitada o residuos según corresponda.

La salida `input` sigue siendo conservadora: una aproximación Float tiene null
mientras no pueda reintroducirse sin perder su naturaleza aproximada. Los
conjuntos o funciones que el parser no represente también pueden no tener input.
La presentación `text` no reemplaza el contrato de reutilización.

Las exclusiones del AST se transportan al sustituir, se comprueban en términos
de sumas y se aplican a soluciones cuando es posible. Son condiciones necesarias
parciales. Las condiciones de Piecewise corresponden a alternativas, no a una
conjunción global; las exclusiones en una variable integrada quedan como
información del integrando. Los residuos de una solución y sus datos iniciales
son verificaciones locales, sin prueba de completitud o dominio global.
Las exclusiones retenidas se revisan también en puntos iniciales. Sustituir
parámetros puede reevaluar integrales pendientes y actualizar sus condiciones;
los requisitos sobre límites reales se conservan y transforman.

### Límites y verificación

No hay sesiones persistentes, definiciones arbitrarias de funciones, sistemas
de EDO ni EDP. Los límites de tamaño y trabajo no imponen aislamiento, tiempo
o memoria duros. Un resultado condicionado o no evaluado debe seguir visible.
La aceptación usa identidades exactas, casos numéricos con referencias,
restricciones y residuos; no una afirmación universal de corrección científica.
El cuaderno de ejemplo conserva solo fuentes, sin ejecutar al abrir.

## English

### Purpose and distribution

Extend the console with operations useful for scientific formulation, without
claiming a complete statistical physics library or general compatibility.
These capabilities are included in 0.1.1. The earlier v0.1.0 ZIP retains its
original scope. See the [release notes](../en/releases/0.1.1.md).

### Operation contracts

- `N[expression,p]`: numeric scalar without free symbols, 1–1000 requested
  significant digits; default 15. Strict evaluation preserves Float, including
  zero. More requested digits cannot recover lost information in earlier
  approximations; outputs are not rationalized.
- `Factor`: polynomials over Q. `Together` and `Cancel`: rational functions
  over Q. Float, functions, and irrational coefficients are outside the initial
  scope. Preflight permits eight symbols, estimated degree 256, and up to 4096
  estimated numerator/denominator terms. This is not a timeout.
- `Substitute[expression,x,value]`: one exact, nestable symbol substitution,
  transforming original restrictions. It does not recover previously lost
  information or interpret strings as code. Replacement values must be finite
  scalars; substituting Infinity is not taking a limit.
- `Sum[term,{n,a,b}]`: inclusive integer bounds; an empty range is zero. Terms
  are evaluated with their bindings and restrictions. Limit: 1000 terms per sum,
  2000 shared in one evaluation, including nested sums.
- `Integrate[f,x]` and `Integrate[f,{x,a,b}]`: antiderivatives omit the additive
  constant; real bounds may be infinite. Piecewise branches and unevaluated
  results are preserved; principal values are not requested automatically.
- `Solve[equation,x]`, optionally `Reals` or `Complexes`: complex domain by
  default. Lists allow linear systems of up to eight equations and variables.
  Results are sets, not another language's replacement rules. Free families
  and parameter-dependent degenerate cases are retained or marked unresolved.
- `DSolve[equation,y[x],x]`: one ordinary equation for one function, order 1 or
  2; a list may include the ODE and up to four initial data. Derivatives use
  nested `D`; derivative data use `Substitute[D[y[x],x],x,0]==value`.

General lists are limited to 64 elements and parser limits; they do not provide
matrix algebra by themselves. `==` creates an inert equality with lower
precedence than arithmetic, not assignment or a Boolean proof. Equality chains
are rejected; multiple equations use lists.

### Status, precision, and conditions

Existing fields remain, with additive `status`, `exact`, and `details`.
`exact` only means no Float; it does not prove completeness, an identity, or
convergence. `status` distinguishes approximation, evaluated output, conditions,
no solution, and unresolved or unverified results. `details` records method,
requested precision, or residuals as applicable.

Reusable `input` remains conservative. Float approximations have null until
they can be re-entered without losing their approximate nature. Sets and
functions outside parser representation may also lack input. Display `text`
is not a replacement for this reuse contract.

AST exclusions are transported by substitution, checked in sum terms, and
applied to solutions when possible. They are partial necessary conditions.
Piecewise conditions describe alternatives, not a global conjunction;
exclusions involving an integrated variable remain integrand information.
Solution and initial-data residuals provide local checks, not completeness
or a global domain proof.
Retained exclusions are also checked at initial points. Parameter substitution
may reevaluate pending integrals and update their conditions; requirements on
real bounds are preserved and transformed.

### Limits and verification

There are no persistent sessions, arbitrary function definitions, ODE systems,
or PDE support. Size and work budgets do not enforce hard isolation, time,
or memory bounds. Conditional and unevaluated results remain visible.
Acceptance uses exact identities, numerical references, restrictions, and
residuals, rather than universal scientific correctness. The example notebook
stores only sources and never evaluates them on opening.

## Fuentes del backend / Backend references

[Mediciones reproducibles / Reproducible measurements](../../benchmarks/README.md).

Documentación oficial SymPy 1.14.0, consultada / consulted 2026-10-19:

- [Numerical evaluation](https://docs.sympy.org/latest/modules/evalf.html).
- [Polynomial manipulation](https://docs.sympy.org/latest/modules/polys/reference.html).
- [Substitution](https://docs.sympy.org/latest/modules/core.html#sympy.core.basic.Basic.subs).
- [Integration](https://docs.sympy.org/latest/modules/integrals/integrals.html).
- [Solution sets](https://docs.sympy.org/latest/modules/solvers/solveset.html).
- [Ordinary differential equations](https://docs.sympy.org/latest/modules/solvers/ode.html).

Los límites y la sintaxis anteriores son decisiones de Mathechan; no describen
todo SymPy. / These limits and syntax are Mathechan decisions, not the full
scope of SymPy.
