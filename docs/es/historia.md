# Historia y antecedentes

[English](../en/history.md) · [Inicio](../../README.md)

## Origen de Mathechan

Mathechan comenzó el **18 de octubre de 2026** como proyecto personal de
Edward Larroza H., estudiante de doctorado en Física. La intención es construir
un programa abierto para formular, calcular y visualizar problemas de física
teórica, con especial interés en física estadística.

El horizonte inicial abarca **2026–2031**. La versión 0.1.0 es un prototipo por
consola; la aplicación de escritorio pertenece al desarrollo previsto.
La sintaxis familiar y la integración de cálculo y gráficos toman a Mathematica
como referencia técnica, sin plantear una réplica completa.

El 19 de octubre de 2026, la versión 0.1.1 amplió la consola con evaluación
numérica de precisión configurable, álgebra racional, sustitución, sumas finitas,
integración y resolución de ecuaciones y EDO de alcance acotado. Sus
[notas de versión](versiones/0.1.1.md) documentan capacidades y límites.

## Mathematica como antecedente

La siguiente selección recoge hitos relevantes para el proyecto. Las fechas
mensuales proceden del [historial oficial de versiones](../SOURCES.md#s01);
las fechas precisas y capacidades se documentan en las fuentes indicadas.

| Fecha | Versión | Hito |
|---|---|---|
| 23 junio 1988 | 1.0 | Lanzamiento, tras el desarrollo de 1986–1988. [S02](../SOURCES.md#s02) |
| Enero 1991 | 2.0 | EDO, compilación numérica y comunicación entre procesos. [S01](../SOURCES.md#s01) |
| 3 septiembre 1996 | 3.0 | Expresiones matemáticas editables y documentos programables. [S04](../SOURCES.md#s04) |
| Mayo 1999 | 4.0 | Mejoras numéricas e intercambio de archivos. [S01](../SOURCES.md#s01) |
| 23 junio 2003 | 5.0 | Renovación numérica y estadística integrada. [S05](../SOURCES.md#s05) |
| Mayo 2007 | 6.0 | Interfaces dinámicas. [S06](../SOURCES.md#s06) |
| Noviembre 2008 | 7.0 | Cálculo paralelo incorporado. [S07](../SOURCES.md#s07) |
| Noviembre 2010 | 8.0 | Probabilidades, esperanzas y distribuciones. [S08](../SOURCES.md#s08) |
| Noviembre 2012 | 9.0 | Procesos aleatorios y Markov. [S09](../SOURCES.md#s09) |
| Julio 2014 | 10.0 | Elementos finitos para EDP. [S10](../SOURCES.md#s10) |
| Abril 2019 | 12.0 | Optimización y asintótica ampliadas. [S01](../SOURCES.md#s01) |
| Enero 2024 | 14.0 | Integración numérica ampliada. [S01](../SOURCES.md#s01) |
| Julio 2026 | 15.0.1 | Correcciones, estabilidad y seguridad. [S01](../SOURCES.md#s01) |

El diseño temprano del cuaderno buscaba conservar un registro editable y
compartible del trabajo con el núcleo de cálculo. Esta motivación está descrita
en el resumen del artículo de Theodore Gray de 1996; aquí se utilizó ese
resumen, no su archivo adjunto. [S03](../SOURCES.md#s03)

## Orientación para el desarrollo

Esta historia sugiere construir primero un núcleo coherente, documentar la
notación y conservar los cálculos antes de ampliar la cobertura. La edición
matemática bidimensional, la interacción y los solucionadores especializados
requieren desarrollos propios.

Para Mathechan, la prioridad será un conjunto pequeño de problemas
reproducibles, con supuestos y límites explícitos. Las fechas de Mathematica
no permiten estimar por sí solas el esfuerzo necesario ni equivalen a etapas
del calendario de Mathechan.

La selección se apoya en fuentes públicas oficiales consultadas el
**18 de octubre de 2026**. No describe código interno, costes o tamaño del
equipo de Wolfram. Véase [el registro de fuentes](../SOURCES.md).
