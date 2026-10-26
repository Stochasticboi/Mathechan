"""Scientific binary acceptance references and rejection of misleading metadata."""

import contextlib
import importlib.util
import io
import json
import math
import subprocess
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from mathechan import evaluate

ROOT = Path(__file__).resolve().parents[1]
SPECIFICATION = importlib.util.spec_from_file_location(
    "scientific_smoke", ROOT / "packaging" / "windows" / "smoke_test.py"
)
smoke = importlib.util.module_from_spec(SPECIFICATION)
SPECIFICATION.loader.exec_module(smoke)


def references():
    """Known algebraic identities, finite sum, polynomial integral, and decay."""
    results = {
        "Probabilities[Canon[{0,1,2},Log[2],{1,2,1}]]": {"kind":"list", "text":"{(4/9),(4/9),(1/9)}"},
        "Energy[Canon[{0,1,2},Log[2],{1,2,1}]]": {"kind":"expression", "text":"2/3"},
        "Variance[Canon[{0,1,2},Log[2],{1,2,1}]]": {"kind":"expression", "text":"4/9"},
        "Entropy[Canon[{0,1,2},0,{1,2,1}]]": {"kind":"expression", "text":"log(4)"},
        "Entropy[Dist[Canon[{0,1,2},0,{1,2,1}]]]": {"kind":"expression", "text":"3*log(2)/2"},
        "Energy[Canon[{2,3},Infinity]]": {"kind":"expression", "text":"2"},
        "HeatCapacity[Canon[{0,1},0]]": {"kind":"expression", "text":"0"},
        "Exp[LogZ[Canon[{0,1},Log[2]]]]": {"kind":"expression", "text":"3/2"},
        "Mean[BinomialDistribution[10,1/3]]": {"kind":"expression", "text":"10/3"},
        "Probability[x==0,{x,PoissonDistribution[0]}]": {"kind":"expression", "text":"1"},
        "CDF[NormalDistribution[0,1],0]": {"kind":"expression", "text":"1/2"},
        "Variance[ExponentialDistribution[2]]": {"kind":"expression", "text":"1/4"},
        "Moment[GammaDistribution[2,3],2]": {"kind":"expression", "text":"54"},
        "Cumulant[PoissonDistribution[3],4]": {"kind":"expression", "text":"3"},
        "MGF[ExponentialDistribution[2],1]": {"kind":"expression", "text":"2"},
        "CF[NormalDistribution[0,1],0]": {"kind":"expression", "text":"1"},
        "Expectation[x,{x,ExponentialDistribution[2]},x>1]": {"kind":"expression", "text":"3/2"},
        "Imag^2": {"kind": "expression", "text": "-1"},
        "Inner[{1,Imag},{1,Imag}]": {"kind": "expression", "text": "2"},
        "Kron[{0,1},{1,0}]": {"kind": "list", "text": "{0,0,1,0}"},
        "PTrace[Proj[{1,0,0,1}],{2,2},2]": {"kind": "matrix", "text": "Matrix([\n[1/2,   0],\n[  0, 1/2]])"},
        "HermQ[{{0,-Imag},{Imag,0}}]": {"kind": "logical", "text": "True"},
        "UnitaryQ[{{0,-Imag},{Imag,0}}]": {"kind": "logical", "text": "True"},
        "PSDCheck[Proj[{1,Imag}]]": {"kind": "logical", "text": "True"},
        "D[Sinh[x],x]": {"kind":"expression", "text":"cosh(x)"},
        "D[Tanh[x],x]": {"kind":"expression", "text":"1 - tanh(x)**2", "conditions":["(Cosh[x]) != 0"]},
        "Integrate[Sech[x],x]": {"kind":"expression", "text":"2*atan(tanh(x/2))", "details":{"verification":"verified","residual":"0"}},
        "Integrate[1/Sqrt[1+x^2],x]": {"kind":"expression", "text":"asinh(x)", "details":{"verification":"verified","residual":"0"}},
        "Probability[And[x==1,y==1],{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": {"kind":"expression", "text":"3/8"},
        "Expectation[x*y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": {"kind":"expression", "text":"3/8"},
        "Mean[MarginalDistribution[JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}],1]]": {"kind":"expression", "text":"1/2"},
        "Probability[y==1,{{x,y},ConditionalDistribution[x==1,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]}]": {"kind":"expression", "text":"3/4"},
        "Covariance[x,y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": {"kind":"expression", "text":"1/8"},
        "Correlation[x,y,{{x,y},JointFiniteDistribution[{{0,0},{0,1},{1,0},{1,1}},{3/8,1/8,1/8,3/8}]}]": {"kind":"expression", "text":"1/2"},
        "Mean[FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]]": {"kind":"expression", "text":"1"},
        "Variance[FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]]": {"kind":"expression", "text":"1/2"},
        "Entropy[FiniteDistribution[{0,1},{1/2,1/2}]]": {"kind":"expression", "text":"log(2)"},
        "Probability[x>=1,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]": {"kind":"expression", "text":"3/4"},
        "Expectation[x^2,{x,FiniteDistribution[{0,1,2},{1/4,1/2,1/4}]}]": {"kind":"expression", "text":"3/2"},
        "Mean[WeightedDistribution[{0,2},{1,3}]]": {"kind":"expression", "text":"3/2"},
        "Variance[BernoulliDistribution[1/4]]": {"kind":"expression", "text":"3/16"},
        "Mean[DiscreteUniformDistribution[{1,6}]]": {"kind":"expression", "text":"7/2"},
        "Dimensions[{{1,2},{3,4}}]": {"kind": "list", "text": "{2,2}"},
        "{{1,2},{3,4}}.{{5,6},{7,8}}": {"kind": "matrix", "text": "Matrix([\n[19, 22],\n[43, 50]])"},
        "Transpose[{{1,2},{3,4}}]": {"kind": "matrix", "text": "Matrix([\n[1, 3],\n[2, 4]])"},
        "Tr[{{1,2},{3,4}}]": {"kind": "expression", "text": "5"},
        "Det[{{1,2},{3,4}}]": {"kind": "expression", "text": "-2"},
        "Inverse[{{1,2},{3,4}}]": {"kind": "matrix", "text": "Matrix([\n[ -2,    1],\n[3/2, -1/2]])"},
        "MatrixRank[{{1,2},{2,4}}]": {"kind": "expression", "text": "1"},
        "LinearSolve[{{2,0},{0,3}},{4,9}]": {"kind": "list", "text": "{2,3}"},
        "Eigenvalues[{{1,0},{0,2}}]": {"kind": "list", "text": "{1,2}"},
        "Eigenvectors[{{1,0},{0,2}}]": {"kind": "list", "text": "{{1,0},{0,1}}"},
        "MatrixPower[{{1,1},{0,1}},3]": {"kind": "matrix", "text": "Matrix([\n[1, 3],\n[0, 1]])"},
        "MatrixExp[{{0,1},{0,0}}]": {"kind": "matrix", "text": "Matrix([\n[1, 1],\n[0, 1]])"},
        "N[Pi,30]": {
            "kind": "expression",
            "text": "3.14159265358979323846264338328",
            "exact": False,
            "status": "approximate",
            "details": {
                "numeric_evaluations": [
                    {"requested_significant_digits": 30, "approximate": True}
                ]
            },
        },
        "Factor[x^2-1]": {"kind": "expression", "text": "(x - 1)*(x + 1)"},
        "Together[1/x+1/y]": {
            "kind": "expression",
            "text": "(x + y)/(x*y)",
            "conditions": ["(x) != 0", "(y) != 0"],
        },
        "Cancel[(x^2-1)/(x-1)]": {
            "kind": "expression",
            "text": "x + 1",
            "conditions": ["((-1+x)) != 0"],
        },
        "Substitute[a*x,a,2]": {"kind": "expression", "text": "2*x"},
        "(x^2+a*x)/.x->2": {"kind": "expression", "text": "2*a + 4"},
        "D[x^2*y^3,{x,2},y]": {"kind": "expression", "text": "6*y**2"},
        "Series[Sin[x],{x,0,5}]": {"kind": "expression", "text": "x - x**3/6 + x**5/120 + O(x**6)",
                                   "status": "series", "details": {"global_equality": False, "truncated": True, "remainder": ["O(x**6)"]}},
        "Product[k,{k,1,5}]": {"kind": "expression", "text": "120"},
        "Sum[1/n^2,{n,1,Infinity}]": {"kind": "expression", "text": "pi**2/6"},
        "Curl[{-y,x,0},{x,y,z}]": {"kind": "matrix", "text": "Matrix([\n[0],\n[0],\n[2]])"},
        "Integrate[1,{x,0,1},{y,0,x}]": {"kind": "expression", "text": "1/2"},
        "Limit[Sin[x]/x,x,0]": {"kind": "expression", "text": "1"},
        "Normal[Series[Exp[x],{x,0,2}]]": {"kind": "expression", "text": "x**2/2 + x + 1",
                                           "status": "series", "warnings": ["local approximation"],
                                           "details": {"normal": {"global_equality": False}}},
        "Sum[n^2,{n,1,3}]": {"kind": "expression", "text": "14"},
        "Integrate[x^2,{x,0,1}]": {"kind": "expression", "text": "1/3"},
        "Solve[x^2==4,x]": {
            "kind": "solutions",
            "text": "{-2, 2}",
            "details": {"verification": "verified"},
        },
        "DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]": {
            "kind": "solutions",
            "text": "Eq(y(x), 3*exp(-2*x))",
            "status": "verified",
            "details": {
                "verification": "verified",
                "ode_residuals": ["0"],
                "initial_residuals": ["0"],
                "initial_defined": True,
                "initial_conditions": 1,
            },
        },
    }
    spherical = ["Contains(r, Reals)", "Contains(theta, Reals)", "Contains(phi, Reals)",
                 "r > 0", "theta > 0", "theta < pi"]
    cylindrical = ["Contains(rho, Reals)", "Contains(phi, Reals)", "Contains(z, Reals)", "rho > 0"]
    for source, kind, text, chart, basis, conditions in (
        ('Grad[r^2,{r,theta,phi},"Spherical"]', "matrix", "Matrix([\n[2*r],\n[  0],\n[  0]])", "Spherical", "orthonormal", spherical),
        ('Div[{r,0,0},{r,theta,phi},"Spherical"]', "expression", "3", "Spherical", "orthonormal", spherical),
        ('Curl[{0,rho,0},{rho,phi,z},"Cylindrical"]', "matrix", "Matrix([\n[0],\n[0],\n[2]])", "Cylindrical", "orthonormal", cylindrical),
        ('Hessian[r^2/2,{r,theta,phi},"Spherical"]', "matrix", "Matrix([\n[1, 0, 0],\n[0, 1, 0],\n[0, 0, 1]])", "Spherical", "orthonormal", spherical),
        ('Jacobian[{r,0,0},{r,theta,phi},"Spherical"]', "matrix", "Matrix([\n[1, 0, 0],\n[0, 0, 0],\n[0, 0, 0]])", "Spherical", "component_functions_by_coordinate", spherical),
        ('Jacobian[{r,0,0},{r,theta,phi},"Spherical","Orthonormal"]', "matrix", "Matrix([\n[1, 0, 0],\n[0, 1, 0],\n[0, 0, 1]])", "Spherical", "orthonormal", spherical),
    ):
        results[source] = {"kind": kind, "text": text, "status": "conditional",
                           "conditions": list(conditions), "details": {"coordinates": chart, "basis": basis}}
    for payload in results.values():
        payload.setdefault("exact", True)
        payload.setdefault("status", "evaluated")
        payload.setdefault("details", {})
        payload.setdefault("conditions", [])
        payload.setdefault("warnings", [])
    return results


