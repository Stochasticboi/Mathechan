# Lenguaje experimental v0

[English](../en/language.md)

Este documento describe el código **0.2.0.dev4**. La descarga publicada
**0.2.0-dev0** incluye las sesiones y el álgebra ampliada, pero no los límites
de dev1, las ampliaciones de cálculo y reglas de dev2 ni las cartas curvilíneas
de dev3 ni el álgebra lineal de dev4. Las subsecciones
históricas de 0.1.1 registran el alcance de esa versión anterior.
Consulte [las descargas](../../README.md) para elegir una distribución.

Mathechan ofrece una consola experimental con un parser propio y evaluación
matemática mediante SymPy. La sintaxis toma como referencia convenciones de
Mathematica, pero no ofrece compatibilidad general con Wolfram Language.
Todavía no hay interfaz gráfica ni editor visual de cuadernos.

## Expresiones

| Elemento | Sintaxis y comportamiento |
|---|---|
| Enteros y decimales | Exactos: `0.1+0.2` produce `3/10` |
| Símbolos | Letras ASCII seguidas de letras o dígitos; distinguen mayúsculas |
| Constantes | `Pi`, `E`; `Infinity` en rangos, límites y series |
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

## Álgebra lineal: desarrollo 0.2.0.dev4

Las funciones aceptan `Matrix[{{...},{...}}]` y listas rectangulares anidadas.
Una lista plana representa un vector sin orientación en `Dot`; `Vector[{...}]`
es una matriz columna explícita. Las entradas son escalares exactos, simbólicos
o aproximados. Los decimales literales siguen siendo racionales exactos:
`N[matriz,50]` o `N[lista,50]` produce entradas aproximadas a la precisión solicitada.

| Operación | Sintaxis y resultado |
|---|---|
| Tamaño | `Dimensions[A]`: lista de dimensiones; un vector plano tiene una dimensión. |
| Aritmética | `A+B`, `A-B`, `-A`, `c*A`, `A/c`; suma/resta con dimensiones iguales y divisor escalar no nulo. |
| Producto | `Dot[A,B]` o `A.B`; admite cadenas y contracciones matriz-vector/vector-matriz. |
| Transpuesta y traza | `Transpose[A]`, `Tr[A]`; la transpuesta no conjuga. |
| Determinante e inversa | `Det[A]`, `Inverse[A]`; matriz cuadrada, inversa condicionada a determinante no nulo. |
| Rango | `MatrixRank[A]`; cuando depende de parámetros devuelve una rama condicionada, sin declararla universal. |
| Sistemas | `LinearSolve[A,b]` resuelve `A x=b`; admite varios segundos miembros como matriz. |
| Espectro | `Eigenvalues[A]`, `Eigenvectors[A]`; véanse las convenciones siguientes. |
| Potencia | `MatrixPower[A,n]` o `A^n`, con entero entre -32 y 32; exponente negativo requiere inversa. |
| Exponencial | `MatrixExp[A]`, incluyendo matrices no diagonalizables. |

`A*B` conserva el producto matricial histórico entre matrices; no significa
producto elemento a elemento. Para expresar el producto de forma explícita se
recomienda `Dot` o `.`. Entre vectores planos use `Dot`; `*` entre dos vectores
se rechaza por ambiguo. La contracción es bilineal: no conjuga componentes
complejas. El punto tiene precedencia mayor que `*` y menor que `^`;
`1.25` sigue siendo un único decimal. Los vectores resultado pueden sumarse,
restarse y escalarse, preservando su forma de lista.

```wolfram
Dot[{{1,2},{3,4}},{{5,6},{7,8}}]
Det[{{1,2},{3,4}}]
LinearSolve[{{2,0},{0,3}},{4,9}]
MatrixExp[{{0,1},{0,0}}]
```

Estos ejemplos dan, respectivamente, una matriz con filas `{19,22}` y `{43,50}`,
`-2`, `{2,3}` y una matriz con filas `{1,1}` y `{0,1}`.

Los sistemas exactos pueden devolver una solución única, una familia con
parámetros internos independientes, o el conjunto vacío con estado `no_solution`.
Si la matriz es constante y la compatibilidad depende del segundo miembro,
se conservan ecuaciones como `b==0` junto con la solución condicionada.
No se sustituye un sistema incompatible por mínimos cuadrados. Las matrices
rectangulares con coeficientes paramétricos requieren especialización cuando
no se puede decidir la rama. Las condiciones de inversa, rango y espacios
propios son ejecutables: sobreviven a sustituciones y al guardado de sesiones.
Una especialización excluida exige recalcular desde la matriz original.

