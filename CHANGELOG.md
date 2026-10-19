# Versiones / Releases

## Sin publicar / Unreleased

### Español

- Rama de desarrollo, sin nueva release: `N` con precisión solicitada,
  `Factor`, `Together`, `Cancel`, `Substitute`, sumas finitas `Sum`,
  `Integrate`, `Solve` y `DSolve` en alcances explícitamente acotados.
- Igualdades inertes `==`, listas de hasta 64 elementos y metadatos aditivos
  `status`, `exact` y `details`; condiciones necesarias y ramas alternativas.
- Entrada reutilizable verificada separada de `text`; los Float no se
  racionalizan ni reciben entrada que pierda su carácter aproximado.
- Documentación ES/EN y `examples/scientific.mchan` sin resultados guardados.
- La versión del paquete sigue en 0.1.0; eso no incorpora estas capacidades
  al ZIP publicado anteriormente.

- Los cuadernos se guardan con UTF-8 y saltos LF; el límite de 2 MB se aplica
  a los mismos bytes al guardar y abrir, también en Windows.
- La carga limita los bytes leídos y notifica los errores de conversión JSON
  mediante `NotebookError`.

### English

- Development branch, no new release: `N` with requested precision,
  `Factor`, `Together`, `Cancel`, `Substitute`, finite `Sum`,
  `Integrate`, `Solve`, and `DSolve` within explicitly bounded scopes.
- Inert `==` equalities, lists of up to 64 elements, and additive `status`,
  `exact`, and `details` metadata; necessary conditions and alternative branches.
- Verified reusable input separate from `text`; Float values are neither
  rationalized nor given input that loses their approximate nature.
- ES/EN documentation and `examples/scientific.mchan` without stored results.
- The package version remains 0.1.0; this does not update the previously
  published ZIP with these capabilities.

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
