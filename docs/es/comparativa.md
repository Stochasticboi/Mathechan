# Comparativa con Mathematica

[English](../en/comparison.md) · [Inicio](../../README.md)

Mathematica es una referencia de diseño. Esta comparación separa sus capacidades
documentadas, la distribución inicial **v0.1.0** y **Mathechan 0.1.1**.
No se presenta un benchmark contra Mathematica ni una compatibilidad general.

| Área | Referencia documentada | Distribución v0.1.0 | Mathechan 0.1.1 |
|---|---|---|---|
| Lenguaje | Expresiones con cabeza y argumentos. [S11](../SOURCES.md#s11) | Parser restringido y aritmética exacta. | Añade igualdades inertes `==`, listas de hasta 64 elementos y operaciones científicas acotadas. |
| Núcleo | Interfaz textual. [S12](../SOURCES.md#s12) | CLI mediante SymPy 1.14. | Mantiene CLI sin sesión persistente; añade estado, exactitud representacional y detalles. |
| Cuadernos | Registro editable. [S03](../SOURCES.md#s03) | JSON `.mchan` inerte, sin editor gráfico. | Conserva formato y carga inerte; añade fuentes científicas de ejemplo sin resultados. |
| Álgebra y cálculo | Integración con supuestos. [S05](../SOURCES.md#s05) | `Expand`, `Simplify`, `D` y funciones elementales. | Añade `N`, `Factor`, `Together`, `Cancel`, `Substitute`, `Sum`, `Integrate`, `Solve` y `DSolve`, con límites explícitos. |
| Gráficos | Muestreo y controles de Plot. [S13](../SOURCES.md#s13) | 201 muestras y SVG univariado. | Comprueba restricciones originales muestreadas; mantiene muestreo fijo sin detector general de polos. |
| Interacción | Interfaces dinámicas. [S06](../SOURCES.md#s06) | Pendiente. | Pendiente. |
| Probabilidad | Esperanzas sobre distribuciones. [S14](../SOURCES.md#s14) | Herramientas especializadas pendientes. | Pendientes; una suma o integral genérica no es una biblioteca de física estadística. |
| Procesos | Markov finito discreto y continuo. [S15](../SOURCES.md#s15) | Pendiente. | Pendiente. |
| EDP | Elementos finitos. [S10](../SOURCES.md#s10) | Pendiente. | Pendiente; DSolve actual solo admite EDO para una función. |
| Paralelismo | Cálculo paralelo integrado. [S07](../SOURCES.md#s07) | Pendiente. | Pendiente. |

## Diferencias entre 0.1.0 y 0.1.1

El ZIP v0.1.0 admite `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`,
`Simplify`, `D` y `Plot`. Conserva ese alcance original; las operaciones
científicas siguientes se incorporan en 0.1.1. Véanse las
[notas de versión](versiones/0.1.1.md).

El bloque nuevo admite precisión solicitada de 1 a 1000 dígitos, álgebra racional
sobre Q y sustitución exacta con restricciones transportadas. Las sumas tienen
extremos enteros inclusivos y presupuestos finitos. La integración puede devolver
ramas condicionadas o una integral sin evaluar: no todo retorno es una respuesta
cerrada.

`Solve` distingue el dominio complejo por defecto y real explícito, conjuntos
de soluciones y sistemas lineales; conserva casos parametrizados no resueltos.
`DSolve` admite una EDO de orden 1 o 2 y datos iniciales, con residuos cuando
pueden comprobarse. Eso no prueba completitud ni dominio global.

Las condiciones son necesarias y parciales; `exact: true` indica ausencia de
Float, no demostración científica. `input` se ofrece cuando se verifica una
representación reutilizable; las aproximaciones Float y otros resultados pueden
dejarlo en null. `status` y `details` distinguen esos casos. Consulte
[el lenguaje](lenguaje.md) y [la decisión](../decisions/002-scientific-operations.md).

## Límites y prioridades

Plot puede omitir polos entre muestras y unir discontinuidades. No tiene
muestreo adaptativo ni validación general de singularidades. Los cuadernos
conservan texto; SVG se exporta por separado. Abrirlos no ejecuta celdas.

La interfaz gráfica, el proceso persistente, la cancelación robusta y las
herramientas de física estadística siguen pendientes. Los límites del parser
no garantizan tiempo/memoria ni aislamiento.

El desarrollo se orienta a problemas reproducibles con supuestos y referencias.
SymPy sostiene este bloque, sin cerrar la elección de motor a largo plazo.
Las pruebas verifican casos concretos; no acreditan paridad con Mathematica,
exactitud universal ni validación física general. Véanse
[objetivos](objetivos.md) y [fuentes](../SOURCES.md).
