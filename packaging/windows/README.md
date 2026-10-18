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

The script creates a new `.venv-build`, installs the versions fixed in
`requirements-build.txt`, runs the tests, collects license notices, and invokes:

```powershell
$licenseDir = (Resolve-Path build/windows/licenses).Path
.\.venv-build\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --console --name Mathechan --paths src --distpath dist --workpath build/windows/work --specpath build/windows --copy-metadata sympy --copy-metadata mpmath --add-data ('{0}:licenses' -f $licenseDir) packaging/windows/launcher.py
```

For an existing clean environment with those dependencies and the project
already installed, collect notices with its Python interpreter first:

```powershell
python packaging/windows/collect_licenses.py build/windows/licenses
Copy-Item -LiteralPath LICENSE -Destination build/windows/licenses/MATHECHAN-LICENSE.txt
```

Then run the PyInstaller command above with that environment's `python`.
Keep the notices alongside the executable in the release archive as well.
The script never deletes an existing environment: use a clean checkout for a
new build. Pinning dependency versions does not guarantee identical bytes
across operating system or Python patch versions. Record the Python version,
architecture, dependency list, source revision, and executable checksum.

Before publishing, execute the binary on a separate Windows installation:

```powershell
.\dist\Mathechan.exe 'D[x^3,x]'
.\dist\Mathechan.exe --demo --output gaussian.svg
.\dist\Mathechan.exe
Get-FileHash -Algorithm SHA256 -LiteralPath dist/Mathechan.exe
```

Check expected expressions, errors, interactive exit, JSON output, SVG content,
and running without a separate Python installation. Source tests do not prove
that an executable works. Record build and binary validation results for each
release; this recipe alone does not establish a successful package build.

## Español

La receta apunta a Windows x64 y CPython 3.12. Produce `dist/Mathechan.exe`, una
aplicación de consola: sin argumentos abre una sesión interactiva y con argumentos
ejecuta el evaluador existente. Todavía no hay interfaz gráfica. La construcción
debe ejecutarse en Windows.

Desde la raíz del repositorio, ejecute `packaging/windows/build.ps1`. Crea un
entorno `.venv-build` nuevo, instala las versiones fijadas, ejecuta pruebas,
recoge avisos de licencia y construye el ejecutable. No borra entornos existentes.
Los comandos anteriores también permiten usar un entorno limpio ya preparado.

Antes de publicar, verifique el binario en otra instalación Windows, sin Python
instalado: cálculo exacto, errores controlados, salida del modo interactivo,
salida JSON y exportación SVG. Registre versiones, revisión fuente y SHA-256.
Las pruebas del código fuente y esta receta no demuestran por sí solas que el
ejecutable esté construido o funcione correctamente.

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
The collector stops if notices are missing instead of assuming they exist.
