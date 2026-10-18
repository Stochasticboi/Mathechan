# Lenguaje experimental v0

[English](../en/language.md)

Mathechan 0.1 ofrece una consola experimental con un parser propio y evaluación
matemática mediante SymPy. La sintaxis toma como referencia convenciones de
Mathematica, pero no ofrece compatibilidad general con Wolfram Language.
Todavía no hay interfaz gráfica ni editor visual de cuadernos.

## Expresiones

| Elemento | Sintaxis y comportamiento |
|---|---|
| Enteros y decimales | Exactos: `0.1+0.2` produce `3/10` |
| Símbolos | Letras ASCII seguidas de letras o dígitos; distinguen mayúsculas |
| Constantes | `Pi`, `E` |
| Operadores | `+`, `-`, `*`, `/`, `^`; multiplicación explícita |
| Agrupación | Paréntesis: `(x+1)^2` |
| Funciones de un argumento | `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`, `Simplify` |
| Derivada | `D[expresión, símbolo]` |
| Gráfico | `Plot[expresión, {símbolo, mínimo, máximo}]`, solo como expresión raíz |

La potencia asocia a la derecha: `x^2^3` significa `x^(2^3)`. Tiene precedencia
sobre el signo: `-x^2` significa `-(x^2)`. Resta y división asocian a la izquierda.
Los resultados textuales usan por ahora la representación de SymPy, por ejemplo
`3*x**2`; esa salida no garantiza ser entrada válida del parser de Mathechan.
El campo adicional `input` contiene una entrada reutilizable verificada cuando
el resultado cabe en el subconjunto y límites actuales; si no, vale `null` en
JSON o `None` en Python. `text` conserva su formato anterior.

`I` sigue siendo un símbolo genérico. La constante imaginaria producida por
`Sqrt[-1]` tiene también `text: "I"`, pero su `input` es `Sqrt[-1]`; el símbolo
genérico tiene `input: "I"`. Las constantes matemáticas se escriben `Pi` y `E`.
Para reutilizar resultados, elegir `input`, no copiar automáticamente `text`.

El impresor cubre enteros, racionales, símbolos admitidos, sumas, productos,
potencias y `Sin`, `Cos`, `Exp`, `Log`. Usa `^` y corchetes. Se valida el candidato
mediante el parser, el evaluador y una igualdad estructural, sin una llamada
global adicional a `Simplify`. Resultados que requieran funciones no admitidas,
demasiados tokens o números demasiado largos no obtienen una entrada reutilizable.
No se intenta encontrar siempre la representación más corta posible.

No se admiten asignaciones, patrones, funciones del usuario, listas generales,
`Integrate`, `Solve`, unidades o sesiones con estado. Los símbolos no se asumen
reales automáticamente. Las operaciones siguen las convenciones de SymPy y
sus dominios complejos, salvo restricciones explícitas como las de `Plot`.
El programa no proporciona todavía hipótesis físicas ni pasos de solución.

## Consola

El ejecutable Windows sin argumentos abre una consola interactiva. Cada línea
se evalúa de forma independiente; `exit`, `quit` o `salir` terminan la sesión.
Con argumentos se ejecuta un comando:

```powershell
.\Mathechan.exe 'D[x^3,x]'
.\Mathechan.exe '1/3+1/6' --json
.\Mathechan.exe 'Sqrt[-1]' --input
.\Mathechan.exe 'Plot[Exp[-x^2],{x,-3,3}]' --output gaussian.svg
.\Mathechan.exe --demo --output gaussian.svg
```

La consola interactiva muestra un resumen de `Plot`; exportar SVG requiere
`--output` en un comando. No abre automáticamente ventanas de gráficos.
Al instalar el paquete Python también puede usarse `python -m mathechan` con
los mismos argumentos; ese comando requiere una expresión o `--demo`.

`--input` emite solo entrada reutilizable en stdout y condiciones/avisos en
stderr. Si no existe representación verificada, termina con código 2 y un error
claro. Es incompatible con `--json`. La consola interactiva añade una línea
`Entrada / Input` cuando la representación reutilizable difiere de `text`.

## Condiciones originales

