"""Independent exact references for the bounded numerical polynomial solver."""

import json
import unittest
from unittest.mock import patch

import sympy as sp

from mathechan.numeric_solve import solve_polynomial_numerically


class NumericalPolynomialBackendTests(unittest.TestCase):
    def setUp(self):
        self.x = sp.Symbol("x")

    def test_exact_isolation_precedes_30_digit_real_approximations(self):
        outcome = solve_polynomial_numerically(self.x**2 - 2, self.x)
        values = sorted(outcome.value, key=float)
        self.assertEqual(outcome.status, "approximate")
        self.assertEqual(len(values), 2)
        self.assertLess(abs(values[1] - sp.sqrt(2).evalf(50)), sp.Rational(1, 10)**29)
        self.assertTrue(all(isinstance(value, sp.Float) for value in values))
        self.assertTrue(outcome.details["completeness"]["exact_isolation"])
        self.assertFalse(outcome.details["completeness"]["approximation_certified"])
        self.assertEqual(outcome.details["verification"], "normalized_residual_passed")
        self.assertEqual(outcome.details["multiplicities"], [1, 1])
        self.assertTrue(all(item["passed"] for item in outcome.details["residuals"]))
        json.dumps(outcome.details, allow_nan=False)

    def test_multiplicities_do_not_duplicate_finite_set_entries(self):
        outcome = solve_polynomial_numerically((self.x - 2)**3 * (self.x + 1)**2, self.x)
        self.assertEqual(len(outcome.value), 2)
        self.assertEqual(dict(zip(outcome.details["exact_roots"], outcome.details["multiplicities"])), {"-1": 2, "2": 3})
        self.assertTrue(all(isinstance(value, sp.Float) for value in outcome.value))

    def test_complex_roots_and_real_filter_are_classified_exactly(self):
        complex_result = solve_polynomial_numerically(self.x**2 + 1, self.x, precision=50)
        self.assertEqual(len(complex_result.value), 2)
        self.assertTrue(all(value.has(sp.Float) for value in complex_result.value))
        real_result = solve_polynomial_numerically(self.x**2 + 1, self.x, domain="Reals")
        self.assertIs(real_result.value, sp.S.EmptySet)
        self.assertEqual(real_result.status, "no_solution")
        mixed = solve_polynomial_numerically((self.x - 1)*(self.x**2 + 1), self.x, domain=sp.S.Reals)
        self.assertEqual(len(mixed.value), 1)
        self.assertEqual(next(iter(mixed.value)), sp.Float(1, 30))

    def test_original_rational_poles_are_excluded_before_rounding(self):
        outcome = solve_polynomial_numerically((self.x**2 - 1)/(self.x - 1), self.x)
        self.assertEqual(outcome.details["exact_roots"], ["-1"])
        self.assertEqual(next(iter(outcome.value)), sp.Float(-1, 30))
        excluded = solve_polynomial_numerically(self.x**2 - 2, self.x, restrictions=(self.x**2 - 2,))
        self.assertIs(excluded.value, sp.S.EmptySet)

    def test_requirements_and_assumptions_filter_exact_roots(self):
        outcome = solve_polynomial_numerically(self.x**2 - 2, self.x, requirements=(self.x > 0,))
        self.assertEqual(len(outcome.value), 1)
        self.assertGreater(next(iter(outcome.value)), 0)
        under_assumption = solve_polynomial_numerically(self.x**2 - 2, self.x, assumptions=self.x < 0)
        self.assertEqual(len(under_assumption.value), 1)
        self.assertLess(next(iter(under_assumption.value)), 0)

    def test_order_conditions_discard_complex_roots_without_aborting(self):
        outcome = solve_polynomial_numerically(self.x**4 - 1, self.x, assumptions=self.x > 0)
        self.assertEqual(outcome.value, sp.FiniteSet(sp.Float(1, 30)))
        empty = solve_polynomial_numerically(self.x**2 + 1, self.x, assumptions=self.x > 0)
        self.assertIs(empty.value, sp.S.EmptySet)

    def test_rounded_inequality_violations_are_flagged_but_exact_equalities_are_not(self):
        scale = sp.Integer(10)**30
        outcome = solve_polynomial_numerically(scale*self.x - (scale - 1), self.x, precision=10,
                                               assumptions=self.x < 1)
        self.assertEqual(outcome.status, "unverified")
        self.assertFalse(outcome.details["domain_at_approximation"])
        exact_condition = solve_polynomial_numerically(3*self.x - 1, self.x, precision=10,
                                                       requirements=(sp.Eq(self.x, sp.Rational(1, 3)),))
        self.assertEqual(exact_condition.status, "approximate")
        self.assertTrue(exact_condition.details["domain_at_approximation"])

    def test_negated_discrete_membership_is_not_falsely_rejected_after_rounding(self):
        condition = sp.Not(sp.Contains(self.x, sp.S.Integers))
        outcome = solve_polynomial_numerically(self.x**2 - 2, self.x, assumptions=condition)
        self.assertIn(outcome.status, {"approximate", "conditional"})
        self.assertEqual(len(outcome.value), 2)
        self.assertIsNot(outcome.details["domain_at_approximation"], False)

    def test_disjunction_cannot_be_made_true_by_ignoring_a_false_exact_equality(self):
        scale = sp.Integer(10)**30
        condition = sp.Or(sp.Eq(self.x, 0), self.x > 1)
        outcome = solve_polynomial_numerically(scale*self.x - (scale + 1), self.x,
                                               precision=10, assumptions=condition)
        self.assertEqual(outcome.status, "unverified")
        self.assertFalse(outcome.details["domain_at_approximation"])

    def test_undecided_conditions_retain_candidates_conditionally(self):
        a = sp.Symbol("a")
        outcome = solve_polynomial_numerically(self.x**2 - 2, self.x, restrictions=(a,), requirements=(a > 0,))
        self.assertEqual(len(outcome.value), 2)
        self.assertEqual(outcome.status, "conditional")
        self.assertTrue(outcome.conditions)
        self.assertFalse(outcome.details["completeness"]["conditions_decided"])

    def test_precision_and_input_scope_are_strict(self):
        for precision in (True, False, 9, 201, 15.0, sp.Rational(25, 2)):
            with self.subTest(precision=precision):
                self.assertRaises(ValueError, solve_polynomial_numerically, self.x**2 - 2, self.x, precision)
        a = sp.Symbol("a")
        for expression in (sp.sin(self.x), self.x + a, self.x + sp.pi, self.x**33 - 1):
            with self.subTest(expression=expression):
                self.assertRaises(ValueError, solve_polynomial_numerically, expression, self.x)
        self.assertRaises(ValueError, solve_polynomial_numerically, self.x - 1, self.x + 1)
        self.assertRaises(ValueError, solve_polynomial_numerically, self.x - 1, self.x, domain="Integers")
        for precision in (10, 200):
            result = solve_polynomial_numerically(self.x - 1, self.x, precision)
            self.assertEqual(result.details["requested_significant_digits"], precision)

    def test_preflight_rejects_excessive_expansion_before_isolation(self):
        expression = sp.Pow(sp.Add(self.x, 1, 2*self.x**2, evaluate=False), 100, evaluate=False)
        with patch("sympy.Poly.all_roots", side_effect=AssertionError("should not isolate")):
            self.assertRaises(ValueError, solve_polynomial_numerically, expression, self.x)

    def test_identity_and_constant_contradiction_keep_exact_sets(self):
        identity = solve_polynomial_numerically(sp.Eq(0, 0, evaluate=False), self.x, domain="Reals")
        self.assertIs(identity.value, sp.S.Reals)
        self.assertEqual(identity.status, "solved")
        excluded = solve_polynomial_numerically(sp.Integer(0), self.x, restrictions=(self.x - 1,))
        self.assertFalse(excluded.value.contains(1))
        self.assertTrue(excluded.value.contains(2))
        self.assertFalse(excluded.value.has(sp.ConditionSet))
        conditional = solve_polynomial_numerically(sp.Integer(0), self.x, requirements=(self.x > 0,))
        self.assertTrue(conditional.value.has(sp.ConditionSet))
        self.assertEqual(conditional.status, "unresolved")
        contradiction = solve_polynomial_numerically(sp.Integer(2), self.x)
        self.assertIs(contradiction.value, sp.S.EmptySet)
        self.assertEqual(contradiction.status, "no_solution")

    def test_residuals_report_original_equation_and_normalized_polynomial(self):
        outcome = solve_polynomial_numerically((self.x**2 - 2)/(self.x + 3), self.x, precision=40)
        for item in outcome.details["residuals"]:
            self.assertTrue(item["original_residual_finite"])
            self.assertIn("original_equation_residual", item)
            self.assertIn("polynomial_residual", item)
            self.assertLessEqual(sp.sympify(item["normalized_backward_error"]), sp.sympify(item["threshold"]))
        self.assertTrue(any("no es una cota" in item for item in outcome.warnings))

    def test_rounded_root_at_original_pole_is_not_reported_as_success(self):
        scale = sp.Integer(10)**30
        expression = (scale*self.x - (scale + 1))/(self.x - 1)
        outcome = solve_polynomial_numerically(expression, self.x, precision=10)
        self.assertEqual(outcome.status, "unverified")
        self.assertFalse(outcome.details["residuals"][0]["original_residual_finite"])
        self.assertTrue(any("polo" in item for item in outcome.warnings))

    def test_distinct_exact_roots_collapsing_under_rounding_are_flagged(self):
        scale = sp.Integer(10)**30
        outcome = solve_polynomial_numerically((self.x - 1)*(scale*self.x - (scale + 1)), self.x, precision=10)
        self.assertEqual(len(outcome.details["exact_roots"]), 2)
        self.assertEqual(len(outcome.value), 1)
        self.assertEqual(outcome.status, "unverified")
        self.assertFalse(outcome.details["completeness"]["distinct_approximations"])

    def test_cancelled_exclusion_is_rechecked_at_the_rounded_point(self):
        exact_root = 1 + sp.Rational(1, 10)**30
        outcome = solve_polynomial_numerically(self.x - exact_root, self.x, precision=10,
                                               restrictions=(self.x - 1,))
        self.assertEqual(outcome.status, "unverified")
        self.assertFalse(outcome.details["domain_at_approximation"])
        self.assertFalse(outcome.details["residuals"][0]["domain_at_approximation"])
        self.assertTrue(any("exclusión original" in item for item in outcome.warnings))
        sufficient = solve_polynomial_numerically(self.x - exact_root, self.x, precision=50,
                                                  restrictions=(self.x - 1,))
        self.assertEqual(sufficient.status, "approximate")
        self.assertTrue(sufficient.details["domain_at_approximation"])

    def test_backend_failure_cannot_return_partial_success(self):
        with patch("sympy.Poly.all_roots", side_effect=NotImplementedError("isolation failed")):
            self.assertRaises(ValueError, solve_polynomial_numerically, self.x**2 - 2, self.x)
        with patch("mathechan.numeric_solve._approximate", side_effect=[sp.Float(-1, 30), ValueError("second failed")]):
            self.assertRaises(ValueError, solve_polynomial_numerically, self.x**2 - 1, self.x)


if __name__ == "__main__":
    unittest.main()