Los autovalores se ordenan mediante `default_sort_key` de SymPy, con
multiplicidad algebraica. Los autovectores son vectores derechos no normalizados,
agrupados por autovalor; `details.eigenvalues_for_vectors` indica el emparejamiento.
Una matriz defectuosa devuelve sólo los vectores independientes disponibles y
`basis_complete=false`, sin rellenar con vectores nulos. Las diagonales simbólicas
conservan una base universal; sus multiplicidades pueden requerir especialización.
El cálculo decimal espectral usa los racionales binarios almacenados y evalúa
el resultado después; no modela la incertidumbre de los datos ni certifica dígitos.

Los sistemas aproximados registran residuos y, cuando procede, una estimación
del condicionamiento. Los autovectores aproximados incluyen comprobaciones
de residuo y avisos de bases mal condicionadas. El rango numérico no usa una
tolerancia configurable: un pivote muy pequeño puede contar como no nulo.
Aumentar la precisión no recupera información perdida en datos aproximados.

Alcance: álgebra densa de hasta ocho filas/columnas y 64 entradas, entrada de
256 operaciones simbólicas y salida de 4096 operaciones/64 entradas. Las
operaciones espectrales admiten hasta 4×4 y ocho símbolos; para orden cuatro
con parámetros o entradas aproximadas se requiere forma triangular. Una
matriz simbólica densa 3×3 admite hasta tres símbolos y 64 operaciones de entrada.
La precisión de entrada espectral se limita a 80 dígitos. Son presupuestos
estructurales, no límites duros de tiempo o memoria. No hay matrices dispersas
ni bibliotecas numéricas nativas adicionales en esta etapa.

## Cálculo y reglas: desarrollo 0.2.0.dev3

Esta sección corresponde al código actual, posterior al ZIP 0.2.0-dev0.
La sintaxis se aproxima a Wolfram en los casos descritos; no se declara
compatibilidad con todo su sistema de reglas, series o evaluación.

### Sustitución mediante reglas

```wolfram
(x^2+a*x) /. x -> 2
ReplaceAll[x^2+a*x,Rule[x,2]]
Substitute[x^2+a*x,{x->2}]
```

Las tres formas devuelven `4+2*a`. Sigue admitiéndose
`Substitute[expr,x,valor]`, con el alcance local previo de su variable.
`ReplaceAll` evalúa la expresión y las reglas en el contexto de sesión;
los valores ya asignados pueden cambiar qué partes quedan disponibles para
reemplazar. El lado izquierdo de una regla inmediata también se evalúa.

Una lista se aplica en un solo recorrido: `{x,y}/.{x->y,y->2}` da `{y,2}`.
El primer reemplazo aplicable gana y no se vuelve a recorrer lo recién insertado.
Para pasos sucesivos, encadenar: `x/.x->y/.y->2` da `2`.
Se admiten partes exactas, listas, matrices y ecuaciones dentro de los tipos
actuales; no se implementan el reemplazo de cabezas ni el emparejamiento completo
por atributos de Wolfram. `//.` no está implementado.

Las reglas son datos guardables: `r=x->a` captura el valor actual de `a`;
`r=x:>a` (`RuleDelayed`) calcula el lado derecho al aplicar la regla.
Cargar una sesión no ejecuta ese cuerpo diferido.

```wolfram
Sin[x]+Sin[y] /. Sin[t_] -> t^2
{2,1/2,z} /. t_Integer :> t+1
{N[1/2,20],1/2} /. t_Real -> 0
```

Los patrones nombrados admitidos son `t_`/`t_Scalar` para escalares,
`t_Integer` para enteros exactos y `t_Real` para números Float aproximados.
`_Real` no equivale al constructor previo `RealPattern`, que comprueba la
propiedad matemática de ser real. Los decimales literales conservan la semántica
exacta anterior: `0.5` es racional, mientras `N[1/2,20]` es Float.
No se admiten comodines anónimos, secuencias `__`, condiciones de patrón ni
el sistema general de atributos. Hasta ocho patrones y 64 reglas por llamada;
los nombres protegidos no pueden usarse como parámetros de patrón.

