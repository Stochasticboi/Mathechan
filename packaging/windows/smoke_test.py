"""Check a Windows console executable without relying on an external Python."""

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


class SmokeTestError(RuntimeError):
    """The executable did not satisfy a distribution acceptance check."""


def isolated_environment(environment=None):
    """Retain Windows system paths, removing Python search configuration."""
    original = os.environ if environment is None else environment
    removed = {"PYTHONPATH", "PYTHONHOME", "PATH", "VIRTUAL_ENV", "__PYVENV_LAUNCHER__"}
    clean = {key: value for key, value in original.items() if key.upper() not in removed}
    system_root = next((value for key, value in original.items() if key.upper() == "SYSTEMROOT"), None)
    if not system_root:
        raise SmokeTestError("SystemRoot is required for the Windows executable check.")
    clean["PATH"] = str(Path(system_root) / "System32") + ";" + system_root
    return clean


def require(condition, message):
    if not condition:
        raise SmokeTestError(message)


def check_plot(payload, svg):
    """Check the exported curve and numerical data against a known sine curve."""
    require(payload.get("kind") == "plot", "Plot did not return a plot result.")
    points = payload.get("points")
    require(isinstance(points, list) and len(points) == 201, "Plot must return 201 samples.")
    for point in points:
        require(isinstance(point, list) and len(point) == 2, "Invalid plot sample.")
        require(all(isinstance(value, (int, float)) and not isinstance(value, bool)
                    and math.isfinite(value) for value in point), "Plot contains a nonfinite sample.")
    expected = [(math.pi * index / 200, math.sin(math.pi * index / 200)) for index in range(201)]
    require(all(math.isclose(actual[0], reference[0], rel_tol=1e-10, abs_tol=1e-12)
                and math.isclose(actual[1], reference[1], rel_tol=1e-10, abs_tol=1e-12)
                for actual, reference in zip(points, expected)), "Unexpected sine curve samples.")
    try:
        root = ET.fromstring(svg)
        curve = root.find("{http://www.w3.org/2000/svg}polyline")
        coordinates = [tuple(float(value) for value in pair.split(","))
                       for pair in curve.attrib["points"].split()] if curve is not None else []
    except (ET.ParseError, KeyError, ValueError) as error:
        raise SmokeTestError(f"Invalid SVG plot: {error}") from error
    require(root.tag == "{http://www.w3.org/2000/svg}svg" and len(coordinates) == 201,
            "SVG must contain a curve with 201 points.")
    require(root.get("width") == "640" and root.get("height") == "340"
            and root.get("viewBox") == "0 0 640 340", "Unexpected SVG canvas geometry.")
    require(all(len(pair) == 2 and all(math.isfinite(value) for value in pair) for pair in coordinates),
            "SVG contains invalid or nonfinite coordinates.")
    # The sine reference has range [0, 1]; the renderer adds 5% above and below.
    expected_coordinates = [(40 + 560 * x / math.pi, 280 - 240 * (y + 0.05) / 1.1)
                            for x, y in expected]
    require(all(math.isclose(actual[0], reference[0], rel_tol=0, abs_tol=0.001)
                and math.isclose(actual[1], reference[1], rel_tol=0, abs_tol=0.001)
                for actual, reference in zip(coordinates, expected_coordinates)),
            "SVG curve does not match the normalized sine samples.")
    require(payload.get("svg") == svg, "JSON and exported SVG differ.")


def smoke_test(executable, timeout=60):
    executable = Path(executable).resolve(strict=True)
    require(executable.is_file(), "Executable path must be a file.")
    require(math.isfinite(timeout) and timeout > 0, "Timeout must be positive and finite.")
    environment = isolated_environment()
    checks = []
    with tempfile.TemporaryDirectory(prefix="mathechan-smoke-") as directory:
        def run(*arguments, input_text=""):
            try:
                result = subprocess.run([str(executable), *arguments], input=input_text,
                                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                                        cwd=directory, env=environment, timeout=timeout)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise SmokeTestError(f"Executable check failed: {error}") from error
            require("Traceback" not in result.stdout + result.stderr, "Executable printed a traceback.")
            return result

        result = run("D[x^3,x]", "--json")
        require(result.returncode == 0, f"Derivative failed: {result.stderr}")
        try:
            payload = json.loads(result.stdout)
        except ValueError as error:
            raise SmokeTestError("Derivative did not return valid JSON.") from error
        require(isinstance(payload, dict) and payload.get("kind") == "expression"
                and payload.get("text") == "3*x**2", "Derivative JSON has an unexpected exact result.")
        checks.append("exact-derivative-json")

        result = run("1/0")
        require(result.returncode == 2 and "Error:" in result.stderr, "Division by zero was not a controlled error.")
        checks.append("controlled-error")

        svg_path = Path(directory) / "sine.svg"
        result = run("Plot[Sin[x],{x,0,Pi}]", "--json", "--output", str(svg_path))
        require(result.returncode == 0, f"SVG export failed: {result.stderr}")
        try:
            payload = json.loads(result.stdout)
            require(isinstance(payload, dict), "Plot JSON must be an object.")
            check_plot(payload, svg_path.read_text(encoding="utf-8"))
        except (ValueError, OSError) as error:
            raise SmokeTestError(f"Cannot read exported plot: {error}") from error
        checks.append("finite-svg-201-samples")

        result = run(input_text="D[x^3,x]\nexit\n")
        require(result.returncode == 0 and "3*x**2" in result.stdout and "Goodbye" in result.stdout,
                "Interactive calculation and exit failed.")
        checks.append("interactive-exit")
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--timeout", type=float, default=60, help="Timeout per invocation in seconds")
    args = parser.parse_args(argv)
    try:
        checks = smoke_test(args.executable, args.timeout)
    except (SmokeTestError, OSError) as error:
        parser.exit(1, f"Smoke test failed: {error}\n")
    print("OK: " + ", ".join(checks))
    print("System-path isolation passed; a separate clean Windows installation still requires validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
