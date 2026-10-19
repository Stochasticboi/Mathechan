"""Casos exactos, contrato de precedencia y rechazo de entradas no admitidas."""

import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from mathechan import MathechanError, evaluate


class KernelTests(unittest.TestCase):
    def test_exact_arithmetic(self):
        for source, expected in (("1/3+1/6", "1/2"), ("0.1+0.2", "3/10"), ("2^10", "1024")):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_precedence(self):
        for source, expected in (("-x^2", "-x**2"), ("(-x)^2", "x**2"),
                                 ("x^2^3", "x**8"), ("2^-3", "1/8"),
                                 ("1-2-3", "-4"), ("8/4/2", "1")):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_symbolic_functions(self):
        for source, expected in (("D[x^3,x]", "3*x**2"), ("Sin[Pi/2]", "1"),
                                 ("Simplify[Sin[x]^2+Cos[x]^2]", "1"),
                                 ("Expand[(x+1)^2]", "x**2 + 2*x + 1"),
                                 ("Log[E]", "1"), ("Sqrt[4]", "2")):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).text, expected)

    def test_rejects_invalid_and_arbitrary_code(self):
        for source in ("", "x=2", "__import__('os')", "x.__class__", "open[x]", "Sin[]",
                       "Sin[x,y]", "D[x,2]", "D[x]", "2x", "1/0", "Log[0]",
                       "Plot[Sin[x],{Pi,0,1}]", "2^1001", "(x", "x;1", "x[1]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)

    def test_plot_and_svg(self):
        result = evaluate("Plot[Sin[x],{x,0,Pi}]")
        self.assertEqual(result.kind, "plot")
        self.assertEqual(len(result.points), 201)
        self.assertAlmostEqual(result.points[100][1], 1.0)
        self.assertEqual(ET.fromstring(result.svg).tag, "{http://www.w3.org/2000/svg}svg")
        json.dumps(result.to_dict(), allow_nan=False)

    def test_constant_plot(self):
        self.assertEqual(evaluate("Plot[2,{x,-1,1}]").points[0][1], 2.0)

    def test_large_finite_plot_range_serializes_as_strict_json(self):
        result = evaluate("Plot[2,{x,0,10^307}]")
        self.assertEqual(len(result.points), 201)
        self.assertEqual(result.points[0][0], 0.0)
        self.assertEqual(result.points[-1][0], 1e307)
        self.assertTrue(all(math.isfinite(value) for point in result.points for value in point))
        json.dumps(result.to_dict(), allow_nan=False)
        self.assertNotIn("inf", result.svg.lower())

    def test_large_finite_plot_value_has_finite_svg_coordinates(self):
        result = evaluate("Plot[10^308,{x,0,1}]")
        json.dumps(result.to_dict(), allow_nan=False)
        svg = ET.fromstring(result.svg)
        polyline = svg.find("{http://www.w3.org/2000/svg}polyline")
        self.assertIsNotNone(polyline)
        coordinates = [tuple(map(float, pair.split(","))) for pair in polyline.attrib["points"].split()]
        self.assertEqual(len(coordinates), 201)
        self.assertTrue(all(math.isfinite(value) for point in coordinates for value in point))
        self.assertAlmostEqual(coordinates[100][1], 160.0)
        self.assertNotIn("inf", result.svg.lower())

    def test_plot_domain_and_range_errors(self):
        for source in ("Plot[1/x,{x,-1,1}]", "Plot[Sqrt[x],{x,-1,1}]", "Plot[x,{x,1,0}]",
                       "Plot[x+y,{x,0,1}]", "Plot[x,{x,0,y}]", "Plot[x,{x,0}]",
                       "Plot[x,x]", "Plot[x,{x,1,1}]", "Plot[x,{x,0,10^1000}]"):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)

    def test_cli_and_svg_export(self):
        expression = subprocess.run([sys.executable, "-m", "mathechan", "D[x^3,x]", "--json"],
                                    capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(expression.stdout)["text"], "3*x**2")
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "plot.svg"
            subprocess.run([sys.executable, "-m", "mathechan", "--demo", "--output", str(destination)],
                           capture_output=True, text=True, check=True)
            ET.parse(destination)


if __name__ == "__main__":
    unittest.main()
