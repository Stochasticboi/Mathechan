"""Track explicit nonzero conditions before cancellation, without global domains."""

import contextlib
import io
import json
import unittest

from mathechan import MathechanError, evaluate
from mathechan.__main__ import main


class ExplicitDomainTests(unittest.TestCase):
    def test_cancelled_division_keeps_nonzero_condition(self):
        result = evaluate("x/x")
        self.assertEqual(result.text, "1")
        self.assertEqual(result.input, "1")
        self.assertEqual(result.conditions, ("(x) != 0",))
        self.assertTrue(result.warnings)
        self.assertEqual(result.to_dict()["conditions"], ["(x) != 0"])

    def test_polynomial_cancellation_and_explicit_simplification(self):
        for source in ("(x^2-1)/(x-1)", "Simplify[(x^2-1)/(x-1)]"):
            with self.subTest(source=source):
                result = evaluate(source)
                self.assertEqual(result.conditions, ("((-1+x)) != 0",))
        self.assertEqual(evaluate("Simplify[(x^2-1)/(x-1)]").text, "x + 1")

    def test_negative_powers_and_nested_divisions(self):
        for source in ("x^(-2)", "0/x", "1/(x/x)", "D[x/x,x]", "(x^(-1))^0"):
            with self.subTest(source=source):
                self.assertEqual(evaluate(source).conditions, ("(x) != 0",))

    def test_repeated_conditions_are_unique_and_constants_need_no_condition(self):
        self.assertEqual(evaluate("x/x+x^(-1)").conditions, ("(x) != 0",))
        self.assertEqual(evaluate("x/2+2^(-1)").conditions, ())

    def test_plot_rejects_original_holes_even_after_cancellation(self):
        for source in (
            "Plot[x/x,{x,-1,1}]", "Plot[0/x,{x,-1,1}]",
            "Plot[(x^2-1)/(x-1),{x,0,2}]",
            "Plot[Sin[x]/Sin[x],{x,0,1}]",
            "Plot[x^(-1)*x,{x,-1,1}]",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(MathechanError, "denominador original es cero"):
                    evaluate(source)

    def test_plot_preserves_conditions_on_valid_range(self):
        result = evaluate("Plot[x/x,{x,1,2}]")
        self.assertEqual(result.conditions, ("(x) != 0",))
        self.assertTrue(all(y == 1.0 for _, y in result.points))

    def test_plot_checks_symbolically_exact_endpoints_before_float_conversion(self):
        for source in (
            "Plot[1/Sin[x],{x,1,Pi}]",
            "Plot[Sin[x]^(-1)*Sin[x],{x,1,Pi}]",
            "Plot[1/(x-Log[2]),{x,Log[2],1}]",
            "Plot[(x-Log[2])^(-1)*(x-Log[2]),{x,Log[2],1}]",
        ):
            with self.subTest(source=source):
                with self.assertRaisesRegex(MathechanError, "denominador original es cero"):
                    evaluate(source)

    def test_plot_does_not_silently_accept_unbound_cancelled_parameters(self):
        with self.assertRaisesRegex(MathechanError, "variables adicionales"):
            evaluate("Plot[y/y,{x,1,2}]")

    def test_input_mode_sends_conditions_to_stderr_without_polluting_stdout(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main(["x/x", "--input"])
        self.assertEqual(status, 0)
        self.assertEqual(output.getvalue(), "1\n")
        self.assertIn("(x) != 0", errors.getvalue())
        self.assertIn("por separado", errors.getvalue())

    def test_cli_json_has_conditions_and_no_side_channel_messages(self):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main(["x/x", "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["conditions"], ["(x) != 0"])
        self.assertEqual(errors.getvalue(), "")

    def test_plain_cli_shows_conditions(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["x/x"]), 0)
        self.assertIn("Condiciones / Conditions: (x) != 0", output.getvalue())


if __name__ == "__main__":
    unittest.main()

