"""Check a Windows console executable without relying on an external Python."""

import argparse
from decimal import Decimal, InvalidOperation, localcontext
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET


class SmokeTestError(RuntimeError):
    """The executable did not satisfy a distribution acceptance check."""


SCIENTIFIC_CASES = (
    ("numeric-precision", "N[Pi,30]"),
    ("factor", "Factor[x^2-1]"),
    ("together", "Together[1/x+1/y]"),
    ("cancel-with-domain", "Cancel[(x^2-1)/(x-1)]"),
    ("substitute", "Substitute[a*x,a,2]"),
    ("finite-sum", "Sum[n^2,{n,1,3}]"),
    ("definite-integral", "Integrate[x^2,{x,0,1}]"),
    ("algebraic-solutions", "Solve[x^2==4,x]"),
    ("verified-initial-value-ode", "DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]"),
    ("wolfram-replacement", "(x^2+a*x)/.x->2"),
    ("mixed-derivative", "D[x^2*y^3,{x,2},y]"),
    ("taylor-remainder", "Series[Sin[x],{x,0,5}]"),
    ("finite-product", "Product[k,{k,1,5}]"),
    ("convergent-infinite-sum", "Sum[1/n^2,{n,1,Infinity}]"),
    ("cartesian-curl", "Curl[{-y,x,0},{x,y,z}]"),
    ("iterated-integral", "Integrate[1,{x,0,1},{y,0,x}]"),
    ("bilateral-limit", "Limit[Sin[x]/x,x,0]"),
    ("series-normal", "Normal[Series[Exp[x],{x,0,2}]]"),
    ("spherical-gradient", 'Grad[r^2,{r,theta,phi},"Spherical"]'),
    ("spherical-divergence", 'Div[{r,0,0},{r,theta,phi},"Spherical"]'),
    ("cylindrical-curl", 'Curl[{0,rho,0},{rho,phi,z},"Cylindrical"]'),
    ("geometric-hessian", 'Hessian[r^2/2,{r,theta,phi},"Spherical"]'),
    ("component-jacobian", 'Jacobian[{r,0,0},{r,theta,phi},"Spherical"]'),
    ("physical-vector-gradient", 'Jacobian[{r,0,0},{r,theta,phi},"Spherical","Orthonormal"]'),
    ("matrix-dimensions", "Dimensions[{{1,2},{3,4}}]"),
    ("matrix-dot", "{{1,2},{3,4}}.{{5,6},{7,8}}"),
    ("matrix-transpose", "Transpose[{{1,2},{3,4}}]"),
    ("matrix-trace", "Tr[{{1,2},{3,4}}]"),
    ("matrix-determinant", "Det[{{1,2},{3,4}}]"),
    ("matrix-inverse", "Inverse[{{1,2},{3,4}}]"),
    ("matrix-rank", "MatrixRank[{{1,2},{2,4}}]"),
    ("matrix-linear-solve", "LinearSolve[{{2,0},{0,3}},{4,9}]"),
    ("matrix-eigenvalues", "Eigenvalues[{{1,0},{0,2}}]"),
    ("matrix-eigenvectors", "Eigenvectors[{{1,0},{0,2}}]"),
    ("matrix-power", "MatrixPower[{{1,1},{0,1}},3]"),
    ("matrix-exponential", "MatrixExp[{{0,1},{0,0}}]"),
    ("finite-mean", "Mean[FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]]"),
    ("finite-variance", "Variance[FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]]"),
    ("finite-entropy", "Entropy[FiniteDistribution[{0,1},{1/2,1/2}]]"),
    ("finite-event", "Probability[x>=1,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]"),
    ("finite-expectation", "Expectation[x^2,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]"),
    ("weighted-mean", "Mean[WeightedDistribution[{0,2},{1,3}]]"),
    ("bernoulli-variance", "Variance[BernoulliDistribution[1/4]]"),
    ("discrete-uniform-mean", "Mean[DiscreteUniformDistribution[{1,6}]]"),
    ("joint-event", "Probability[And[x==1,y==1],{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]"),
    ("joint-expectation", "Expectation[x*y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]"),
    ("joint-marginal", "Mean[MarginalDistribution[JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}],1]]"),
    ("joint-conditional", "Probability[y==1,{{x,y},ConditionalDistribution[x==1,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]}]"),
    ("joint-covariance", "Covariance[x,y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]"),
    ("joint-correlation", "Correlation[x,y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]"),
)

