"""Collect distribution notices and the Python license for binary redistribution."""

from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys


NAMES = ("sympy", "mpmath", "pyinstaller", "pyinstaller-hooks-contrib",
         "setuptools", "packaging", "altgraph", "pefile", "pywin32-ctypes")
NOTICE_MARKERS = ("LICENSE", "COPYING", "NOTICE", "AUTHORS")


def collect_licenses(destination, names=NAMES, python_prefix=None):
    """Validate every listed notice before copying; require a nonempty license."""
    destination = Path(destination)
    sources = []
    for name in names:
        package = distribution(name)
        files = [file for file in package.files or ()
                 if any(marker in file.name.upper() for marker in NOTICE_MARKERS)]
        if not files:
            raise SystemExit(f"No license notices found for {name}; inspect the installed distribution.")
        has_license = False
        for index, relative in enumerate(files):
            origin = Path(package.locate_file(relative))
            if not origin.is_file():
                raise SystemExit(f"Listed notice is missing for {name}: {relative}")
            try:
                content = origin.read_bytes()
            except OSError as error:
                raise SystemExit(f"Cannot read notice for {name}: {relative}: {error}") from error
            if any(marker in relative.name.upper() for marker in ("LICENSE", "COPYING")) and content.strip():
                has_license = True
            sources.append((origin, destination / name / f"{index:02d}-{relative.name}"))
        if not has_license:
            raise SystemExit(f"No nonempty LICENSE or COPYING file found for {name}; AUTHORS alone is insufficient.")
    python_license = Path(sys.base_prefix if python_prefix is None else python_prefix) / "LICENSE.txt"
    try:
        if not python_license.is_file() or not python_license.read_bytes().strip():
            raise SystemExit("Python LICENSE.txt is missing or empty; inspect the Python installation.")
        sources.append((python_license, destination / "PYTHON-LICENSE.txt"))
        for origin, target in sources:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origin, target)
    except OSError as error:
        raise SystemExit(f"Cannot collect required license notices: {error}") from error


def main():
    collect_licenses(sys.argv[1])


if __name__ == "__main__":
    main()
