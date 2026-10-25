# Versiones / Releases

## 0.2.0.dev8 — Sin publicar / Unreleased

### Español

- Álgebra compleja con nombres breves: `Conj`, `Re`, `Im`, `Adj`, `Inner`,
  `Norm`, `Unit`, `Dyad`, `Proj`, `Kron` y `Ortho`. `Imag` representa la unidad
  imaginaria; `I` conserva su significado de símbolo genérico.
- `HermQ`, `UnitaryQ` y `PSDCheck` verifican identidades o devuelven fórmulas
  simbólicas pendientes. `PTrace` calcula la traza parcial por subsistemas,
  con el primer factor tensorial como el más significativo.
- Requisitos ejecutables de norma positiva conservados tras simplificación,
  asignación y persistencia. Los predicados booleanos simbólicos se guardan,
  cargan y reducen mediante sustitución; `Assuming` ofrece refinamiento parcial.
- Matrices hasta 8×8 y 64 entradas; `PSDCheck` hasta 4×4 y traza parcial con
  hasta cuatro subsistemas y dimensión total ocho. Los datos aproximados no
  tienen tolerancia de clasificación ni precisión certificada; `Ortho` avisa
  de bases casi dependientes. La descarga 0.2.0-dev0 conserva su alcance anterior.

### English

- Short complex-algebra commands: `Conj`, `Re`, `Im`, `Adj`, `Inner`, `Norm`,
  `Unit`, `Dyad`, `Proj`, `Kron` and `Ortho`. `Imag` represents the imaginary
  unit; `I` remains a generic symbol.
- `HermQ`, `UnitaryQ` and `PSDCheck` check identities or return undecided
  symbolic formulas. `PTrace` traces out selected subsystems, with the first
  tensor factor the most significant.
- Executable positive-norm requirements survive simplification, assignment
  and storage. Symbolic boolean predicates can be saved, loaded and reduced
  through substitution; `Assuming` provides partial refinement.
- Matrices up to 8×8 and 64 entries; `PSDCheck` up to 4×4 and partial trace
  with up to four subsystems and total dimension eight. Approximate inputs
  have no classification tolerance or certified precision; `Ortho` warns
  about nearly dependent bases. The 0.2.0-dev0 download retains its earlier scope.

## 0.2.0.dev7 — Sin publicar / Unreleased

### Español

- `Sinh`, `Cosh`, `Tanh`, `Coth`, `Sech`, `Csch` y sus seis inversas con
  evaluación simbólica/numérica, derivación e integración.
- Registro común para evaluación, entrada reutilizable y códec de sesiones.
  Se conservan polos antes de cancelar y denominadores de derivadas escalares
  o vectoriales; las ramas principales complejas tienen advertencias explícitas.
- Verificación acotada de primitivas hiperbólicas mediante sus definiciones
  exponenciales cuando la simplificación inicial no reconoce la identidad.
- Cuatro casos adicionales de aceptación binaria y documentación ES/EN existente
  actualizada. Sin nuevas dependencias ni cambios en la release 0.2.0-dev0.

### English

- `Sinh`, `Cosh`, `Tanh`, `Coth`, `Sech`, `Csch`, and their six inverses,
  with symbolic/numerical evaluation, differentiation and integration.
- Shared evaluation, reusable-input and session-codec registry. Pole exclusions
  and scalar/vector derivative denominators survive cancellation; principal
  complex branches have explicit warnings.
- Bounded antiderivative verification through exponential definitions when
  initial simplification does not recognize a hyperbolic identity.
- Four additional executable acceptance cases and updated existing bilingual
  documentation. No new dependencies or changes to the 0.2.0-dev0 release.

## 0.2.0.dev6 — Sin publicar / Unreleased

### Español

- `JointFiniteDistribution` para tablas finitas de dos a cuatro coordenadas,
  con estados distintos, masas normalizadas y requisitos ejecutables.
- `MarginalDistribution` proyecta y agrupa coordenadas por índices desde uno;
  `Probability` y `Expectation` admiten múltiples variables locales.
- `ConditionalDistribution` condiciona sobre eventos decididos por fila,
  conservando su probabilidad positiva incluso tras cancelación y guardado.
- `Covariance` y `Correlation` de observables reales, calculadas con momentos
  centrados y condiciones de varianza positiva. Persistencia validada y
  representación reutilizable para distribuciones conjuntas.
- Seis casos nuevos de aceptación del ejecutable y documentación ES/EN existente
  actualizada. Sin nuevas dependencias ni cambios en la release 0.2.0-dev0.

### English

