# Lenguaje experimental v0

[English](../en/language.md)

Este documento describe el código **0.2.0.dev12**. La descarga publicada
**0.2.0-dev0** incluye las sesiones y el álgebra ampliada, pero no los límites
de dev1, las ampliaciones de cálculo y reglas de dev2 ni las cartas curvilíneas
de dev3, el álgebra lineal de dev4, la probabilidad finita de dev5–dev6 ni las
hiperbólicas de dev7, las operaciones complejas de dev8 ni las familias y
momentos probabilísticos de dev9, los sistemas canónicos de dev10 ni MaxEnt de dev11 ni las entropías generalizadas de dev12. Las subsecciones
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
| Constantes | `Pi`, `E`, `Imag`; `Infinity` en rangos, límites y series |
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

`Imag` es la constante imaginaria y equivale a `Sqrt[-1]`. `I` sigue siendo un
símbolo genérico. La constante imaginaria tiene `text: "I"`, pero su `input`
canónico es `Sqrt[-1]`, incluso si se escribió `Imag`; el símbolo genérico
tiene `input: "I"`. Las otras constantes matemáticas se escriben `Pi` y `E`.
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

## Estados y operadores complejos: desarrollo 0.2.0.dev8

Las listas planas y las matrices columna representan kets en estas operaciones.
Una matriz fila conserva su orientación: use `Adj[v]` para formar el bra.
Los símbolos son complejos genéricos salvo hipótesis explícitas.

| Operación | Significado y ejemplo |
|---|---|
| `Conj` | Conjugación elemento a elemento: `Conj[{1,Imag}]` devuelve `{1,-Imag}`. |
| `Re` | Parte real de un escalar, vector o matriz: `Re[1+Imag]` devuelve `1`. |
| `Im` | Parte imaginaria elemento a elemento: `Im[1+Imag]` devuelve `1`. |
| `Adj` | Conjugada transpuesta: `Adj[{1,Imag}]` es la matriz fila `{{1,-Imag}}`. |
| `Inner` | Producto hermítico: `Inner[{1,Imag},{1,Imag}]` devuelve `2`. Conjuga el primer argumento. |
| `Norm` | Norma euclídea compleja: `Norm[{3,4*Imag}]` devuelve `5`. |
| `Unit` | Normaliza un ket: `Unit[{3,4*Imag}]` devuelve `{3/5,4*Imag/5}`. |
| `Dyad` | `Dyad[u,v]` forma `u v†`, sin normalizar. |
| `Proj` | `Proj[v]` forma `v v† / Inner[v,v]`, el proyector normalizado. |
| `Kron` | Producto tensorial de dos a ocho factores: `Kron[{1,0},{0,1}]` devuelve `{0,1,0,0}`. |
| `Ortho` | Gram–Schmidt hermítico ordenado: `Ortho[{{1,Imag},{1,0}}]`. Rechaza vectores nulos o dependientes. |
| `HermQ` | Comprueba `A†=A`: `HermQ[{{0,-Imag},{Imag,0}}]` devuelve `True`. |
| `UnitaryQ` | Comprueba `A† A=Identity`: `UnitaryQ[{{0,1},{1,0}}]` devuelve `True`. |
| `PSDCheck` | Comprueba hermiticidad y semidefinición positiva, incluidos autovalores nulos: `PSDCheck[{{1,0},{0,0}}]` devuelve `True`. |
| `PTrace` | `PTrace[rho,{d1,d2,...},{subsistemas}]` traza los subsistemas indicados, numerados desde uno. |

`Dot` y `.` conservan su producto bilineal: no conjugan automáticamente.
Por ejemplo, `Dot[{1,Imag},{1,Imag}]` devuelve `0`, mientras que `Inner`
devuelve `2`. `Dyad[v,v]` coincide con `Proj[v]` cuando `v` está normalizado.
`Unit` y `Proj` requieren norma estrictamente positiva; `Ortho` la requiere
en cada residual. Estos requisitos se conservan tras cancelar expresiones,
asignar resultados y guardar/cargar la sesión. `Proj[{z}]` puede simplificarse
a `{{1}}`, pero sigue excluyendo `z=0`.

Ejemplo en una sesión: estado de Bell y estado reducido del primer qubit.
Las líneas muestran entradas consecutivas; cada resultado puede inspeccionarse.

```wolfram
bell=Unit[Kron[{1,0},{1,0}]+Kron[{0,1},{0,1}]]
rho=Proj[bell]
Inner[bell,bell]
PSDCheck[rho]
PTrace[rho,{2,2},{2}]
```

