"""Scientific examples and failure contracts for local series expansions."""

import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.series_ops import series_expression, series_parameter_exclusions


class SeriesOperationsTests(unittest.TestCase):
    def setUp(self):
        self.x = sp.Symbol("x")

    def test_elementary_maclaurin_retains_order(self):
        x = self.x
        cases = (
            (sp.sin(x), x - x**3 / 6),
            (sp.cos(x), 1 - x**2 / 2),
            (sp.exp(x), 1 + x + x**2 / 2 + x**3 / 6),
            (sp.log(1+x), x - x**2 / 2 + x**3 / 3),
        )
        for expression, expected in cases:
            with self.subTest(expression=expression):
                outcome = series_expression(expression, x, sp.S.Zero, 4)
                self.assertEqual(outcome.value.removeO(), expected)
                self.assertEqual(outcome.value.getO(), sp.Order(x**4, (x, 0)))
                self.assertEqual(outcome.status, "series")
                self.assertFalse(outcome.details["global_equality"])
                self.assertFalse(outcome.details["certified_numeric_error"])

    def test_shifted_center(self):
        x = self.x
        outcome = series_expression(sp.exp(x-2), x, sp.Integer(2), 3)
        self.assertEqual(sp.expand(outcome.value.removeO() - (1+(x-2)+(x-2)**2/2)), 0)
        self.assertEqual(outcome.value.getO(), sp.Order((x-2)**3, (x, 2)))

    def test_exact_polynomial(self):
        outcome = series_expression(self.x**2+1, self.x, sp.S.Zero, 4)
        self.assertEqual(outcome.status, "evaluated")
        self.assertTrue(outcome.details["global_equality"])
        self.assertEqual(outcome.details["remainder"], [])

    def test_laurent_and_fractional_power(self):
        x = self.x
        outcome = series_expression(sp.exp(x)/x**2, x, sp.S.Zero, 3)
        self.assertEqual(outcome.value.getO(), sp.Order(x**3))
        self.assertEqual(sp.expand(outcome.value.removeO()), x**2/24+x/6+sp.Rational(1,2)+1/x+1/x**2)
        self.assertEqual(series_expression(sp.sqrt(x), x, sp.S.Zero, 3).value, sp.sqrt(x))

    def test_left_side_branch(self):
        x = self.x
        right = series_expression(sp.Abs(x), x, sp.S.Zero, 3)
        left = series_expression(sp.Abs(x), x, sp.S.Zero, 3, "Left")
        self.assertEqual(right.value, x)
        self.assertEqual(left.value, -x)
        self.assertEqual(left.details["direction"], "Left")
        for branch in (right, left):
            self.assertFalse(branch.details["global_equality"])
            self.assertTrue(branch.details["local_identity_only"])
            self.assertEqual(branch.status, "conditional")

    def test_finite_lateral_identity_need_not_hold_on_entire_half_axis(self):
        x = self.x
        outcome = series_expression(sp.Abs(x-1), x, sp.S.Zero, 3)
        self.assertEqual(outcome.value, 1-x)
        self.assertFalse(outcome.details["global_equality"])
        self.assertTrue(outcome.details["local_identity_only"])
        self.assertEqual(outcome.status, "conditional")
        self.assertNotEqual(outcome.value.subs(x, 2), sp.Abs(x-1).subs(x, 2))

    def test_infinity_expansion(self):
        x = self.x
        for point in (sp.oo, -sp.oo):
            outcome = series_expression(1/(x+1), x, point, 4)
            self.assertEqual(outcome.value.removeO(), 1/x-1/x**2+1/x**3)
            self.assertEqual(outcome.value.getO(), sp.Order(x**-4, (x, point)))
            self.assertEqual(outcome.details["point"], str(point))

    def test_complex_values_along_real_path(self):
        x = self.x
        outcome = series_expression(sp.exp(sp.I*x), x, sp.S.Zero, 3)
        self.assertEqual(outcome.value.removeO(), 1+sp.I*x-x**2/2)
        self.assertEqual(outcome.details["path"], "real")

    def test_parameter_pole_exposes_missing_case(self):
        x, a = self.x, sp.Symbol("a")
        outcome = series_expression(1/(x+a), x, sp.S.Zero, 3)
        self.assertTrue(any("Ne(a, 0)" in item for item in outcome.conditions))
        self.assertFalse(outcome.details["parameter_branches_complete"])
        self.assertEqual(series_expression(1/x, x, sp.S.Zero, 3).value, 1/x)

    def test_parameter_is_not_assumed_positive(self):
        x, a = self.x, sp.Symbol("a")
        outcome = series_expression(sp.exp(a*x), x, sp.S.Zero, 3)
        self.assertEqual(outcome.value.removeO(), 1+a*x+a**2*x**2/2)
        self.assertFalse(any("positive" in item or "> 0" in item for item in outcome.conditions))

    def test_low_order_singular_coefficients_keep_parameter_exclusion(self):
        x, a = self.x, sp.Symbol("a")
        for expression in (sp.log(a+x), sp.sqrt(a+x), sp.exp(1/(a+x))):
            with self.subTest(expression=expression):
                outcome = series_expression(expression, x, sp.S.Zero, 1)
                self.assertTrue(any("Ne(a, 0)" in item for item in outcome.conditions))

    def test_parameter_degeneracy_hidden_in_remainder_is_not_lost(self):
        x, a = self.x, sp.Symbol("a")
        expression = sp.sqrt(a+x)-sp.sqrt(a)
        outcome = series_expression(expression, x, sp.S.Zero, 1)
        self.assertEqual(outcome.value, sp.Order(x))
        self.assertTrue(any("Ne(a, 0)" in item for item in outcome.conditions))
        self.assertEqual(series_parameter_exclusions(expression, x, sp.S.Zero), (a,))

    def test_infinity_parameter_dominant_balance_requires_nonzero_leading_term(self):
        x, a = self.x, sp.Symbol("a")
        self.assertEqual(series_parameter_exclusions(sp.sqrt(a*x*x+x), x, sp.oo), (a,))

    def test_explicit_singular_center_remains_available_for_puiseux_expansion(self):
        x = self.x
        self.assertEqual(series_parameter_exclusions(sp.sqrt(x), x, sp.S.Zero), ())
        self.assertEqual(series_expression(sp.sqrt(x), x, sp.S.Zero, 3).value, sp.sqrt(x))

    def test_unspecified_function_requires_regularity(self):
        x = self.x
        outcome = series_expression(sp.Function("f")(x), x, sp.S.Zero, 3)
        self.assertEqual(outcome.status, "series")
        self.assertTrue(any("regularidad" in item for item in outcome.conditions))

    def test_essential_singularity_and_failed_backend_stay_unresolved(self):
        x = self.x
        outcome = series_expression(sp.exp(1/x), x, sp.S.Zero, 4)
        self.assertEqual(outcome.status, "unresolved")
        self.assertEqual(outcome.value.func.__name__, "Series")
        outcome = series_expression(sp.sin(x), x, sp.oo, 4)
        self.assertEqual(outcome.status, "unresolved")
        with patch("mathechan.series_ops.sp.series", side_effect=NotImplementedError):
            self.assertEqual(series_expression(sp.exp(x), x, sp.S.Zero, 3).status, "unresolved")

    def test_flat_function_does_not_become_global_zero(self):
        outcome = series_expression(sp.exp(-1/self.x), self.x, sp.S.Zero, 4)
        self.assertEqual(outcome.status, "series")
        self.assertEqual(outcome.value, sp.Order(self.x**4))
        self.assertFalse(outcome.details["global_equality"])

    def test_invalid_inputs_and_budgets_reject_before_backend(self):
        x = self.x
        requests = [(sp.exp(x), x, sp.S.Zero, n) for n in (0, -1, 33, True, 2.0, sp.Rational(3,2))]
        requests += [
            (sp.exp(x), x+1, sp.S.Zero, 3),
            (sp.exp(x), x, sp.I, 3),
            (sp.exp(x), x, x, 3),
            (sp.oo, x, sp.S.Zero, 3),
            (sp.Eq(x, 1), x, sp.S.Zero, 3),
            (sum(sp.Symbol(f"a{i}") for i in range(9)), x, sp.S.Zero, 3),
            (sum(sp.sin(x+i) for i in range(150)), x, sp.S.Zero, 3),
        ]
        with patch("mathechan.series_ops.sp.series") as backend:
            for request in requests:
                with self.subTest(request=request), self.assertRaises(ValueError):
                    series_expression(*request)
            with self.assertRaises(ValueError):
                series_expression(sp.exp(x), x, sp.S.Zero, 3, "Both")
            backend.assert_not_called()


if __name__ == "__main__":
    unittest.main()
