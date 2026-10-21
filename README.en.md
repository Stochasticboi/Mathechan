# Mathechan

[Español](README.md)

A personal project by **Edward Larroza H., a doctoral student in Physics**.

Mathechan is an open-source program under development for theoretical physics,
with a particular interest in statistical physics. Its goal is to bring
symbolic computation, numerical methods, plots, and reproducible notebooks
together in a desktop application.

The project began on **18 October 2026**, with an initial five-year horizon
through October 2031. Its syntax takes Mathematica as a reference, with its
own specification and a scope developed incrementally.

## Experimental version 0.1.1

The current version runs **from the command line**, using a restricted parser
and SymPy 1.14 for evaluation. It does not yet have a graphical interface.

- Exact arithmetic, including decimals interpreted as rational numbers.
- Functions `Sin`, `Cos`, `Exp`, `Log`, and `Sqrt`.
- `Expand`, `Simplify`, and differentiation with `D`.
- Univariate plots with `Plot` and SVG export.
- Reading and writing JSON `.mchan` notebooks, without execution on opening.

`Plot` uses 201 uniformly spaced samples: it may miss singularities between
samples and does not provide adaptive sampling. Notebooks store text results;
plots are exported separately. General Wolfram Language compatibility and
validation for general scientific use are not claimed.

## Scientific operations in 0.1.1

Version 0.1.1 extends the console with `N`, `Factor`, `Together`,
`Cancel`, `Substitute`, finite `Sum`, `Integrate`, `Solve`, and `DSolve`. It adds
lists, `==` equalities, and metadata distinguishing approximation, conditions,
and unresolved results. `N[Pi,50]` requests 50 digits;
`Sum[n^2,{n,1,10}]` returns 385.

These are bounded implementations: rational algebra over Q, linear algebraic
systems, and ODEs for one dependent function of order 1 or 2. Conditions and
checks are partial. See [syntax and limits](docs/en/language.md) and the
[example without precomputed results](examples/scientific.mchan).

These functions belong to **0.1.1**; the earlier 0.1.0 ZIP retains its original
scope. The graphical interface and dedicated statistical physics tools remain
pending. See the [0.1.1 release notes](docs/en/releases/0.1.1.md).

A later increment, **under development without a new release**, adds a local
numeric-variable session and limited immediate assignment. It is not part of
the published 0.1.1 ZIP and adds no graphical interface. See
[the language](docs/en/language.md) for scope; individual evaluation remains
stateless.

## Downloads and source code

Published versions and their files are available in
[Releases](https://github.com/Stochasticboi/Mathechan/releases/tag/v0.1.1).
For Windows x64, download the
[ZIP archive](https://github.com/Stochasticboi/Mathechan/releases/download/v0.1.1/Mathechan-0.1.1-windows-x64.zip),
extract it and open `Mathechan.exe`. It opens an interactive console.
The graphical interface is still under development. Release notes describe
the Python packages, source code and checks performed.

Installation from source requires Python 3.11 or later. From the repository
directory, preferably in a virtual environment:

```console
python -m pip install -e .
python -m mathechan "D[x^3, x]"
python -m mathechan "Plot[Exp[-x^2], {x, -3, 3}]" --output gaussian.svg
```

The first evaluation returns `3*x**2`. The second creates an SVG file.

## Documentation

- [Objectives and development horizon, 2026–2031](docs/en/objectives.md).
- [Project history and background](docs/en/history.md).
- [Comparison with Mathematica](docs/en/comparison.md).
- [Experimental language](docs/en/language.md).
- [Version 0.1.1 release notes](docs/en/releases/0.1.1.md).
- [Sources](docs/SOURCES.md).
- [Contributing](CONTRIBUTING.md).

Documentation is included in the repository and can be downloaded with the
source code. It distinguishes implemented functions, current limitations,
and development objectives.

## Tests and license

```console
python -m unittest discover -s tests -v
```

Mathechan is licensed under **GPL-3.0-or-later**; see [LICENSE](LICENSE).
Dependencies retain their own licenses. Mathematica and Wolfram Language are
technical references; Mathechan is independent of Wolfram Research.