def plot_fixture():
    points = [
        [math.pi * index / 200, math.sin(math.pi * index / 200)] for index in range(201)
    ]
    coordinates = " ".join(
        f"{40 + 2.8 * index:.3f},{280 - (240 / 1.1) * (point[1] + 0.05):.3f}"
        for index, point in enumerate(points)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="640" height="340" viewBox="0 0 640 340">'
        f'<polyline points="{coordinates}"/></svg>'
    )
    return {"kind": "plot", "points": points, "svg": svg}, svg


class ScientificPayloadTests(unittest.TestCase):
    def test_independent_references_and_current_source_satisfy_contract(self):
        fixtures = references()
        self.assertEqual(len(smoke.SCIENTIFIC_CASES), 78)
        for _, source in smoke.SCIENTIFIC_CASES:
            with self.subTest(source=source):
                smoke.check_scientific_payload(source, fixtures[source])
                smoke.check_scientific_payload(source, evaluate(source).to_dict())

    def test_numeric_precision_metadata_and_value_are_both_required(self):
        good = references()["N[Pi,30]"]
        mutations = []
        payload = deepcopy(good)
        payload["details"]["numeric_evaluations"][0]["requested_significant_digits"] = (
            20
        )
        mutations.append(payload)
        payload = deepcopy(good)
        payload["text"] = "3.14159265358979300000000000000"
        mutations.append(payload)
        payload = deepcopy(good)
        payload["text"] = "3.141592653589793"
        mutations.append(payload)
        payload = deepcopy(good)
        payload["exact"] = True
        mutations.append(payload)
        payload = deepcopy(good)
        payload["status"] = "evaluated"
        mutations.append(payload)
        payload = deepcopy(good)
        payload["text"] = "NaN"
        mutations.append(payload)
        for payload in mutations:
            with self.subTest(payload=payload), self.assertRaises(smoke.SmokeTestError):
                smoke.check_scientific_payload("N[Pi,30]", payload)

    def test_curvilinear_exact_values_require_domain_and_basis(self):
        for source in smoke.CURVILINEAR_REFERENCES:
            for field, bad in (("conditions", []), ("status", "evaluated"), ("details", {})):
                payload = deepcopy(references()[source])
                payload[field] = bad
                with self.subTest(source=source, field=field), self.assertRaises(smoke.SmokeTestError):
                    smoke.check_scientific_payload(source, payload)

    def test_exact_operations_reject_wrong_result_status_and_missing_fields(self):
        for field, bad in (
            ("text", "15"),
            ("status", "unresolved"),
            ("exact", False),
            ("details", []),
        ):
            payload = references()["Sum[n^2,{n,1,3}]"]
            payload[field] = bad
            with self.subTest(field=field), self.assertRaises(smoke.SmokeTestError):
                smoke.check_scientific_payload("Sum[n^2,{n,1,3}]", payload)
        with self.assertRaises(smoke.SmokeTestError):
            smoke.check_scientific_payload("Factor[x^2-1]", [])

    def test_original_domain_conditions_must_survive(self):
        for source in ("Together[1/x+1/y]", "Cancel[(x^2-1)/(x-1)]"):
            payload = references()[source]
            payload["conditions"] = []
            with self.subTest(source=source), self.assertRaises(smoke.SmokeTestError):
                smoke.check_scientific_payload(source, payload)

    def test_verified_status_cannot_replace_ode_and_initial_residuals(self):
        source = "DSolve[{D[y[x],x]==-2*y[x],y[0]==3},y[x],x]"
        for field, bad in (
            ("ode_residuals", ["1"]),
            ("initial_residuals", ["3"]),
            ("initial_defined", False),
            ("verification", "unverified"),
            ("initial_conditions", True),
        ):
            payload = references()[source]
            payload["details"][field] = bad
            with self.subTest(field=field), self.assertRaises(smoke.SmokeTestError):
                smoke.check_scientific_payload(source, payload)