CURVILINEAR_REFERENCES = {
    'Grad[r^2,{r,theta,phi},"Spherical"]': ("matrix", "Matrix([\n[2*r],\n[  0],\n[  0]])", "Spherical", "orthonormal"),
    'Div[{r,0,0},{r,theta,phi},"Spherical"]': ("expression", "3", "Spherical", "orthonormal"),
    'Curl[{0,rho,0},{rho,phi,z},"Cylindrical"]': ("matrix", "Matrix([\n[0],\n[0],\n[2]])", "Cylindrical", "orthonormal"),
    'Hessian[r^2/2,{r,theta,phi},"Spherical"]': ("matrix", "Matrix([\n[1, 0, 0],\n[0, 1, 0],\n[0, 0, 1]])", "Spherical", "orthonormal"),
    'Jacobian[{r,0,0},{r,theta,phi},"Spherical"]': ("matrix", "Matrix([\n[1, 0, 0],\n[0, 0, 0],\n[0, 0, 0]])", "Spherical", "component_functions_by_coordinate"),
    'Jacobian[{r,0,0},{r,theta,phi},"Spherical","Orthonormal"]': ("matrix", "Matrix([\n[1, 0, 0],\n[0, 1, 0],\n[0, 0, 1]])", "Spherical", "orthonormal"),
}

EXACT_REFERENCES = {
    "Probability[And[x==1,y==1],{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": ("expression", "3/8"),
    "Expectation[x*y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": ("expression", "3/8"),
    "Mean[MarginalDistribution[JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}],1]]": ("expression", "1/2"),
    "Probability[y==1,{{x,y},ConditionalDistribution[x==1,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]}]": ("expression", "3/4"),
    "Covariance[x,y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": ("expression", "1/8"),
    "Correlation[x,y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": ("expression", "1/2"),
    "Mean[FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]]": ("expression", "1"),
    "Variance[FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]]": ("expression", "1/2"),
    "Entropy[FiniteDistribution[{0,1},{1/2,1/2}]]": ("expression", "log(2)"),
    "Probability[x>=1,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]": ("expression", "3/4"),
    "Expectation[x^2,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]": ("expression", "3/2"),
    "Mean[WeightedDistribution[{0,2},{1,3}]]": ("expression", "3/2"),
    "Variance[BernoulliDistribution[1/4]]": ("expression", "3/16"),
    "Mean[DiscreteUniformDistribution[{1,6}]]": ("expression", "7/2"),
    "Dimensions[{{1,2},{3,4}}]": ("list", "{2,2}"),
    "{{1,2},{3,4}}.{{5,6},{7,8}}": ("matrix", "Matrix([\n[19, 22],\n[43, 50]])"),
    "Transpose[{{1,2},{3,4}}]": ("matrix", "Matrix([\n[1, 3],\n[2, 4]])"),
    "Tr[{{1,2},{3,4}}]": ("expression", "5"),
    "Det[{{1,2},{3,4}}]": ("expression", "-2"),
    "Inverse[{{1,2},{3,4}}]": ("matrix", "Matrix([\n[ -2,    1],\n[3/2, -1/2]])"),
    "MatrixRank[{{1,2},{2,4}}]": ("expression", "1"),
    "LinearSolve[{{2,0},{0,3}},{4,9}]": ("list", "{2,3}"),
    "Eigenvalues[{{1,0},{0,2}}]": ("list", "{1,2}"),
    "Eigenvectors[{{1,0},{0,2}}]": ("list", "{{1,0},{0,1}}"),
    "MatrixPower[{{1,1},{0,1}},3]": ("matrix", "Matrix([\n[1, 3],\n[0, 1]])"),
    "MatrixExp[{{0,1},{0,0}}]": ("matrix", "Matrix([\n[1, 1],\n[0, 1]])"),
    "Factor[x^2-1]": ("expression", "(x - 1)*(x + 1)"),
    "Together[1/x+1/y]": ("expression", "(x + y)/(x*y)"),
    "Cancel[(x^2-1)/(x-1)]": ("expression", "x + 1"),
    "Substitute[a*x,a,2]": ("expression", "2*x"),
    "Sum[n^2,{n,1,3}]": ("expression", "14"),
    "Integrate[x^2,{x,0,1}]": ("expression", "1/3"),
    "Solve[x^2==4,x]": ("solutions", "{-2, 2}"),
    "DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]": ("solutions", "Eq(y(x), 3*exp(-2*x))"),
    "(x^2+a*x)/.x->2": ("expression", "2*a + 4"),
    "D[x^2*y^3,{x,2},y]": ("expression", "6*y**2"),
    "Series[Sin[x],{x,0,5}]": ("expression", "x - x**3/6 + x**5/120 + O(x**6)"),
    "Product[k,{k,1,5}]": ("expression", "120"),
    "Sum[1/n^2,{n,1,Infinity}]": ("expression", "pi**2/6"),
    "Curl[{-y,x,0},{x,y,z}]": ("matrix", "Matrix([\n[0],\n[0],\n[2]])"),
    "Integrate[1,{x,0,1},{y,0,x}]": ("expression", "1/2"),
    "Limit[Sin[x]/x,x,0]": ("expression", "1"),
    "Normal[Series[Exp[x],{x,0,2}]]": ("expression", "x**2/2 + x + 1"),
}


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


