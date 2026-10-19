# History and background

[Español](../es/historia.md) · [Home](../../README.en.md)

## Mathechan's origins

Mathechan began on **18 October 2026** as a personal project by Edward Larroza H.,
a doctoral student in Physics. The intention is to build an open program for
formulating, calculating, and visualizing problems in theoretical physics,
with a particular interest in statistical physics.

The initial horizon spans **2026–2031**. Version 0.1.0 is a command-line
prototype; the desktop application belongs to the planned development.
Familiar syntax and the integration of calculation and plotting take Mathematica
as a technical reference, without proposing a complete replica.

On 19 October 2026, version 0.1.1 extended the console with configurable-precision
numerical evaluation, rational algebra, substitution, finite sums, integration,
and bounded algebraic/ODE solving. Its [release notes](releases/0.1.1.md)
describe the capabilities and limitations.

## Mathematica as a reference

The following selection covers milestones relevant to the project. Monthly
dates come from the [official version history](../SOURCES.md#s01);
precise dates and capabilities are documented in the indicated sources.

| Date | Version | Milestone |
|---|---|---|
| 23 June 1988 | 1.0 | Release, following development during 1986–1988. [S02](../SOURCES.md#s02) |
| January 1991 | 2.0 | ODEs, numerical compilation, and interprocess communication. [S01](../SOURCES.md#s01) |
| 3 September 1996 | 3.0 | Editable mathematical expressions and programmable documents. [S04](../SOURCES.md#s04) |
| May 1999 | 4.0 | Numerical and file interchange improvements. [S01](../SOURCES.md#s01) |
| 23 June 2003 | 5.0 | Numerical overhaul and integrated statistics. [S05](../SOURCES.md#s05) |
| May 2007 | 6.0 | Dynamic interfaces. [S06](../SOURCES.md#s06) |
| November 2008 | 7.0 | Built-in parallel computation. [S07](../SOURCES.md#s07) |
| November 2010 | 8.0 | Probabilities, expectations, and distributions. [S08](../SOURCES.md#s08) |
| November 2012 | 9.0 | Random processes and Markov processes. [S09](../SOURCES.md#s09) |
| July 2014 | 10.0 | Finite elements for PDEs. [S10](../SOURCES.md#s10) |
| April 2019 | 12.0 | Expanded optimization and asymptotics. [S01](../SOURCES.md#s01) |
| January 2024 | 14.0 | Expanded numerical integration. [S01](../SOURCES.md#s01) |
| July 2026 | 15.0.1 | Fixes, stability, and security. [S01](../SOURCES.md#s01) |

The early notebook design aimed to preserve an editable, shareable record of
work with the computational kernel. This motivation is described in the
summary of Theodore Gray's 1996 article; that summary was used here,
rather than its attached file. [S03](../SOURCES.md#s03)

## Implications for development

This history suggests building a coherent kernel, documenting notation, and
preserving calculations before expanding coverage. Two-dimensional mathematical
editing, interactivity, and specialized solvers require their own development.

Mathechan will prioritize a small collection of reproducible problems with
explicit assumptions and limits. Mathematica's release dates alone do not
establish the effort required or correspond to stages in Mathechan's schedule.

This selection uses official public sources consulted on **18 October 2026**.
It does not describe Wolfram's internal code, costs, or team size.
See [the source register](../SOURCES.md).
