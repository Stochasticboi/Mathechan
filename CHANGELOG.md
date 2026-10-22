# Versiones / Releases

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