Los tres últimos resultados son `1`, `True` y `Matrix[{{1/2,0},{0,1/2}}]`.
`Kron` usa el primer factor como subsistema más significativo: en dos qubits,
la base se ordena `00`, `01`, `10`, `11`. `PTrace` usa esa misma convención;
una lista vacía no traza ninguno y trazar todos devuelve el escalar `Tr[rho]`.

Los predicados devuelven `True`, `False` o una fórmula booleana simbólica
cuando no pueden decidir. No se interpreta una fórmula pendiente como verdad.
Estas fórmulas se pueden guardar/cargar y especializar con `/.`; por ejemplo,
`h=HermQ[{{z}}]` seguido de `h /. z -> 2` devuelve `True`.
`Assuming` refina casos reconocibles, pero el refinamiento de fórmulas y
expresiones complejas es parcial.

Límites: ocho filas/columnas y 64 entradas; ocho símbolos y 256 operaciones
de entrada, hasta 4096 operaciones de salida. `PSDCheck` admite hasta 4×4 y
usa todos los menores principales, hasta 15 comprobaciones de determinantes.
`PTrace` admite de uno a cuatro subsistemas y dimensión total hasta ocho.
`Kron` comprueba el tamaño antes de construir el resultado. Son presupuestos
estructurales, sin garantía de tiempo o memoria.

Con `Float` no se aplica tolerancia absoluta ni relativa para declarar cero,
hermiticidad, unitariedad o positividad. Los predicados `HermQ`, `UnitaryQ` y
`PSDCheck` examinan los valores binarios almacenados como racionales exactos.
Las otras operaciones, incluidas `Norm` y `Unit`, usan aritmética aproximada
de SymPy; la excepción es `Ortho`, que hace Gram–Schmidt con esos valores
como racionales exactos y aproxima al final. No se certifican cifras ni
incertidumbre física. `Ortho` devuelve una lista de kets ortonormales y
avisa si la norma residual al cuadrado respecto a la de entrada es menor que
`1e-12`. Ese aviso describe sensibilidad, sin descartar el vector. Más cifras
de cálculo no recuperan información perdida en los datos.

## Funciones hiperbólicas: desarrollo 0.2.0.dev7

Se admiten `Sinh`, `Cosh`, `Tanh`, `Coth`, `Sech` y `Csch`, y sus inversas
`ArcSinh`, `ArcCosh`, `ArcTanh`, `ArcCoth`, `ArcSech` y `ArcCsch`.
Todas requieren un argumento escalar finito. Funcionan en expresiones,
derivadas ordinarias/superiores/mixtas y vectoriales, integrales, `N`, `Plot`
y sesiones guardadas. Los resultados representables reciben entrada reutilizable.

| Función | Derivada respecto de x |
|---|---|
| `Sinh[x]` | `Cosh[x]` |
| `Cosh[x]` | `Sinh[x]` |
| `Tanh[x]` | `Sech[x]^2`, también puede representarse como `1-Tanh[x]^2`. |
| `Coth[x]` | `-Csch[x]^2` |
| `Sech[x]` | `-Sech[x]*Tanh[x]` |
| `Csch[x]` | `-Csch[x]*Coth[x]` |

```wolfram
D[Sinh[x],x]
D[Sinh[3*x^2],x]
Integrate[Cosh[x],x]
Integrate[Sech[x],x]
Integrate[1/Sqrt[1+x^2],x]
```

Estos ejemplos devuelven `Cosh[x]`, `6*x*Cosh[3*x^2]`, `Sinh[x]`,
`2*ArcTan[Tanh[x/2]]` y `ArcSinh[x]`, respectivamente. El integrador omite la
constante aditiva y lo advierte. Si la verificación sencilla de una primitiva
hiperbólica no reconoce una identidad, intenta una transformación acotada a
exponenciales; sólo declara residuo verificado cuando se reduce exactamente a cero.
Una integral no resuelta o no verificada conserva su diagnóstico.

No se supone que los símbolos sean reales. `Tanh` y `Sech` excluyen los ceros
complejos de `Cosh`; `Coth` y `Csch` excluyen los de `Sinh`. `ArcTanh` y
`ArcCoth` excluyen argumentos ±1; `ArcSech` y `ArcCsch` excluyen cero.
Las exclusiones se registran antes de cancelar y acompañan a resultados y
definiciones guardadas. Las derivadas hiperbólicas también conservan los
denominadores explícitos de su resultado antes de operaciones posteriores.