Antes de simplificar se conservan restricciones de denominadores en divisiones
explícitas y bases de potencias con exponente conocido negativo. Por ejemplo,
`x/x` devuelve `text: "1"`, `input: "1"` y la condición `(x) != 0`;
`Simplify[(x^2-1)/(x-1)]` devuelve `x + 1` y conserva la condición de `x-1`.
Las condiciones se muestran en consola y aparecen en el campo JSON `conditions`.
Son texto informativo, no nueva sintaxis de comparación.

La entrada del resultado simplificado no incorpora automáticamente esas
restricciones. Conservar también `conditions` y `warnings`: volver a evaluar
`1` por sí solo no reconstruye la procedencia de `x/x`. Para un gráfico, `input`
conserva la fuente original ya validada, con sus restricciones explícitas.

Este seguimiento es conservador y parcial. No calcula el dominio universal,
no determina todos los cortes de rama y no incorpora automáticamente el dominio
de cada función o derivada. `Plot` comprueba denominadores originales en cada
muestra y rechaza el cero aunque se haya cancelado: `Plot[x/x,{x,-1,1}]` falla
en 0. También rechaza condiciones con parámetros sin valor que no puede comprobar.
Los extremos se comprueban con sus valores simbólicos exactos: un denominador
`Sin[x]` en el extremo `Pi` se detecta como cero antes de redondear coordenadas.
Los ceros entre muestras siguen pudiendo pasar inadvertidos; no hay una
inferencia general de polos ni un criterio de cercanía a cero con tolerancia.
Ver [decisión sobre resultados y dominios](../decisions/001-results-and-domains.md).

## Límites numéricos y de entrada

El parser admite hasta 4096 caracteres, 256 tokens, 40 niveles sintácticos,
100 caracteres por número y exponentes numéricos de valor absoluto hasta 1000.
Estas restricciones no garantizan límites de tiempo o memoria. Una operación
simbólica puede tardar; no hay aislamiento ni timeout duro.

`Plot` toma 201 muestras equidistantes y genera un SVG de 640×340. Exige una
sola variable libre y un rango real finito creciente. Rechaza valores complejos,
indefinidos o no representables como float finito, así como escalas que no
puedan representarse. El muestreo fijo puede omitir singularidades y unir
discontinuidades entre muestras: no sustituye una verificación científica
del gráfico ni detecta todos los polos. El SVG se guarda en la ruta solicitada.

## API Python

`from mathechan import evaluate, MathechanError`.
`evaluate(source)` devuelve `EvaluationResult` con `kind`, `text`, `latex`,
`svg`, `points`, `input`, `conditions` y `warnings`; `to_dict()` produce contenido
serializable con los campos nuevos añadidos. Los errores
esperados se notifican con `MathechanError`. El parser traduce un árbol propio
a objetos SymPy sin interpretar la entrada como código Python.

## Cuadernos JSON v0.1

La extensión inicial es `.mchan`. Cada documento contiene exactamente
`format`, `version`, `versions` y `cells`. `format` es `mathechan-notebook` y
`version` es `0.1`. `versions` contiene las cadenas `kernel` y `sympy`.
Cada celda contiene `id` único, `kind` (`code` o `markdown`), `source` y `results`.
Los resultados persistidos solo admiten objetos `{"kind":"text","text":"…"}`.

Abrir y guardar nunca evalúa celdas ni interpreta markdown. El texto debe ser
Unicode válido codificable en UTF-8. Se rechazan campos desconocidos, ids y
claves JSON duplicados, versiones de formato desconocidas y constantes JSON
no estándar. El tamaño máximo es 2 MB. Los resultados guardados son históricos:
no prueban que el código actual haya sido ejecutado.

API en `mathechan.notebook`: `new_notebook()`, `new_cell(source, kind="code")`,
`validate_notebook(document)`, `load_notebook(path)`, `save_notebook(document, path)`.
No se admiten HTML o SVG embebidos en este formato inicial. El archivo
`examples/gaussian.mchan` contiene fuentes sin resultados precalculados;
`Exp[-x^2]` por sí sola no es una densidad normalizada.
