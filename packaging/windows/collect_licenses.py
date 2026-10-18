"""Collect distribution notices and the Python license for binary redistribution."""

from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys


def main():
    destination = Path(sys.argv[1])
    destination.mkdir(parents=True, exist_ok=True)
    names = ("sympy", "mpmath", "pyinstaller", "pyinstaller-hooks-contrib",
             "setuptools", "packaging", "altgraph", "pefile", "pywin32-ctypes")
    for name in names:
        package = distribution(name)
        files = [file for file in package.files or ()
                 if any(marker in file.name.upper() for marker in ("LICENSE", "COPYING", "NOTICE", "AUTHORS"))]
        if not files:
            raise SystemExit(f"No license notices found for {name}; inspect the installed distribution.")
        for index, relative in enumerate(files):
            origin = Path(package.locate_file(relative))
            if origin.is_file():
                target = destination / name / f"{index:02d}-{relative.name}"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(origin, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if not python_license.is_file():
        raise SystemExit("Python LICENSE.txt was not found; inspect the Python installation.")
    shutil.copy2(python_license, destination / "PYTHON-LICENSE.txt")


if __name__ == "__main__":
    main()