def check_scientific_payload(source, payload):
    """Check explicit reference values and metadata without evaluating input text."""
    require(isinstance(payload, dict), f"Scientific JSON must be an object: {source}")
    require(isinstance(payload.get("text"), str), f"Scientific JSON needs text: {source}")
    require(isinstance(payload.get("conditions"), list)
            and all(isinstance(item, str) for item in payload["conditions"]), "Invalid scientific conditions metadata.")
    require(isinstance(payload.get("warnings"), list)
            and all(isinstance(item, str) for item in payload["warnings"]), "Invalid scientific warnings metadata.")
    details = payload.get("details")
    require(isinstance(details, dict), "Scientific JSON needs details metadata.")
    if source == "N[Pi,30]":
        require(payload.get("kind") == "expression" and payload.get("status") == "approximate"
                and payload.get("exact") is False, "N must be explicitly approximate, not exact.")
        evaluations = details.get("numeric_evaluations")
        require(isinstance(evaluations, list) and len(evaluations) == 1
                and isinstance(evaluations[0], dict), "N must report its requested precision.")
        precision = evaluations[0].get("requested_significant_digits")
        require(type(precision) is int and precision == 30 and evaluations[0].get("approximate") is True,
                "N must report 30 requested significant digits.")
        try:
            value = Decimal(payload["text"])
            require(value.is_finite() and len(value.as_tuple().digits) == 30,
                    "N must print a finite value with 30 significant digits.")
            with localcontext() as context:
                context.prec = 80
                reference = Decimal("3.14159265358979323846264338327950288419716939937510")
                require(abs(value - reference) <= Decimal("5e-30"), "N does not meet the 30-digit pi reference.")
        except InvalidOperation as error:
            raise SmokeTestError("N did not return a decimal value.") from error
        return
    if source in CURVILINEAR_REFERENCES:
        kind, text, chart, basis = CURVILINEAR_REFERENCES[source]
        require(payload.get("kind") == kind and payload["text"] == text,
                f"Unexpected exact curvilinear result: {source}")
        require(payload.get("exact") is True and payload.get("status") == "conditional",
                "Curvilinear results must preserve the regular chart domain.")
        required = ({"Contains(r, Reals)", "Contains(theta, Reals)", "Contains(phi, Reals)",
                     "r > 0", "theta > 0", "theta < pi"} if chart == "Spherical" else
                    {"Contains(rho, Reals)", "Contains(phi, Reals)", "Contains(z, Reals)", "rho > 0"})
        require(required.issubset(payload["conditions"]), "Curvilinear result lost chart requirements.")
        require(details.get("coordinates") == chart and details.get("basis") == basis,
                "Curvilinear result lost chart or basis metadata.")
        return
    require(source in EXACT_REFERENCES, f"Unknown scientific reference: {source}")
    kind, text = EXACT_REFERENCES[source]
    expected_status = ("verified" if source.startswith("DSolve[") else "series"
                       if source.startswith(("Series[", "Normal[")) else "evaluated")
    require(payload.get("kind") == kind and payload["text"] == text,
            f"Unexpected exact scientific result: {source}")
    require(payload.get("exact") is True and payload.get("status") == expected_status,
            f"Unexpected scientific exactness or status: {source}")
    if source.startswith("Series["):
        require(details.get("global_equality") is False and details.get("truncated") is True
                and details.get("remainder") == ["O(x**6)"], "Series lost its local remainder metadata.")
    if source.startswith("Normal["):
        require(details.get("normal", {}).get("global_equality") is False and bool(payload["warnings"]),
                "Normal must retain its approximation provenance.")
    if source.startswith("Together["):
        require(set(payload["conditions"]) == {"(x) != 0", "(y) != 0"}, "Together lost its original domain conditions.")
    elif source.startswith("Cancel["):
        require(payload["conditions"] == ["((-1+x)) != 0"], "Cancel lost the excluded point x=1.")
    if source.startswith("Solve["):
        require(details.get("verification") == "verified", "Solve roots were not verified.")
    elif source.startswith("DSolve["):
        require(details.get("verification") == "verified" and details.get("ode_residuals") == ["0"]
                and details.get("initial_residuals") == ["0"] and details.get("initial_defined") is True
                and type(details.get("initial_conditions")) is int and details["initial_conditions"] == 1,
                "DSolve did not verify its ODE and initial data.")


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