Las inversas usan valores principales complejos, de acuerdo con el backend;
un argumento real fuera de una rama real puede producir un valor complejo.
Las condiciones de polos no describen todos los cortes ni certifican
diferenciabilidad global. Una primitiva verificada por derivación es una
verificación local en su rama. Véanse las
[convenciones de funciones hiperbólicas inversas](https://dlmf.nist.gov/4.37).

## Sistemas canónicos finitos: desarrollo 0.2.0.dev10

Este primer bloque de la etapa 6 implementa el ensamble canónico con espectro
fijo. La inferencia finita `MaxEnt` se incorpora en 6B; las entropías
generalizadas se incorporan en 6C. `Canon[E,beta]` crea un modelo, no un ajuste de restricciones.
Las energías pueden repetirse; cada entrada tiene un identificador distinto.
`Canon[E,beta,g]` declara degeneraciones enteras positivas, una por entrada.
Sin `g`, cada entrada representa un microestado. Los conteos no son un prior
normalizado: la partición física es `Z=Sum[g_i*Exp[-beta*E_i]]`.

| Consulta | Significado |
|---|---|
| `Probabilities[r]` | Probabilidades de los grupos de nivel, en el orden declarado. |
| `Dist[r]` | Distribución sobre índices `1,...,n`; sus estados no son las energías. |
| `LogZ[r]` | Logaritmo de la partición física. Para obtener `Z`, usar `Exp[LogZ[r]]`. |
| `Energy[r]` | Energía media `U`. |
| `Variance[r]` | Varianza de la energía, no de los índices. |
| `Entropy[r]` | Entropía de microestados `S/kB`, incluida la degeneración. |
| `FreeEnergy[r]` | Energía libre `F=-LogZ[r]/beta`; requiere `beta!=0`. |
| `HeatCapacity[r]` | Capacidad calorífica reducida `C/kB=beta^2*Variance[r]`. |
| `Levels[r]`, `Degens[r]` | Energías y degeneraciones declaradas. |

Ejemplo en una sesión, con tres grupos y cuatro microestados:

```wolfram
r=Canon[{0,1,2},Log[2],{1,2,1}]
Probabilities[r]
Energy[r]
Variance[r]
Entropy[Canon[{0,1,2},0,{1,2,1}]]
Entropy[Dist[Canon[{0,1,2},0,{1,2,1}]]]
```

Resultados: `{4/9,4/9,1/9}`, `2/3`, `4/9`, `Log[4]` y `3*Log[2]/2`.
La última consulta mide entropía de grupos de nivel; difiere de la de
microestados porque `S/kB=-Sum[P_i*Log[P_i/g_i]]`.

La convención es `beta=1/(kB*T)`. Se muestran `S/kB` y `C/kB`; las energías
y `F` usan las unidades de entrada. No hay comprobación automática de unidades.
Beta finito debe ser real y puede ser cero o negativo. Esto no atribuye por sí
solo una temperatura física negativa a un espectro truncado. Los parámetros
simbólicos de beta deben ser independientes de las energías y degeneraciones:
este bloque no trata espectros dependientes de temperatura.

Sumar una constante a todas las energías conserva probabilidades, entropía y
varianza, y desplaza `U` y `F` por esa constante. Para espectro fijo,
`U=-D[LogZ,beta]` y `Variance=D[LogZ,{beta,2}]`. Una salida puede necesitar
reescritura o simplificación adicional para comprobar una identidad simbólica.

`Canon[E,Infinity,g]` y `Canon[E,-Infinity,g]` representan límites exactos
sobre los grupos de energía mínima o máxima. Requieren energías numéricas
cuyo orden se pueda decidir. La degeneración decide los pesos entre grupos
extremos empatados. La varianza y el límite de `C/kB` son cero; la entropía
residual es el logaritmo de la degeneración total extrema. `LogZ` puede no
tener valor finito en ese límite; esa consulta se rechaza. `FreeEnergy` en
beta cero se rechaza incluso si su fórmula se simplificaría a una constante.

`N[r,50]` conserva el modelo con precisión numérica solicitada de 50 cifras;
los datos deben ser numéricos. `Canon[E,beta,g,precision]` es la forma explícita
de cuatro argumentos usada por el impresor: cero selecciona cálculo exacto o
automático, y de 10 a 200 solicita cálculo numérico. Los datos `Float` numéricos
sin precisión explícita usan la menor precisión de entrada dentro de ese rango.
Con parámetros simbólicos, sus valores binarios se usan como racionales exactos.

La evaluación numérica usa energías relativas y exponenciales desplazadas.
`Probabilities[r]` muestra aproximaciones; `Dist[r]` normaliza exactamente los
pesos binarios almacenados como racionales. Esta normalización no certifica
las probabilidades físicas. `exact` describe representación matemática, no
incertidumbre experimental ni una cota universal de error. Los diagnósticos
numéricos de cada consulta indican método, precisión y residuo de normalización.

Guardar conserva datos del modelo, degeneraciones, beta, precisión y condiciones.
Cargar valida esos datos sin ejecutar fuente ni calcular observables. Las
consultas explícitas vuelven a calcular sus resultados; no se guarda una caché
de diagnósticos como si fuera un certificado de inferencia MaxEnt.

Límites: hasta 64 grupos, ocho símbolos, 256 operaciones de entrada y 4096
de salida; coeficientes racionales de hasta 12000 bits. El modo numérico limita
la dispersión de log-pesos a 6000 y aplica presupuestos adicionales de tamaño.
Si se exceden, rechaza el cálculo en lugar de eliminar probabilidades pequeñas.
Un sistema finito no demuestra una transición singular en el límite termodinámico.

## Probabilidad y momentos: desarrollo 0.2.0.dev9

La etapa 5 queda completada para las familias y operaciones descritas aquí,
junto con las distribuciones escalares y conjuntas finitas de dev5–dev6.
Este alcance no incluye distribuciones conjuntas continuas generales ni un
catálogo arbitrario de distribuciones. Los apartados de dev5–dev6 conservan
el registro de los incrementos anteriores.

| Distribución | Parámetros y convención |
|---|---|
| `BinomialDistribution[n,p]` | `n` entero no negativo, `0<=p<=1`. Admite `n=0`, `p=0` y `p=1`. |
| `PoissonDistribution[lambda]` | `lambda>=0`; `lambda=0` concentra toda la masa en cero. |
| `NormalDistribution[mu,sigma]` | Media real `mu` y desviación estándar `sigma>0`. |
| `ExponentialDistribution[rate]` | Tasa `rate>0`; media `1/rate`. |
| `GammaDistribution[shape,scale]` | Forma y escala positivas; media `shape*scale`. El segundo parámetro no es una tasa. |

Los parámetros son reales finitos. Las condiciones simbólicas se conservan
en el resultado y en las sesiones; una sustitución que las viola se rechaza,
incluso si una simplificación ya eliminó el parámetro de la expresión.
Guardar y cargar reconstruye datos matemáticos validados, sin ejecutar la
fuente guardada.

| Operación | Alcance y significado |
|---|---|
| `PDF[d,x]` | Masa puntual en distribuciones discretas; densidad en continuas. Una densidad no es la probabilidad de un punto. |
| `CDF[d,x]` | `P(X<=x)`, continua por derecha; acepta extremos infinitos. La versión discreta respeta el retículo y el piso del argumento. |
| `Support[d]` | Conjunto de soporte; puede depender de los parámetros. No enumera un soporte infinito. |
| `Mean[d]`, `Variance[d]`, `StandardDeviation[d]` | Media, varianza y desviación estándar poblacionales. |
| `Entropy[d]` | Shannon para masas; entropía diferencial para densidades, en nats. La entropía diferencial puede ser negativa. |
| `MGF[d,t]` | `E[Exp[t*X]]`; alias `MomentGeneratingFunction`. |
| `CF[d,t]` | `E[Exp[Imag*t*X]]`; alias `CharacteristicFunction`. |
| `Moment[d,n]` | Momento respecto al origen `E[X^n]`, orden entero exacto de cero a doce. |
| `CentralMoment[d,n]` | `E[(X-E[X])^n]`, orden entero exacto de cero a doce. |
| `Cumulant[d,n]` | Cumulante de orden entero exacto de uno a doce, obtenido de la generatriz de cumulantes alrededor de cero. |

En una distribución conjunta finita de dimensión hasta cuatro, `MGF` y `CF`
reciben una lista de argumentos, uno por coordenada: `MGF[j,{s,t}]`.
Los momentos y cumulantes conjuntos usan multiíndices de órdenes no negativos,
por ejemplo `Moment[j,{1,1}]` o `Cumulant[j,{1,1}]`, con orden total hasta doce.
El momento mixto no presupone independencia entre coordenadas.

Los argumentos de `MGF` y `CF` son reales. La MGF exponencial exige `t<rate`;
la gamma exige `t<1/scale`. Sus funciones características son válidas para
todo argumento real. Estas restricciones se conservan tras sustitución y
persistencia; no se confunde una continuación algebraica con una integral
convergente fuera de ese dominio.

Eventos y observables usan variables locales. Los parámetros libres de los
eventos se restringen a valores reales, con condiciones conservadas tras
sustitución y persistencia. Por ejemplo:
`Probability[x>0,{x,NormalDistribution[0,1]}]` y
`Expectation[x^2,{x,NormalDistribution[0,1]}]`. Las covarianzas y correlaciones
de familias escalares admiten observables polinómicos reales dentro del
presupuesto de momentos. No representan dos variables independientes por
usar dos observables del mismo `x`.

La esperanza condicionada se escribe `Expectation[expr,{x,d},evento]` y
requiere probabilidad estrictamente positiva del evento. Los momentos
condicionados se obtienen con `expr=x^n`; en espacios finitos también se
puede aplicar `Moment` a `ConditionalDistribution[evento,{x,d}]`.
`ConditionalDistribution` sigue siendo una operación finita: esta versión
no construye un objeto general de distribución continua truncada.

```wolfram
Mean[BinomialDistribution[10,1/4]]
Probability[x==0,{x,PoissonDistribution[2]}]
CDF[NormalDistribution[0,1],0]
CentralMoment[NormalDistribution[0,2],4]
Cumulant[PoissonDistribution[3],4]
Expectation[x,{x,ExponentialDistribution[2]},x>1]
```

Resultados: `5/2`, `Exp[-2]`, `1/2`, `48`, `3` y `3/2`.

Los observables se comprueban antes de cancelar polos que estén dentro de
un estado con masa positiva. Los estados de masa cero se excluyen antes de
evaluar el observable. En continuas, las integrales impropias y la existencia
de la esperanza se tratan por separado de una simplificación formal.

Una suma o integral que el motor no resuelve conserva estado `unresolved` y
sus advertencias: no se ofrece como cifra calculada. Esto incluye la entropía
de Poisson y ciertas acumuladas o entropías binomiales simbólicas/grandes.
Una densidad gamma puede divergir en cero para `shape<1`, aunque su integral
sea normalizable. Los conjuntos de soporte pueden carecer de `input` reutilizable
y no todos son asignables o guardables. Los datos aproximados no certifican
precisión ni incertidumbre física; más cifras no reparan datos inciertos.
Las varianzas de las familias usan identidades directas para evitar restar
momentos grandes casi iguales. Los momentos y cálculos de observables que
racionalizan valores binarios almacenados evitan esa cancelación aritmética,
sin recuperar información que no estaba en los datos originales.

Presupuestos: hasta ocho símbolos y 256 operaciones de entrada en familias;
momentos hasta orden total doce; tablas conjuntas de hasta cuatro coordenadas
y 64 estados. Salidas hasta 4096 operaciones. Son límites estructurales, sin
garantía de tiempo o memoria. MaxCal y simulación pertenecen a etapas
posteriores.

## Probabilidad discreta finita: desarrollo 0.2.0.dev5

Este incremento inicia la etapa de probabilidad; no incorpora todavía toda la
estadística matemática. Una distribución es un objeto inmutable, con estados
escalares reales finitos distintos y una masa de probabilidad por estado.

| Operación | Sintaxis y significado |
|---|---|
| Masas normalizadas | `FiniteDistribution[{estados},{masas}]`: exige masas reales entre 0 y 1 cuya suma sea exactamente 1. No renormaliza. |
| Pesos | `WeightedDistribution[{estados},{pesos}]`: pesos reales no negativos, suma positiva; normalización explícita. |
| Bernoulli | `BernoulliDistribution[p]`: estados `{0,1}`, masas `{1-p,p}` y condición `0<=p<=1`. |
| Uniforme discreta | `DiscreteUniformDistribution[{a,b}]`: enteros consecutivos entre extremos enteros exactos inclusivos. |
| Inspección | `States[d]` y `Probabilities[d]`: listas alineadas, incluidas las masas cero. |
| Soporte efectivo | `Support[d]`: estados de masa positiva; si no puede decidir qué masas son cero, solicita especializar los parámetros. |
| Momentos | `Mean[d]`, `Variance[d]`, `StandardDeviation[d]`; varianza poblacional de la distribución. |
| Entropía | `Entropy[d]`: Shannon en nats, con logaritmo natural y convención `0 Log[0]=0`. |
| Evento | `Probability[evento,{x,d}]`: probabilidad de un evento lógico. |
| Observable | `Expectation[expresión,{x,d}]`: suma finita ponderada del observable, que puede ser complejo. |

En una sesión se puede evaluar, una línea por vez:

```wolfram
d=FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]
Mean[d]
Variance[d]
Expectation[x^2,{x,d}]
Probability[x>=1,{x,d}]
Entropy[d]
```

Los resultados son `1`, `1/2`, `3/2`, `3/4` y `3 Log[2]/2`, respectivamente.
La variable `x` es local: oculta su definición exterior durante el cálculo y
no modifica la sesión. Un evento escalar como `Probability[a,{x,d}]` se rechaza.
Eventos con parámetros indecididos conservan una expresión por casos, sin elegir
una rama arbitrariamente; las comparaciones de orden exigen operandos reales.

Las hipótesis de realidad, no negatividad, distinción de estados y normalización
son requisitos ejecutables. Acompañan incluso a resultados constantes y se
comprueban tras sustituciones. Las distribuciones y sus condiciones se guardan
en JSON validado; cargar no ejecuta expresiones de entrada. La forma canónica
`FiniteDistribution[...]` no conserva por sí sola las restricciones originales
de los pesos: deben mantenerse junto con las condiciones del resultado.

Los estados de masa demostrablemente cero se omiten antes de evaluar un evento
u observable: un valor indefinido sólo en esos estados no causa un error. Si la
masa es simbólica y no se demuestra que sea cero, una singularidad se rechaza
conservadoramente. La entropía mantiene sus ramas de masa cero también después
de sustituir parámetros y guardar la sesión.

Alcance: una variable, entre 1 y 64 estados, ocho símbolos y 256 operaciones de
entrada; resultado de hasta 4096 operaciones. Las operaciones ligadas comparten
el presupuesto de 2000 términos. Estos límites no son un timeout ni una cota de
memoria. `N[Mean[d],p]` y `N[Probabilities[d],p]` ofrecen aproximaciones; `N[d]`
no crea una distribución aproximada. Las masas Float se validan según su suma
binaria almacenada exacta, sin tolerancia oculta. Para pesos Float, la normalización
usa sus racionales binarios exactos y advierte que la incertidumbre no se certifica.
Véanse las [convenciones de distribuciones discretas](https://www.itl.nist.gov/div898/handbook/eda/section3/eda361.htm).

### Distribuciones conjuntas y dependencias: desarrollo 0.2.0.dev6

La etapa 5 prepara probabilidades, observables y medidas de dependencia para
física estadística. Este incremento amplía la base discreta a varios observables;
La inferencia MaxEnt finita se documenta en su sección; MaxCal y simulaciones siguen pendientes.

`JointFiniteDistribution[{{x1,y1},...},{p1,...}]` representa masas de probabilidad
conjuntas. Cada fila tiene de dos a cuatro coordenadas reales finitas. Las filas
deben ser distintas, y las masas no negativas suman exactamente uno; no se
presupone independencia ni que estén presentes todas las combinaciones de valores.

| Operación | Sintaxis |
|---|---|
| Inspección y entropía | `States[d]`, `Probabilities[d]`, `Support[d]`, `Entropy[d]`, con las convenciones anteriores. |
| Marginal | `MarginalDistribution[d,1]` proyecta la primera coordenada y suma las masas de valores repetidos. |
| Varias coordenadas | `MarginalDistribution[d,{2,1}]` conserva ese orden; una sola coordenada produce `FiniteDistribution`, varias producen una conjunta. |
| Evento/observable | `Probability[evento,{{x,y},d}]`, `Expectation[expresión,{{x,y},d}]`; variables locales distintas, una por coordenada. |
| Condicionamiento | `ConditionalDistribution[evento,{{x,y},d}]`; también admite una distribución escalar con `{x,d}`. |
| Covarianza | `Covariance[f,g,{{x,y},d}]`, para observables reales de la misma distribución. |
| Correlación | `Correlation[f,g,{{x,y},d}]`, con ambas varianzas estrictamente positivas. |

La marginal usa `q(z)=Sum[p_i]` sobre las filas proyectadas en `z`. Las
colisiones simbólicas no decididas pueden producir requisitos de distinción:
si después coinciden valores antes tratados como distintos, hay que recalcular
desde la distribución original ya especializada.

El condicionamiento calcula `p_i 1_A(i)/P(A)` y conserva el requisito ejecutable
`P(A)>0` antes de cancelar. Un evento de probabilidad cero se rechaza. Su verdad
debe poder decidirse en cada fila de masa no nula o indecidida; las igualdades
simples de las hipótesis pueden decidir parámetros. Si no se decide, se pide
especialización. Las filas descartadas permanecen declaradas con masa cero;
`Support` devuelve sólo el soporte efectivo. La entrada canónica normalizada
no reconstruye por sí sola la condición original de probabilidad positiva.

La covarianza poblacional se calcula mediante la suma centrada
`E[(f-E[f])*(g-E[g])]`, sin corrección muestral ni conjugación compleja. La
correlación divide por el producto de desviaciones estándar; una varianza cero
se rechaza incluso si una expresión genérica se simplificaría a `1`. Se permite
`Expectation` de un observable complejo, pero esta covarianza exige observables
reales. Covarianza cero no demuestra independencia.

Ejemplo de ocupación binaria de dos sitios, una línea por evaluación:

```wolfram
d=JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]
Mean[MarginalDistribution[d,1]]
Covariance[x,y,{{x,y},d}]
Correlation[x,y,{{x,y},d}]
c=ConditionalDistribution[x==1,{{x,y},d}]
Probability[y==1,{{x,y},c}]
```

Los resultados numéricos son `1/2`, `1/8`, `1/2` y `3/4`, respectivamente.
Las hipótesis, las condiciones de los eventos y las varianzas positivas se
conservan tras sustituciones y al guardar/cargar. Las distribuciones conjuntas
son datos validados; abrirlas no ejecuta expresiones.

Se mantienen 64 filas, ocho símbolos y 256 operaciones de entrada, con un
máximo de cuatro coordenadas por fila; límites del parser y de resultados
siguen aplicándose. Las masas Float se agregan y condicionan como sus valores
binarios exactos, sin certificar incertidumbre. No hay tolerancia automática
para declarar nulas probabilidades o varianzas pequeñas.

Quedan para incrementos posteriores generatrices, binomial, otras familias y
distribuciones continuas. No se añaden muestreo aleatorio ni simulaciones.

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


## Inferencia MaxEnt finita: desarrollo 0.2.0.dev11

`MaxEnt[F,m]` maximiza la entropía de Shannon bajo normalización y medias
impuestas. `MaxEnt[F,m,q]` minimiza `KL(p||q)` con una referencia normalizada.
Las filas de `F` son estados y sus columnas observables; `m` contiene las medias
solicitadas. Para un observable se admite un vector y una media escalar.

```wolfram
r = MaxEnt[{0,1},1/4]
Probabilities[r]
(* {3/4,1/4} *)
Dual[r]
(* {Log[3]} *)
Residuals[r]
(* {0} *)
```

Las entradas deben ser racionales numéricas o aproximaciones `N` que se
convierten a su valor binario racional almacenado. No admite parámetros
simbólicos ni constantes irracionales exactas. La referencia debe sumar
exactamente uno; sus ceros excluyen estados. El límite actual es 32 estados,
cuatro observables y 4096 bits por racional de entrada.

| Consulta | Resultado |
| --- | --- |
| `Probabilities[r]`, `Dist[r]` | Masas; distribución con estados numerados desde 1 |
| `Entropy[r]`, `RelEntropy[r]` | Shannon y KL respecto de la referencia |
| `Score[r]` | Shannon sin referencia explícita; menos KL con referencia |
| `Means[r]`, `Targets[r]`, `Residuals[r]` | Medias alcanzadas, solicitadas y su diferencia |
| `Active[r]`, `Rank[r]`, `Converged[r]` | Estados activos, rango independiente y convergencia validada |
| `Dual[r]`, `FaceDual[r]` | Multiplicadores globales interiores o de la cara activa |
| `LogZ[r]`, `DualGap[r]` | Normalizador relativo y brecha dual estimada |

Se usa la convención `p_i = q_i Exp[-lambda.F_i]/Z` sobre el soporte activo.
`LogZ` usa `q` normalizada, uniforme si se omite: **no es la partición física**
de `Canon` y no define energía libre. Las columnas redundantes tienen
multiplicador cero. En una frontera `Dual` devuelve un error; `FaceDual`
expone el dual de la cara con una advertencia. El soporte se determina respecto
de los estados permitidos por `q`.

La factibilidad y la cara mínima se comprueban con aritmética racional y
certificados. Si el procedimiento geométrico excede su presupuesto, informa
un límite de cálculo, no infactibilidad. La enumeración de respaldo tiene un
máximo de 20000 bases. Se resuelven exactamente casos cerrados; el resto usa
Newton amortiguado con centrado, escalado y log-sum-exp, hasta 200 iteraciones.
`MaxEnt[F,m,q,precision]` solicita entre 10 y 100 dígitos, 50 por defecto.
No se retorna una distribución uniforme como sustituto de un fallo.

Los diagnósticos incluyen residuos de medias y estacionariedad, iteraciones,
precisión y brecha dual estimada. La tolerancia numérica usa residuos escalados;
`Residuals` conserva la diferencia sin escalar de las masas almacenadas.
La precisión no es una cota rigurosa ni representa incertidumbre de los datos.
Los casos exactos registran precisión cero. El rango logarítmico de pesos se
limita a 6000 y los racionales de salida a 12000 bits; casos que excedan los
presupuestos se rechazan. `N` no aumenta la precisión de un resultado guardado:
para ello se solicita otra inferencia con el cuarto argumento.

Las sesiones guardan datos, probabilidades, dual, testigo factible y certificado
de soporte. Al cargar se validan normalización, medias, cara y estacionariedad
sin ejecutar fuente, programación lineal ni optimización. Esta validación
aritmética no acredita la autenticidad criptográfica del archivo.
La etapa 6B cubre espacios finitos; MaxEnt continuo, restricciones con
incertidumbre, entropías generalizadas y MaxCal quedan fuera de este bloque.


## Entropías generalizadas y funciones q: desarrollo 0.2.0.dev12

Este bloque completa la etapa 6 para espacios finitos. Separa calcular un
funcional de entropía de inferir una distribución óptima: `MaxEnt` conserva
los objetivos Shannon/KL de 6B. No ofrece optimización Rényi/Tsallis, MaxCal,
modelos continuos ni ensambles cuánticos térmicos.

| Operación | Definición y dominio |
| --- | --- |
| `Renyi[d,a]` | ln(Σ p_i^a)/(1−a), a≥0; a=1 usa Shannon, a=0 cuenta el soporte positivo, a=Infinity usa −ln(max p_i). |
| `Tsallis[d,q]` | (1−Σ p_i^q)/(q−1), q>0; q=1 usa Shannon. Devuelve S_q/kB, sin multiplicar por una constante física. |
| `KL[d,r]` | Σ p_i ln(p_i/r_i), dirección d respecto de r; alinea por etiquetas, no por posición. |
| `Escort[d,q]` | Distribución con las mismas etiquetas y masas p_i^q/Σ p_j^q, q>0. |
| `QExp[x,q]` | [1+(1−q)x]^(1/(1−q)); q=1 usa Exp[x]. |
| `QLog[x,q]` | (x^(1−q)−1)/(1−q), x>0; q=1 usa Log[x]. |

`d` y `r` deben ser distribuciones finitas o conjuntas finitas, con hasta 64
estados y los presupuestos previos de construcción. Los parámetros son reales;
se admiten símbolos con condiciones guardables. Se usan logaritmos naturales
(nats para Rényi y KL). Los órdenes negativos no están implementados.

```wolfram
d = FiniteDistribution[{0,1},{1/4,3/4}]
Tsallis[d,2]
(* 3/8 *)
Probabilities[Escort[d,2]]
(* {1/10,9/10} *)
Renyi[BernoulliDistribution[1/2],2]
(* Log[2] *)
QExp[2,1/2]
(* 4 *)
QLog[4,1/2]
(* 2 *)
```

Las masas nulas no contribuyen a Shannon ni a KL; no se evalúa `0 Log[0]`.
El orden cero de Rényi cuenta estados de masa positiva, no filas declaradas.
Si p_i>0 pero r_i=0, KL devuelve +Infinity con estado `divergent`. Una
referencia puede incluir otros estados. Los espacios deben ser de la misma
clase y dimensión; etiquetas cuya igualdad sea indecidible requieren
especialización antes del cálculo. Las KL infinitas o simbólicas con ramas
infinitas se pueden consultar, pero no asignar ni guardar como escalares finitos.

En `QExp`, q<1 incluye el corte: si 1+(1−q)x≤0, devuelve cero. Para q>1
exige 1+(1−q)x>0; la frontera divergente y valores posteriores producen un
error de dominio. `QLog` exige x>0. Las derivadas simbólicas por ramas no
demuestran diferenciabilidad en el punto de corte. Las condiciones se conservan
al sustituir parámetros; q=1 selecciona la rama ordinaria antes de dividir.

Para medias escort se construye explícitamente la distribución y se usan las
consultas habituales, por ejemplo `Mean[Escort[d,2]]`. `Mean[d]` sigue siendo
la media ordinaria: no se cambia silenciosamente la restricción de un modelo.
Para aplicar estos funcionales a 6A/6B, convertir con `Dist`, por ejemplo
`Tsallis[Dist[MaxEnt[{0,1},1/4]],2]`. En modelos con degeneración,
`Dist[Canon[...]]` representa masas de niveles, no una expansión en microestados;
sus entropías generalizadas de niveles no sustituyen la entropía física de 6A.

Las entradas Float se interpretan por su valor binario almacenado. Cerca del
orden uno, la evaluación usa cifras de guarda; no certifica dígitos ni
incertidumbre experimental. Los funcionales limitan la salida numérica a 100
cifras y el trabajo a 600; las funciones q limitan el trabajo a 2000.
Los coeficientes exactos del orden y de las funciones q admiten hasta 4096 bits,
y las potencias se rechazan antes de superar 12000 bits estimados. Esta guardia
conservadora también limita las potencias de los funcionales aproximados.
Las sustituciones y los parámetros de funciones definidas conservan el límite
experimental de exponente ±1000.
Las probabilidades escort aproximadas se normalizan como racionales almacenados,
pero su procedencia aproximada se mantiene en consultas y sesiones.

Los resultados finitos y sus condiciones se guardan como datos matemáticos;
cargar no ejecuta fuente. Las sesiones previas siguen siendo legibles. Las
definiciones pueden incluir el indicador booleano opcional `approximate`,
que conserva procedencia sin modificar su valor matemático.
Convenciones basadas en [Rényi (1961)](../SOURCES.md#s16) y
[Tsallis (2002)](../SOURCES.md#s17); la implementación usa los dominios acotados
descritos aquí.
