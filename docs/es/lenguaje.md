# Lenguaje experimental v0

[English](../en/language.md)

Este documento describe **Mathechan 0.1.1**. Las operaciones científicas se
incorporan en esta versión; el ZIP anterior v0.1.0 conserva su alcance original.
Consulte [las notas de versión](versiones/0.1.1.md) y
[las descargas](../../README.md) antes de elegir una distribución.
La sección «En desarrollo: sesión numérica» describe un incremento posterior,
sin nueva release; no debe atribuirse al ZIP publicado de 0.1.1.

Mathechan 0.1.1 ofrece una consola experimental con un parser propio y evaluación
matemática mediante SymPy. La sintaxis toma como referencia convenciones de
Mathematica, pero no ofrece compatibilidad general con Wolfram Language.
Todavía no hay interfaz gráfica ni editor visual de cuadernos.

## Expresiones

| Elemento | Sintaxis y comportamiento |
|---|---|
| Enteros y decimales | Exactos: `0.1+0.2` produce `3/10` |
| Símbolos | Letras ASCII seguidas de letras o dígitos; distinguen mayúsculas |
| Constantes | `Pi`, `E`; `Infinity` en límites de integración |
| Operadores | `+`, `-`, `*`, `/`, `^`; multiplicación explícita |
| Agrupación | Paréntesis: `(x+1)^2` |
| Funciones de un argumento | `Sin`, `Cos`, `Exp`, `Log`, `Sqrt`, `Expand`, `Simplify` |
| Derivada | `D[expresión, símbolo]` |
| Gráfico | `Plot[expresión, {símbolo, mínimo, máximo}]`, solo como expresión raíz |
| Igualdad | `ladoIzquierdo == ladoDerecho`; ecuación inerte, sin asignación |
| Listas | `{a,b,...}`; hasta 64 elementos por lista, dentro de los límites del parser |

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

En la versión publicada 0.1.1 no se admiten asignaciones, patrones, definiciones de funciones del usuario,
unidades o sesiones con estado. `y[x]` como función desconocida se utiliza en el
contexto acotado de `DSolve`; no habilita definiciones arbitrarias. Los símbolos no se asumen
reales automáticamente. Las operaciones siguen las convenciones de SymPy y
sus dominios complejos, salvo restricciones explícitas como las de `Plot`.
El programa no proporciona todavía hipótesis físicas ni pasos de solución.

## En desarrollo: sesión numérica

Este incremento añade estado numérico local en la API `Session` y la consola
interactiva de Windows. Sigue en desarrollo, sin cambio de versión ni nueva
distribución: el ZIP v0.1.1 conserva la evaluación independiente de cada línea.
La función `evaluate(source)` continúa sin estado y rechaza asignaciones `=`.
`==` mantiene su significado de igualdad inerte.

Una sesión admite una asignación inmediata de raíz `nombre=expresión` por
llamada. El valor debe ser escalar, numérico, finito, sin símbolos libres ni
condiciones pendientes, y con estado incondicional. Se permiten números exactos
y aproximaciones Float; se preserva su precisión, sin convertirlos a racionales
ni a float de máquina para guardarlos.

```python
from mathechan import Session

session = Session()
session.evaluate("x=2")
session.evaluate("a=x+1")
session.evaluate("x=4")
print(session.evaluate("a").text)  # 3
```

`a` conserva el valor calculado al asignarla; no almacena una fórmula que cambie
al reasignar `x`. Cada objeto Session es independiente. La API también está en
`mathechan.session.Session`. El resultado sigue siendo `EvaluationResult`; la
asignación devuelve el valor, no una definición simbólica. Las llamadas del
ejemplo son separadas: no se añade ejecución de scripts con `;`.

El límite es 64 variables por sesión; reasignar una existente no ocupa otra
entrada. Se protegen constantes y nombres de operaciones, incluidos `Pi`, `E`,
`Infinity`, `Reals` y `Complexes`. Se rechazan listas, ecuaciones,
resultados condicionados y asignaciones simbólicas como `a=y+1` si `y` no tiene
valor numérico. Las funciones admitidas pueden calcular valores numéricos;
eso no crea definiciones de funciones del usuario. No hay `Clear` ni persistencia en disco.
Cerrar la consola o crear otra sesión no recupera variables de una anterior.

### Variables ligadas y contexto de resultados