- `JointFiniteDistribution` for finite tables of two to four coordinates, with
  distinct states, normalized masses and executable requirements.
- `MarginalDistribution` projects and groups coordinates using one-based indices;
  `Probability` and `Expectation` accept multiple local variables.
- `ConditionalDistribution` conditions on row-wise decided events, retaining
  positive event probability through cancellation and session storage.
- `Covariance` and `Correlation` for real observables use centered moments and
  positive-variance requirements. Validated joint-distribution persistence and
  reusable input representation.
- Six additional executable acceptance cases and updated existing bilingual
  documentation. No new dependencies or changes to the 0.2.0-dev0 release.

## 0.2.0.dev5 — Sin publicar / Unreleased

### Español

- Inicio de probabilidad discreta finita: `FiniteDistribution`,
  `WeightedDistribution`, `BernoulliDistribution` y `DiscreteUniformDistribution`.
  Validación de estados reales distintos, masas y normalización; soporte de
  parámetros con requisitos ejecutables, sin renormalización implícita.
- `States`, `Support`, `Probabilities`, `Mean`, `Variance`, `StandardDeviation`,
  `Entropy`, `Probability` y `Expectation`. Variables locales, estados de masa
  cero omitidos antes de evaluar observables y entropía en nats sin `0 Log[0]`.
- Distribuciones guardables sin ejecutar fuente al cargar. Sustitución de
  resultados por casos corregida para seleccionar condiciones antes de ramas;
  corregida una falsa contradicción de pertenencias racionales a los reales.
- Ocho casos nuevos de aceptación del ejecutable. Documentación ES/EN existente
  actualizada. Sin nuevas dependencias ni cambios en la release 0.2.0-dev0.

### English

- Initial finite discrete probability: `FiniteDistribution`,
  `WeightedDistribution`, `BernoulliDistribution`, and `DiscreteUniformDistribution`.
  Distinct real states, masses, and normalization are validated; symbolic
  requirements remain executable, with no implicit normalization.
- `States`, `Support`, `Probabilities`, `Mean`, `Variance`, `StandardDeviation`,
  `Entropy`, `Probability`, and `Expectation`. Local variables, zero-mass states
  skipped before observable evaluation, and zero-safe entropy in nats.
- Distributions survive storage without executing source on load. Piecewise
  replacement now selects conditions before branches; fixed a false
  contradiction involving rational-expression membership in the reals.
- Eight new executable acceptance cases and updated existing bilingual docs.
  No additional dependencies or changes to the published 0.2.0-dev0 release.

## 0.2.0.dev4 — Sin publicar / Unreleased

### Español

- Álgebra lineal densa: `Dimensions`, `Dot` y `A.B`, `Transpose`, `Tr`, `Det`,
  `Inverse`, `MatrixRank`, `LinearSolve`, `Eigenvalues`, `Eigenvectors`,
  `MatrixPower` y `MatrixExp`. Suma, resta, escalado y producto matricial
  conservan el comportamiento previo de `Matrix`; los vectores resultado
  admiten composición aritmética.
- `N` aproxima matrices y listas numéricas. Los sistemas distinguen soluciones
  únicas, familias y ausencia de soluciones; las ramas paramétricas retienen
  requisitos ejecutables. Las matrices defectuosas no se rellenan con vectores nulos.
- Diagnósticos de residuo y condicionamiento para cálculos aproximados, sin
  certificar dígitos. El impresor ofrece entrada reutilizable para matrices
  exactas representables. Doce nuevos casos de aceptación del ejecutable.
- Se mantienen los límites documentados de tamaño y complejidad. Sin nuevas
  dependencias ni cambios en el descargable 0.2.0-dev0.

### English

- Dense linear algebra: `Dimensions`, `Dot` and `A.B`, `Transpose`, `Tr`, `Det`,
  `Inverse`, `MatrixRank`, `LinearSolve`, `Eigenvalues`, `Eigenvectors`,
  `MatrixPower`, and `MatrixExp`. Addition, subtraction, scaling, and historical
  `Matrix` multiplication remain available; vector results support arithmetic composition.
- `N` approximates numerical matrices and lists. Linear systems distinguish
  unique solutions, families, and no solution; parametric branches retain
  executable requirements. Defective matrices never receive zero eigenvector padding.
- Residual and condition diagnostics for approximate computations without
  certified digits. Representable exact matrices receive reusable input.
  Twelve additional executable acceptance cases.
- Documented size and complexity budgets remain in force. No new dependencies
  or changes to the published 0.2.0-dev0 download.

