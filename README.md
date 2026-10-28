# Mathechan

**Cálculo simbólico y numérico para física teórica y estadística.**

[English](README.en.md) · [Descargar](https://github.com/Stochasticboi/Mathechan/releases/tag/v0.2.0-dev0) · [Lenguaje](docs/es/lenguaje.md) · [Notas de versiones](CHANGELOG.md)

Proyecto de código abierto de **Edward Larroza H., estudiante de doctorado en Física**.
Iniciado en octubre de 2026 para reunir cálculo, gráficos y cuadernos en una
aplicación de escritorio. Actualmente se utiliza por consola; la interfaz
gráfica está pendiente.

## Probar Mathechan

| Opción | Versión | Cómo obtenerla |
| --- | --- | --- |
| Consola para Windows x64 | 0.2.0-dev0 · preliminar | [Descargar ZIP](https://github.com/Stochasticboi/Mathechan/releases/download/v0.2.0-dev0/Mathechan-0.2.0-dev0-windows-x64.zip), descomprimir y abrir `Mathechan.exe`. |
| Código en desarrollo | **0.2.0.dev11** | Usar la rama [`main`](https://github.com/Stochasticboi/Mathechan/tree/main) con Python 3.11 o posterior. |

El ZIP contiene las funciones de **dev0**. Para usar los avances posteriores,
incluido MaxEnt, instala desde el código fuente:

```console
python -m pip install -e .
python -m mathechan "D[x^3,x]"
```

Desde la carpeta del repositorio, la segunda línea devuelve `3*x**2`.
Los módulos del programa están en [`src/mathechan`](src/mathechan).

## Evolución del proyecto

Cada fila resume lo que se añadió a la versión anterior. Los detalles y las
correcciones están en el [historial de cambios](CHANGELOG.md). Los ejemplos
requieren la versión indicada o una posterior.

| Versión | Qué incorporó |
| --- | --- |
| **0.1.0** · 18 oct 2026 | Primer núcleo: aritmética exacta, expresiones simbólicas, derivadas, simplificación, gráficos SVG y cuadernos JSON.<br>Ejemplo: `D[x^3,x]` |
| **0.1.1** · 19 oct 2026 | Evaluación numérica, factorización, fracciones algebraicas, sustitución, sumas finitas, integración, ecuaciones y EDO.<br>Ejemplo: `Integrate[x^2,{x,0,1}]` |
| **0.2.0.dev0** · 22 oct 2026 | Sesiones persistentes, definiciones y funciones, hipótesis, álgebra ampliada y sistemas no lineales. **Versión descargable actual.**<br>Ejemplo: `Assuming[x>0,Simplify[Sqrt[x^2]]]` |
| **0.2.0.dev1** | Límites reales, bilaterales y laterales; distinción entre convergencia, divergencia y cálculo pendiente.<br>Ejemplo: `Limit[Sin[x]/x,x,0]` |
| **0.2.0.dev2** | Reglas `/.`, `->` y `:>`, series, derivadas mixtas, productos, cálculo vectorial cartesiano e integrales iteradas.<br>Ejemplo: `x^2 /. x -> 3` |
| **0.2.0.dev3** | Cálculo vectorial en coordenadas cilíndricas y esféricas.<br>Ejemplo: `Div[{r,0,0},{r,t,p},"Spherical"]` |
| **0.2.0.dev4** | Operaciones matriciales, rango, sistemas lineales, autovalores, autovectores y exponencial matricial.<br>Ejemplo: `Eigenvalues[{{1,0},{0,2}}]` |
| **0.2.0.dev5** | Probabilidad discreta finita: distribuciones, eventos, esperanza, varianza y entropía.<br>Ejemplo: `Mean[BernoulliDistribution[1/4]]` |
| **0.2.0.dev6** | Distribuciones conjuntas, marginales, condicionamiento, covarianza y correlación.<br>Ejemplo: `JointFiniteDistribution[{{0,0},{1,1}},{1/2,1/2}]` |
| **0.2.0.dev7** | Funciones hiperbólicas y sus inversas, con derivación e integración.<br>Ejemplo: `D[Sinh[x],x]` |
| **0.2.0.dev8** | Álgebra compleja para sistemas cuánticos pequeños: adjuntos, productos tensoriales, proyectores y traza parcial.<br>Ejemplo: `Adj[{{1,Imag},{0,1}}]` |
| **0.2.0.dev9** | Binomial, Poisson, normal, exponencial y gamma; densidades, acumuladas, generatrices, momentos y cumulantes.<br>Ejemplo: `CDF[NormalDistribution[0,1],0]` |
| **0.2.0.dev10** | Ensambles canónicos finitos: degeneración, energía media, fluctuaciones, energía libre y capacidad calorífica.<br>Ejemplo: `Energy[Canon[{0,1},Log[2]]]` |
| **0.2.0.dev11** · actual | Inferencia MaxEnt finita: Shannon o KL con referencia, varias medias, soporte activo y resultados guardables.<br>Ejemplo: `Probabilities[MaxEnt[{0,1},1/4]]` |

Las versiones **dev1–dev11** están integradas en el código; todavía no tienen
un descargable propio. La sintaxis y los límites de cada operación se describen
en la [referencia del lenguaje](docs/es/lenguaje.md).

## Próximo desarrollo

El siguiente bloque de física estadística abordará entropías generalizadas:
Rényi, Tsallis y q-exponencial. La interfaz de escritorio y el editor de
cuadernos forman parte del [plan 2026–2031](docs/es/objetivos.md).

## Documentación y contribuciones

- [Sintaxis, ejemplos y límites](docs/es/lenguaje.md).
- [Historia y antecedentes](docs/es/historia.md) · [Comparativa con Mathematica](docs/es/comparativa.md).
- [Cómo contribuir](CONTRIBUTING.md) · [Fuentes](docs/SOURCES.md).

El núcleo utiliza SymPy 1.14. La sintaxis toma Wolfram Language como referencia,
con una especificación propia y sin compatibilidad general. Los gráficos
actuales usan muestreo fijo; los cuadernos no ejecutan código al abrirse.

Para ejecutar las pruebas desde el repositorio:

```console
python -m unittest discover -s tests -v
```

**GPL-3.0-or-later** · [Licencia](LICENSE). Proyecto independiente de Wolfram Research.
