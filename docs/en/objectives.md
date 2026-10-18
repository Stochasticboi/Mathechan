# Mathechan objectives

[Español](../es/objetivos.md) · [Home](../../README.en.md)

Mathechan is a personal project by Edward Larroza H., a doctoral student in
Physics. Its goal is to develop an open desktop environment for formulating,
calculating, and visualizing problems in theoretical physics, with priority
given to statistical physics. Its initial horizon runs from October 2026 to
October 2031.

## Scientific direction

The mathematical base should support symbolic computation, numerical methods,
and plots. Proposed extensions include probability distributions, averages,
fluctuations, correlations, and partition functions. Usefulness for students
and researchers requires documented assumptions, reproducible examples, and
explicit limits for each operation.

The syntax is inspired by Mathematica, but shared notation does not imply
general compatibility with its programs. Mathechan's language will be specified
as testable capabilities are added.

## Proposed development path

| Period | Objective | Progress criterion |
|---|---|---|
| 2026–2027 | Initial kernel and language | Command-line evaluation, exact reference cases, and documented basic plots. |
| 2027–2028 | Desktop and notebooks | Edit, save, reopen, and execute calculations with identifiable state. |
| 2028–2029 | Statistical physics tools | A limited collection of problems with reference results. |
| 2029–2030 | Numerical methods and visualization | Measure precision, convergence, and performance before expanding coverage. |
| 2030–2031 | Consolidation | Maintainable distribution, documentation, and review of scientific examples. |

Dates guide the work; they do not guarantee coverage or equivalence with other
systems. Scope will be reviewed against available time and the results of
each stage.

## Starting point

Version 0.1.0 is a command-line prototype with exact arithmetic, a restricted
set of symbolic functions, differentiation, SVG plots, and `.mchan` files.
The desktop interface and specialized tools remain to be developed. See
[the comparison](comparison.md) for the distinction between available and
planned capabilities.

A future first scientific workflow will define a finite discrete system,
normalize its probabilities, compute observables, and plot their dependence
on a parameter. This is a development objective; the current prototype does
not implement it as a specialized tool.