Las reglas transforman también restricciones e hipótesis usadas en el cálculo.
`x/x/.x->0` y `Assuming[x>0,Sqrt[x^2]/.x->-1]` se rechazan aunque la expresión
se hubiera simplificado. No se reescriben operadores ligados pendientes ni
restos `O` con `ReplaceAll`; sustituir los parámetros antes de calcular, usar
`Substitute` cuando corresponda, o extraer explícitamente `Normal`.

### Derivadas y cálculo vectorial

```wolfram
D[Sin[x],{x,3}]
D[x^2*y^3,{x,2},y]
Grad[x^2+y^2,{x,y}]
Div[{x^2,y^2,z^2},{x,y,z}]
Curl[{-y,x,0},{x,y,z}]
Jacobian[{x*y,x+y},{x,y}]
Hessian[x^2+y^2,{x,y}]
```

Se admiten derivadas sucesivas y mixtas con órdenes positivos hasta 32 en total,
parámetros simbólicos y las funciones expuestas por Mathechan. No se presupone
que un símbolo sea real; por ejemplo, algunas derivadas de `Abs` quedan formales.
Las condiciones originales se conservan. No se certifica diferenciabilidad global.

Sin tercer argumento se usa `Cartesian`, de una a ocho variables. `Curl`
requiere tres componentes y variables. `Grad`, `Curl`, `Jacobian` y `Hessian`
devuelven matrices inmutables; `Div` devuelve un escalar. Se comprueban dimensiones
y se limita la salida a 64 elementos/4096 operaciones, con entrada de hasta
256 operaciones/ocho símbolos. No añade álgebra matricial general.

El tercer argumento selecciona `Cartesian`, `Cylindrical` o `Spherical`,
como nombre o cadena (`Spherical` y `"Spherical"` son equivalentes).
Las cartas curvilíneas son tridimensionales:

| Carta | Variables, en orden | Dominio regular |
|---|---|---|
| `Cylindrical` | `{rho,phi,z}`: radio, azimut, altura | Coordenadas reales, `rho>0`. |
| `Spherical` | `{r,theta,phi}`: radio, ángulo polar desde +z, azimut | Coordenadas reales, `r>0`, `0<theta<Pi`. |

El azimut se trata como coordenada real local, sin imponer un corte periódico.
Los vectores de entrada y salida tienen componentes en la **base ortonormal
local**, no en la base coordenada. `Grad` de un vector devuelve la matriz del
gradiente covariante: fila i = componente y columna j = dirección de derivación
ortonormal. `Hessian` devuelve el Hessiano geométrico en esa misma base;
incluye la variación de la base y no es la tabla de segundas parciales crudas.

```wolfram
Grad[r^2,{r,theta,phi},"Spherical"]             (* {2*r,0,0} *)
Div[{rho,0,z},{rho,phi,z},Cylindrical]          (* 3 *)
Curl[{0,rho,0},{rho,phi,z},"Cylindrical"]      (* {0,0,2} *)
Hessian[r^2/2,{r,theta,phi},Spherical]          (* identidad 3x3 *)
Jacobian[{r,0,0},{r,theta,phi},Spherical]      (* diagonal {1,0,0} *)
Jacobian[{r,0,0},{r,theta,phi},Spherical,"Orthonormal"]
(* identidad 3x3, igual a Grad del mismo campo *)
```

`Jacobian` usa por defecto `Components`: derivadas parciales ordinarias de
las funciones componentes respecto de las variables, también con salida
rectangular. `Orthonormal`, como cuarto argumento, requiere un campo de tres
componentes y devuelve el gradiente vectorial geométrico 3x3. No convierte un
mapa de coordenadas automáticamente en un campo físico.

Los requisitos de la carta acompañan al resultado aunque se simplifique a una
constante y se comprueban tras sustituciones. Los ejes y el origen quedan fuera
del dominio regular; una expresión simplificada finita no certifica su extensión
a esos puntos. No se admiten cartas arbitrarias ni tensores de rango superior.

### Series y aproximaciones locales

```wolfram
Series[Sin[x],{x,0,5}]
Series[Exp[x],{x,1,2}]
Series[1/(x+1),{x,Infinity,2}]
Normal[Series[Exp[x],{x,0,2}]]
```

El orden n **incluye el término de grado n**, como en la forma usual de Wolfram:
el primer ejemplo da `x-x^3/6+x^5/120+O(x^6)`. Admite n de 0 a 31, centros
reales numéricos y ±Infinity. Un tercer argumento `Left` o `Right` selecciona
el camino real lateral; en infinito la orientación la fija el punto.
Incluye Taylor/Maclaurin, Laurent/Puiseux y expansiones asintóticas básicas
cuando el backend las determina. No se garantiza un radio de convergencia.

