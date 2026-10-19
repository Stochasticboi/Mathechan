# Operaciones científicas / Scientific operations

Medición local / Local measurement: 2026-10-19.

Comparación entre / Comparison between `2893c0b` (base integrada / integrated
base) y / and `7b9241a` (operaciones científicas / scientific operations).
Python 3.12.1, SymPy 1.14.0, Windows 11 x64, AMD64 Family 25 Model 97 Stepping 2.
No se añadieron dependencias de ejecución / No runtime dependencies were added.

Desde el repositorio con el paquete instalado / From the repository with the
package installed:

```console
python benchmarks/scientific.py --suite all --repeats 31
```

El script contiene las entradas exactas y emite JSON. La evaluación medida
incluye parser, cálculo, representación y comprobación de entrada reutilizable.
Se descarta un calentamiento por caso; se hicieron tres procesos por revisión,
alternando base y cambio. Las tablas agrupan 93 muestras por caso. Mediana y
desviación absoluta mediana (MAD), en milisegundos; no incluye arranque de Python.

The script contains the exact inputs and emits JSON. Timings include parsing,
calculation, formatting, and reusable-input validation. One warm-up per case is
discarded. Three processes per revision alternated baseline and change, giving
93 samples per case. Tables report median and median absolute deviation (MAD)
in milliseconds, excluding interpreter startup.

| Caso / Case | Antes / Before: median ± MAD (ms) | Después / After: median ± MAD (ms) |
|---|---:|---:|
| Arithmetic | 0.0442 ± 0.0023 | 0.0489 ± 0.0032 |
| Derivative | 0.2998 ± 0.0261 | 0.2981 ± 0.0136 |
| Expand | 6.4019 ± 0.5809 | 6.2460 ± 0.5466 |
| Simplify | 7.1850 ± 0.4936 | 8.5207 ± 1.8537 |
| Gaussian plot | 12.5329 ± 0.8943 | 13.4089 ± 1.0456 |
| Rational plot | 2.4646 ± 0.1706 | 2.9450 ± 0.4721 |

Una primera medición aislada fue más ruidosa, por lo que se repitió la comparación
alternada. No se afirma aceleración ni ausencia universal de regresiones. En
esta muestra las medianas de Simplify y el gráfico racional suben alrededor de
19%; su dispersión también aumenta. Un perfil separado de 1000 derivadas tomó
1.008 s antes y 1.106 s después bajo cProfile: muestra trabajo adicional en
evaluación y validación; no es una medida de latencia sin instrumentación.

An initial single measurement was noisier, so an alternating comparison was
run. This does not claim acceleration or universally unchanged performance.
Simplify and rational-plot medians rise by about 19%, with greater dispersion.
A separate profile of 1000 derivatives took 1.008 s before and 1.106 s after
under cProfile, showing added evaluation and validation work; these are not
uninstrumented latency measurements.

| Operación nueva / New operation | Median ± MAD (ms) |
|---|---:|
| N, 50 digits | 0.0830 ± 0.0226 |
| Factor | 1.4764 ± 0.3548 |
| Together | 0.8530 ± 0.0533 |
| Cancel | 0.8503 ± 0.0845 |
| Substitute | 0.6027 ± 0.1360 |
| Sum, 1000 terms | 9.5292 ± 1.4643 |
| Integrate, Gaussian | 6.4118 ± 1.0572 |
| Solve, quadratic | 3.8783 ± 0.6519 |
| DSolve, decay with initial value | 15.9237 ± 1.3404 |

Son casos pequeños con caché caliente. No miden memoria, coste de primer uso,
arranque del ejecutable ni complejidad asintótica. No son límites de tiempo ni
garantías para otros problemas o equipos. Las cotas del lenguaje se explican
en [español](../docs/es/lenguaje.md) y [English](../docs/en/language.md).

These are small cases with warm caches, not memory, cold-start, executable
startup, or asymptotic-complexity measurements. They are neither time limits
nor guarantees for other problems or hardware. See the language references
for the operation budgets.
