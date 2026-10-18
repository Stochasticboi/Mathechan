"""Results keep their legacy display and provide only verified reusable input."""

import contextlib
import io
import json
import unittest

import sympy as sp

from mathechan import MathechanError, evaluate
from mathechan.__main__ import main
from mathechan.kernel import Parser, build
from mathechan.printer import expression_input


class ReusableResultTests(unittest.TestCase):
    def test_imaginary_constant_is_distinct_from_generic_symbol(self):
        imaginary = evaluate("Sqrt[-1]")
        symbol = evaluate("I")
        self.assertEqual(imaginary.text, "I")
        self.assertEqual(symbol.text, "I")
        self.assertEqual(imaginary.input, "Sqrt[-1]")
        self.assertEqual(symbol.input, "I")
        self.assertEqual(evaluate(imaginary.input + "^2").text, "-1")
        self.assertEqual(evaluate(symbol.input + "^2").text, "I**2")

    def test_supported_results_roundtrip_structurally(self):
        sources = (
            "Pi", "E", "pi", "I", "1/3", "-2/3", "0.1+0.2", "-x^2",
            "x^2^3", "x+y+1", "3*x*y", "Sqrt[x]", "(-1)^(1/3)",
            "Sin[x]", "Cos[x]", "Exp[x]", "Log[x]",
            "D[x^x,x]", "D[Exp[-x^2],x]", "Expand[(x+1)^3]",
            "Exp[Sqrt[-1]*x]",
        )
        for source in sources:
            with self.subTest(source=source):
                result = evaluate(source)
                self.assertIsNotNone(result.input)
                original = build(Parser(source).parse())
                restored = build(Parser(result.input).parse())
                self.assertEqual(restored, original)
                self.assertEqual(evaluate(result.input).text, result.text)

    def test_rejects_result_functions_outside_language(self):
        result = evaluate("Simplify[Sin[x]/Cos[x]]")
        self.assertEqual(result.text, "tan(x)")
        self.assertIsNone(result.input)
        self.assertTrue(result.warnings)

    def test_limits_do_not_turn_valid_results_into_invalid_input(self):
        for source in ("2^1000", "Expand[(x+1)^35]", "Exp[1001*Log[x]]"):
            with self.subTest(source=source):
                result = evaluate(source)
                self.assertIsNone(result.input)
                self.assertTrue(result.text)
                self.assertTrue(result.warnings)

    def test_printer_rejects_unsafe_names_and_unencodable_assumptions(self):
        for symbol in (sp.Symbol("x;open"), sp.Symbol("Pi"),
                       sp.Symbol("x", positive=True)):
            with self.subTest(symbol=repr(symbol)):
                self.assertIsNone(expression_input(symbol))
        self.assertRaises(MathechanError, evaluate, "__import__('os')")
        self.assertIsNone(expression_input(sp.Float("0.1")))

    def test_json_fields_are_additive_and_serializable(self):
        payload = evaluate("Sqrt[-1]").to_dict()
        self.assertEqual(payload["kind"], "expression")
        self.assertEqual(payload["text"], "I")
        self.assertEqual(payload["input"], "Sqrt[-1]")
        self.assertEqual(payload["conditions"], [])
        self.assertEqual(payload["warnings"], [])
        json.dumps(payload, allow_nan=False)

    def test_plot_reuses_validated_original_source(self):
        source = "Plot[Sin[x],{x,0,1}]"
        result = evaluate(source)
        self.assertEqual(result.input, source)
        restored = evaluate(result.input)
        self.assertEqual(restored.points, result.points)

    def test_cli_input_mode_prints_only_executable_expression(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main(["Sqrt[-1]", "--input"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "Sqrt[-1]\n")
        self.assertEqual(errors.getvalue(), "")

    def test_cli_input_mode_reports_unrepresentable_result_without_partial_output(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main(["2^1000", "--input"])
        self.assertEqual(status, 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("entrada reutilizable", errors.getvalue())

    def test_cli_json_and_input_modes_are_exclusive(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                main(["x", "--json", "--input"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()

