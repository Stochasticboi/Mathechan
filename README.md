# Mathechan

[English](README.en.md)

Proyecto personal de **Edward Larroza H., estudiante de doctorado en Física**.

Mathechan es un programa de código abierto en desarrollo para trabajar con
problemas de física teórica, con especial interés en física estadística.
El objetivo es reunir cálculo simbólico, métodos numéricos, gráficos y
cuadernos reproducibles en una aplicación de escritorio.

El proyecto comenzó el **18 de octubre de 2026**, con un horizonte inicial de
cinco años, hasta octubre de 2031. Su sintaxis toma a Mathematica como referencia,
con una especificación propia y un alcance definido progresivamente.

## Versión preliminar 0.2.0.dev0

El código actual incorpora sesiones persistentes, definiciones simbólicas y
diferidas, funciones con parámetros locales, hipótesis, `FullSimplify`, `Collect`,
`Apart`, sistemas algebraicos y `NSolve`. `AnalyzeDomain`, `Reduce` y `CertifiedN`
exponen análisis acotados con sus condiciones y límites. Consulte el
[lenguaje](docs/es/lenguaje.md) para conocer la sintaxis y el alcance comprobado.
Estas funciones están incluidas en la [versión preliminar 0.2.0-dev0](https://github.com/Stochasticboi/Mathechan/releases/tag/v0.2.0-dev0).
Las descargas anteriores conservan su alcance original.

## Desarrollo posterior

El código en desarrollo **0.2.0.dev6** incorpora límites, series, productos,
derivadas mixtas, cálculo vectorial cartesiano, cilíndrico y esférico e integrales iteradas.
La sustitución admite `expr /. x -> valor`, listas de reglas y reglas diferidas.
Los operadores curvilíneos usan componentes ortonormales y conservan las
condiciones de la carta; el jacobiano distingue derivadas de componentes y
gradiente vectorial geométrico.
Incluye álgebra lineal densa: operaciones con matrices, `Dot`/`A.B`,
determinantes, inversas, rango, sistemas lineales, autovalores, autovectores,
potencias y exponencial matricial. `N` admite matrices y listas numéricas.
Inicia probabilidad discreta finita: distribuciones y pesos normalizados,
Bernoulli, uniforme discreta, probabilidad de eventos, esperanza, varianza,
desviación estándar y entropía, con condiciones conservadas en sesión.
Admite tablas conjuntas finitas, marginales, condicionamiento sobre eventos,
covarianza y correlación de observables reales.
Estos incrementos no están en el descargable 0.2.0-dev0. Véase el
[lenguaje](docs/es/lenguaje.md) para el alcance y sus restricciones.

## Consola experimental

La versión publicada funciona **por consola** y utiliza un parser restringido
con evaluación mediante SymPy 1.14. Todavía no tiene interfaz gráfica.

- Aritmética exacta, incluidos decimales interpretados como racionales.
- Funciones `Sin`, `Cos`, `Exp`, `Log` y `Sqrt`.
- Operaciones `Expand`, `Simplify` y derivación con `D`.
- Gráficos univariados con `Plot` y exportación SVG.
- Lectura y escritura de cuadernos JSON `.mchan`, sin ejecución al abrir.

`Plot` utiliza 201 muestras uniformes: puede omitir singularidades entre
muestras y no dispone de muestreo adaptativo. Los cuadernos guardan resultados
de texto; los gráficos se exportan por separado. No se declara compatibilidad
general con Wolfram Language ni validación para uso científico general.

## Operaciones científicas en 0.1.1

La versión 0.1.1 amplía la consola con `N`, `Factor`, `Together`, `Cancel`,
`Substitute`, sumas finitas `Sum`, `Integrate`, `Solve` y `DSolve`. Añade listas,
igualdades `==` y metadatos para distinguir aproximación, condiciones y resultados
no resueltos. `N[Pi,50]` solicita 50 dígitos; `Sum[n^2,{n,1,10}]` devuelve 385.

Son implementaciones acotadas: álgebra racional sobre Q, sistemas algebraicos
lineales y EDO para una sola función de orden 1 o 2. Las condiciones y
verificaciones son parciales. Consulte [la sintaxis y los límites](docs/es/lenguaje.md)
y [el ejemplo sin resultados precalculados](examples/scientific.mchan).

Estas funciones corresponden a **0.1.1**; el ZIP anterior de 0.1.0 conserva
su alcance original. La interfaz gráfica y las herramientas especializadas
de física estadística siguen pendientes. Véanse las
[notas de 0.1.1](docs/es/versiones/0.1.1.md).

La consola de 0.2.0.dev0 conserva una sesión con definiciones e hipótesis.
La API de evaluación individual sigue sin estado. El alcance está en
[el lenguaje](docs/es/lenguaje.md).

## Descargas y código fuente

Las versiones publicadas y sus archivos se encuentran en
[Releases](https://github.com/Stochasticboi/Mathechan/releases/tag/v0.2.0-dev0).
Para Windows x64, descargue el
[archivo ZIP](https://github.com/Stochasticboi/Mathechan/releases/download/v0.2.0-dev0/Mathechan-0.2.0-dev0-windows-x64.zip),
descomprímalo y abra `Mathechan.exe`. Se abrirá una consola interactiva.
La interfaz gráfica sigue en desarrollo. Las notas de la versión incluyen
el código fuente, las sumas SHA-256 y las comprobaciones realizadas.

Para instalar desde el código fuente se requiere Python 3.11 o posterior.
Desde la carpeta del repositorio, preferiblemente en un entorno virtual:

```console
python -m pip install -e .
python -m mathechan "D[x^3, x]"
python -m mathechan "Plot[Exp[-x^2], {x, -3, 3}]" --output gaussian.svg
```

La primera evaluación devuelve `3*x**2`. La segunda crea un archivo SVG.

## Documentación

- [Objetivos y recorrido 2026–2031](docs/es/objetivos.md).
- [Historia del proyecto y antecedentes](docs/es/historia.md).
- [Comparativa con Mathematica](docs/es/comparativa.md).
- [Lenguaje experimental](docs/es/lenguaje.md).
- [Notas de la versión 0.1.1](docs/es/versiones/0.1.1.md).
- [Fuentes](docs/SOURCES.md).
- [Cómo contribuir](CONTRIBUTING.md).

La documentación está incluida en el repositorio y puede descargarse junto
con el código fuente. Los documentos distinguen funciones implementadas,
limitaciones actuales y objetivos de desarrollo.

## Pruebas y licencia

```console
python -m unittest discover -s tests -v
```

Mathechan se distribuye bajo **GPL-3.0-or-later**; véase [LICENSE](LICENSE).
Las dependencias conservan sus licencias. Mathematica y Wolfram Language son
referencias técnicas; Mathechan es un proyecto independiente de Wolfram Research.
