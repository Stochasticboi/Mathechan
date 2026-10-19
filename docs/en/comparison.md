# Comparison with Mathematica

[Español](../es/comparativa.md) · [Home](../../README.en.md)

Mathematica is a design reference. This comparison separates its documented
capabilities, the published **v0.1.0** distribution, and the **development branch**.
The latter is not a new release; the package version remains 0.1.0.
This is not a benchmark or a general compatibility claim.

| Area | Documented reference | v0.1.0 distribution | Development branch, no new release |
|---|---|---|---|
| Language | Expressions with heads and arguments. [S11](../SOURCES.md#s11) | Restricted parser and exact arithmetic. | Adds inert `==` equalities, lists of up to 64 elements, and bounded scientific operations. |
| Kernel | Text interface. [S12](../SOURCES.md#s12) | CLI using SymPy 1.14. | Keeps stateless CLI; adds status, representational exactness, and details. |
| Notebooks | Editable work record. [S03](../SOURCES.md#s03) | Inert `.mchan` JSON without graphical editing. | Keeps the format and inert loading; adds scientific example sources without results. |
| Algebra and calculus | Integration with assumptions. [S05](../SOURCES.md#s05) | `Expand`, `Simplify`, `D`, and elementary functions. | Adds `N`, `Factor`, `Together`, `Cancel`, `Substitute`, `Sum`, `Integrate`, `Solve`, and `DSolve`, with explicit limits. |
| Plotting | Sampling and Plot controls. [S13](../SOURCES.md#s13) | 201 samples and univariate SVG. | Checks sampled original restrictions; keeps fixed sampling without general pole detection. |
| Interactivity | Dynamic interfaces. [S06](../SOURCES.md#s06) | Pending. | Pending. |
| Probability | Expectations over distributions. [S14](../SOURCES.md#s14) | Specialized tools pending. | Pending; a generic sum or integral is not a statistical physics library. |
| Processes | Finite discrete/continuous Markov processes. [S15](../SOURCES.md#s15) | Pending. | Pending. |
| PDEs | Finite elements. [S10](../SOURCES.md#s10) | Pending. | Pending; current DSolve only supports one-function ODEs. |
| Parallelism | Integrated parallel computation. [S07](../SOURCES.md#s07) | Pending. | Pending. |

## Published distribution and development code

The v0.1.0 ZIP supports `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`,
`Simplify`, `D`, and `Plot`. Keeping the same source package version does
not make branch changes part of that distribution.

The new block supports requested precision from 1 to 1000 digits, rational
algebra over Q, and exact substitution with transported restrictions. Sums use
inclusive integer bounds and finite budgets. Integration may return conditional
branches or unevaluated integrals: not every return is a closed answer.

`Solve` distinguishes the default complex domain from explicit real solving,
solution sets, and linear systems; unresolved parameter cases are preserved.
`DSolve` supports one ODE of order 1 or 2 and initial data, with residual checks
when possible. These checks do not establish completeness or a global domain.

Conditions are necessary and partial; `exact: true` means no Float, not a
scientific proof. `input` is offered when a reusable representation is checked;
Float approximations and other results may leave it null. `status` and
`details` distinguish these cases. See [the language](language.md) and
[the decision](../decisions/002-scientific-operations.md).

## Limits and priorities

Plot may miss poles between samples and connect discontinuities. It has no
adaptive sampling or general singularity validation. Notebooks store text;
SVG is exported separately. Opening them never evaluates cells.

The graphical interface, persistent process, robust cancellation, and dedicated
statistical physics tools remain pending. Parser limits do not guarantee
execution time, memory, or isolation.

Development focuses on reproducible problems with explicit assumptions and
references. SymPy supports this block without settling the long-term engine.
Tests check specific cases, not parity with Mathematica, universal accuracy,
or general physical validation. See [objectives](objectives.md) and
[sources](../SOURCES.md).
