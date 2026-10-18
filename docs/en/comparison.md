# Comparison with Mathematica

[Español](../es/comparativa.md) · [Home](../../README.en.md)

Mathematica is a reference for Mathechan's design. This comparison distinguishes
its documented capabilities, functions in the **0.1.0** prototype, and pending
work. It is neither a performance measurement nor a compatibility claim.

| Area | Documented reference | Mathechan 0.1.0 |
|---|---|---|
| Language | Expressions with heads and arguments. [S11](../SOURCES.md#s11) | Restricted parser; exact arithmetic and rational decimals. |
| Kernel | Kernel access through a text interface. [S12](../SOURCES.md#s12) | CLI evaluation using SymPy 1.14; no persistent session. |
| Notebooks | Editable record of work. [S03](../SOURCES.md#s03) | Inert `.mchan` JSON; loading and saving, without a graphical editor. |
| Algebra and calculus | Integration with documented assumptions. [S05](../SOURCES.md#s05) | `Expand`, `Simplify`, `D`, and elementary functions; no general integration. |
| Plotting | Sampling and `Plot` controls. [S13](../SOURCES.md#s13) | One variable, 201 uniform samples, and SVG export. |
| Interactivity | Dynamic interfaces. [S06](../SOURCES.md#s06) | Pending. |
| Probability | Expectations with respect to distributions. [S14](../SOURCES.md#s14) | Specialized tools pending. |
| Processes | Finite Markov processes in discrete and continuous time. [S15](../SOURCES.md#s15) | Pending. |
| PDEs | Numerical solution using finite elements. [S10](../SOURCES.md#s10) | Pending. |
| Parallelism | Integrated parallel computation. [S07](../SOURCES.md#s07) | Pending. |

## Currently usable scope

The subset accepts `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`,
`Simplify`, and `D[expression, variable]`. It does not include assignments,
patterns, implicit multiplication, or all differentiation forms. Text output
uses SymPy notation; it is not guaranteed to be directly reusable as
Mathechan input.

`Plot` requires finite real endpoints and a single free variable. It rejects
non-real or non-finite values encountered while sampling, but may miss poles
between samples. It has neither general singularity detection nor adaptive
sampling. The `.mchan` files store text results; SVG output is exported
separately. Opening a notebook does not execute its cells.

The desktop application, persistent process, robust cancellation, and
specialized statistical physics tools remain to be developed. Parser input
limits do not provide security isolation.

## Priorities

Development will focus on statistical physics problems that can be reproduced
with explicit assumptions and reference results. The long-term engine choice
remains open: SymPy supports evaluation of this first subset, without deciding
all future choices.

Repository tests check specific cases of arithmetic, precedence,
differentiation, errors, export, and notebook format. They do not establish
universal accuracy, parity with another system, or physical validation.
See [the objectives](objectives.md), [the language](language.md), and
[the sources](../SOURCES.md).