`status=series` conserva la naturaleza local y truncada. `exact=true` sólo
indica ausencia de Float; no convierte el resto en una cota numérica certificada.
`Normal` elimina el `O` explícitamente y conserva una advertencia y procedencia
de aproximación; no establece una igualdad global con la función original.
Las series, incluso con centro infinito, y su orden se pueden guardar en sesión.
Una identidad sin resto que sólo vale localmente, sin entorno determinado, no
se almacena como definición global. Los casos paramétricos degenerados se
excluyen explícitamente: sustituir los parámetros antes de desarrollar permite
estudiar otra rama. Los fallos conservan una petición sin resolver.

### Sumas y productos ampliados

```wolfram
Product[k,{k,1,5}]
Sum[n^2,{n,1,m}]
Sum[j,{i,1,3},{j,1,i}]
Sum[1/n^2,{n,1,Infinity}]
Sum[q^n,{n,0,Infinity}]
```

Los ejemplos determinados dan `120`, una expresión condicionada a m entero,
`10` y `Pi^2/6`; la geométrica conserva la condición de convergencia y una
rama pendiente. Hasta tres rangos: el primero es el exterior. Los límites
interiores pueden depender de índices exteriores; su integralidad debe poder
comprobarse. La variable ligada no hereda su valor de sesión.

Un rango finito invertido se considera vacío: suma 0 y producto 1, conservando
la convención previa de Mathechan, sin adoptar la convención de Karr.
Se mantienen 1000 términos por rango y 2000 en total, compartidos entre llamadas
anidadas y reglas. Los límites simbólicos requieren enteros; la convergencia
infinita sólo se acepta cuando el método la determina. Divergencias y casos
indecidibles permanecen como `Sum`/`Product` inertes, sin devolver un infinito
escalar. Para productos infinitos se usa el criterio de convergencia a un valor
finito **no nulo**; un límite de productos parciales igual a cero se informa
como producto divergente bajo esa convención. Dominios no verificables quedan
pendientes; no se cancelan términos indefinidos silenciosamente.

### Integración iterada y funciones especiales

`Integrate` conserva antiderivadas, integrales definidas e impropias, parámetros
y funciones especiales admitidas por el backend. Por ejemplo,
`Integrate[Exp[-x^2],x]` produce una expresión con `erf`, aunque esa función
no tenga todavía una llamada pública de entrada reutilizable.

```wolfram
Integrate[x*y,x,y]
Integrate[1,{x,0,1},{y,0,x}]
Integrate[1,{x,0,1},{y,0,Sqrt[x]}]
Integrate[Exp[-a*x],{x,0,Infinity}]
```

Se admiten hasta tres variables distintas, con el primer rango como exterior.
Los límites dependientes deben ser reales y definidos sobre todo el intervalo
exterior; las regiones no verificables se rechazan conservadoramente.
El ejemplo con `Sqrt[x]` da `2/3`; cambiar el rango exterior a [-1,0] se rechaza.
No se certifican las hipótesis de Fubini ni se intercambia el orden de integración.
Las antiderivadas omiten constantes aditivas; las condiciones paramétricas y
ramas pendientes se conservan. No se sustituye automáticamente una integral
simbólica por una aproximación numérica.

Los presupuestos anteriores son estructurales, no límites efectivos de tiempo
o memoria ni una garantía de escalabilidad. Estas operaciones no añaden una
interfaz gráfica ni las herramientas especializadas de las etapas posteriores.

## En desarrollo: lenguaje y sesiones

La API `Session` y la consola interactiva de Windows mantienen estado local
desde 0.2.0.dev0. El ZIP anterior v0.1.1 conserva su alcance original.
La función `evaluate(source)` continúa sin estado y rechaza asignaciones `=`.
`==` mantiene su significado de igualdad inerte.

Una sesión admite una asignación inmediata de raíz `nombre=expresión` por
llamada. Admite valores escalares numéricos o simbólicos y conserva sus
restricciones originales. Se permiten números exactos y aproximaciones Float;
se preserva su precisión, sin convertirlos a racionales ni a float de máquina.

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

