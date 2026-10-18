# Comparativa con Mathematica

[English](../en/comparison.md) · [Inicio](../../README.md)

Mathematica es una referencia para diseñar Mathechan. La comparación distingue
capacidades documentadas de ese sistema, funciones del prototipo **0.1.0** y
trabajo pendiente. No es una medición de rendimiento ni una declaración de
compatibilidad.

| Área | Referencia documentada | Mathechan 0.1.0 |
|---|---|---|
| Lenguaje | Expresiones con cabeza y argumentos. [S11](../SOURCES.md#s11) | Parser propio restringido; aritmética exacta y decimales racionales. |
| Núcleo | Uso del kernel mediante interfaz textual. [S12](../SOURCES.md#s12) | CLI con evaluación mediante SymPy 1.14; sin sesión persistente. |
| Cuadernos | Registro editable del trabajo. [S03](../SOURCES.md#s03) | JSON `.mchan` inerte; carga y guardado, sin editor gráfico. |
| Álgebra y cálculo | Integración con supuestos documentados. [S05](../SOURCES.md#s05) | `Expand`, `Simplify`, `D` y funciones elementales; sin integración general. |
| Gráficos | Muestreo y controles de `Plot`. [S13](../SOURCES.md#s13) | Una variable, 201 muestras uniformes y exportación SVG. |
| Interacción | Interfaces dinámicas. [S06](../SOURCES.md#s06) | Pendiente. |
| Probabilidad | Esperanzas respecto de distribuciones. [S14](../SOURCES.md#s14) | Herramientas especializadas pendientes. |
| Procesos | Markov finito en tiempo discreto y continuo. [S15](../SOURCES.md#s15) | Pendiente. |
| EDP | Solución numérica mediante elementos finitos. [S10](../SOURCES.md#s10) | Pendiente. |
| Paralelismo | Cálculo paralelo integrado. [S07](../SOURCES.md#s07) | Pendiente. |

## Alcance que puede utilizarse hoy

El subconjunto admite `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`,
`Simplify` y `D[expresión, variable]`. No incluye asignaciones, patrones,
multiplicación implícita ni todas las formas de derivación. La representación
textual del resultado usa la notación de SymPy; no se promete que pueda
reintroducirse directamente como código de Mathechan.

`Plot` exige extremos reales finitos y una sola variable libre. Rechaza
valores no reales o no finitos encontrados al muestrear, pero puede omitir
polos entre muestras. No tiene detección general de singularidades ni
muestreo adaptativo. Los archivos `.mchan` conservan resultados de texto;
el SVG se exporta como archivo separado. Abrir un cuaderno no ejecuta celdas.

La aplicación de escritorio, el proceso persistente, la cancelación robusta
y las herramientas especializadas de física estadística siguen pendientes.
Los límites de entrada del parser no constituyen aislamiento de seguridad.

## Prioridades

El desarrollo se orientará a problemas de física estadística que puedan
reproducirse con supuestos y resultados de referencia. La elección del motor
a largo plazo permanece abierta: SymPy permite evaluar este primer subconjunto,
pero no determina todas las decisiones futuras.

Las pruebas del repositorio verifican casos concretos de aritmética,
precedencia, derivación, errores, exportación y formato de cuaderno. No
demuestran exactitud universal, paridad con otro sistema o validación física.
Consulte [los objetivos](objetivos.md), [el lenguaje](lenguaje.md) y
[las fuentes](../SOURCES.md).