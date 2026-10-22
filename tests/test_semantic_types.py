"""Containers and diagnostics preserve exact values and explicit limitations."""

import json
import unittest

import sympy as sp

from mathechan import MathechanError, Session, evaluate
from mathechan.kernel import Parser, build
from mathechan.semantic_types import HeldExpression


class SemanticContainerTests(unittest.TestCase):
    def test_vector_is_an_immutable_column_and_matrix_is_rectangular(self):
        vector = build(Parser("Vector[{1,1/3,x}]").parse())
        matrix = build(Parser("Matrix[{{1,2},{3,4}}]").parse())
        self.assertIsInstance(vector, sp.ImmutableMatrix)
        self.assertEqual(vector.shape, (3, 1))
        self.assertEqual(vector[1], sp.Rational(1, 3))
        self.assertEqual(matrix, sp.ImmutableMatrix([[1, 2], [3, 4]]))
        self.assertEqual(evaluate("Matrix[{{1,2},{3,4}}]").kind, "matrix")
        self.assertRaises(TypeError, matrix.__setitem__, (0, 0), 9)

    def test_entries_use_session_values_and_preserve_denominator_conditions(self):
        session = Session()
        session.evaluate("k=3")
        result = session.evaluate("Matrix[{{k,x/x}}]")
        self.assertIn("3", result.text)
        self.assertTrue(result.conditions)
        self.assertEqual(session.evaluate("k").text, "3")

    def test_containers_validate_shape_elements_and_bound(self):
        too_many = "Matrix[{" + ",".join("{" + ",".join(["1"] * 9) + "}" for _ in range(8)) + "}]"
        for source in (
            "Vector[{}]", "Vector[1]", "Vector[{{1}}]", "Matrix[{}]",
            "Matrix[{{}}]", "Matrix[{1,2}]", "Matrix[{{1},{2,3}}]",
            "Matrix[{{1==1}}]", "Vector[{Hold[x]}]", too_many,
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)
        allowed = "Matrix[{" + ",".join("{" + ",".join(["1"] * 8) + "}" for _ in range(8)) + "}]"
        self.assertEqual(build(Parser(allowed).parse()).shape, (8, 8))


class HeldSyntaxTests(unittest.TestCase):
    def test_hold_preserves_syntax_without_arithmetic_or_function_evaluation(self):
        for source in ("Hold[1/0]", "Hold[Unknown[1]]", "Hold[1+2]", "Hold[Log[0]]"):
            with self.subTest(source=source):
                value = build(Parser(source).parse())
                self.assertIsInstance(value, HeldExpression)
                result = evaluate(source)
                self.assertEqual(result.kind, "held")
                self.assertTrue(result.text.startswith("Hold["))
                self.assertFalse(result.conditions)
                json.dumps(result.to_dict(), allow_nan=False)

    def test_release_uses_the_current_lexical_context(self):
        session = Session()
        session.evaluate("x=3")
        held = session.evaluate("Hold[x+2]")
        self.assertIn("x", held.text)
        self.assertEqual(session.evaluate("ReleaseHold[Hold[x+2]]").text, "5")
        self.assertEqual(evaluate("ReleaseHold[Hold[1+2]]").text, "3")
        self.assertEqual(evaluate("ReleaseHold[Hold[Hold[1+2]]]").kind, "held")

    def test_release_enforces_normal_errors_and_hold_is_not_a_scalar(self):
        for source in (
            "Hold[]", "Hold[x,y]", "ReleaseHold[3]", "ReleaseHold[]",
            "ReleaseHold[Hold[1/0]]", "ReleaseHold[Hold[Unknown[1]]]", "1+Hold[x]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)


class NumericalDiagnosticTests(unittest.TestCase):
    def test_display_changes_presentation_but_keeps_the_exact_value(self):
        value = build(Parser("Display[1/3,5]").parse())
        self.assertEqual(value, sp.Rational(1, 3))
        result = evaluate("Display[1/3,5]")
        self.assertTrue(result.exact)
        self.assertEqual(result.details["presentation"]["digits"], 5)
        self.assertEqual(result.text, "0.33333")
        self.assertEqual(evaluate("3*Display[1/3,5]").text, "1")
        session = Session()
        session.evaluate("x=Display[1/3,5]")
        self.assertEqual(session.evaluate("3*x").text, "1")

    def test_numeric_error_is_a_nonnegative_estimate_not_a_certified_bound(self):
        result = evaluate("NumericError[Pi,15]")
        metadata = result.details["numeric_error"]
        self.assertFalse(metadata["certified_bound"])
        self.assertEqual(metadata["digits"], 15)
        self.assertEqual(metadata["comparison_digits"], 25)
        self.assertGreater(sp.sympify(metadata["absolute_difference"]), 0)
        self.assertTrue(any("estimación" in item for item in result.warnings))
        self.assertEqual(evaluate("NumericError[1,15]").text, "0")
        approximate = evaluate("NumericError[N[Pi,10],20]")
        self.assertTrue(any("dígitos perdidos" in item for item in approximate.warnings))

    def test_precision_arguments_and_error_inputs_are_bounded(self):
        for source in (
            "Display[Pi,0]", "Display[Pi,1001]", "Display[Pi,1/2]",
            "NumericError[Pi,991]", "NumericError[x,15]", "NumericError[Infinity,15]",
            "Display[Vector[{1}],5]", "NumericError[1]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)


class PartialFunctionDomainTests(unittest.TestCase):
    def test_log_preserves_nonzero_condition_without_assuming_reality(self):
        result = evaluate("Log[x]-Log[x]")
        self.assertEqual(result.text, "0")
        self.assertTrue(any("x" in item and "!= 0" in item for item in result.conditions))
        self.assertRaises(MathechanError, evaluate, "Log[0]")
        self.assertIn("I", evaluate("Log[-1]").text)

    def test_complex_principal_branches_and_inverse_singularities(self):
        self.assertEqual(evaluate("Sqrt[-1]").text, "I")
        self.assertTrue(any("rama principal" in item for item in evaluate("Sqrt[x]").warnings))
        self.assertEqual(build(Parser("ArcSin[1]").parse()), sp.pi / 2)
        self.assertEqual(build(Parser("ArcCos[1]").parse()), 0)
        self.assertEqual(build(Parser("ArcTan[1]").parse()), sp.pi / 4)
        self.assertRaises(MathechanError, evaluate, "ArcTan[Sqrt[-1]]")
        self.assertTrue(evaluate("ArcTan[x]").conditions)

    def test_gamma_poles_are_excluded_and_symbolic_tracking_is_partial(self):
        self.assertEqual(evaluate("Gamma[5]").text, "24")
        self.assertRaises(MathechanError, evaluate, "Gamma[0]")
        self.assertRaises(MathechanError, evaluate, "Gamma[-2]")
        result = evaluate("Gamma[x]")
        self.assertTrue(any("entero no positivo" in item for item in result.conditions))
        self.assertTrue(any("parcial" in item for item in result.warnings))
        self.assertEqual(result.status, "conditional")
        self.assertFalse(evaluate("Gamma[1/2]").conditions)

    def test_substitution_rechecks_gamma_poles_after_cancellation(self):
        for source in (
            "Substitute[Gamma[x],x,0]", "Substitute[Gamma[x]/Gamma[x],x,-1]",
            "Substitute[Gamma[x]-Gamma[x],x,0]",
        ):
            with self.subTest(source=source):
                self.assertRaises(MathechanError, evaluate, source)
        self.assertEqual(evaluate("Substitute[Gamma[x]/Gamma[x],x,2]").text, "1")


if __name__ == "__main__":
    unittest.main()