El límite es 64 definiciones por sesión; reasignar una existente no ocupa otra
entrada. Se protegen constantes y nombres de operaciones, incluidos `Pi`, `E`,
`Infinity`, `Reals` y `Complexes`. Se admiten escalares, listas, matrices y
expresiones retenidas; se rechazan ecuaciones y resultados no verificados.
Una asignación como `a=y+1` conserva una expresión calculada en ese momento.
Cerrar la consola no guarda automáticamente las variables.

La API `session.save("trabajo.json")` guarda explícitamente el estado, y
`Session.load("trabajo.json")` crea otra sesión a partir de ese archivo. El
formato `mathechan-session` v0.1 conserva definiciones, condiciones y bits Float.
Admite hasta 2 MB y 64 definiciones; rechaza campos desconocidos, claves
duplicadas y constructores fuera de la lista admitida. Cargar no ejecuta los
árboles de definiciones diferidas ni las expresiones `Hold`. No usa pickle ni
interpreta cadenas como código. No es el formato de cuadernos `.mchan`.

`session.evaluate("Clear[x]")` elimina únicamente la definición de `x` en esa
sesión y libera su entrada; la siguiente evaluación de `x` devuelve el símbolo.
El nombre se toma sin sustituir su valor. Los valores ya calculados de otras
variables se conservan: después de `x=2`, `a=x+1` y `Clear[x]`, `a` sigue siendo 3.
Si el nombre no tiene definición, la llamada no cambia el estado.

`Clear` exige un único nombre de variable y solo se admite como comando
independiente de sesión. Constantes y nombres de operaciones, incluido `Clear`,
están protegidos. Argumentos como `Clear[x+1]`, varios nombres o llamadas anidadas
se rechazan sin borrar valores. El resultado tiene `kind: "session"`,
`input: null` y `details.clear` con `name` y el booleano `removed`; su texto es una
confirmación, no una expresión matemática. `evaluate("Clear[x]")` sin sesión
no está admitido. `ClearAll[]` elimina las definiciones de la sesión; las
hipótesis se administran por separado con `ClearAssumptions[]`.

`session.evaluate("Definition[x]")` consulta el valor guardado de `x` sin
evaluarlo de nuevo ni modificar la sesión. Por ejemplo, después de `x=2`,
`a=x+1` y `x=4`, `Definition[a]` muestra `a = 3`, no la fórmula original.
Si no existe una definición, lo indica sin crearla; después de `Clear[x]`,
`Definition[x]` informa que no hay definición.

La consulta exige un único nombre sin evaluar y solo se admite como comando
independiente de sesión. Los nombres protegidos, incluido `Definition`, y los
argumentos compuestos o llamadas anidadas se rechazan. `evaluate` sin sesión
no admite esta consulta. No enumera variables ni describe funciones incorporadas.
Devuelve `kind: "session"`, `input: null` y `details.definition` con `name` y
`defined`; cuando existe el valor, añade `value` (texto) y `exact` (booleano).
El resultado conserva la distinción exacta/aproximada y los dígitos del valor
almacenado; su `status: "evaluated"` indica una consulta completada. `text` y
`value` son información para inspección, no entrada reutilizable garantizada.
Esta consulta no proporciona historial ni restaura valores de otras sesiones.

### Definiciones simbólicas y funciones

Las asignaciones guardan expresiones calculadas, no reglas diferidas. Si se
ejecuta `f=x^2` y después `x=3`, `f` conserva `x^2`. Para evaluar en un punto,
usar `Substitute[f,x,3]`. Las condiciones del cálculo original acompañan a la
definición y se comprueban al sustituir: guardar `f=x/x` no permite después
`Substitute[f,x,0]`.

`Define[f,{x,y},a*x+y]` define una función con parámetros locales distintos.
Los valores globales disponibles, como `a`, se capturan al definirla. Se llama
con `f[2,3]`. `With[{x,y},{2,3},x+y]` evalúa con valores locales simultáneos sin modificar
los nombres de la sesión. No es la sintaxis completa de Wolfram Language.

`SetDelayed[a,x+1]` guarda una expresión que usa el estado actual al consultar
`a`. `DefineDelayed[f,{x},expresión]` hace lo mismo para una función.
`DefinePattern[f,{IntegerPattern[n]},If[n<=1,1,n*f[n-1]]]` permite una función
recursiva con argumento entero. También existen `RealPattern` y `ScalarPattern`;
se admite una definición por nombre, sin sobrecargas ni patrones arbitrarios.
`If[condición,sí,no]` solo evalúa la rama elegida; una condición no decidida
conserva la llamada retenida. Cada evaluación admite 32 llamadas diferidas
anidadas y 10000 pasos; excederlos produce un error, no una recursión indefinida.

