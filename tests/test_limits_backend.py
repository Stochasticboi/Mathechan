"""Analytic references and failure semantics for real-path limits."""

import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.limits import limit_expression


class LimitBackendTests(unittest.TestCase):
    def setUp(self):
        self.x = sp.Symbol("x")

    def test_removable_singularity_is_bilateral(self):
        result = limit_expression(sp.sin(self.x) / self.x, self.x, sp.S.Zero)
        self.assertEqual((result.value, result.status), (1, "evaluated"))
        self.assertEqual(set(result.details["sides"]), {"left", "right"})
        self.assertEqual(result.details["verification"], "not_checked")

    def test_odd_pole_has_no_bilateral_limit(self):
        result = limit_expression(1 / self.x, self.x, sp.S.Zero)
        self.assertEqual(result.status, "no_limit")
        self.assertIsInstance(result.value, sp.Limit)
        self.assertEqual(result.value.args[-1], sp.Symbol("+-"))
        self.assertEqual(result.details["sides"]["left"]["value"], "-oo")
        self.assertEqual(result.details["sides"]["right"]["value"], "oo")

    def test_even_pole_is_retained_divergent(self):
        result = limit_expression(1 / self.x**2, self.x, sp.S.Zero)
        self.assertEqual(result.status, "divergent")
        self.assertIsInstance(result.value, sp.Limit)
        self.assertEqual(result.details["extended_value"], "+oo")

    def test_one_sided_pole_signs(self):
        for direction, sign in (("Left", "-oo"), ("Right", "+oo")):
            with self.subTest(direction=direction):
                result = limit_expression(1 / self.x, self.x, sp.S.Zero, direction)
                self.assertEqual(result.status, "divergent")
                self.assertEqual(result.details["extended_value"], sign)

    def test_jump(self):
        result = limit_expression(sp.Abs(self.x) / self.x, self.x, sp.S.Zero)
        self.assertEqual(result.status, "no_limit")
        self.assertIsInstance(result.value, sp.Limit)

    def test_oscillation_is_not_an_interval_value(self):
        result = limit_expression(sp.sin(1 / self.x), self.x, sp.S.Zero)
        self.assertEqual(result.status, "no_limit")
        self.assertIsInstance(result.value, sp.Limit)
        self.assertIn("AccumBounds", result.details["sides"]["right"]["value"])

    def test_damped_oscillation(self):
        result = limit_expression(self.x * sp.sin(1 / self.x), self.x, sp.S.Zero)
        self.assertEqual((result.value, result.status), (0, "evaluated"))

    def test_principal_complex_values_on_negative_real_path(self):
        for expr, expected in ((sp.sqrt(self.x), sp.I), (sp.log(self.x), sp.I * sp.pi)):
            for direction in ("Both", "Left", "Right"):
                with self.subTest(expr=expr, direction=direction):
                    result = limit_expression(expr, self.x, -sp.S.One, direction)
                    self.assertEqual((result.value, result.status), (expected, "evaluated"))

    def test_infinity_is_determined_by_point(self):
        for point in (sp.oo, -sp.oo):
            result = limit_expression(1 / self.x, self.x, point)
            self.assertEqual((result.value, result.status), (0, "evaluated"))
            self.assertEqual(set(result.details["sides"]), {"infinity"})
            for direction in ("Left", "Right"):
                with self.assertRaises(ValueError):
                    limit_expression(self.x, self.x, point, direction)

    def test_unknown_parameter_branches_are_not_guessed(self):
        a = sp.Symbol("a")
        result = limit_expression(sp.exp(a * self.x), self.x, sp.oo)
        self.assertEqual(result.status, "unresolved")
        self.assertIsInstance(result.value, sp.Limit)

    def test_explicit_finite_parameter(self):
        a = sp.Symbol("a", finite=True)
        result = limit_expression(a + self.x, self.x, sp.S.Zero)
        self.assertEqual((result.value, result.status), (a, "evaluated"))

    def test_finite_parameter_with_unknown_sign_still_unresolved(self):
        a = sp.Symbol("a", real=True, finite=True)
        result = limit_expression(sp.exp(a * self.x), self.x, sp.oo)
        self.assertEqual(result.status, "unresolved")
        self.assertIsInstance(result.value, sp.Limit)

    def test_unknown_backend_piecewise_branches_stay_unresolved(self):
        a = sp.Symbol("a", real=True)
        branched = sp.Piecewise((1, a > 0), (0, True))
        with patch("mathechan.limits.sp.limit", return_value=branched):
            result = limit_expression(self.x, self.x, sp.S.Zero)
        self.assertEqual(result.status, "unresolved")

    def test_float_data_not_labeled_exact(self):
        result = limit_expression(self.x + sp.Float("0.1"), self.x, sp.S.Zero)
        self.assertEqual(result.status, "unverified")
        self.assertTrue(result.warnings)

    def test_undefined_function_stays_inert(self):
        result = limit_expression(sp.Function("f")(self.x), self.x, sp.S.Zero)
        self.assertEqual(result.status, "unresolved")
        self.assertIsInstance(result.value, sp.Limit)

    def test_backend_failure_is_an_unresolved_request(self):
        with patch("mathechan.limits.sp.limit", side_effect=NotImplementedError):
            result = limit_expression(self.x, self.x, sp.S.Zero)
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(len(result.details["sides"]), 2)

    def test_invalid_arguments(self):
        for variable, point, direction in (
            (self.x + 1, sp.S.Zero, "Both"),
            (self.x, sp.I, "Both"),
            (self.x, self.x, "Both"),
            (self.x, sp.nan, "Both"),
            (self.x, sp.S.Zero, "Up"),
        ):
            with self.subTest(variable=variable, point=point, direction=direction):
                with self.assertRaises(ValueError):
                    limit_expression(self.x, variable, point, direction)

    def test_structural_budget(self):
        expr = sum(sp.Symbol(f"a{i}", finite=True) for i in range(9)) + self.x
        with self.assertRaises(ValueError):
            limit_expression(expr, self.x, sp.S.Zero)


if __name__ == "__main__":
    unittest.main()