## 0.2.0.dev3 — Sin publicar / Unreleased

### Español

- `Grad`, `Div`, `Curl` y `Hessian` admiten cartas `Cylindrical` y `Spherical`,
  además de `Cartesian` por defecto. Los vectores usan la base ortonormal local;
  `Grad` de un vector y `Hessian` incluyen los términos geométricos de esa base.
- `Jacobian` conserva por defecto las derivadas parciales de las componentes,
  incluso para salidas rectangulares. El cuarto argumento `Orthonormal` calcula
  el gradiente vectorial geométrico 3×3.
- Las opciones admiten nombres o cadenas. Se conservan las condiciones reales
  de la carta: radio positivo y, en esféricas, ángulo polar entre 0 y Pi.
  El descargable 0.2.0-dev0 no cambia.

### English

- `Grad`, `Div`, `Curl`, and `Hessian` support `Cylindrical` and `Spherical`
  charts alongside the default `Cartesian`. Vectors use the local orthonormal
  basis; vector `Grad` and `Hessian` include its geometric connection terms.
- `Jacobian` defaults to ordinary component derivatives, allowing rectangular
  output. Its fourth argument `Orthonormal` returns the geometric 3×3 vector gradient.
- Options accept names or strings. Real chart conditions remain attached:
  positive radius and, in spherical coordinates, polar angle between 0 and Pi.
  The published 0.2.0-dev0 download is unchanged.

## 0.2.0.dev2 — Sin publicar / Unreleased

### Español

- Reglas `->`, `:>` y aplicación `/.`/`ReplaceAll`, listas de reglas y patrones
  escalares nombrados acotados. `Substitute[expr,x,valor]` conserva su forma previa;
  `Substitute[expr,reglas]` admite la nueva forma. Reglas guardables en sesión,
  sin ejecutar cuerpos diferidos al cargar.
- `Series[expr,{x,punto,n}]` incluye el grado n y conserva el resto `O`;
  `Normal` extrae la aproximación truncada conservando su procedencia.
- Derivadas superiores y mixtas, productos finitos, sumas/productos simbólicos
  e infinitos, con resultados condicionados o pendientes cuando corresponda.
- `Grad`, `Div`, `Curl`, `Jacobian`, `Hessian` en coordenadas cartesianas e
  integrales iteradas de hasta tres variables, sin certificar el intercambio de orden.
- Conservación de hipótesis, degeneraciones paramétricas y presupuestos de
  trabajo compartidos. Documentación y pruebas ES/EN actualizadas.
- No modifica la release descargable 0.2.0-dev0.

### English

- `->`/`:>` rules and `/.`/`ReplaceAll`, rule lists and bounded named scalar
  patterns. The original `Substitute[expr,x,value]` remains supported;
  `Substitute[expr,rules]` accepts the new form. Session persistence never
  executes delayed rule bodies on load.
- `Series[expr,{x,point,n}]` includes degree n and retains the `O` remainder;
  `Normal` extracts the truncated approximation while retaining provenance.
- Higher/mixed derivatives, finite products, symbolic and infinite aggregates,
  preserving conditional or unresolved outcomes.
- Cartesian `Grad`, `Div`, `Curl`, `Jacobian`, `Hessian` and iterated integrals
  with up to three variables; interchange of integration order is not certified.
- Preserves assumptions, parameter degeneracies and shared work budgets.
  Updated bilingual documentation and regression tests.
- The published 0.2.0-dev0 download is unchanged.

## 0.2.0.dev1 — Sin publicar / Unreleased

### Español

- `Limit[expr,x,punto]` calcula un límite bilateral sobre el eje real; `Left`
  y `Right` seleccionan un lateral. Admite puntos reales exactos e infinitos reales.
- Distingue valor finito, divergencia, ausencia de límite y cálculo pendiente.
  Los tres últimos conservan `Limit` sin evaluar, con diagnósticos de los laterales.
- Respeta la variable ligada, conserva exclusiones de parámetros y verifica
  que las hipótesis cubran el entorno lateral. Los casos paramétricos no
  determinados permanecen pendientes. No cambia el descargable 0.2.0-dev0.

### English

- `Limit[expr,x,point]` computes a bilateral real-axis limit; `Left` and `Right`
  select one side. Exact real points and real infinities are supported.
- Distinguishes finite values, divergence, absence of a limit, and unresolved
  requests. The latter three retain an unevaluated `Limit` with side diagnostics.
- Respects bound-variable scope, retains parameter exclusions, and checks that
  hypotheses cover the approach neighbourhood. Undetermined parameter cases
  remain unresolved. The published 0.2.0-dev0 download is unchanged.