Si un parámetro y un símbolo capturado tienen el mismo nombre, `Definition`
usa etiquetas distintas para mostrarlos. Por ejemplo, `a=x` seguido de
`Define[g,{x},x+a]` conserva el `x` libre de `a`: `g[2]` da `x+2`. La consulta
muestra `g[arg1] = arg1 + x`; `parameters` conserva el nombre original y
`parameter_labels` identifica la etiqueta de presentación.

### Hipótesis y lógica

Se admiten `==`, `!=`, `<`, `<=`, `>` y `>=`, y los operadores `And`, `Or`,
`Not`, con `True` y `False`. Una condición no es una asignación. Las
pertenencias se expresan con `Element[x,Reals]`, `Complexes`, `Integers` o
`Element[x,Interval[0,1]]` (intervalo real cerrado).

`Assuming[condición,expresión]`, `Refine[expresión,condición]` y
`Simplify[expresión,condición]` usan hipótesis locales. Por ejemplo,
`Refine[Sqrt[x^2],Element[x,Reals]]` da `Abs(x)` y
`Assuming[x>0,Sqrt[x^2]]` da `x`; sin hipótesis la raíz no se convierte en `x`.
Las condiciones necesarias se conservan en el resultado.

En una sesión, `Assume[x>0]` agrega una hipótesis persistente en memoria,
`Assumptions[]` la consulta y `ClearAssumptions[]` la elimina. No afecta a
otras sesiones. Las contradicciones sencillas se rechazan antes de cambiar
el estado. No hay un decisor completo de consistencia de condiciones
multivariables o trascendentes: las hipótesis no decididas siguen siendo
condiciones, no hechos demostrados por el programa.

Los gráficos comprueban las hipótesis en cada muestra y rechazan las que no
pueden validar. Una integral definida no usa una rama simplificada bajo
hipótesis si no puede comprobarlas en todo su intervalo. `Solve` filtra los
candidatos finitos excluidos por las hipótesis; las familias no verificadas
conservan condiciones o quedan sin resolver.

### Contenedores, retención y precisión

`Vector[{1,x,3}]` representa un vector columna y `Matrix[{{1,2},{3,4}}]`
una matriz inmutable rectangular, con hasta 64 elementos escalares. Una lista
sigue siendo una lista; el álgebra matricial general pertenece a una etapa
posterior. `Hold[1/0]` conserva el árbol sin ejecutar la división;
`ReleaseHold[Hold[1/0]]` intenta evaluarlo y detecta el error.

`Display[Pi,8]` cambia el texto de presentación, conservando internamente el
valor exacto. `N[Pi,50]` sí calcula una aproximación a la precisión solicitada.
`NumericError[Pi,20]` compara evaluaciones a 20 y 30 dígitos: informa una
estimación de diferencia absoluta, **no una cota certificada**. Aumentar los
dígitos no recupera información perdida en entradas aproximadas.

`Log`, `Sqrt`, `ArcSin`, `ArcCos` y `ArcTan` usan ramas principales complejas.
Se conservan exclusiones conocidas como el cero de `Log`, los puntos ±i de
`ArcTan` y los polos enteros no positivos de `Gamma`. Los avisos identifican
el alcance parcial del análisis: no se certifican todos los cortes de rama,
dominios ni singularidades de expresiones compuestas.

`AnalyzeDomain[expresión,x,Reals]` consulta el dominio real continuo con las
exclusiones originales. Con `Complexes` informa valores finitos y describe
cortes de rama conocidos, sin confundirlos con un dominio holomorfo global.
El campo `details.complete` distingue los casos determinados de los pendientes.
`CertifiedN[Sqrt[2],40]` añade un intervalo racional y una cota absoluta respecto
del Float emitido, certificados mediante aislamiento polinómico exacto. Solo
admite constantes algebraicas reales exactas, grado hasta 32 y 10–200 dígitos;
no certifica `Pi`, datos Float ni incertidumbre experimental.

`FullSimplify[expresión]` y `FullSimplify[expresión,hipótesis]` comparan candidatos
de simplificación, combinación racional y trigonometría, verificando su
equivalencia en el contexto indicado. Tienen un límite de 256 operaciones y
ocho símbolos; no garantizan una forma mínima universal. Las restricciones
originales acompañan al resultado y a las definiciones guardadas.