class ScientificSmokeTests(unittest.TestCase):
    def test_scientific_mode_executes_all_scientific_json_checks(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "application.exe"
            executable.write_bytes(b"fixture")
            payloads = references()
            plot, svg = plot_fixture()

            def run(command, **options):
                self.assertEqual(options["timeout"], 7)
                self.assertEqual(options["env"], {"PATH": "system"})
                if len(command) == 1:
                    return subprocess.CompletedProcess(
                        command, 0, "3*x**2\nGoodbye", ""
                    )
                source = command[1]
                if source == "1/0":
                    return subprocess.CompletedProcess(
                        command, 2, "", "Error: division by zero"
                    )
                if source.startswith("Plot["):
                    Path(command[-1]).write_text(svg, encoding="utf-8")
                    result = plot
                elif source == "D[x^3,x]":
                    result = {"kind": "expression", "text": "3*x**2"}
                else:
                    self.assertEqual(command[2:], ["--json"])
                    result = payloads[source]
                return subprocess.CompletedProcess(command, 0, json.dumps(result), "")

            with (
                patch.object(
                    smoke, "isolated_environment", return_value={"PATH": "system"}
                ),
                patch.object(smoke.subprocess, "run", side_effect=run) as runner,
            ):
                checks = smoke.smoke_test(executable, timeout=7, scientific=True)
            self.assertEqual(len(checks), 82)
            self.assertEqual(runner.call_count, 82)
            self.assertEqual(checks[4:], [label for label, _ in smoke.SCIENTIFIC_CASES])

    def test_command_line_option_is_forwarded(self):
        with (
            patch.object(smoke, "smoke_test", return_value=["fixture"]) as execute,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(
                smoke.main(["application.exe", "--timeout", "8", "--scientific"]), 0
            )
        execute.assert_called_once_with(Path("application.exe"), 8.0, scientific=True, sessions=False)


if __name__ == "__main__":
    unittest.main()
