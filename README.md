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

## Distribución publicada: 0.1.0 experimental

La versión actual funciona **por consola** y utiliza un parser restringido
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

## Código en desarrollo: operaciones científicas

La rama de desarrollo amplía la consola con `N`, `Factor`, `Together`, `Cancel`,
`Substitute`, sumas finitas `Sum`, `Integrate`, `Solve` y `DSolve`. Añade listas,
igualdades `==` y metadatos para distinguir aproximación, condiciones y resultados
no resueltos. `N[Pi,50]` solicita 50 dígitos; `Sum[n^2,{n,1,10}]` devuelve 385.

Son implementaciones acotadas: álgebra racional sobre Q, sistemas algebraicos
lineales y EDO para una sola función de orden 1 o 2. Las condiciones y
verificaciones son parciales. Consulte [la sintaxis y los límites](docs/es/lenguaje.md)
y [el ejemplo sin resultados precalculados](examples/scientific.mchan).

**Todavía no hay una nueva release para estas funciones.** El código mantiene
la versión de paquete 0.1.0; eso no incorpora estas capacidades al ZIP v0.1.0
publicado anteriormente. La interfaz gráfica y las herramientas especializadas
de física estadística siguen pendientes.

## Descargas y código fuente

Las versiones publicadas y sus archivos se encuentran en
[Releases](https://github.com/Stochasticboi/Mathechan/releases/tag/v0.1.0).
Para Windows x64, descargue el
[archivo ZIP](https://github.com/Stochasticboi/Mathechan/releases/download/v0.1.0/Mathechan-0.1.0-windows-x64.zip),
descomprímalo y abra `Mathechan.exe`. Se abrirá una consola interactiva.
La interfaz gráfica sigue en desarrollo. Las notas de la versión incluyen
los paquetes Python, el código fuente y las comprobaciones realizadas.

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