### Álgebra en desarrollo: Collect y Apart

Estas operaciones pertenecen al código en desarrollo, no al ZIP v0.1.1.

| Operación | Ejemplo | Alcance |
|---|---|---|
| `Collect[expresión,x]` | `Collect[a*x+b*x+x^2,x]` | Agrupa por potencias de `x`, expandiendo un polinomio acotado sobre Q. |
| `Apart[expresión,x]` | `Apart[1/(x*(x+1)),x]` | Fracciones parciales racionales respecto de `x`, con parámetros simbólicos. |

Reutilizan los límites de álgebra racional: hasta ocho símbolos, grado 256 y
estimación de expansión de 4096 términos. No admiten Float ni funciones
trascendentes. La variable explícita oculta su valor de sesión; se conservan
las restricciones originales y los ámbitos de índices anidados.

Una descomposición paramétrica puede requerir condiciones adicionales.
`Apart[1/(x*(x+a)),x]` introduce factores `1/a`: conserva tanto la rama `a!=0`
como el caso `a=0`, cuyo resultado es `1/x^2`, mediante `Piecewise`. La generación
automática cubre una degeneración afín de un parámetro. Casos más amplios
conservan exclusiones explícitas y requieren tratar sus ramas por separado.

### Álgebra en desarrollo: NSolve

`NSolve[ecuación,x]` aproxima las soluciones de una ecuación polinómica o racional
univariada con coeficientes algebraicos o Float. Por defecto usa `Complexes` y
30 dígitos solicitados. También admite `NSolve[x^2==2,x,50]`,
`NSolve[x^2==-1,x,Reals]` y `NSolve[x^2==2,x,Reals,50]`.

Este incremento admite grado de numerador hasta 32 y precisión entera de 10 a
200 dígitos, conservando los límites de crecimiento del álgebra racional.
Los datos Float conservan su precisión de entrada: pedir más dígitos no la
recupera. Los decimales literales siguen siendo racionales exactos del lenguaje.
`NSolve[{x^2+y^2==1,x-y==0},{x,y},Reals,40]` admite sistemas polinómicos de
hasta ocho variables y ecuaciones, grado total hasta ocho. Las familias
continuas no se convierten en una lista artificial de puntos.

`NSolve[Cos[x]==x,x,{1},40]` solicita una búsqueda local desde el inicio 1.
Para sistemas, proporcionar una lista de inicios; la forma
`NSolve[ecuaciones,variables,Reals,40,{inicios}]` fija además el dominio.
El resultado lleva `completeness: false`: un residuo pequeño no prueba que se
hayan encontrado todas las raíces ni unicidad global. Parámetros libres quedan
condicionados o requieren valores antes de la búsqueda numérica.

Primero se aíslan las raíces exactas del polinomio; se comprueban dominio,
exclusiones originales e hipótesis antes de aproximarlas. El resultado incluye
multiplicidades y diagnósticos de residuos. Un residuo normalizado pequeño es
una comprobación numérica, no una cota certificada del error de cada raíz ni
una garantía de buen condicionamiento. Las condiciones no decididas y las
aproximaciones que no pasan las comprobaciones se indican expresamente.
Las identidades no se convierten en una lista finita ficticia: conservan el
conjunto de soluciones correspondiente, o un conjunto condicionado pendiente.

Las aproximaciones tienen `input: null`; el texto no se presenta como entrada
exacta reutilizable. `NSolve` está disponible en el código en desarrollo, no
en el ZIP publicado v0.1.1.

`Solve` admite también sistemas polinómicos no lineales acotados y verifica
candidatos por sustitución. Con coeficientes simbólicos de grado uno o dos,
`details.branches` separa los casos de coeficiente principal nulo, solución
genérica, identidad y contradicción; el conjunto global conserva sus condiciones.
`Reduce[condición,x,Reals]` reduce condiciones univariadas y conserva
`ConditionSet` cuando no puede decidirlas. No es un decisor universal de lógica
o sistemas algebraicos.

### Variables ligadas y contexto de resultados

Las variables formales de `D`, `Sum`, `Integrate`, `Solve`, `NSolve`, `DSolve` y `Plot`
ocultan el valor global del mismo nombre en su ámbito; los otros parámetros
numéricos de sesión sí se aplican. Con `x=3`, `D[x^2,x]` devuelve `2*x` e
`Integrate[x,x]` muestra `x**2/2`, no derivada cero ni una integral de la constante
3. Para evaluar la derivada en 3 se utiliza `Substitute[D[x^2,x],x,3]`.
El resultado simbólico puede guardarse mediante `a=D[x^2,x]` como un snapshot
de `2*x`, con las reglas de asignación inmediata descritas arriba.