## 0.2.0.dev0 — 2026-10-22 (preliminar / preview)

### Español

- Sesiones con asignaciones simbólicas, contenedores, funciones inmediatas y
  diferidas, patrones escalares acotados y guardado explícito en JSON validado.
- Hipótesis locales y persistentes, restricciones originales conservadas,
  `FullSimplify`, `Collect`, `Apart`, `Reduce` y `AnalyzeDomain` con alcance explícito.
- Sistemas polinómicos no lineales, ramas degeneradas de coeficientes y `NSolve`
  con aislamiento algebraico o búsqueda local desde un inicio indicado.
- `CertifiedN` produce intervalos y cotas racionales para constantes algebraicas
  reales; `NumericError` sigue siendo una estimación sin certificación.
- Distribución preliminar de consola para Windows x64, código fuente y sumas
  SHA-256. Los archivos publicados de v0.1.1 se conservan.

### English

- Sessions support symbolic assignments, containers, immediate and deferred
  functions, bounded scalar patterns, and explicit validated JSON persistence.
- Local and persistent assumptions, retained original restrictions, `FullSimplify`,
  `Collect`, `Apart`, `Reduce`, and `AnalyzeDomain` with explicit scope.
- Nonlinear polynomial systems, coefficient-degeneracy branches, and `NSolve`
  using algebraic isolation or a local search from a supplied initial point.
- `CertifiedN` provides rational enclosures and bounds for real algebraic
  constants; `NumericError` remains an uncertified estimate.
- Preview console distribution for Windows x64, source code and SHA-256
  checksums. Previously published v0.1.1 assets are preserved.

## 0.1.1 — 2026-10-19

[Notas en español](docs/es/versiones/0.1.1.md) ·
[English release notes](docs/en/releases/0.1.1.md)

### Español

- `N` con precisión solicitada,
  `Factor`, `Together`, `Cancel`, `Substitute`, sumas finitas `Sum`,
  `Integrate`, `Solve` y `DSolve` en alcances explícitamente acotados.
- Igualdades inertes `==`, listas de hasta 64 elementos y metadatos aditivos
  `status`, `exact` y `details`; condiciones necesarias y ramas alternativas.
- Entrada reutilizable verificada separada de `text`; los Float no se
  racionalizan ni reciben entrada que pierda su carácter aproximado.
- Documentación ES/EN y `examples/scientific.mchan` sin resultados guardados.
- La versión del paquete y la distribución pasan a 0.1.1; el ZIP anterior
  de 0.1.0 conserva su alcance original.

- Los cuadernos se guardan con UTF-8 y saltos LF; el límite de 2 MB se aplica
  a los mismos bytes al guardar y abrir, también en Windows.
- La carga limita los bytes leídos y notifica los errores de conversión JSON
  mediante `NotebookError`.

### English

- `N` with requested precision,
  `Factor`, `Together`, `Cancel`, `Substitute`, finite `Sum`,
  `Integrate`, `Solve`, and `DSolve` within explicitly bounded scopes.
- Inert `==` equalities, lists of up to 64 elements, and additive `status`,
  `exact`, and `details` metadata; necessary conditions and alternative branches.
- Verified reusable input separate from `text`; Float values are neither
  rationalized nor given input that loses their approximate nature.
- ES/EN documentation and `examples/scientific.mchan` without stored results.
- The package and distribution advance to 0.1.1; the earlier 0.1.0 ZIP
  retains its original scope.

- Notebooks are written as UTF-8 with LF line endings; saving and loading
  apply the 2 MB limit to the same bytes, including on Windows.
- Loading bounds the bytes read and reports JSON conversion failures through
  `NotebookError`.

## 0.1.0 — 2026-10-18

### Español

Primera versión preliminar del núcleo de cálculo. Incluye aritmética exacta,
expresiones simbólicas, derivadas, simplificación y gráficos SVG. El formato
de cuaderno conserva texto y código en JSON. La entrada admite un subconjunto
pequeño de sintaxis matemática con funciones entre corchetes.

La distribución inicial se utiliza por consola. El editor de cuadernos de
escritorio y las herramientas específicas de física estadística están en
desarrollo.

### English

First preliminary release of the computation kernel. It includes exact
arithmetic, symbolic expressions, differentiation, simplification and SVG
plots. The notebook format stores text and code as JSON. Input supports a
small subset of mathematical syntax with square-bracket function calls.

This release runs in a console. The desktop notebook editor and dedicated
statistical physics tools are under development.
