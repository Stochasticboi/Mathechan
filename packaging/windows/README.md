# Windows console distribution / Distribución de consola Windows

## English

This recipe targets Windows x64 and CPython 3.12. The output is a console
application, `dist/Mathechan.exe`. Without arguments it opens an interactive
console; command-line arguments use the existing evaluator. It is not a
graphical desktop interface. The recipe must run on Windows; PyInstaller does
not cross-compile Windows executables on other systems.

From the repository root, with the Python launcher and 64-bit Python 3.12 installed:

```powershell
.\packaging\windows\build.ps1
```

An explicit interpreter path also avoids shell aliases:

```powershell
.\packaging\windows\build.ps1 -PythonExecutable C:\Python312\python.exe
```

Replace that example with the actual 64-bit CPython 3.12 path.

The script creates a new `.venv-build`, installs the versions fixed in
`requirements-build.txt`, runs the tests, collects license notices, and invokes:

```powershell
$buildPython = (Resolve-Path .\.venv-build\Scripts\python.exe).Path
$licenseDir = (Resolve-Path build/windows/licenses).Path
& $buildPython -m PyInstaller --noconfirm --clean --onefile --console --name Mathechan --paths src --distpath dist --workpath build/windows/work --specpath build/windows --copy-metadata sympy --copy-metadata mpmath --add-data ('{0}:licenses' -f $licenseDir) packaging/windows/launcher.py
```

For an existing clean environment with those dependencies and the project
already installed, collect notices with its Python interpreter first:

```powershell
& $buildPython packaging/windows/collect_licenses.py build/windows/licenses
Copy-Item -LiteralPath LICENSE -Destination build/windows/licenses/MATHECHAN-LICENSE.txt
```

Set `$buildPython` to that environment's absolute interpreter path before
collecting notices and running the PyInstaller command above.
Keep the notices alongside the executable in the release archive as well.
The script never deletes an existing environment: use a clean checkout for a
new build. Pinning dependency versions does not guarantee identical bytes
across operating system or Python patch versions. Record the Python version,
architecture, dependency list, source revision, and executable checksum.

The recipe runs the executable acceptance check before reporting success:

```powershell
& $buildPython packaging/windows/smoke_test.py dist/Mathechan.exe --timeout 60 --scientific
```

The timeout applies to each invocation. The check verifies exact derivative JSON,
a controlled division-by-zero error without a traceback, all 201 sine samples
against `math.sin`, the SVG coordinates on a 640×340 canvas with 5% padding
(0.001 coordinate tolerance), and an interactive calculation followed by exit. It removes
`PYTHONPATH`, `PYTHONHOME`, and virtual-environment settings from the subprocess
environment, and sets `PATH` to Windows/System32 and Windows. It runs from a
temporary working directory without the source tree on the Python search path.
The scientific option adds nine JSON checks for numerical precision, rational
algebra, substitution, finite sums, integration, equation roots, and ODE/initial
residuals. All thirteen checks must pass. This checks system-path isolation,
not a separate clean machine.

The Windows CI job uses this recipe and uploads its executable, notices, build
environment, and SHA-256 only after all checks pass. It does not publish releases.

For broader Windows validation, also execute the binary on a separate installation:

```powershell
.\dist\Mathechan.exe 'D[x^3,x]'
.\dist\Mathechan.exe --demo --output gaussian.svg
.\dist\Mathechan.exe
Get-FileHash -Algorithm SHA256 -LiteralPath dist/Mathechan.exe
```

Check expected expressions, errors, interactive exit, JSON output, SVG content,
and running without a separate Python installation. Source tests do not prove
that an executable works. Record build and binary validation results for each
release. Experimental release notes must state when independent clean-Windows
validation is pending. A passing check covers these cases, not every setup.

## Español

La receta apunta a Windows x64 y CPython 3.12. Produce `dist/Mathechan.exe`, una
aplicación de consola: sin argumentos abre una sesión interactiva y con argumentos
ejecuta el evaluador existente. Todavía no hay interfaz gráfica. La construcción
debe ejecutarse en Windows.