Los índices de sumas anidadas conservan su ámbito local. Por ejemplo,
`Sum[D[n^2,n],{n,1,3}]` sigue devolviendo 12; una variable de sesión `n`
no sustituye el índice ligado. Las definiciones conservan esta distinción de ámbitos.

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

### Límites: desarrollo 0.2.0.dev1

Este incremento está en el código en desarrollo; no está incluido en el ZIP
publicado 0.2.0-dev0.

```wolfram
Limit[Sin[x]/x,x,0]
Limit[Sqrt[x^2]/x,x,0,Left]
Limit[Sqrt[x^2]/x,x,0,Right]
Limit[1/x,x,Infinity]
```

Los valores de estos ejemplos son `1`, `-1`, `1` y `0`. La forma
`Limit[expresión,variable,punto]` es **bilateral**, igual que la opción explícita
`Both`. El cuarto argumento `Left` o `Right` selecciona el acercamiento por
valores reales menores o mayores que el punto; no es una dirección en el plano
complejo. Son opciones literales, independientes de variables del mismo nombre.
En `Infinity` y `-Infinity` la dirección la determina el punto y se omite esa
opción. No se admiten límites multivariables ni puntos complejos.

La expresión puede tomar valores complejos en la rama principal. El punto
límite no necesita pertenecer a su dominio: `Limit[(x^2-1)/(x-1),x,1]` devuelve
`2`. Las exclusiones de la variable ligada quedan en
`details.limit_expression_exclusions`; las exclusiones independientes siguen en
`conditions`. Por ejemplo, cancelar `a*x/(a*x)` conserva la exigencia `a != 0`.

`status` distingue:

- `evaluated`: valor finito exacto calculado por el backend.
- `unverified`: datos o resultados aproximados; sin certificación de error.
- `conditional`: resultado sujeto a hipótesis o exclusiones de parámetros.
- `divergent`: límite infinito, como `Limit[1/x^2,x,0]`.
- `no_limit`: laterales distintos u oscilación sin valor único, como
  `Limit[1/x,x,0]` o `Limit[Sin[1/x],x,0]`.
- `unresolved`: el método no determina el resultado o sus ramas paramétricas.

Divergencia, ausencia de límite y cálculos pendientes conservan un objeto
`Limit` inerte, con `input=null`; no producen un escalar infinito ni presentan
un intervalo de oscilación como valor límite. Consulte `details.sides`,
`details.extended_value` cuando esté presente, y las advertencias. `exact=true`
describe la representación sin Float, no demuestra existencia ni certificación.
`verification` permanece `not_checked`: no se aporta una prueba independiente
por definición epsilon-delta.

La variable es local aunque tenga una asignación en la sesión. Las hipótesis
sobre ella deben valer en un entorno lateral completo, salvo el propio punto.
`Assuming[x>0,Limit[Sqrt[x^2]/x,x,0,Right]]` es válido; pedir el bilateral con
esa hipótesis se rechaza. Contextos discretos, mixtos o no verificables se
rechazan conservadoramente. Se aceptan valores de parámetros ya asignados;
las ramas de símbolos sin finitud demostrada permanecen pendientes, incluso
si el backend podría proponer un resultado genérico.

Se limita la expresión a 256 operaciones y ocho símbolos. Son presupuestos
estructurales, no límites efectivos de tiempo o memoria. La comprobación de
degeneraciones de denominadores paramétricos se limita a polinomios racionales
de grado total hasta 32 y expansión estimada de hasta 4096 términos; otros
casos se rechazan conservadoramente. La persistencia JSON
actual no admite guardar resultados `Limit` inertes; sí valores finitos dentro
de los tipos ya admitidos. `Series`, `Product` y las demás ampliaciones de la
etapa de cálculo no forman parte de este incremento.

El backend utiliza [los límites de SymPy 1.14](https://docs.sympy.org/latest/modules/series/series.html#limits),
comparando explícitamente ambos laterales cuando se pide `Both`.

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
El lenguaje y las sesiones descritos arriba corresponden al código en desarrollo:
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
`Session` proporciona el contexto persistente descrito arriba; `evaluate` sigue sin estado.
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