Las variables formales de `D`, `Sum`, `Integrate`, `Solve`, `DSolve` y `Plot`
ocultan el valor global del mismo nombre en su ámbito; los otros parámetros
numéricos de sesión sí se aplican. Con `x=3`, `D[x^2,x]` devuelve `2*x` e
`Integrate[x,x]` muestra `x**2/2`, no derivada cero ni una integral de la constante
3. Para evaluar la derivada en 3 se utiliza `Substitute[D[x^2,x],x,3]`.
El resultado simbólico de `D[x^2,x]` no puede almacenarse mediante `a=D[x^2,x]`.

Los índices de sumas anidadas conservan su ámbito local. Por ejemplo,
`Sum[D[n^2,n],{n,1,3}]` sigue devolviendo 12; una variable de sesión `n`
no sustituye el índice ligado. Esta regla no añade asignaciones simbólicas.

`input` conserva su contrato de reutilización **sin estado**. Volver a introducir
una salida simbólica en una sesión puede cambiarla por sus valores globales:
con `x=3`, reintroducir `2*x` da 6. Para reproducir una expresión independiente,
usar `evaluate` sin estado o una sesión nueva y conservar condiciones por
separado. Un Plot que use parámetros de sesión solo ofrece `input` si puede
ser autosuficiente; si no, queda en None/null.

Abrir o guardar un `.mchan` no ejecuta celdas, crea asignaciones ni restaura
variables. El formato de cuaderno y sus resultados de texto no se convierten
en almacenamiento del estado de Session.

## Operaciones científicas de 0.1.1

### Aproximación, álgebra y sustitución

| Operación | Ejemplo | Alcance actual |
|---|---|---|
| `N` | `N[Pi,50]` | Escalar numérico sin símbolos libres; 15 dígitos solicitados por defecto o entero de 1 a 1000. |
| `Factor` | `Factor[x^2-1]` | Polinomios con coeficientes racionales, sobre Q. |
| `Together` | `Together[1/x+1/(x+1)]` | Combina denominadores en funciones racionales sobre Q. |
| `Cancel` | `Cancel[(x^2-1)/(x-1)]` | Cancela factores racionales conservando exclusiones originales como condiciones. |
| `Substitute` | `Substitute[x^2+y,x,1/3]` | Una sustitución exacta, resultado `y + 1/9`; admite anidación. |

`N` usa evaluación de precisión estricta: si no puede sostener la precisión
solicitada, devuelve un error útil. Los resultados aproximados conservan `Float`,
también cero; no se convierten a racionales. Pedir más dígitos a un valor ya
aproximado no recupera información perdida. `details.numeric_evaluations` registra
los dígitos significativos solicitados. La salida con Float tiene `input: null`
mientras el lenguaje no pueda preservar su carácter aproximado al reintroducirla.

Factorización y operaciones racionales no son `Simplify` general: por ahora
rechazan funciones, Float y coeficientes irracionales como `Pi` o `Sqrt[2]`.
Su control previo admite hasta ocho símbolos, grado estimado 256 por numerador
y denominador y una estimación conservadora de 4096 términos. Puede rechazar
una entrada antes de expandir; esas cotas no son un límite temporal garantizado.

`Substitute` conserva otros símbolos y transforma las restricciones originales.
`Substitute[x/x,x,0]` se rechaza; `Substitute[x/x,x,y]` conserva `y != 0`.
Solo admite valores escalares finitos: sustituir `Infinity` no equivale a tomar
un límite, aunque `Integrate` sí lo admita como extremo directo. No deshace
simplificaciones anteriores basadas en supuestos. Sustituir un parámetro puede
reevaluar una Integral pendiente y actualizar o eliminar condiciones de ramas;
los requisitos de realidad de los límites se conservan y transforman.

### Sumas e integración

`Sum[n^2,{n,1,10}]` devuelve `385`. Los extremos son enteros exactos e inclusivos;
un intervalo vacío devuelve cero. Cada suma admite 1000 términos y una evaluación
completa comparte un presupuesto de 2000 términos, incluidas sumas anidadas.
El índice está ligado localmente, puede ocultar un índice externo y no deja
asignaciones en una sesión. Los términos se evalúan con sus restricciones: una
singularidad no desaparece por cancelar primero una fórmula genérica.