Desde la raíz del repositorio, ejecute `packaging/windows/build.ps1`. Crea un
entorno `.venv-build` nuevo, instala las versiones fijadas, ejecuta pruebas,
recoge avisos de licencia y construye el ejecutable. No borra entornos existentes.
Los comandos anteriores también permiten usar un entorno limpio ya preparado.
Puede indicar un intérprete absoluto con `-PythonExecutable`; los comandos
manuales usan `$buildPython` para evitar alias del shell.

La receta ejecuta `smoke_test.py` sobre el binario antes de declarar éxito.
Comprueba derivada JSON exacta, error de división por cero sin traceback,
las 201 muestras contra `math.sin`, sus coordenadas SVG en un lienzo 640×340
con margen del 5% (tolerancia 0.001) y cálculo interactivo seguido de salida.
La opción `--scientific`, activada por la receta, añade nueve comprobaciones JSON
de precisión, álgebra racional, sustitución, sumas, integrales, raíces y residuos
de EDO/datos iniciales. Deben pasar las trece comprobaciones.
Cada invocación tiene un timeout configurable. El proceso elimina `PYTHONPATH`,
`PYTHONHOME` y variables de entorno virtual; su `PATH` contiene únicamente
Windows/System32 y Windows. Trabaja en un directorio temporal. Este aislamiento
de rutas no equivale a probar en otra máquina limpia.

El trabajo Windows de CI construye y comprueba el ejecutable real; solo después
sube el artefacto con avisos, entorno y SHA-256. No publica versiones.

Para ampliar la validación, compruebe el binario en otra instalación Windows, sin Python
instalado: cálculo exacto, errores controlados, salida del modo interactivo,
salida JSON y exportación SVG. Registre versiones, revisión fuente y SHA-256.
Las notas de una versión experimental deben declarar si esa validación sigue
pendiente. Las pruebas del código fuente no sustituyen las del ejecutable. Superar los
casos de aceptación tampoco verifica todas las instalaciones Windows posibles.

## Versions and licenses / Versiones y licencias

Version selections were checked on PyPI on 2026-10-18. Runtime dependencies
are pinned for this recipe independently of the package's supported ranges.
The selected build dependencies are not all claimed to be their newest release.

- [PyInstaller 6.22.3](https://pypi.org/project/pyinstaller/6.22.3/)
  and [usage options](https://pyinstaller.org/en/v6.22.3/usage.html).
- [Hooks 2026.8](https://pypi.org/project/pyinstaller-hooks-contrib/2026.8/),
  [altgraph 0.17.5](https://pypi.org/project/altgraph/0.17.5/),
  [pefile 2024.8.26](https://pypi.org/project/pefile/2024.8.26/),
  [pywin32-ctypes 0.2.3](https://pypi.org/project/pywin32-ctypes/0.2.3/).
- [setuptools 80.9.0](https://pypi.org/project/setuptools/80.9.0/),
  [packaging 26.3](https://pypi.org/project/packaging/26.3/),
  [SymPy 1.14.0](https://pypi.org/project/sympy/1.14.0/),
  [mpmath 1.3.0](https://pypi.org/project/mpmath/1.3.0/).

The collector copies installed SymPy, mpmath, PyInstaller and hooks license
notices, plus Python's `LICENSE.txt` and Mathechan's GPL license. Metadata for
SymPy and mpmath is also bundled with `--copy-metadata`; this does not replace
license review. Preserve notices and provide the corresponding Mathechan source
for binary redistribution under its license. The [PyInstaller license](https://pyinstaller.org/en/v6.22.3/license.html)
includes an executable distribution exception; dependency licenses still apply.
The collector requires every notice listed in distribution metadata to exist,
be readable, and copy successfully. Each distribution needs a nonempty file
whose name contains LICENSE or COPYING; AUTHORS or NOTICE alone is insufficient.
Python's LICENSE.txt must also exist and be nonempty. A collection failure stops
the build. This verifies the presence of these files, not their legal adequacy.

El colector falla si falta cualquier aviso listado o no puede leerlo o copiarlo.
Cada distribución requiere un archivo LICENSE o COPYING no vacío; AUTHORS o
NOTICE por sí solos no bastan. También exige LICENSE.txt de Python. Esto verifica
la presencia de los archivos; no sustituye la revisión de sus condiciones.
