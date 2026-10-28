# Mathechan

**Symbolic and numerical computing for theoretical and statistical physics.**

[Español](README.md) · [Download](https://github.com/Stochasticboi/Mathechan/releases/tag/v0.2.0-dev0) · [Language](docs/en/language.md) · [Release notes](CHANGELOG.md)

An open-source project by **Edward Larroza H., a doctoral student in Physics**.
Started in October 2026 to bring computation, plots and notebooks together in
a desktop application. It currently runs in a console; the graphical interface
is pending.

## Try Mathechan

| Option | Version | How to get it |
| --- | --- | --- |
| Windows x64 console | 0.2.0-dev0 · preview | [Download ZIP](https://github.com/Stochasticboi/Mathechan/releases/download/v0.2.0-dev0/Mathechan-0.2.0-dev0-windows-x64.zip), extract it and open `Mathechan.exe`. |
| Development source | **0.2.0.dev12** | Use the [`main`](https://github.com/Stochasticboi/Mathechan/tree/main) branch with Python 3.11 or later. |

The ZIP contains **dev0** features. For later additions, including MaxEnt,
install from source:

```console
python -m pip install -e .
python -m mathechan "D[x^3,x]"
```

Run these commands from the repository directory. The second line returns
`3*x**2`. Program modules live in [`src/mathechan`](src/mathechan).

## Project timeline

Each row describes what was added to the preceding version. Details and fixes
are recorded in the [changelog](CHANGELOG.md). Syntax is available from the
listed version; argument names describe the expected input.

| Version | What it added |
| --- | --- |
| **0.1.0** · 18 Oct 2026 | First kernel: exact arithmetic, symbolic expressions, differentiation, simplification, SVG plots and JSON notebooks.<br>Syntax: `D[expr,x]` |
| **0.1.1** · 19 Oct 2026 | Numerical evaluation, factoring, rational expressions, substitution, finite sums, integration, equations and ODEs.<br>Syntax: `Integrate[expr,{x,a,b}]` |
| **0.2.0.dev0** · 22 Oct 2026 | Persistent sessions, definitions and functions, assumptions, extended algebra and nonlinear systems. **Current downloadable version.**<br>Syntax: `Assuming[condition,expr]` |
| **0.2.0.dev1** | Real two-sided and one-sided limits; distinct convergent, divergent and unresolved results.<br>Syntax: `Limit[expr,x,a]` |
| **0.2.0.dev2** | `/.`, `->` and `:>` rules, series, mixed derivatives, products, Cartesian vector calculus and iterated integrals.<br>Syntax: `expr /. x -> value` |
| **0.2.0.dev3** | Vector calculus in cylindrical and spherical coordinates.<br>Syntax: `Div[field,{r,theta,phi},"Spherical"]` |
| **0.2.0.dev4** | Matrix arithmetic, rank, linear systems, eigenvalues, eigenvectors and matrix exponentials.<br>Syntax: `Eigenvalues[matrix]` |
| **0.2.0.dev5** | Finite discrete probability: distributions, events, expectation, variance and entropy.<br>Syntax: `Mean[distribution]` |
| **0.2.0.dev6** | Joint distributions, marginals, conditioning, covariance and correlation.<br>Syntax: `JointFiniteDistribution[states,masses]` |
| **0.2.0.dev7** | Hyperbolic functions and their inverses, with differentiation and integration.<br>Syntax: `D[Sinh[x],x]` |
| **0.2.0.dev8** | Complex algebra for small quantum systems: adjoints, tensor products, projectors and partial traces.<br>Syntax: `Adj[matrix]` |
| **0.2.0.dev9** | Binomial, Poisson, normal, exponential and gamma families; densities, cumulative distributions, generating functions, moments and cumulants.<br>Syntax: `CDF[distribution,x]` |
| **0.2.0.dev10** | Finite canonical ensembles: degeneracy, mean energy, fluctuations, free energy and heat capacity.<br>Syntax: `Energy[Canon[energies,beta]]` |
| **0.2.0.dev11** | Finite MaxEnt inference: Shannon or KL against a reference, multiple means, active support and saved results.<br>Syntax: `MaxEnt[observables,means]` |
| **0.2.0.dev12** · current | Rényi, Tsallis, KL divergence, escort distributions and q-functions. Completes the finite statistical-physics stage.<br>Syntax: `Tsallis[distribution,q]` · `QExp[x,q]` |

Versions **dev1–dev12** are integrated into the source; they do not yet have
separate downloads. See the [language reference](docs/en/language.md) for
operation syntax and limits.

## Scope and next steps

The finite statistical-physics stage covers canonical ensembles, Shannon/KL
inference and generalized entropy functionals. Rényi/Tsallis inference, MaxCal
and continuous models remain later extensions. The desktop interface and
notebook editor remain in the [2026–2031 plan](docs/en/objectives.md).

## Documentation and contributions

- [Syntax, examples and limits](docs/en/language.md).
- [History and background](docs/en/history.md) · [Comparison with Mathematica](docs/en/comparison.md).
- [Contributing](CONTRIBUTING.md) · [Sources](docs/SOURCES.md).

The kernel uses SymPy 1.14. Its syntax takes Wolfram Language as a reference,
with its own specification and no general compatibility. Current plots use
fixed sampling; notebooks do not execute code when opened.

To run the tests from the repository:

```console
python -m unittest discover -s tests -v
```

**GPL-3.0-or-later** · [License](LICENSE). Independent of Wolfram Research.