def check_session_outputs(result, fresh):
    """Check exact snapshots, failure atomicity, and process-local state."""
    def values(output):
        return [part.strip().splitlines()[0]
                for part in output.split("Mathechan> ")[1:] if part.strip()]

    require(result.returncode == 0 and "Goodbye" in result.stdout,
            "Session did not exit normally.")
    require(values(result.stdout)[:6] == ["1/3", "2/3", "5", "2/3", "0", "0"],
            "Session lost exact values, immediate snapshots, or assignment atomicity.")
    require("Error:" in result.stderr, "Failed assignment did not report its error.")
    require(fresh.returncode == 0 and fresh.stderr == "" and "Goodbye" in fresh.stdout,
            "Fresh session did not exit normally.")
    require(values(fresh.stdout)[0:1] == ["b"], "Definitions leaked into a fresh process.")


def smoke_test(executable, timeout=60, scientific=False, sessions=False):
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
        if scientific:
            for label, source in SCIENTIFIC_CASES:
                result = run(source, "--json")
                require(result.returncode == 0, f"Scientific operation failed: {source}: {result.stderr}")
                try:
                    payload = json.loads(result.stdout)
                except ValueError as error:
                    raise SmokeTestError(f"Scientific operation did not return JSON: {source}") from error
                check_scientific_payload(source, payload)
                checks.append(label)
        if sessions:
            result = run(input_text="a=1/3\nb=a+a\na=5\nb\nx=0\nx=1/0\nx\nsalir\n")
            fresh = run(input_text="b\nsalir\n")
            check_session_outputs(result, fresh)
            checks.extend(("session-exact-snapshots-and-atomicity", "fresh-process-isolation"))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--timeout", type=float, default=60, help="Timeout per invocation in seconds")
    parser.add_argument("--scientific", action="store_true", help="Also verify scientific and calculus operations")
    parser.add_argument("--sessions", action="store_true", help="Also verify numerical assignment sessions")
    args = parser.parse_args(argv)
    try:
        checks = smoke_test(args.executable, args.timeout, scientific=args.scientific, sessions=args.sessions)
    except (SmokeTestError, OSError) as error:
        parser.exit(1, f"Smoke test failed: {error}\n")
    print("OK: " + ", ".join(checks))
    print("System-path isolation passed; a separate clean Windows installation still requires validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