`Integrate[x^2,x]` calcula una antiderivada **sin constante aditiva**.
`Integrate[Exp[-x^2],{x,-Infinity,Infinity}]` devuelve `sqrt(pi)`.
Los límites definidos son reales e independientes de la variable; pueden ser
infinitos reales. La antiderivada puede incluir comprobación por derivación en
`details`; una integral definida no queda verificada solo por devolver un valor.

Se conservan resultados `Piecewise`: sus condiciones describen **ramas
alternativas**, no requisitos que deban cumplirse todos a la vez. Una `Integral`
sin evaluar conserva `status: "unresolved"`. Las ramas divergentes se señalan;
un Piecewise sin construcción pendiente usa estado `conditional`.
no se solicita automáticamente valor principal. Las exclusiones del integrando
en su variable ligada se registran como `details.integrand_conditions`, no como
restricciones de una variable libre del resultado. Esto no sustituye un análisis
general de convergencia, ramas o dominio.

### Ecuaciones y ecuaciones diferenciales

`Solve[x^2==2,x]` trabaja sobre `Complexes` por defecto;
`Solve[x^2==2,x,Reals]` restringe a reales. La igualdad `==` se conserva como
ecuación, incluso si sus lados se simplifican a lo mismo; no es una asignación.
No se admiten cadenas `a==b==c`: utilice una lista.

`Solve[{x+y==3,x-y==1},{x,y}]` devuelve el conjunto de tuplas `{(2,1)}`.
Se admiten hasta ocho ecuaciones y variables distintas; los sistemas son lineales.
El resultado puede ser vacío, un conjunto finito, una familia parametrizada o
un conjunto condicionado. Los residuos por sustitución y el dominio aparecen
en `details` cuando se comprueban. Si el rango o grado depende de parámetros,
no se omiten casos degenerados: puede conservarse un resultado condicionado
con estado no resuelto. Las exclusiones originales del denominador se aplican
a las soluciones; no se presume que todo conjunto sea una lista reutilizable.
Una familia real sujeta a restricciones externas puede conservar estado
`conditional`, sin presentarse como conjunto real incondicional.

`DSolve[D[y[x],x]==y[x],y[x],x]` admite una EDO ordinaria para una función de
orden 1 o 2. Las derivadas superiores se escriben anidadas. Ejemplo con datos:

```text
DSolve[{D[D[y[x],x],x]+y[x]==0,y[0]==1,Substitute[D[y[x],x],x,0]==0},y[x],x]
```

Se admite una EDO y hasta cuatro datos iniciales; datos incompatibles o fuera
del alcance se rechazan. La solución anterior es `y(x)=cos(x)`. La salida puede
conservar constantes arbitrarias, varias ramas o una ecuación no resuelta.
`details.ode_residuals` e `initial_residuals` informan verificaciones locales;
un residuo nulo no prueba completitud de la familia, existencia/unicidad ni
dominio global. No se admiten sistemas de EDO ni derivadas parciales.
También se comprueban exclusiones originales retenidas en los puntos iniciales;
si su evaluación es incierta, no se presenta una verificación incondicional.

El cuaderno [scientific.mchan](../../examples/scientific.mchan) contiene fuentes
de ejemplo sin resultados guardados. Véase la
[decisión de alcance](../decisions/002-scientific-operations.md).

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
La sesión numérica descrita arriba corresponde al incremento en desarrollo:
la distribución publicada 0.1.1 y los comandos individuales permanecen sin estado.

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
`Session` se añade únicamente en el incremento en desarrollo descrito arriba.
`evaluate(source)` devuelve `EvaluationResult` con `kind`, `text`, `latex`,
`svg`, `points`, `input`, `conditions`, `warnings`, `status`, `exact` y `details`;
`to_dict()` produce contenido
serializable con los campos nuevos añadidos. Los errores
esperados se notifican con `MathechanError`. El parser traduce un árbol propio
a objetos SymPy sin interpretar la entrada como código Python.

Los campos son aditivos. `exact` indica ausencia de Float en la expresión
devuelta; no acredita que el problema esté completamente resuelto. `status`
distingue, entre otros, `evaluated`, `approximate`, `verified`, `unverified`,
`conditional`, `unresolved` y `no_solution`. `details` informa método, precisión
solicitada, residuos o verificaciones según la operación; no tiene todos los
campos en todos los resultados. `conditions` conserva condiciones necesarias
parciales y condiciones de ramas identificadas como tales. Una llamada anidada
puede propagar avisos y estado: no se interpreta `exact: true` como éxito universal.

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
