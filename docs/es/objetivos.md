# Objetivos de Mathechan

[English](../en/objectives.md) · [Inicio](../../README.md)

Mathechan es un proyecto personal de Edward Larroza H., estudiante de doctorado
en Física. Su objetivo es desarrollar un entorno abierto de escritorio para
formular, calcular y visualizar problemas de física teórica, con prioridad en
física estadística. El horizonte inicial es octubre de 2026 a octubre de 2031.

## Dirección científica

La base matemática debe permitir cálculo simbólico, métodos numéricos y
gráficos. Sobre ella se propone incorporar distribuciones de probabilidad,
promedios, fluctuaciones, correlaciones y funciones de partición. La utilidad
para estudiantes e investigadores requiere documentación de los supuestos,
ejemplos reproducibles y límites explícitos de cada operación.

La sintaxis se inspira en Mathematica, pero compartir notación no implica
compatibilidad general con sus programas. El lenguaje de Mathechan se
especificará a medida que se incorporen capacidades comprobables.

## Recorrido propuesto

| Periodo | Objetivo | Criterio de avance |
|---|---|---|
| 2026–2027 | Núcleo y lenguaje inicial | Evaluación desde consola, casos exactos y gráficos básicos documentados. |
| 2027–2028 | Escritorio y cuadernos | Editar, guardar, reabrir y ejecutar cálculos con estado identificable. |
| 2028–2029 | Herramientas de física estadística | Un conjunto acotado de problemas con resultados de referencia. |
| 2029–2030 | Métodos numéricos y visualización | Precisión, convergencia y rendimiento medidos antes de ampliar cobertura. |
| 2030–2031 | Consolidación | Distribución mantenible, documentación y revisión de ejemplos científicos. |

Las fechas orientan el trabajo; no garantizan cobertura ni equivalencia con
otros sistemas. El alcance se revisará según la dedicación disponible y los
resultados de cada etapa.

## Punto de partida

La versión 0.1.0 es un prototipo por consola con aritmética exacta, un conjunto
restringido de funciones simbólicas, derivación, gráficos SVG y archivos
`.mchan`. Esa versión no incluía interfaz gráfica ni herramientas de física
estadística. Consulte [la comparativa](comparativa.md) para separar lo disponible
de lo proyectado.

El código actual completa la etapa de física estadística finita con ensambles
canónicos, inferencia Shannon/KL y funcionales Rényi/Tsallis. Incluye soporte,
condiciones y persistencia de resultados. Las ampliaciones continuas, MaxCal,
inferencia con entropías generalizadas y ensambles cuánticos térmicos requieren
desarrollo posterior. Consulte el [lenguaje](lenguaje.md) para los límites y
la [cronología](../../README.md) para distinguir código y descargables.
